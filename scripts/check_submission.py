"""Offline evidence and link checks for the competition submission manuscripts.

Reads only committed analysis, snapshot and Markdown files. No network or secrets.
These checks verify document consistency, not customer demand or field accuracy.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from check_presentation import (APPROVED, ASSUMPTIONS, SNAPSHOT_DATE, ZERO_DATES, ZERO_TEXT, compact,
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

    # 2026-10-11 recalculation: the snapshot date is no longer candidates[0] (rule order 7/3, 8/20, 7/10).
    replay = read_json("docs/real-data/replay-results.json")
    session = read_json("frontend/src/demo/observed-snapshot.json")["approved"]
    snapshot_date = session["tournament"]["date_start"]
    candidate = next((row for row in replay["candidates"] if row["date"] == snapshot_date), None)
    day = next((row for row in replay["days"] if row["date"] == snapshot_date), None)
    proposal = session["proposal"]
    assigned = {row["match_id"] for row in proposal["assignments"]}
    stopped = {row["match_id"] for row in session["recommendations"] if row["level"] == 4}
    check("candidate list, replay day row and fixed snapshot agree on July 10 coverage and originally stopped assignments",
          snapshot_date == SNAPSHOT_DATE and candidate is not None and day is not None
          and [row["date"] for row in replay["candidates"][:3]] == ["2026-07-03", "2026-08-20", SNAPSHOT_DATE]
          and all(candidate[key] == day[key] for key in ("assigned", "postponed", "salvaged", "common_count",
                                                          "original_heat", "proposed_heat", "max_wbgt_c", "solver"))
          and day["assigned"] == len(assigned) == 15
          and day["postponed"] == proposal["postponed_count"] == len(proposal["postponed"]) == 0
          and day["salvaged"] == day["original_stop_count"] == len(stopped) == len(stopped & assigned) == 9
          and day["solver"] == "CP-SAT OPTIMAL")
    original, proposed = proposal["original_heat_score"], proposal["proposed_heat_score"]
    percent = round((original - proposed) / original * 100, 2)
    check("common-game score reduction and percentage match evidence",
          day["original_heat"] == original == 6051
          and day["proposed_heat"] == proposed == 4469
          and len(proposal["common_match_ids"]) == day["common_count"] == 15
          and (original - proposed, percent) == (1582, 26.14)
          and all(token in compact(docs["proposal.md"]) for token in ("6051→4469", "1582점", "26.14%")))
    peak = max(session["risks"], key=lambda row: row["wbgt_c"])
    check("July 10 model estimate includes correct low and high values",
          (peak["wbgt_c"], peak["wbgt_low_c"], peak["wbgt_high_c"]) == (30.848, 29.348, 32.348)
          and peak["wbgt_c"] == day["max_wbgt_c"] and peak["valid_time"] == "2026-07-10T15:00:00+09:00"
          and all(token in docs["proposal.md"] for token in ("30.848", "29.348~32.348", "현장 WBGT 실측 아님")))
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
