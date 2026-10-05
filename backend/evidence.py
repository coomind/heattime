"""Read-only projections of existing schedule calculations; no new policy or solver."""
from datetime import datetime, timedelta
from fastapi.encoders import jsonable_encoder
from backend.exports import record_context
from backend.service import Service
from backend.schedule.optimizer import participants, sunset, validate, Candidate
from backend.schedule.recommend import recommend
from backend.weather.models import KST


def schedule_evidence(session, match_id, view="proposed"):
    if view not in {"proposed", "approved"}:
        raise ValueError("알 수 없는 일정 보기입니다.")
    decision = session.get("decision") or {}
    s = record_context(session) if view == "approved" else session
    t, matches, venues, risks, settings, engine = Service.context(s)
    by = {m.id: m for m in matches}
    if match_id not in by:
        raise KeyError(match_id)
    match = by[match_id]
    if view == "approved" and not decision:
        raise ValueError("아직 승인한 일정이 없습니다.")
    if view == "proposed" and not session.get("proposal"):
        raise ValueError("자동 제안을 먼저 생성하세요.")
    plan = decision if view == "approved" else session["proposal"]
    state = ("approved" if view == "approved" else
             "rejected_proposal" if decision.get("operator_action") == "rejected" else
             "superseded_proposal" if decision.get("operator_action") == "modified" else
             "accepted_proposal" if decision.get("operator_action") == "accepted" else "unapproved")
    result = {"view": view, "state": state, "match": jsonable_encoder(match),
              "label": s["label"], "policy": s["policy"],
              "original": next(r for r in s["recommendations"] if r["match_id"] == match_id),
              "assignment": None, "recommendation": None, "risks": [], "constraints": None,
              "postponed_reason": None, "solver": (session.get("proposal") or {}).get("solver"),
              "coverage_optimal": (session.get("proposal") or {}).get("coverage_optimal", False)}
    if view == "approved" and decision.get("operator_action") == "rejected":
        result["state"] = "rejected"
        return result
    assigned = {a["match_id"]: a for a in plan.get("assignments", [])}
    if match_id not in assigned:
        row = next((p for p in plan.get("postponed", []) if p["match_id"] == match_id), None)
        result["postponed_reason"] = row["reason"] if row else "결과 없음 · 운영자 확인 필요"
        return result
    a = assigned[match_id]
    start, end = datetime.fromisoformat(a["start"]), datetime.fromisoformat(a["end"])
    venue = next(v for v in venues if v.id == a["venue_id"])
    rec = recommend(match.model_copy(update={"scheduled_start": start, "venue_id": venue.id}), risks, engine)
    parts = participants(matches)
    team_names = {row["id"]: row["name"] for row in s["teams"]}
    rest = settings.rest_by_age[t.age_group]
    rest_rows, cleanup_rows = [], []
    for other in assigned.values():
        if other["match_id"] == match_id:
            continue
        os, oe = datetime.fromisoformat(other["start"]), datetime.fromisoformat(other["end"])
        early_end, late_start = (oe, start) if os <= start else (end, os)
        gap = (late_start - early_end).total_seconds() / 60
        shared = parts[match_id] & parts[other["match_id"]]
        if shared:
            rest_rows.append({"match_id": other["match_id"], "team_names": [team_names.get(x, x) for x in sorted(shared)],
                              "possible_participants": bool(match.depends_on or by[other["match_id"]].depends_on),
                              "gap_min": gap, "required_min": rest, "ok": gap >= rest})
        if other["venue_id"] == venue.id:
            cleanup_rows.append({"match_id": other["match_id"], "gap_min": gap,
                                 "required_min": settings.cleanup_min, "ok": gap >= settings.cleanup_min})
    base = datetime.combine(start.astimezone(KST).date(), datetime.min.time(), KST)
    opening, closing = base + timedelta(hours=settings.open_hour), base + timedelta(hours=settings.close_hour)
    sun = sunset(base.date(), venue.lat, venue.lon) if not venue.has_lights else None
    effective_close = min(closing, sun) if sun else closing
    dep_rows = [{"match_id": dep, "end": assigned.get(dep, {}).get("end"),
                 "ok": dep in assigned and datetime.fromisoformat(assigned[dep]["end"]) <= start}
                for dep in match.depends_on]
    candidates = [Candidate(**{**r, "start": datetime.fromisoformat(r["start"]),
                  "end": datetime.fromisoformat(r["end"])}) for r in assigned.values()]
    errors = validate(candidates, matches, t, venues, risks, settings)
    result.update({"assignment": a, "venue_name": venue.name, "recommendation": jsonable_encoder(rec),
                   "risks": [{k: jsonable_encoder(getattr(r, k)) for k in
                              ("venue_id", "valid_time", "wbgt_c", "wbgt_low_c", "wbgt_high_c", "level", "decision_wbgt_c", "method_version")}
                             for r in risks if r.venue_id == venue.id and r.valid_time.date() == base.date()],
                   "constraints": {"rest": rest_rows, "cleanup": cleanup_rows, "dependencies": dep_rows,
                                   "open": opening.isoformat(), "close": closing.isoformat(),
                                   "sunset": sun.isoformat() if sun else None, "effective_close": effective_close.isoformat(),
                                   "end_with_cleanup": (end + timedelta(minutes=settings.cleanup_min)).isoformat(),
                                   "cleanup_min": settings.cleanup_min, "has_lights": venue.has_lights,
                                   "operating_ok": start >= opening and end + timedelta(minutes=settings.cleanup_min) <= effective_close,
                                   "schedule_errors": errors}})
    return result
