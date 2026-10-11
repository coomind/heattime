"""Check presentation evidence, manuscript consistency, links and planned timing.

This is an offline document check. It does not load settings, secrets, or fetch data.
The six-character/second timing estimate is a rehearsal assumption, not a measured rate.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "docs/presentation"
APPROVED = "수원 관측 자료로 재현한 가상 12팀 대회에서는 62일 중 47일에, 일정을 재배치해도 15경기 전부를 같은 날 배정할 수 없었습니다."
# 2026-10-11 recalculation (solar interval alignment, 0.1C decision rounding, deterministic tie-break).
# Author decision 2026-10-11: demo date = first hot candidate (daily max air temp >= 31C, then the existing
# rule), repeated 5 times (docs/real-data/demo-day-check.json); extreme supporting scene = 2026-08-08.
SNAPSHOT_DATE = "2026-08-10"
EXTREME_DATE = "2026-08-08"
HOT_CANDIDATE_DATES = ["2026-08-10", "2026-08-14", "2026-07-14", "2026-08-09", "2026-08-11"]
# Exact 8/10 values from replay-results.json hot_candidates[0] / observed-snapshot.json:
# assigned, postponed, common, original heat, proposed heat, originally-stopped-now-assigned, original stop count.
SNAPSHOT_VALUES = (13, 2, 13, 6442, 3879, 13, 14)
SNAPSHOT_MAX_WBGT = 31.274
EXTREME_VALUES = (7, 8, 7, 4663, 2087, 35.4, 34.828)
ZERO_DATES = ["2026-07-11", "2026-07-12", "2026-07-13", "2026-07-31", "2026-08-01",
              "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07"]
ZERO_TEXT = "0경기배정일은10일(7월11·12·13·31일,8월1·3·4·5·6·7일)"
ASSUMPTIONS = "경기장 보정 +2.5℃, 유소년 추정 상단값 판정, 동일 관측소 1곳 공유, 이 가상 대회의 대진·휴식·운영시간·일몰 제약"
LIMITATION = "보정 +2.5℃는 해외 연구 기반 설계 가정으로, 국내 구장 검증과 전문가 검토가 필요"
CHARS_PER_SECOND = 6


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def demo_config() -> dict:
    """Read backend/config/demo.yaml without the YAML dependency (two scalar keys)."""
    values = {}
    for line in (ROOT / "backend/config/demo.yaml").read_text(encoding="utf-8").splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def seconds(time: str) -> int:
    minutes, remainder = map(int, time.split(":"))
    return minutes * 60 + remainder


def intervals(text: str, pattern: str):
    return [(label, seconds(start), seconds(end), int(duration))
            for label, start, end, duration in re.findall(pattern, text)]


def continuous(rows, start: int, end: int) -> bool:
    position = start
    for _, left, right, duration in rows:
        if left != position or right - left != duration or duration <= 0:
            return False
        position = right
    return position == end


def run(write_timing: bool) -> dict:
    docs = {p.name: p.read_text(encoding="utf-8") for p in sorted(PRESENTATION.glob("*.md"))}
    slides, qa, demo, capture = (docs[name] for name in
                               ("slides.md", "qa.md", "demo-script.md", "capture-list.md"))
    evidence = load_json("docs/real-data/replay-results.json")
    solar = load_json("docs/real-data/solar/solar-metrics.json")
    peaks = load_json("docs/wbgt-sanity/peak-traces.json")
    sensitivity = load_json("docs/wbgt-sanity/sensitivity-results.json")
    scenarios = {s["name"]: s for s in sensitivity["scenarios"]}
    checks = []

    def check(name: str, passed: bool):
        checks.append({"name": name, "passed": bool(passed)})

    # Preserve the checks recorded in p6-report.md and real-data/a6-presentation.md.
    # The 7/10 snapshot values (6051→4469, 30.848, 28.4C, 75~90%) are retired with the 8/10 demo date.
    stale = ("6080", "2856", "14배정/1연기", "실제 응답 확보 후",
             "6114", "4319", "32.043", "38.062", "29.36%", "62일중46일", "중지10경기",
             "6051", "4469", "30.848", "29.348~32.348", "26.14%", "중지9경기", "28.4℃", "75~90%", "2026-07-10", "7월10일")
    check("기존 합성 수치·시연 날짜 혼입 없음", all(not any(token in compact(body) for token in stale)
                                               for body in docs.values()))
    config = demo_config()
    hot = evidence["hot_candidates"]
    candidate = next(row for row in hot if row["date"] == SNAPSHOT_DATE)
    day = next(row for row in evidence["days"] if row["date"] == SNAPSHOT_DATE)
    extreme = next(row for row in evidence["days"] if row["date"] == EXTREME_DATE)
    repeat = {row["date"]: row for row in load_json("docs/real-data/demo-day-check.json")["checks"]}
    check("기존 관측 시연 수치 대조", [row["date"] for row in hot] == HOT_CANDIDATE_DATES
          and hot[0]["date"] == SNAPSHOT_DATE == config.get("demo_date") and config.get("extreme_date") == EXTREME_DATE
          and evidence["hot_selection_rule"].startswith("daily max air temperature >= 31C")
          and all(candidate[key] == day[key] for key in ("assigned", "postponed", "common_count", "original_heat",
                                                          "proposed_heat", "salvaged", "max_wbgt_c", "solver"))
          and (candidate["assigned"], candidate["postponed"], candidate["common_count"], candidate["original_heat"],
               candidate["proposed_heat"], candidate["salvaged"], candidate["original_stop_count"]) == SNAPSHOT_VALUES
          and candidate["max_wbgt_c"] == SNAPSHOT_MAX_WBGT and candidate["max_ta_c"] == 31.6
          and candidate["solver"] == "CP-SAT OPTIMAL"
          and [row["match_id"] for row in candidate["postponement_reasons"]] == ["final", "semi2"]
          and (extreme["assigned"], extreme["postponed"], extreme["common_count"], extreme["original_heat"],
               extreme["proposed_heat"], extreme["max_ta_c"], extreme["max_wbgt_c"]) == EXTREME_VALUES
          and all(repeat[d]["passed"] and len(repeat[d]["runs"]) == 5
                  and all(r["cp_sat_status"] == "OPTIMAL" and r["solver_wall_sec"] <= repeat[d]["time_limit_sec"] / 2
                          for r in repeat[d]["runs"])
                  and len({r["schedule_sha256"] for r in repeat[d]["runs"]}) == 1 for d in (SNAPSHOT_DATE, EXTREME_DATE))
          and all(token in compact(slides + demo) for token in
                  ("6442", "3879", "31.274", "29.774~32.774", "13경기", "2경기", "중지단계14경기중13경기",
                   "31.6℃", "44~67%", "8월10일", "8월14일", "7월14일", "8월9일", "8월11일",
                   "8월8일", "35.4℃", "7경기배정", "8경기연기", "최고기온33℃이상인날은모두8경기이상연기"))
          and all(token not in compact(slides.split("## 부록 ·")[0]) for token in ("39.79%", "26.14%", "29.36%", "38.229")))
    check("기존 관측 일사 수치 대조", solar["count"] == 927 and solar["missing_count"] == 561
          and round(solar["mae_wm2"], 2) == 62.67 and round(solar["bias_wm2"], 2) == 6.74
          and round(solar["max_absolute_error_wm2"], 2) == 460.07
          and all(token in compact(slides + qa) for token in ("927시간", "561시간", "62.67", "+6.74", "460.07")))
    original_questions = ("앱 추정 WBGT는 부정확", "케이웨더", "여름 한철", "기준 수치", "사고 나면 책임", "실제로 써본", "왜 경기도")
    check("기존 필수 질의응답7개 유지", all(re.search(rf"^## {i}\. .*{re.escape(term)}", qa, re.M)
                                          for i, term in enumerate(original_questions, 1)))
    check("기존 추정·가상·한계·라이선스 고지 유지", all(term in slides + qa for term in
          ("의사결정 보조", "가상 예시", "현장 검증된 통계 신뢰구간", "전문가 자문", "아마추어 영상 품질", "연구 단계"))
          and "Argonne" in docs["sources.md"] and "SIL OFL" in slides
          and (ROOT / "backend/assets/fonts/OFL.txt").is_file()
          and (ROOT / "docs/licenses").is_dir())

    # The multiline flag is explicit here so the time table is the only input.
    schedule = intervals(slides, r"(?m)^\| (\d+[AB]? [^|]+) \| (\d+:\d+)–(\d+:\d+) \| (\d+)초 \|[^\n]+$")
    ids = [row[0].split()[0] for row in schedule]
    durations = {row[0].split()[0]: row[3] for row in schedule}
    blocks = [durations.get("1", 0), durations.get("2", 0),
              sum(durations.get(str(i), 0) for i in range(3, 7)),
              durations.get("7A", 0) + durations.get("7B", 0), durations.get("8", 0),
              durations.get("9", 0) + durations.get("10", 0)]
    check("기존7분/3분 및40·40·180·60·50·50 구성", continuous(schedule, 0, 420)
          and ids == ["1", "2", "3", "4", "5", "6", "7A", "7B", "8", "9", "10"]
          and blocks == [40, 40, 180, 60, 50, 50])
    demo_times = re.findall(r"(?m)^\| (\d+:\d+)–(\d+:\d+) \|", demo)
    demo_rows = [(str(i), seconds(a), seconds(b), seconds(b) - seconds(a))
                 for i, (a, b) in enumerate(demo_times, 1)]
    check("기존 시연 클릭 시간표180초", len(demo_rows) == 9 and continuous(demo_rows, 80, 260))

    baseline = scenarios["baseline"]
    zero_dates = [d["date"] for d in baseline["days"] if d["assigned"] == 0]
    replay_zero = [d["date"] for d in evidence["days"] if d["assigned"] == 0]
    check("47일 조건부 문장·전체 가정·0배정10일 근거", len(baseline["days"]) == 62
          and baseline["summary"]["incomplete_days"] == 47 == sum(d["assigned"] < 15 for d in evidence["days"])
          and baseline["summary"]["zero_assignment_days"] == 10
          and zero_dates == replay_zero == ZERO_DATES
          and all(APPROVED in body and ASSUMPTIONS in body
                  and ZERO_TEXT in compact(body) and "37일" in body
                  for body in (slides, qa, demo, capture)))
    check("민감도47→26/47→14와분석용판정", scenarios["offset_0"]["summary"]["incomplete_days"] == 26
          and scenarios["offset_0_central"]["summary"]["incomplete_days"] == 14
          and all(token in qa for token in ("47→26일", "47→14일", "보정값", "일반 재현", "중앙값 판정은 분석용")))
    peak = peaks["rows"][0]
    peak_contexts = [paragraph for body in docs.values() for paragraph in body.split("\n\n") if "38.229" in paragraph]
    check("최고값 모델추정·보정·범위와근거", peak["date"] == "2026-08-19" and peak["venue_id"] == "mock-suwon-c"
          and max((d["max_wbgt_c"], d["date"]) for d in evidence["days"]) == (38.229, "2026-08-19")
          and round(peak["result"]["wbgt_c"], 2) == 35.73 and peak["field_offset_c"] == 2.5
          and (peak["central_c"], peak["low_c"], peak["upper_c"]) == (38.229, 36.729, 39.729)
          and len(peak_contexts) >= 2
          and all(all(token in compact(paragraph) for token in
                      ("관측WBGT가아니라", "관측입력기반추정35.73", "+2.5", "중앙값", "36.729~39.729"))
                  for paragraph in peak_contexts))
    sections = {match.group(1): match.group(2) for match in re.finditer(
        r"(?ms)^## (\d+[AB]?) ·[^\n]*\n(.*?)(?=^## |\Z)", slides)}
    check("시연·62일·민감도 화면 수치 분리", all(token not in sections["7B"] for token in
          ("6442", "3879", "31.274", "38.229", "47→26", "47→14"))
          and all(token not in "".join(sections[str(i)] for i in range(3, 7))
                  for token in ("38.229", "47→26", "47→14"))
          and "별도 질의응답 부록 화면" in qa and "서로 다른 화면" in capture)
    check("해외 보정 가정·미수행 검증·공간 차이 설명", LIMITATION in slides
          and "현장 WBGT 대조·인터뷰·전문가 자문은 아직 하지 않았습니다" in slides
          and all(term in qa for term in ("미측정", "관측 오차 범위나 신뢰구간이 아닙니다", "로드맵", "약풍", "복사")))

    speech = {}
    for label, body in sections.items():
        script = body.split("**발표자 대본**", 1)[1].split("**발표자 메모**", 1)[0]
        script = script.split("\n근거:", 1)[0].split("\n발표 마지막 화면", 1)[0]
        speech[label] = len(re.sub(r"\s+", " ", script.strip()))
    group_ids = [("문제", ["1"]), ("왜 지금", ["2"]), ("시연", ["3", "4", "5", "6"]),
                 ("기술", ["7A", "7B"]), ("사업화", ["8"]), ("한계·출처", ["9", "10"])]
    timing = [{"block": name, "planned_seconds": duration, "characters": sum(speech[i] for i in labels),
               "estimated_seconds": round(sum(speech[i] for i in labels) / CHARS_PER_SECOND, 2)}
              for (name, labels), duration in zip(group_ids, blocks)]
    check("글자수가정 기준 각슬라이드·6구간 예산", all(speech[i] <= durations[i] * CHARS_PER_SECOND for i in speech)
          and all(row["characters"] <= row["planned_seconds"] * CHARS_PER_SECOND for row in timing))
    answers = {}
    for i in range(8, 11):
        answer = re.search(rf"(?ms)^## {i}\. .*?\*\*30초 답변\*\*\s*(.*?)(?=\n\*\*|\Z)", qa).group(1).strip()
        answers[str(i)] = len(re.sub(r"\s+", " ", answer))
    check("추가 질의응답3개30초 글자수 예산", len(answers) == 3 and all(length <= 30 * CHARS_PER_SECOND for length in answers.values()))
    video = intervals(capture, r"(?m)^\| (\d+) \| (\d+:\d+)–(\d+:\d+) \| \d+:\d+–\d+:\d+ \| [^|]+ \| (\d+)초 \|[^\n]+$")
    check("캡처 목록9장면180초·별도부록", len(video) == 9 and continuous(video, 0, 180)
          and "본 발표 외" in capture and "앱에 새 분석 화면을 추가하는 작업이 아니다" in capture)
    links = []
    for filename, body in docs.items():
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
            if "://" not in target and not target.startswith("#"):
                links.append((filename, target))
    # The timing file is generated below; other references must already exist.
    check("기존 및추가 로컬링크 존재", all((PRESENTATION / target.split("#")[0]).exists()
          or (write_timing and target == "timing-check.md") for _, target in links))
    result = {"passed": all(c["passed"] for c in checks), "checks": checks, "local_link_count": len(links),
              "timing_assumption_chars_per_second": CHARS_PER_SECOND, "timing": timing,
              "slide_characters": speech, "new_qa_characters": answers}
    if write_timing and result["passed"]:
        lines = ["# 발표 시간 글자 수 점검", "",
                 "2026-10-11 · scripts/check_presentation.py로 원고를 재검산했다(최초 작성 2026-10-05; 2026-10-11 재계산 수치와 시연일 8월10일 확정 반영).", "",
                 "발표자 대본만 세고 화면 문구·메모·표·출처 설명은 제외한다. 공백/문장부호를 포함하며 연속 공백·줄바꿈은 공백 한 칸으로 정규화한다.",
                 "초당6자(분당360자)는 계산용 리허설 가정이다. 실제 발화 속도나 7분 완주를 측정한 값이 아니다. 숫자·영문 읽기와 클릭 시간은 실제 리허설로 확인한다.", "",
                 "| 구간 | 예정 시간 | 대본 글자 수 | 가정상 읽기 시간 | 예정 시간 내 여부 |", "|---|---:|---:|---:|---|"]
        for row in timing:
            lines.append(f"| {row['block']} | {row['planned_seconds']}초 | {row['characters']}자 | {row['estimated_seconds']:.2f}초 | 통과 |")
        total_chars = sum(speech.values())
        lines += [f"| 합계 | 420초 | {total_chars}자 | {total_chars / CHARS_PER_SECOND:.2f}초 | 통과 |", "",
                  "문제40초/왜 지금40초/시연180초/기술60초/사업화50초/한계·출처50초를 유지한다.",
                  "기술은7A20초+7B40초로 나누고 방법 설명을 줄였다. 일사 비교 수치는 화면 부기로만 남긴다. 시연 안내도20초 슬롯에 들어가도록 간결하게 정리했다.", "",
                  "| 슬라이드 | 대본 글자 수 | 예정 시간 | 가정상 읽기 시간 |", "|---|---:|---:|---:|"]
        lines += [f"| {i} | {speech[i]}자 | {durations[i]}초 | {speech[i] / CHARS_PER_SECOND:.2f}초 |" for i in ids]
        lines += ["", "| 추가 질의응답 | 대본 글자 수 | 목표 | 가정상 읽기 시간 |", "|---|---:|---:|---:|"]
        lines += [f"| {i} | {length}자 | 30초 | {length / CHARS_PER_SECOND:.2f}초 |" for i, length in answers.items()]
        lines += ["", "민감도·최고값·관측소 공유 답변은 질의응답용 별도 화면이다. 본 발표420초와 시연180초에 부록90초를 더하지 않는다.",
                  "자동 검산 뒤 대본을 소리 내어 읽고 실제7분/시연3분/추가 답변각30초를 직접 확인한다.", "",
                  "재실행: 프로젝트 루트에서 `./.venv/Scripts/python.exe scripts/check_presentation.py --write-timing`.", ""]
        (PRESENTATION / "timing-check.md").write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-timing", action="store_true", help="검사 통과 후 글자 수 시간표 갱신")
    args = parser.parse_args()
    result = run(args.write_timing)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
