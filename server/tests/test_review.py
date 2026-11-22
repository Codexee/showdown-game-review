"""Stage 4 server pieces: review endpoint, turn narration, placeholder eval, sprite proxy."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.battle import parse_log
from server.battle.narrate import events_by_turn
from server.config import Config
from server.evaluate import win_chance
from server.sprites import sprite_id

from .conftest import RANDBATS_ID, VGC_ID, load_replay

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
def client(tmp_path, fake):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "play.pokemonshowdown.com":
            fake.requests.append(request)
            if request.url.path.endswith("/garchomp.png"):
                return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
            return httpx.Response(404, text="not found")
        return fake.handler(request)
    cfg = Config(data_dir=tmp_path, default_username="Codexe", poll_minutes=15,
                 request_delay=0, poller_enabled=False)
    with TestClient(create_app(cfg, httpx.MockTransport(handler))) as c:
        yield c


@pytest.mark.parametrize("species,expected", [
    ("Garchomp", "garchomp"), ("Palafin-Hero", "palafin-hero"), ("Ho-Oh", "hooh"),
    ("Kommo-o-Totem", "kommoo-totem"), ("Tapu Koko", "tapukoko"), ("Mr. Mime-Galar", "mrmime-galar"),
    ("Necrozma-Dawn-Wings", "necrozma-dawnwings"), ("Chi-Yu", "chiyu"),
])
def test_sprite_ids(species, expected):
    assert sprite_id(species) == expected


def test_sprite_proxy_caches_and_validates(client, fake, tmp_path):
    r = client.get("/sprites/gen5/garchomp.png")
    assert r.status_code == 200 and r.content == PNG
    assert (tmp_path / "sprites" / "gen5" / "garchomp.png").exists()
    n = len(fake.requests)
    assert client.get("/sprites/gen5/garchomp.png").status_code == 200
    assert len(fake.requests) == n  # served from disk
    assert client.get("/sprites/gen5/nosuchmon.png").status_code == 404
    assert client.get("/sprites/gen5/nosuchmon.png").status_code == 404
    assert len(fake.requests) == n + 1  # a 404 is remembered too
    assert client.get("/sprites/gen6/garchomp.png").status_code == 404  # unknown folder
    assert client.get("/sprites/gen5/Bad_Name.png").status_code == 404


def test_narration_reads_like_the_game():
    ev = events_by_turn(load_replay(RANDBATS_ID)["log"])
    leads = [e["text"] for e in ev[0]]
    assert leads == ["Codexe sent out Dedenne (100%).", "charizardslayer1 sent out Sawsbuck (100%)."]
    turn2 = [e["text"] for e in ev[2]]
    assert "Metagross was paralyzed (Static)." in turn2
    assert "Ampharos's Assault Vest was knocked off." in turn2
    last = max(ev)
    assert ev[last][-1] == {"text": "charizardslayer1 won the battle.", "side": None, "kind": "end"}


def test_placeholder_eval_is_sane():
    states = parse_log(load_replay(RANDBATS_ID)["log"]).states
    assert win_chance(states[0], "p1") == pytest.approx(0.5)
    for s in states:
        assert win_chance(s, "p1") + win_chance(s, "p2") == pytest.approx(1.0)
    assert win_chance(states[-1], "p1") == 0.0 and win_chance(states[-1], "p2") == 1.0  # Codexe lost


def test_review_endpoint(client, fake):
    fake.add(load_replay(VGC_ID), uploadtime=1)
    client.post("/api/import/url", json={"url": VGC_ID})
    r = client.get(f"/api/games/{VGC_ID}/review").json()
    assert r["perspective"] == "p1" and r["eval_method"] == "placeholder"
    steps = r["steps"]
    assert steps[0]["events"][0]["kind"] == "switch"          # leads
    assert steps[-1]["ended"] and steps[-1]["eval"] == 0.0    # Codexe lost
    mon = next(m for m in steps[3]["state"]["sides"]["p1"]["team"] if m["species"] == "Floette-Mega")
    assert mon["sprite"] == "floette-mega"
    assert "log" not in r["game"] and "inputlog" not in r["game"]
    other = client.get(f"/api/games/{VGC_ID}/review?side=p2").json()
    assert other["perspective"] == "p2" and other["steps"][-1]["eval"] == 1.0
    assert client.get(f"/api/games/{VGC_ID}/review?side=all").status_code == 400
    assert client.get("/api/games/nope-1/review").status_code == 404
