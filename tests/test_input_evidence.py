"""Provenance labels and captured calibration histories preserve original calculations."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.input_evidence import input_evidence

ROOT = Path(__file__).resolve().parents[1]
def frozen(prefix):
    return json.loads((ROOT / f"frontend/src/demo/{prefix}.json").read_text(encoding="utf-8"))["approved"]


@pytest.mark.parametrize("prefix", ["snapshot", "observed-snapshot"])
@pytest.mark.parametrize("index", range(72))
def test_all_offline_input_rows_preserve_values_units_and_original_source(prefix, index):
    s = frozen(prefix); r = s["risks"][index]
    packet = json.loads((ROOT / f"frontend/src/demo/{prefix}-input-evidence.json").read_text(encoding="utf-8"))
    e = input_evidence(s, r["venue_id"], r["valid_time"])
    assert packet["inputs"][r["venue_id"] + "|" + r["valid_time"]] == e
    assert e["risk"] == r and e["weather"] == r["inputs"]["weather"]
    assert e["pressure_hpa"] == r["inputs"]["settings"]["pressure_hpa"]
    assert e["solar_observed"] == (e["weather"]["solar_wm2"] is not None)
    if e["solar_energy_mj_m2"] is not None:
        assert e["weather"]["solar_wm2"] == pytest.approx(e["solar_energy_mj_m2"] * 1_000_000 / 3600)
        assert e["solar_interval_start"] and e["solar_interval_end"]
    if prefix == "observed-snapshot":
        assert e["solar_missing_hours"] == 9
        assert e["weather"]["is_mock"] is False
    # Regenerated 2026-10-11 bundles were replayed with history capture, so the (empty) history is known.
    assert e["audit"]["history_known"] is True and e["audit"]["rows"] == [] and e["audit"]["applied_id"] is None


def test_zero_irradiance_and_missing_observation_are_distinguished():
    for expected in (0, None):
        s = frozen("observed-snapshot"); r = s["risks"][0]
        # Explicit boundary inputs: the 2026-08-10 bundle's 00:00 row (risks[0]) has no observed solar value.
        r["inputs"]["weather"]["solar_wm2"] = expected
        e = input_evidence(s, r["venue_id"], r["valid_time"])
        assert e["solar_observed"] is (expected == 0)


def test_manual_audit_matches_existing_engine_and_captures_history_at_replay(tmp_path):
    with TestClient(create_app(tmp_path / "audit.sqlite3")) as client:
        venue = "mock-suwon-a"
        rows = [("2026-08-01T08:00:00+09:00", True), ("2026-08-01T12:00:00+09:00", True),
                ("2026-08-01T10:00:00+09:00", False), ("2026-08-02T12:00:00+09:00", True),
                ("2026-07-30T12:00:00+09:00", True)]
        ids = []
        for time, mock in rows:
            response = client.post("/api/manual", json={"venue_id": venue, "valid_time": time, "wbgt_c": 28, "is_mock": mock})
            assert response.status_code == 200; ids.append(response.json()["id"])
        s = client.post("/api/replays", json={"date": "2026-08-01"}).json()
        assert len(s["manual_history"]) == 5
        base = f"/api/sessions/{s['id']}/input-evidence"
        def get(hour):
            return client.get(base, params={"venue_id": venue, "valid_time": f"2026-08-01T{hour:02}:00:00+09:00"}).json()
        e = get(11); a = e["audit"]
        assert a["applied_id"] == ids[0] and a["calibration"] == e["risk"]["inputs"]["calibration"]
        statuses = {m["id"]: m["status"] for m in a["rows"]}
        assert "자료 구분 불일치" in statuses[ids[2]]
        assert "입력 시각 이전" in statuses[ids[1]] and "입력 시각 이전" in statuses[ids[3]]
        assert "참고 자료 없음" in statuses[ids[4]]
        assert get(13)["audit"]["applied_id"] == ids[1]
        assert "이후 입력으로 대체" in next(m for m in get(13)["audit"]["rows"] if m["id"] == ids[0])["status"]
        assert get(7)["audit"]["applied_id"] is None
        before = get(13)
        client.post("/api/manual", json={"venue_id": venue, "valid_time": rows[0][0], "wbgt_c": 30, "is_mock": True})
        assert len(client.get("/api/manual").json()) == 6
        assert get(13) == before
        assert client.get(base, params={"venue_id": venue, "valid_time": "2026-08-01T11:00:00"}).status_code == 422
        assert client.get(base, params={"venue_id": "unknown", "valid_time": rows[0][0]}).status_code == 404


def test_approved_source_and_history_do_not_follow_later_mutations():
    s = frozen("observed-snapshot"); r = s["risks"][12]
    original = input_evidence(s, r["venue_id"], r["valid_time"], "approved")
    changed = deepcopy(s); changed["risks"] = []; changed["manual_history"] = []
    assert input_evidence(changed, r["venue_id"], r["valid_time"], "approved") == original
    changed["decision"] = None
    with pytest.raises(ValueError):
        input_evidence(changed, r["venue_id"], r["valid_time"], "approved")
