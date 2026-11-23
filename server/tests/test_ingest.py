from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Config
from server.ingest import clean_log, game_id_from_room, replay_ref_from_room

from .conftest import RANDBATS_ID, VGC_ID, load_replay

PLAY = "https://play.pokemonshowdown.com"


@pytest.fixture
def client(tmp_path, transport):
    cfg = Config(data_dir=tmp_path, default_username="Codexe", poll_minutes=15,
                 request_delay=0, poller_enabled=False)
    with TestClient(create_app(cfg, transport)) as c:
        yield c


def battle_body(replay_id: str, **extra) -> dict:
    log = load_replay(replay_id)["log"]
    client_log = "|init|battle\n|title|x vs y\n|request|{\"wait\":true}\n" + log
    return {"roomid": f"battle-{replay_id}", "log": client_log, **extra}


def test_room_ids():
    assert game_id_from_room("battle-gen9randombattle-123") == "gen9randombattle-123"
    assert game_id_from_room("battle-gen9ou-123-abc123pw") == "gen9ou-123"
    assert replay_ref_from_room("battle-gen9ou-123-abc123pw") == ("gen9ou-123", "abc123")
    assert replay_ref_from_room("battle-gen9ou-123") == ("gen9ou-123", None)
    for bad in ("lobby", "battle-../../x-1", "battle-gen9ou"):
        with pytest.raises(ValueError):
            game_id_from_room(bad)
    assert clean_log("|init|battle\n|title|t\n|j|a\n\n|start") == "|j|a\n|start\n"


def test_ingest_finished_battle_with_own_team(client):
    side = {"name": "Codexe", "id": "p1", "pokemon": [{"ident": "p1: Dedenne", "item": "leftovers"}]}
    body = battle_body(RANDBATS_ID, request={"side": side}, username="Codexe")
    r = client.post("/api/ingest", json=body)
    assert r.status_code == 200, r.text
    assert r.json() == {"id": RANDBATS_ID, "added": True, "finished": True}
    game = client.get(f"/api/games/{RANDBATS_ID}").json()
    assert game["source"] == "userscript" and game["result"] == "loss"
    assert game["own_team"]["pokemon"][0]["item"] == "leftovers"
    assert "|init|" not in game["log"] and "|request|" not in game["log"]
    assert client.get("/api/settings").json()["last_ingest"] is not None
    # sending it again changes nothing
    assert client.post("/api/ingest", json=body).json()["added"] is False


def test_ingest_rejects_unfinished_unless_marked(client):
    log = "|init|battle\n|player|p1|Codexe|1|\n|player|p2|B|2|\n|start\n|turn|1\n"
    body = {"roomid": "battle-gen9ou-55", "log": log}
    assert client.post("/api/ingest", json=body).status_code == 400
    r = client.post("/api/ingest", json=dict(body, incomplete=True))
    assert r.json() == {"id": "gen9ou-55", "added": True, "finished": False}
    assert client.get("/api/games/gen9ou-55").json()["result"] is None


def test_userscript_copy_upgraded_by_replay_server(client, fake):
    client.post("/api/sync")  # sets the start time
    client.post("/api/ingest", json=battle_body(RANDBATS_ID))
    fake.add(load_replay(RANDBATS_ID), uploadtime=int(time.time()) + 5)
    r = client.post("/api/sync").json()
    assert r["added"] == []  # not new, but upgraded
    game = client.get(f"/api/games/{RANDBATS_ID}").json()
    assert game["has_inputlog"] and game["uploadtime"] is not None
    assert game["source"] == "userscript"  # remembers it was captured live


def test_poller_does_not_stop_at_ingested_game(client, fake):
    """Regression: an ingested newer game must not hide older uploads from the poller."""
    client.post("/api/sync")
    now = int(time.time())
    fake.add(load_replay(VGC_ID), uploadtime=now + 10)          # uploaded, not yet polled
    client.post("/api/ingest", json=battle_body(RANDBATS_ID))     # played after, captured live
    fake.add(load_replay(RANDBATS_ID), uploadtime=now + 20)     # and uploaded
    r = client.post("/api/sync").json()
    assert VGC_ID in r["added"]


def test_ingest_private(client, fake):
    client.post("/api/sync")
    now = int(time.time())
    fake.add(load_replay(VGC_ID), uploadtime=now + 5, password="pw123abc")
    items = [{"id": VGC_ID, "password": "pw123abc", "uploadtime": now + 5},
             {"id": "gen9ou-1", "password": "x", "uploadtime": 1}]  # before start: skipped
    r = client.post("/api/ingest-private", json={"username": "Codexe", "items": items}).json()
    assert r == {"added": [VGC_ID], "skipped": 1, "errors": []}
    assert client.get(f"/api/games/{VGC_ID}").json()["private"] is True
    wrong = client.post("/api/ingest-private", json={"username": "someoneelse", "items": []})
    assert wrong.status_code == 409


