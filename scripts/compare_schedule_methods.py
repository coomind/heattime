"""Offline, equal-constraint comparison of frozen CP-SAT proposals and existing greedy fallback.

Does not change the app, settings, policy, stored replay rankings, or snapshots.
Bootstrap --source-sessions only from the previously generated local replay files.
Subsequent runs rebuild observation inputs and validate the committed frozen solutions.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.engine.settings import EngineSettings
from backend.repository import Repository
from backend.schedule.models import ScheduleSettings
from backend.schedule.optimizer import Candidate, heat_score, optimize, validate
from backend.schedule.recommend import recommend
from backend.service import Service
from backend.weather.asos_samples import load_dataset

EVIDENCE = ROOT / "docs/competition-evidence"
LEDGER = EVIDENCE / "frozen-solutions.json"
INPUT_FIELDS = ("tournament", "matches", "venues", "weather", "risks", "policy", "engine_settings", "schedule_settings")
INPUT_DIGEST_SCHEMA = "comparison-input-v2-float6-derived-input-hash"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def canonical_input(value):
    """Comparison precision only; never round the engine or stored evidence."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite comparison input")
        result = round(value, 6)
        return 0.0 if result == 0 else result
    if isinstance(value, dict):
        return {key: canonical_input(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical_input(item) for item in value]
    return value


def input_digest(session):
    inputs = canonical_input({key: session[key] for key in INPUT_FIELDS})
    # The engine's audit hash derives from unrounded inputs and can also differ
    # across platforms. Re-derive its redundant comparison representation from
    # the full canonical inputs; retain every physical input and risk value.
    # Captured audit hashes / byte-level artifact hashes remain unchanged.
    for risk in inputs["risks"]:
        if "inputs_hash" not in risk or "inputs" not in risk:
            raise ValueError("Missing risk input provenance")
        risk["inputs_hash"] = digest(risk["inputs"])
    return digest({"schema": INPUT_DIGEST_SCHEMA, "inputs": inputs})


def candidates(rows):
    return [Candidate(**{**row, "start": datetime.fromisoformat(row["start"]), "end": datetime.fromisoformat(row["end"]),
                         "cooling_times": [datetime.fromisoformat(time) for time in row["cooling_times"]]}) for row in rows]


def bootstrap(directory):
    original = json.loads((ROOT / "docs/real-data/replay-results.json").read_text(encoding="utf-8"))
    rows = []
    for row in original["days"]:
        session = json.loads((Path(directory) / (row["date"] + ".json")).read_text(encoding="utf-8"))
        proposal = session["proposal"]
        if session["data_origin"] != "kma_observed" or session["tournament"]["date_start"] != row["date"]:
            raise ValueError("Frozen session origin/date mismatch")
        if (len(proposal["assignments"]), proposal["postponed_count"], proposal["original_heat_score"], proposal["proposed_heat_score"], proposal["solver"]) != (
                row["assigned"], row["postponed"], row["original_heat"], row["proposed_heat"], row["solver"]):
            raise ValueError("Frozen proposal differs from published replay evidence")
        rows.append({"date": row["date"], "input_sha256": input_digest(session),
                     "solver": proposal["solver"], "coverage_optimal": proposal["coverage_optimal"],
                     "assignments": proposal["assignments"], "postponed": proposal["postponed"]})
    ledger = {"version": 1, "original_sample_sha256": original["original_sample_sha256"],
              "source": "Previously published 62-day proposals; frozen without re-solving or selecting favorable dates.", "days": rows}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ledger


def verify_assignments(rows, session):
    tournament, matches, venues, risks, settings, engine = Service.context(session)
    selected = candidates(rows)
    ids = {row.match_id for row in selected}
    if not ids <= {match.id for match in matches}:
        raise ValueError("Unknown frozen match")
    errors = validate(selected, matches, tournament, venues, risks, settings)
    if errors:
        raise ValueError("Constraint violation: " + ", ".join(errors))
    by_id = {match.id: match for match in matches}
    for row in selected:
        adjusted = by_id[row.match_id].model_copy(update={"venue_id": row.venue_id, "scheduled_start": row.start})
        rec = recommend(adjusted, risks, engine)
        if (row.end, row.level, row.duration_min, row.cooling_times, row.action, row.heat_score) != (
                rec.end, rec.level, rec.duration_min, rec.cooling_times, rec.action,
                heat_score(risks, row.venue_id, row.start, row.end)):
            raise ValueError("Frozen assignment differs from current unchanged policy/score")
    return selected


def compare_day(session, frozen, greedy):
    cp = verify_assignments(frozen["assignments"], session)
    baseline = verify_assignments([json_row(row) for row in greedy.assignments], session)
    cp_ids, baseline_ids = {row.match_id for row in cp}, {row.match_id for row in baseline}
    all_ids = {match["id"] for match in session["matches"]}
    for ids, postponed in ((cp_ids, frozen["postponed"]), (baseline_ids, greedy.postponed)):
        postponed_ids = {row["match_id"] for row in postponed}
        if ids & postponed_ids or ids | postponed_ids != all_ids or len(postponed_ids) != len(postponed):
            raise ValueError("Coverage/postponement mismatch")
        if any(not row["reason"] for row in postponed):
            raise ValueError("Missing postponement reason")
    common = sorted(cp_ids & baseline_ids)
    return {"date": frozen["date"], "cp_assigned": len(cp), "cp_postponed": len(all_ids - cp_ids),
            "greedy_assigned": len(baseline), "greedy_postponed": len(all_ids - baseline_ids),
            "assignment_gain": len(cp) - len(baseline), "common_match_ids": common,
            "cp_common_heat": sum(row.heat_score for row in cp if row.match_id in common),
            "greedy_common_heat": sum(row.heat_score for row in baseline if row.match_id in common),
            "cp_solver": frozen["solver"], "cp_coverage_optimal": frozen["coverage_optimal"],
            "constraints_ok": True, "greedy_elapsed_sec": round(greedy.elapsed_sec, 6),
            "greedy_assignments": [json_row(row) for row in baseline], "greedy_postponed_reasons": greedy.postponed}


def json_row(row):
    value = asdict(row)
    return {**value, "start": row.start.isoformat(), "end": row.end.isoformat(),
            "cooling_times": [time.isoformat() for time in row.cooling_times]}


def summarize(rows):
    comparable = [row for row in rows if row["common_match_ids"]]
    return {"days": len(rows), "cp_assigned": sum(row["cp_assigned"] for row in rows),
            "greedy_assigned": sum(row["greedy_assigned"] for row in rows),
            "assignment_gain": sum(row["assignment_gain"] for row in rows),
            "more_assigned_days": sum(row["assignment_gain"] > 0 for row in rows),
            "same_assigned_days": sum(row["assignment_gain"] == 0 for row in rows),
            "fewer_assigned_days": sum(row["assignment_gain"] < 0 for row in rows),
            "cp_complete_days": sum(row["cp_postponed"] == 0 for row in rows),
            "greedy_complete_days": sum(row["greedy_postponed"] == 0 for row in rows),
            "common_heat_lower_days": sum(row["cp_common_heat"] < row["greedy_common_heat"] for row in comparable),
            "common_heat_equal_days": sum(row["cp_common_heat"] == row["greedy_common_heat"] for row in comparable),
            "common_heat_higher_days": sum(row["cp_common_heat"] > row["greedy_common_heat"] for row in comparable),
            "no_common_days": len(rows) - len(comparable),
            "cp_common_heat": sum(row["cp_common_heat"] for row in rows),
            "greedy_common_heat": sum(row["greedy_common_heat"] for row in rows)}


def analyze(source_sessions=None):
    ledger = bootstrap(source_sessions) if source_sessions else json.loads(LEDGER.read_text(encoding="utf-8"))
    dataset = load_dataset()
    if ledger["original_sample_sha256"] != dataset.original_sha256 or [row["date"] for row in ledger["days"]] != [day.isoformat() for day in dataset.dates]:
        raise ValueError("Observation fingerprint/date coverage mismatch")
    output = ROOT / "data/output/competition"
    output.mkdir(parents=True, exist_ok=True)
    service = Service(Repository(output / ("comparison-" + uuid4().hex + ".sqlite3")))
    rows = []
    for frozen, day in zip(ledger["days"], dataset.dates):
        session = service.replay(day, mode="observed")
        if session["engine_settings"] != EngineSettings().model_dump() or session["schedule_settings"] != ScheduleSettings().model_dump():
            raise ValueError("Default settings changed")
        if input_digest(session) != frozen["input_sha256"]:
            raise ValueError("Frozen/fresh input mismatch on " + frozen["date"])
        t, m, v, r, settings, engine = Service.context(session)
        baseline = optimize(m, t, v, r, settings, engine, force_greedy=True)
        rows.append(compare_day(session, frozen, baseline))
        print(json.dumps({key: rows[-1][key] for key in ("date", "cp_assigned", "greedy_assigned", "assignment_gain")}), flush=True)
    result = {"version": 1, "station": dataset.station, "original_sample_sha256": dataset.original_sha256,
              "frozen_solutions_sha256": digest(ledger),
              "method": "Frozen CP-SAT vs existing greedy fallback, identical observed inputs/default policy/constraints; common matches only for heat.",
              "limitation": "Internal algorithm comparison, not human operators, competitor products, health outcomes or field WBGT validation.",
              "summary": summarize(rows), "days": rows}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "method-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sessions", type=Path, help="Initial freeze of the existing published daily sessions; no re-solve")
    args = parser.parse_args()
    analyze(args.source_sessions)
