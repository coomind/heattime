"""Regression checks for tournament relationships and atomic CSV input validation."""
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.schedule.models import Match
from backend.schedule.optimizer import participants

CSV_HEADER = "id,round,team_a,team_b,venue_id,scheduled_start,duration_min,depends_on\n"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "integrity.sqlite3"), raise_server_exceptions=False) as client:
        yield client


def other_tournament(client):
    tournament = {**client.get("/api/tournaments/demo").json(),
                  "id": "other", "name": "가상 예시 검증 대회"}
    assert client.post("/api/tournaments", json=tournament).status_code == 201
    for team_id in ("other-a", "other-b"):
        response = client.post("/api/teams", json={"id": team_id, "tournament_id": "other",
                                                 "name": "가상 예시 검증 팀"})
        assert response.status_code == 201


@pytest.mark.parametrize("collision_first", [True, False])
def test_foreign_csv_id_collision_rejected_atomically(client, collision_first):
    other_tournament(client)
    before = client.get("/api/matches").json()
    original = client.get("/api/matches/g1-1").json()
    collision = "g1-1,group,other-a,other-b,mock-suwon-a,2026-08-01T09:00:00+09:00,40,\n"
    valid = "other-new,group,other-a,other-b,mock-suwon-a,2026-08-01T10:00:00+09:00,40,\n"
    rows = collision + valid if collision_first else valid + collision
    response = client.post("/api/tournaments/other/matches/csv", json={"csv_text": CSV_HEADER + rows})
    assert response.status_code == 409, response.text
    assert client.get("/api/matches").json() == before
    assert client.get("/api/matches/g1-1").json() == original
    assert client.get("/api/matches/other-new").status_code == 404
    participants([Match(**m) for m in before if m["tournament_id"] == "demo"])


def test_same_tournament_csv_update_still_allowed(client):
    before = client.get("/api/matches").json()
    original = client.get("/api/matches/g1-1").json()
    row = (f"g1-1,group,{original['team_a']},{original['team_b']},{original['venue_id']},"
           "2026-08-01T09:00:00+09:00,40,\n")
    response = client.post("/api/tournaments/demo/matches/csv", json={"csv_text": CSV_HEADER + row})
    assert response.status_code == 200, response.text
    assert response.json() == {"imported": 1}
    matches = client.get("/api/matches").json()
    assert len(matches) == len(before)
    assert client.get("/api/matches/g1-1").json()["scheduled_start"] == "2026-08-01T09:00:00+09:00"
    assert [m for m in matches if m["id"] != "g1-1"] == [m for m in before if m["id"] != "g1-1"]
    participants([Match(**m) for m in matches])


def test_referenced_team_cannot_move_to_another_tournament(client):
    other_tournament(client)
    team = client.get("/api/teams/t1").json()
    matches = client.get("/api/matches").json()
    assert any("t1" in (m["team_a"], m["team_b"]) for m in matches)
    response = client.put("/api/teams/t1", json={**team, "tournament_id": "other"})
    assert response.status_code == 422, response.text
    assert client.get("/api/teams/t1").json() == team
    assert client.get("/api/matches").json() == matches


def test_referenced_team_rename_still_allowed(client):
    team = client.get("/api/teams/t1").json()
    matches = client.get("/api/matches").json()
    response = client.put("/api/teams/t1", json={**team, "name": "가상 예시 변경 팀명"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "가상 예시 변경 팀명"
    assert response.json()["tournament_id"] == team["tournament_id"]
    assert client.get("/api/matches").json() == matches


def test_unreferenced_team_can_move(client):
    other_tournament(client)
    team = {"id": "unused", "name": "가상 예시 미배정 팀", "tournament_id": "demo"}
    assert client.post("/api/teams", json=team).status_code == 201
    response = client.put("/api/teams/unused", json={**team, "tournament_id": "other"})
    assert response.status_code == 200, response.text
    assert client.get("/api/teams/unused").json()["tournament_id"] == "other"


@pytest.mark.parametrize("malformed", [
    pytest.param(CSV_HEADER + "csv-bad,group,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40\n", id="missing-final-column"),
    pytest.param(CSV_HEADER + "csv-bad,group,t1,t2,mock-suwon-a\n", id="missing-required-columns"),
    pytest.param(CSV_HEADER + "csv-bad,group,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,,extra\n", id="extra-column"),
    pytest.param(CSV_HEADER + 'csv-bad,"unterminated\n', id="unterminated-quote"),
    pytest.param(CSV_HEADER.rstrip("\n") + ",depends_on\n" + "csv-bad,group,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,,\n", id="duplicate-header"),
])
def test_malformed_csv_returns_input_error_without_partial_writes(client, malformed):
    before = client.get("/api/matches").json()
    valid = "csv-valid,group,t1,t2,mock-suwon-a,2026-08-01T08:00:00+09:00,40,\n"
    header, rows = malformed.split("\n", 1)
    # Place a valid row first when the header has the normal width.
    text = header + "\n" + (valid if header + "\n" == CSV_HEADER else "") + rows
    response = client.post("/api/tournaments/demo/matches/csv", json={"csv_text": text})
    assert response.status_code == 422, response.text
    assert client.get("/api/matches").json() == before
    assert client.get("/api/matches/csv-valid").status_code == 404


def test_csv_with_omitted_optional_headers_and_empty_optional_cells_still_allowed(client):
    minimal = ("id,round,team_a,team_b,venue_id,scheduled_start\n"
               "csv-minimal,group,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00\n")
    response = client.post("/api/tournaments/demo/matches/csv", json={"csv_text": minimal})
    assert response.status_code == 200, response.text
    saved = client.get("/api/matches/csv-minimal").json()
    assert saved["duration_min"] == 40 and saved["depends_on"] == []
    empty = CSV_HEADER + "csv-empty,group,t1,t2,mock-suwon-a,2026-08-01T10:00:00+09:00,,\n"
    assert client.post("/api/tournaments/demo/matches/csv", json={"csv_text": empty}).status_code == 200
    assert client.get("/api/matches/csv-empty").json()["duration_min"] == 40