def test_origin_guard(client):
    body = battle_body(RANDBATS_ID)
    evil = {"Origin": "https://evil.example"}
    assert client.post("/api/ingest", json=body, headers=evil).status_code == 403
    assert client.put("/api/settings", json={"username": "x"}, headers=evil).status_code == 403
    assert client.post("/api/sync", headers=evil).status_code == 403
    # Showdown's page may call ingest (fetch fallback), with CORS headers, but nothing else
    pre = client.options("/api/ingest", headers={"Origin": PLAY, "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 204 and pre.headers["access-control-allow-origin"] == PLAY
    ok = client.post("/api/ingest", json=body, headers={"Origin": PLAY})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == PLAY
    assert client.put("/api/settings", json={"username": "x"}, headers={"Origin": PLAY}).status_code == 403
    # this app's own pages
    assert client.post("/api/ingest", json=body, headers={"Origin": "http://127.0.0.1:8765"}).status_code == 200
    # a form-encoded post (no preflight) is refused
    form = client.post("/api/ingest", content=json.dumps(body), headers={"Content-Type": "text/plain"})
    assert form.status_code in (415, 422)


def test_bad_ids_cannot_escape_data_dir(client, tmp_path):
    evil = {"id": "../../../etc/x", "formatid": "../../y", "log": "|player|p1|a|1|\n|player|p2|b|1|\n"}
    r = client.post("/api/import/file", files={"file": ("x.json", json.dumps(evil).encode())})
    assert r.status_code == 400
    assert not any(p.name == "x.json" for p in tmp_path.parent.rglob("x.json"))


def test_userscript_served(client):
    r = client.get("/userscript/showdown-game-review.user.js")
    assert r.status_code == 200 and "==UserScript==" in r.text


# ---- auto-upload (2026-11-23): the userscript ran /savereplay; fetch the replay now
def test_ingest_uploaded_upgrades_and_auto_analyzes(client, fake, monkeypatch):
    from server.review.jobs import Jobs
    queued: list[str] = []
    real_start = Jobs.start
    monkeypatch.setattr(Jobs, "start", lambda self, gid, **kw: (queued.append(gid), real_start(self, gid, **kw))[1])
    client.post("/api/sync")  # sets the start time
    client.post("/api/ingest", json=battle_body(RANDBATS_ID))         # the browser's copy, no inputlog
    body = {"roomid": f"battle-{RANDBATS_ID}"}
    r = client.post("/api/ingest-uploaded", json=body).json()
    assert r == {"id": RANDBATS_ID, "found": False, "added": False}    # not uploaded yet
    fake.add(load_replay(RANDBATS_ID), uploadtime=int(time.time()) + 5)
    r = client.post("/api/ingest-uploaded", json=body).json()
    assert r == {"id": RANDBATS_ID, "found": True, "added": False}     # upgraded, not new
    game = client.get(f"/api/games/{RANDBATS_ID}").json()
    assert game["has_inputlog"] and game["uploadtime"] is not None
    assert queued.count(RANDBATS_ID) == 2   # on the browser copy (unsupported: no inputlog) and on the upgrade
    n = len(fake.requests)
    assert client.post("/api/ingest-uploaded", json=body).json()["found"] is True
    assert len(fake.requests) == n          # already has the server copy: no request


def test_ingest_uploaded_private_room_uses_its_password(client, fake):
    client.post("/api/sync")
    fake.add(load_replay(VGC_ID), uploadtime=int(time.time()) + 5, password="abc123")
    r = client.post("/api/ingest-uploaded", json={"roomid": f"battle-{VGC_ID}-abc123pw"}).json()
    assert r == {"id": VGC_ID, "found": True, "added": True}
    game = client.get(f"/api/games/{VGC_ID}").json()
    assert game["private"] is True and not game["has_inputlog"]   # VGC: no inputlog, so no move review
    assert fake.requests[-1].url.path == f"/{VGC_ID}-abc123pw.json"


def test_ingest_uploaded_rejects_bad_rooms_and_other_sites(client):
    assert client.post("/api/ingest-uploaded", json={"roomid": "lobby"}).status_code == 400
    evil = {"Origin": "https://evil.example"}
    assert client.post("/api/ingest-uploaded", json={"roomid": f"battle-{RANDBATS_ID}"}, headers=evil).status_code == 403
    pre = client.options("/api/ingest-uploaded", headers={"Origin": PLAY, "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 204
