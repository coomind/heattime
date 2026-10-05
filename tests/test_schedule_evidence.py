"""Read-only details use existing recommendations and frozen approval inputs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.evidence import schedule_evidence
from backend.service import Service
from backend.schedule.recommend import recommend

ROOT = Path(__file__).resolve().parents[1]


def bundle(prefix):
    return json.loads((ROOT / f"frontend/src/demo/{prefix}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("prefix", ["snapshot", "observed-snapshot"])
@pytest.mark.parametrize("mid", ["g1-1", "g1-2", "g1-3", "g2-1", "g2-2", "g2-3", "g3-1", "g3-2", "g3-3", "g4-1", "g4-2", "g4-3", "semi1", "semi2", "final"])
def test_all_offline_details_match_existing_engine_and_full_constraints(prefix, mid):
    b = bundle(prefix); s = b["approved"]
    output = json.loads((ROOT / f"frontend/src/demo/{prefix}-evidence.json").read_text(encoding="utf-8"))
    assert output["input_fingerprint"] == b["input_fingerprint"]
    assert output["session_sha256"] == hashlib.sha256(json.dumps(s, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert output["matches"][mid] == schedule_evidence(s, mid)
    e = output["matches"][mid]
    a = next((a for a in s["proposal"]["assignments"] if a["match_id"] == mid), None)
    if a is None:
        assert e["postponed_reason"] and e["assignment"] is None and e["constraints"] is None
    else:
        assert e["assignment"] == a
        t, matches, venues, risks, settings, engine = Service.context(s)
        m = next(m for m in matches if m.id == mid)
        from datetime import datetime
        r = recommend(m.model_copy(update={"scheduled_start": datetime.fromisoformat(a["start"]), "venue_id": a["venue_id"]}), risks, engine)
        assert e["recommendation"]["wbgt_c"] == r.wbgt_c
        assert e["recommendation"]["wbgt_low_c"] == r.wbgt_low_c
        assert e["recommendation"]["wbgt_high_c"] == r.wbgt_high_c
        assert e["recommendation"]["end"] == a["end"]
        assert not e["constraints"]["schedule_errors"]
        assert e["constraints"]["operating_ok"]
        assert all(row["ok"] for key in ("rest", "cleanup", "dependencies") for row in e["constraints"][key])
        assert e["risks"] and e["venue_name"]


def test_approved_detail_uses_frozen_inputs_even_when_live_session_is_changed():
    s = bundle("observed-snapshot")["approved"]
    original = schedule_evidence(s, "g1-1", "approved")
    changed = deepcopy(s)
    changed["risks"] = []; changed["schedule_settings"]["close_hour"] = 8
    changed["venues"][0]["name"] = "changed"
    assert schedule_evidence(changed, "g1-1", "approved") == original


@pytest.mark.parametrize("action,state", [("modified", "superseded_proposal"), ("rejected", "rejected_proposal")])
def test_auto_proposal_is_not_mislabelled_as_applied_schedule(action, state):
    s = bundle("observed-snapshot")["approved"]
    s["decision"]["operator_action"] = action
    assert schedule_evidence(s, "g1-1")["state"] == state
    if action == "rejected":
        e = schedule_evidence(s, "g1-1", "approved")
        assert e["state"] == "rejected" and e["assignment"] is None


def test_details_endpoint_is_readonly_and_requires_proposal_or_approval(tmp_path):
    with TestClient(create_app(tmp_path / "details.sqlite3")) as client:
        s = bundle("observed-snapshot")["approved"]
        client.app.state.repo.put("sessions", s["id"], s)
        before = client.app.state.repo.get("sessions", s["id"])
        url = f"/api/sessions/{s['id']}/matches/g1-1/evidence"
        assert client.get(url).status_code == 200
        assert client.get(url + "?view=approved").json()["state"] == "approved"
        assert client.get(url.replace("g1-1", "unknown")).status_code == 404
        assert client.get(url + "?view=unknown").status_code == 422
        assert client.app.state.repo.get("sessions", s["id"]) == before
        s["decision"] = None; s["proposal"] = None
        client.app.state.repo.put("sessions", s["id"], s)
        assert client.get(url).status_code == 422
        assert client.get(url + "?view=approved").status_code == 422
