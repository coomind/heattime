"""One validation path for read-only CSV preview and transactional import."""
from datetime import date
import csv
import hashlib
import io
import json
from fastapi.encoders import jsonable_encoder
from backend.schedule.models import Match
from backend.schedule.optimizer import participants
from backend.weather.models import KST
from backend.exports import csv_safe


def resources(conn, kind):
    return [json.loads(r[0]) for r in conn.execute("SELECT body FROM resources WHERE kind=? ORDER BY id", (kind,))]


def prepare_csv(repo, tournament_id, text, conn):
    tournament = repo.get("tournaments", tournament_id, conn)
    errors, parsed = [], []
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    def error(line, message, status=422):
        errors.append({"line": line, "message": message, "status": status})
    try:
        if reader.fieldnames and len(reader.fieldnames) != len(set(reader.fieldnames)):
            error(1, "CSV 열 이름이 중복되었습니다.")
        else:
            for raw in reader:
                line = reader.line_num
                if None in raw or any(v is None for v in raw.values()):
                    error(line, f"CSV {line}행의 열 수가 헤더와 다릅니다."); continue
                row = dict(raw); row["tournament_id"] = tournament_id
                row["depends_on"] = [v.strip() for v in row.get("depends_on", "").split(";") if v.strip()]
                for key in ("duration_min", "halves", "half_break_min"):
                    if not row.get(key): row.pop(key, None)
                try:
                    parsed.append((line, Match.model_validate(row)))
                except ValueError as exc:
                    error(line, f"CSV {line}행: {exc}")
    except csv.Error:
        error(reader.line_num, f"CSV {reader.line_num}행의 형식이 올바르지 않습니다. 따옴표를 확인하세요.")
    if not parsed and not errors: error(None, "Empty CSV or duplicate ids")
    matches = resources(conn, "matches"); teams = resources(conn, "teams"); venues = resources(conn, "venues")
    old = {m["id"]: m for m in matches}; team_map = {t["id"]: t for t in teams}; venue_map = {v["id"]: v for v in venues}
    seen = set()
    for line, m in parsed:
        if m.id in seen: error(line, "Empty CSV or duplicate ids")
        seen.add(m.id)
        if m.id in old and old[m.id]["tournament_id"] != tournament_id:
            error(line, f"경기 ID {m.id}는 다른 대회에서 사용 중입니다.", 409)
        if m.venue_id not in venue_map: error(line, f"CSV {line}행: 구장 {m.venue_id}를 찾지 못했습니다.", 404)
        if not date.fromisoformat(tournament["date_start"]) <= m.scheduled_start.astimezone(KST).date() <= date.fromisoformat(tournament["date_end"]):
            error(line, f"CSV {line}행: CSV match outside dates")
        for tid in (m.team_a, m.team_b):
            if tid.startswith("winner:"): continue
            if tid not in team_map: error(line, f"CSV {line}행: 참가팀 {tid}를 찾지 못했습니다.", 404)
            elif team_map[tid]["tournament_id"] != tournament_id: error(line, f"CSV {line}행: Invalid CSV team")
    if parsed and len(seen) == len(parsed):
        existing = [Match(**m) for m in matches if m["tournament_id"] == tournament_id and m["id"] not in seen]
        try: participants(existing + [m for _, m in parsed])
        except ValueError as exc: error(None, "선행 경기 구조: " + str(exc))
    revision = hashlib.sha256(json.dumps({"tournament": tournament, "matches": matches, "teams": teams, "venues": venues},
                              sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    rows = []
    for line, m in parsed:
        current = old.get(m.id); data = jsonable_encoder(m)
        changed = [key for key in data if current and data[key] != current.get(key)]
        rows.append({"line": line, "match": data, "operation": "insert" if current is None else "update" if changed else "unchanged",
                     "changed_fields": changed, "venue_name": venue_map.get(m.venue_id, {}).get("name", m.venue_id),
                     "team_a_name": team_map.get(m.team_a, {}).get("name", m.team_a),
                     "team_b_name": team_map.get(m.team_b, {}).get("name", m.team_b)})
    return {"valid": not errors, "errors": errors, "rows": rows, "revision": revision,
            "tournament_id": tournament_id, "tournament_name": tournament["name"],
            "summary": {op: sum(row["operation"] == op for row in rows) for op in ("insert", "update", "unchanged")}}


def template_csv(repo, tournament_id):
    repo.get("tournaments", tournament_id)
    first = next((m for m in repo.list("matches") if m["tournament_id"] == tournament_id), None)
    if first is None:
        raise ValueError("양식 예제를 만들려면 해당 대회에 경기를 한 건 먼저 등록하세요.")
    fields = ["id", "round", "team_a", "team_b", "venue_id", "scheduled_start", "duration_min", "halves", "half_break_min", "depends_on", "status"]
    output = io.StringIO(newline=""); writer = csv.DictWriter(output, fields); writer.writeheader()
    values = {**{k: first[k] for k in fields if k != "depends_on"}, "depends_on": ";".join(first["depends_on"])}
    writer.writerow({k: csv_safe(v) for k, v in values.items()})
    return ("\ufeff" + output.getvalue()).encode("utf-8")
