"""Preview never writes; the same strict checks and revision guard apply at save."""
import csv
import io
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app

HEADER = "id,round,team_a,team_b,venue_id,scheduled_start,duration_min,depends_on\n"
VALID = HEADER + "g1-1,group,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,\n"
@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "preview.sqlite3")) as c: yield c

def preview(c, text):
    r = c.post("/api/tournaments/demo/matches/csv-preview", json={"csv_text": text})
    assert r.status_code == 200; return r.json()


def test_preview_shows_names_update_and_changes_without_writing_then_save_rechecks(client):
    before = client.get("/api/matches").json(); p = preview(client, VALID)
    assert p["valid"] and not p["errors"] and p["summary"] == {"insert": 0, "update": 1, "unchanged": 0}
    row = p["rows"][0]
    assert row["line"] == 2 and row["operation"] == "update" and "scheduled_start" in row["changed_fields"]
    assert "유소년" in row["team_a_name"] and "수원" in row["venue_name"]
    assert client.get("/api/matches").json() == before
    response = client.post("/api/tournaments/demo/matches/csv", json={"csv_text": VALID, "expected_revision": p["revision"]})
    assert response.json() == {"imported": 1}
    assert client.get("/api/matches/g1-1").json()["scheduled_start"] == "2026-08-01T09:00:00+09:00"


@pytest.mark.parametrize("text", [
    HEADER + "x,g,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40\n",
    HEADER + "x,g,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,,extra\n",
    HEADER + 'x,"unterminated\n',
    HEADER.rstrip("\n") + ",depends_on\nx,g,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,,\n",
    HEADER + "x,g,t1,t2,mock-suwon-a,2026-08-01T09:00:00,40,\n",
    HEADER + "x,g,t1,t2,mock-suwon-a,2026-09-01T09:00:00+09:00,40,\n",
    HEADER + "x,g,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,unknown\n",
    VALID + VALID.split("\n")[1] + "\n",
    "",
])
def test_invalid_preview_and_import_preserve_all_existing_rows(client, text):
    before = client.get("/api/matches").json(); p = preview(client, text)
    assert not p["valid"] and p["errors"]
    assert client.get("/api/matches").json() == before
    assert client.post("/api/tournaments/demo/matches/csv", json={"csv_text": text}).status_code == 422
    assert client.get("/api/matches").json() == before


@pytest.mark.parametrize("field,value", [("team_a", "unknown"), ("venue_id", "unknown")])
def test_unknown_reference_reports_row_and_same_status_when_saved(client, field, value):
    line = dict(next(csv.DictReader(io.StringIO(VALID)))); line[field] = value
    output = io.StringIO(); writer = csv.DictWriter(output, line.keys()); writer.writeheader(); writer.writerow(line)
    p = preview(client, output.getvalue())
    assert not p["valid"] and p["errors"][0]["line"] == 2 and p["errors"][0]["status"] == 404
    assert client.post("/api/tournaments/demo/matches/csv", json={"csv_text": output.getvalue()}).status_code == 404


def test_foreign_id_collision_is_not_previewed_as_legal_update(client):
    t = client.get("/api/tournaments/demo").json(); t["id"] = "other"
    assert client.post("/api/tournaments", json=t).status_code == 201
    m = client.get("/api/matches/g1-1").json(); m.update(id="foreign", tournament_id="other", team_a="winner:a", team_b="winner:b")
    # Store a foreign row directly to isolate the global-id collision from team checks.
    client.app.state.repo.put("matches", "foreign", m)
    text = VALID.replace("g1-1,", "foreign,")
    before = client.get("/api/matches").json(); p = preview(client, text)
    assert not p["valid"] and any(e["status"] == 409 for e in p["errors"])
    assert client.post("/api/tournaments/demo/matches/csv", json={"csv_text": text}).status_code == 409
    assert client.get("/api/matches").json() == before


def test_changed_resources_invalidate_confirmed_revision_without_writing_csv(client):
    p = preview(client, VALID); m = client.get("/api/matches/g1-1").json()
    t = client.get("/api/teams/t1").json(); t["name"] = "가상 예시 이름 변경"
    assert client.put("/api/teams/t1", json=t).status_code == 200
    response = client.post("/api/tournaments/demo/matches/csv", json={"csv_text": VALID, "expected_revision": p["revision"]})
    assert response.status_code == 409 and "다시 확인" in response.text
    assert client.get("/api/matches/g1-1").json() == m
    updated = preview(client, VALID); assert updated["revision"] != p["revision"]
    assert client.post("/api/tournaments/demo/matches/csv", json={"csv_text": VALID, "expected_revision": updated["revision"]}).status_code == 200


def test_template_has_bom_and_roundtrips_as_unchanged_existing_match(client):
    r = client.get("/api/tournaments/demo/matches/csv-template")
    assert r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbf")
    p = preview(client, r.content.decode("utf-8-sig"))
    assert p["valid"] and p["summary"] == {"insert": 0, "update": 0, "unchanged": 1}


def test_template_escapes_spreadsheet_formula_in_untrusted_round(client):
    m = client.get("/api/matches/final").json(); m["round"] = "=1+1"
    client.app.state.repo.put("matches", "final", m)
    r = client.get("/api/tournaments/demo/matches/csv-template")
    row = next(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert row["round"] == "'=1+1"
