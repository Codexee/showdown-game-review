from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Config

from .conftest import RANDBATS_ID, VGC_ID, load_replay


@pytest.fixture
def client(tmp_path, transport):
    cfg = Config(data_dir=tmp_path, default_username="Codexe", poll_minutes=15,
                 request_delay=0, poller_enabled=False)
    with TestClient(create_app(cfg, transport)) as c:
        yield c


def test_first_sync_has_no_backfill(client, fake):
    fake.add(load_replay(RANDBATS_ID), uploadtime=int(time.time()) - 3600)
    r = client.post("/api/sync").json()
    assert r["first_sync"] and r["added"] == [] and r["profile_ok"]
    assert client.get("/api/games").json() == []
    assert client.get("/api/settings").json()["sync_start"] == r["started_at"]


def test_sync_adds_new_games_once(client, fake):
    client.post("/api/sync")  # sets the start time
    now = int(time.time())
    fake.add(load_replay(RANDBATS_ID), uploadtime=now + 10)
    fake.add(load_replay(VGC_ID), uploadtime=now + 20)
    r = client.post("/api/sync").json()
    assert r["added"] == [VGC_ID, RANDBATS_ID] and not r["errors"]
    assert client.post("/api/sync").json()["added"] == []

    games = client.get("/api/games").json()
    assert [g["id"] for g in games] == [VGC_ID, RANDBATS_ID]  # newest played first
    rb = client.get(f"/api/games/{RANDBATS_ID}").json()
    assert rb["result"] == "loss" and rb["opponent"] == "charizardslayer1"
    assert rb["rating_before"] == 1827 and rb["rating_after"] == 1804
    assert rb["has_inputlog"] and rb["inputlog"].startswith(">version")
    assert rb["source"] == "poller"


def test_sync_pages_with_before(client, fake):
    client.post("/api/sync")
    base = load_replay(RANDBATS_ID)
    now = int(time.time())
    for i in range(60):
        fake.add(dict(base, id=f"gen9randombattle-{1000 + i}"), uploadtime=now + 100 + i)
    r = client.post("/api/sync").json()
    assert len(r["added"]) == 60
    assert any("before=" in str(req.url) for req in fake.requests)


def test_private_replay_needs_password_suffix(client, fake):
    client.post("/api/sync")
    fake.add(load_replay(RANDBATS_ID), uploadtime=int(time.time()) + 5, password="secretpw1")
    r = client.post("/api/sync").json()
    assert r["added"] == [RANDBATS_ID]
    assert client.get(f"/api/games/{RANDBATS_ID}").json()["private"] is True


def test_import_url_and_filters(client, fake):
    fake.add(load_replay(VGC_ID), uploadtime=1)  # old game: only reachable by URL
    r = client.post("/api/import/url",
                    json={"url": f"https://replay.pokemonshowdown.com/{VGC_ID}"}).json()
    assert r == {"id": VGC_ID, "added": True}
    assert client.post("/api/import/url", json={"url": VGC_ID}).json()["added"] is False
    assert client.post("/api/import/url", json={"url": "https://example.com/x"}).status_code == 400
    assert client.post("/api/import/url", json={"url": "gen9ou-999"}).status_code == 502

    assert len(client.get("/api/games?result=loss").json()) == 1
    assert client.get("/api/games?result=win").json() == []
    assert len(client.get("/api/games?opponent=zuri").json()) == 1
    assert client.get("/api/games?format=gen9randombattle").json() == []
    assert client.get("/api/formats").json()[0]["format_id"] == "gen9championsvgc2026regmc"


def test_import_files(client):
    log = load_replay(RANDBATS_ID)["log"]
    r = client.post("/api/import/file", files={"file": ("game.log", log.encode())}).json()
    assert r["added"] and r["id"].startswith("upload-")

    html_page = ('<html><body><script type="text/plain" class="battle-log-data">'
                 + load_replay(VGC_ID)["log"].replace("&", "&amp;")
                 + f'</script><a href="https://replay.pokemonshowdown.com/{VGC_ID}">x</a></body></html>')
    r = client.post("/api/import/file", files={"file": ("replay.html", html_page.encode())}).json()
    assert r == {"id": VGC_ID, "added": True}
    game = client.get(f"/api/games/{VGC_ID}").json()
    assert game["summary"]["p1"]["rating_after"] == 1161  # &rarr; survived the unescape

    bad = client.post("/api/import/file", files={"file": ("x.txt", b"hello")})
    assert bad.status_code == 400


def test_turns_endpoint(client, fake):
    fake.add(load_replay(RANDBATS_ID), uploadtime=1)
    client.post("/api/import/url", json={"url": RANDBATS_ID})
    r = client.get(f"/api/games/{RANDBATS_ID}/turns").json()
    assert r["perspective"] == "p1" and r["format_id"] == "gen9randombattle"  # Codexe was p1
    assert len(r["turns"]) == 26 and not r["warnings"]
    opp = r["turns"][3]["sides"]["p2"]["team"]
    assert all(not m["hp_exact"] for m in opp)  # opponent HP as percentages
    full = client.get(f"/api/games/{RANDBATS_ID}/turns?side=all").json()
    assert any(m["hp_exact"] for m in full["turns"][3]["sides"]["p2"]["team"])
    assert client.get(f"/api/games/{RANDBATS_ID}/turns?side=p3").status_code == 400
    assert client.get("/api/games/nope-1/turns").status_code == 404


def test_team_paste_and_settings(client, fake):
    fake.add(load_replay(RANDBATS_ID), uploadtime=1)
    client.post("/api/import/url", json={"url": RANDBATS_ID})
    paste = "Dedenne @ Leftovers\nAbility: Cheek Pouch\n- Nuzzle"
    assert client.put(f"/api/games/{RANDBATS_ID}/team", json={"paste": paste}).json() == {"ok": True}
    assert client.get(f"/api/games/{RANDBATS_ID}").json()["team_paste"] == paste
    assert client.put("/api/games/nope-1/team", json={"paste": "x"}).status_code == 404

    s = client.put("/api/settings", json={"username": "charizardslayer1", "poll_minutes": 30}).json()
    assert s["username"] == "charizardslayer1" and s["poll_minutes"] == 30
    assert client.get(f"/api/games/{RANDBATS_ID}").json()["result"] == "win"
    assert client.put("/api/settings", json={"username": "!!!"}).status_code == 400


def test_no_username_yet(tmp_path, transport):
    # A fresh install has no username: sync asks for one, the profile is empty, nothing breaks.
    cfg = Config(data_dir=tmp_path, default_username="", poll_minutes=15, request_delay=0, poller_enabled=False)
    with TestClient(create_app(cfg, transport)) as c:
        r = c.post("/api/sync")
        assert r.status_code == 400 and "username" in r.json()["detail"]
        assert c.get("/api/profile").json() == {"username": "", "ratings": {}}
        assert c.get("/api/settings").json()["username"] == ""
