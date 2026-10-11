"""Offline evidence and link checks for the competition submission manuscripts.

Reads only committed analysis, snapshot and Markdown files. No network or secrets.
These checks verify document consistency, not customer demand or field accuracy.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from check_presentation import (APPROVED, ASSUMPTIONS, EXTREME_DATE, HOT_CANDIDATE_DATES, SNAPSHOT_DATE,
                                SNAPSHOT_MAX_WBGT, SNAPSHOT_VALUES, ZERO_DATES, ZERO_TEXT, compact, demo_config,
                                run as check_presentation)

ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def run() -> dict:
    directory = ROOT / "docs/submission"
    docs = {path.name: path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.md"))}
    checks = []

    def check(name: str, passed: bool):
        checks.append({"name": name, "passed": bool(passed)})

    check("five submission manuscripts exist", set(docs) == {
        "competition-fit.md", "proposal.md", "validation-plan.md", "evidence.md", "submission-checklist.md"})
    links = [(filename, target) for filename, body in docs.items()
             for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body)
             if "://" not in target and not target.startswith("#")]
    missing_links = [f"{filename}: {target}" for filename, target in links
                     if not (directory / target.split("#")[0]).is_file()]
    check("all local evidence links resolve", not missing_links)
    urls = ("https://ggsports.spectory.net/innovation/contest?bno=60730",
            "https://www.sfinder.co.kr/faq/list", "https://www.sportsprism.net/about/company-intro")
    check("official competition and product comparison citations included",
          all(url in docs["competition-fit.md"] for url in urls))

    # Author decision 2026-10-11: the snapshot date is hot_candidates[0] (daily max air temp >= 31C, then the
    # existing rule) and equals backend/config/demo.yaml demo_date; 2026-08-08 is the extreme supporting scene.
    replay = read_json("docs/real-data/replay-results.json")
    session = read_json("frontend/src/demo/observed-snapshot.json")["approved"]
    snapshot_date = session["tournament"]["date_start"]
    hot = replay["hot_candidates"]
    candidate = next((row for row in hot if row["date"] == snapshot_date), None)
    day = next((row for row in replay["days"] if row["date"] == snapshot_date), None)
    proposal = session["proposal"]
    assigned = {row["match_id"] for row in proposal["assignments"]}
    stopped = {row["match_id"] for row in session["recommendations"] if row["level"] == 4}
    config = demo_config()
    check("hot candidate list, replay day row, demo.yaml and fixed snapshot agree on August 10 coverage and originally stopped assignments",
          snapshot_date == SNAPSHOT_DATE == config.get("demo_date") == hot[0]["date"]
          and config.get("extreme_date") == EXTREME_DATE and candidate is not None and day is not None
          and [row["date"] for row in hot] == HOT_CANDIDATE_DATES
          and all(candidate[key] == day[key] for key in ("assigned", "postponed", "salvaged", "common_count",
                                                          "original_heat", "proposed_heat", "max_wbgt_c", "solver"))
          and day["assigned"] == len(assigned) == SNAPSHOT_VALUES[0]
          and day["postponed"] == proposal["postponed_count"] == len(proposal["postponed"]) == SNAPSHOT_VALUES[1]
          and sorted(row["match_id"] for row in proposal["postponed"]) == ["final", "semi2"]
          and day["salvaged"] == len(stopped & assigned) == SNAPSHOT_VALUES[5]
          and day["original_stop_count"] == len(stopped) == SNAPSHOT_VALUES[6]
          and day["solver"] == "CP-SAT OPTIMAL" and proposal["cp_sat_status"] == "OPTIMAL")
    original, proposed = proposal["original_heat_score"], proposal["proposed_heat_score"]
    percent = round((original - proposed) / original * 100, 2)
    check("common-game score reduction and percentage match evidence",
          day["original_heat"] == original == SNAPSHOT_VALUES[3]
          and day["proposed_heat"] == proposed == SNAPSHOT_VALUES[4]
          and len(proposal["common_match_ids"]) == day["common_count"] == SNAPSHOT_VALUES[2]
          and (original - proposed, percent) == (2563, 39.79)
          and all(token in compact(docs["proposal.md"]) for token in ("6442→3879", "2563점", "39.79%", "13/2경기", "semi2", "final", "준결승2(semi2)", "결승(final)")))
    peak = max(session["risks"], key=lambda row: row["wbgt_c"])
    check("August 10 model estimate includes correct low and high values",
          (peak["wbgt_c"], peak["wbgt_low_c"], peak["wbgt_high_c"]) == (SNAPSHOT_MAX_WBGT, 29.774, 32.774)
          and peak["decision_wbgt_c"] == 32.8 and peak["venue_id"] == "mock-suwon-a"
          and peak["wbgt_c"] == day["max_wbgt_c"] and peak["valid_time"] == "2026-08-10T13:00:00+09:00"
          and all(token in docs["proposal.md"] for token in ("31.274", "29.774~32.774", "현장 WBGT 실측 아님")))
    baseline = next(row for row in read_json("docs/wbgt-sanity/sensitivity-results.json")["scenarios"]
                    if row["name"] == "baseline")
    zero_days = [row["date"] for row in baseline["days"] if row["assigned"] == 0]
    check("conditional 62-day conclusion and complete assumptions retained",
          len(baseline["days"]) == 62 and baseline["summary"]["incomplete_days"] == 47
          and APPROVED in docs["proposal.md"] and ASSUMPTIONS in docs["proposal.md"])
    check("zero-assignment days remain separate from partly postponed days",
          zero_days == ZERO_DATES
          and ZERO_TEXT in compact(docs["proposal.md"]) and "37일" in docs["proposal.md"])
    qa = (ROOT / "docs/presentation/qa.md").read_text(encoding="utf-8")
    answers = {}
    for number in (11, 12):
        match = re.search(rf"(?ms)^## {number}\. .*?\*\*30초 목표 답변\*\*\s*(.*?)(?=\n\*\*|\Z)", qa)
        answers[str(number)] = len(re.sub(r"\s+", " ", match.group(1).strip())) if match else 0
    check("two new Q&A answers fit the unchanged six-character/second rehearsal assumption",
          all(0 < length <= 180 for length in answers.values()))
    presentation = check_presentation(False)
    check("all sixteen existing presentation checks pass", presentation["passed"]
          and len(presentation["checks"]) == 16)
    return {"passed": all(check["passed"] for check in checks), "checks": checks,
            "local_link_count": len(links), "missing_links": missing_links,
            "new_qa_characters": answers,
            "scope": "Document consistency only; customer, field accuracy and winning odds remain unverified."}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
