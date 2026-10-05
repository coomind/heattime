"""Display captured weather and measurement provenance without recalibrating."""
from datetime import datetime
from backend.exports import record_context
from backend.weather.models import require_aware


def measurement_audit(s, risk):
    history = s.get("manual_history")
    if history is None:
        return {"history_known": False, "rows": [], "applied_id": None,
                "calibration": risk["inputs"].get("calibration")}
    current = datetime.fromisoformat(risk["valid_time"])
    candidates, rows = [], []
    same_venue = [r for r in s["risks"] if r["venue_id"] == risk["venue_id"]]
    for row in sorted((m for m in history if m["venue_id"] == risk["venue_id"]), key=lambda m: m["valid_time"]):
        when = datetime.fromisoformat(row["valid_time"])
        refs = [r for r in same_venue if r["is_mock"] == row["is_mock"] and datetime.fromisoformat(r["valid_time"]) <= when]
        ref = max(refs, key=lambda r: r["valid_time"]) if refs else None
        if row["is_mock"] != risk["is_mock"]:
            status = "자료 구분 불일치 · 미적용"
        elif when > current:
            status = "입력 시각 이전 · 미적용"
        elif ref is None or (when - datetime.fromisoformat(ref["valid_time"])).total_seconds() > 3600:
            status = "기존 보정 기준의 1시간 이내 참고 자료 없음 · 미적용"
        else:
            status = "이후 입력으로 대체 · 미적용"
            candidates.append(row["id"])
        rows.append({**row, "status": status, "reference_time": ref["valid_time"] if ref else None})
    applied = candidates[-1] if candidates and risk["inputs"].get("calibration") is not None else None
    for row in rows:
        if row["id"] == applied:
            row["status"] = "현재 시각 추정에 적용"
        elif row["id"] in candidates and applied is None:
            row["status"] = "계산 기록에 보정 없음 · 이력 확인 필요"
    return {"history_known": True, "rows": rows, "applied_id": applied,
            "calibration": risk["inputs"].get("calibration")}


def input_evidence(session, venue_id, valid_time, view="original"):
    if view not in {"original", "proposed", "approved"}:
        raise ValueError("알 수 없는 근거 보기입니다.")
    when = datetime.fromisoformat(valid_time); require_aware(when)
    if view == "approved" and not session.get("decision"):
        raise ValueError("아직 승인한 일정이 없습니다.")
    s = {**record_context(session), "manual_history": session["decision"].get("snapshot", {}).get("manual_history")} if view == "approved" else session
    risk = next((r for r in s["risks"] if r["venue_id"] == venue_id and datetime.fromisoformat(r["valid_time"]) == when), None)
    if risk is None:
        raise KeyError("input evidence")
    inputs = risk["inputs"]; w = inputs["weather"]; solar = inputs["solar"]; v = inputs["venue"]
    provenance = w.get("provenance") or {}
    return {"view": view, "label": s["label"], "data_origin": s.get("data_origin"),
            "risk": risk, "venue_name": v["name"], "weather": w, "solar": solar,
            "solar_observed": w.get("solar_wm2") is not None,
            "solar_energy_mj_m2": provenance.get("solar_energy_mj_m2"),
            "solar_interval_start": provenance.get("solar_interval_start"),
            "solar_interval_end": provenance.get("solar_interval_end"),
            "pressure_hpa": inputs["settings"]["pressure_hpa"],
            "wind_2m_ms": inputs["wind_2m_ms"], "wind_exponent": inputs["settings"]["wind_exponent"],
            "engine_wind_ms": max(inputs["wind_2m_ms"], 0.13),
            "fallback_wind_ms": max(inputs["wind_2m_ms"], 0.5),
            "engine_solar_wm2": 0 if v["surface"] == "indoor" or v["shade"] == "full" else solar["used_wm2"],
            "field_offset_c": v["field_offset_c"], "surface_offset_c": inputs["settings"]["surface_offsets"].get(v["surface"], 0),
            "solar_missing_hours": (s.get("observation_summary") or {}).get("solar_missing_hours"),
            "audit": measurement_audit(s, risk)}
