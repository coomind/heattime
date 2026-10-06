"""Reissue comparison fingerprints only; never solve, change results or read .env."""
from copy import deepcopy
from datetime import date
import argparse
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.repository import Repository
from backend.service import Service
from scripts.analyze_tournament_scale import make_service, WINDOWS
from scripts.compare_schedule_methods import INPUT_FIELDS, INPUT_DIGEST_SCHEMA, digest, input_digest

FOLDER = "docs/competition-evidence/"
FILES = [FOLDER + name for name in ("frozen-solutions.json", "method-comparison.json",
         "no-field-analysis.json", "tournament-scale-analysis.json", "review-fix-results.json")]
FILES += ["frontend/src/demo/no-field-analysis.json", "frontend/src/demo/period-evidence.json"]
HASH_FIELDS = {"input_sha256", "frozen_solutions_sha256", "ledger_sha256", "input_digest_schema", "source_sha256"}


def result_payload(value):
    if isinstance(value, dict):
        return {k: result_payload(v) for k, v in value.items() if k not in HASH_FIELDS}
    if isinstance(value, list):
        return [result_payload(v) for v in value]
    return value


def text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def migrate(write=False):
    before = {name: json.loads((ROOT/name).read_text(encoding="utf-8")) for name in FILES}
    after = deepcopy(before)
    ledger = after[FILES[0]]
    output = ROOT/"data/output/portability"
    output.mkdir(parents=True, exist_ok=True)
    services = {12: Service(Repository(output/(uuid4().hex+".sqlite3"))),
                16: make_service(output/(uuid4().hex+".sqlite3"))}
    fingerprints = {}
    # Rebuild every original input once, WITHOUT requesting optimization.
    dates = {12: [date.fromisoformat(row["date"]) for row in ledger["days"]], 16: WINDOWS}
    for size in (12, 16):
        for day in dates[size]:
            s = services[size].replay(day, tournament_id="demo" if size == 12 else "benchmark16", mode="observed")
            fingerprints[size, day.isoformat()] = {
                "legacy": digest({k: s[k] for k in INPUT_FIELDS}), "new": input_digest(s)}

    updated = 0
    def update_rows(rows, size, key):
        nonlocal updated
        for row in rows:
            fp = fingerprints[size if size else row["teams"], row[key]]
            if row["input_sha256"] not in (fp["legacy"], fp["new"]):
                raise ValueError("Existing evidence does not match unchanged inputs: " + row[key])
            updated += row["input_sha256"] != fp["new"]
            row["input_sha256"] = fp["new"]

    update_rows(ledger["days"], 12, "date")
    update_rows(after[FILES[2]]["days"], 12, "date")
    update_rows(after[FILES[3]]["cases"], 16, "start")
    update_rows(after[FILES[4]]["cases"], None, "start")
    for name in FILES[:5]:
        after[name]["input_digest_schema"] = INPUT_DIGEST_SCHEMA
    after[FILES[1]]["frozen_solutions_sha256"] = digest(ledger)
    after[FILES[2]]["ledger_sha256"] = digest(ledger)
    data = after[FILES[2]]
    after[FILES[5]] = {**data, "days": [{**d, "baselines": {
        k: {a: b for a, b in v.items() if a != "assignments"} for k, v in d["baselines"].items()}} for d in data["days"]]}
    after[FILES[6]]["source_sha256"]["method-comparison.json"] = hashlib.sha256(text(after[FILES[1]]).encode()).hexdigest()
    receipts = []
    for name in FILES:
        old_results, new_results = result_payload(before[name]), result_payload(after[name])
        if old_results != new_results:
            raise ValueError("Result mutation blocked: " + name)
        receipts.append({"path": name, "unchanged_result_payload_sha256": digest(old_results),
                         "before_json_sha256": digest(before[name]), "after_json_sha256": digest(after[name])})
    report = {"schema": INPUT_DIGEST_SCHEMA, "precision": "round(float, 6); signed zero normalized",
        "risk_audit_hash_rule": "Only the comparison representation re-derives a hash from canonical full risk.inputs; captured engine audit hashes remain untouched.",
        "scope": "Comparison fingerprints only; no re-solving, policy/engine change, favorable date selection, snapshot rewrite or .env access.",
        "fresh_input_cases": len(fingerprints), "updated_input_receipts": updated,
        "all_result_payloads_unchanged": True, "files": receipts,
        "mapping": [{"teams": size, "date": day, "legacy_input_sha256": f["legacy"], "input_sha256": f["new"]}
                    for (size, day), f in fingerprints.items()]}
    if write:
        # Preflight all receipts and all result bodies before any evidence write.
        for name in FILES:
            content = (json.dumps(after[name], ensure_ascii=False, separators=(",", ":")) + "\n"
                       if name.startswith("frontend/") else text(after[name]))
            (ROOT/name).write_text(content, encoding="utf-8")
        (ROOT/FOLDER/"portability-migration.json").write_text(text(report), encoding="utf-8")
    print(json.dumps({"schema": INPUT_DIGEST_SCHEMA, "fresh_input_cases": len(fingerprints),
        "updated_input_receipts": updated, "result_payloads_unchanged": True, "written": write}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write all fingerprint receipts after unchanged-result checks")
    migrate(parser.parse_args().write)
