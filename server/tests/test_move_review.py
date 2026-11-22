"""Move review (stage 6): solver, verdicts, summary, job gating, and the sim engine."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from server.config import ROOT
from server.review.analyze import label, lichess_accuracy, solve, summarize, verdict
from server.review.jobs import supported

from .conftest import RANDBATS_ID, VGC_ID, load_replay
from .test_sync_and_api import client  # noqa: F401  (fixture)


def test_lichess_accuracy_curve():
    assert lichess_accuracy(0) == pytest.approx(100, abs=0.01)
    assert 60 < lichess_accuracy(10) < 70
    assert lichess_accuracy(100) == 0
    xs = [lichess_accuracy(x) for x in range(0, 40, 5)]
    assert xs == sorted(xs, reverse=True)


@pytest.mark.parametrize("regret,before,want", [
    (0.2, 0.5, "best"), (3, 0.5, "good"), (5, 0.5, "inaccuracy"), (12, 0.5, "mistake"), (25, 0.5, "blunder"),
    (25, 0.9, "mistake"), (6, 0.9, "good"), (0.1, 0.9, "best"),
])
def test_verdict_bands(regret, before, want):
    assert verdict(regret, before) == want


def test_solve_rock_paper_scissors_is_uniform():
    M = np.array([[0.5, 0, 1], [1, 0.5, 0], [0, 1, 0.5]])
    x, y = solve(M)
    assert np.allclose(x, 1 / 3, atol=0.02) and np.allclose(y, 1 / 3, atol=0.02)


def test_solve_finds_dominant_choice():
    M = np.array([[0.7, 0.8], [0.4, 0.5]])  # row 0 dominates; column 0 is better for p2
    x, y = solve(M)
    assert x[0] > 0.98 and y[0] > 0.98


def test_label():
    info = {"moves": [{"id": "uturn", "name": "U-turn"}], "team": [{"name": "Venu", "species": "Venusaur"}],
            "canTera": "Fire"}
    assert label("move 1", info) == "U-turn"
    assert label("move 1 terastallize", info) == "U-turn + Tera Fire"
    assert label("switch 1", info) == "Switch to Venusaur"


def test_summarize_counts_and_luck():
    side = lambda v, r: {"verdict": v, "regret": r, "played_label": "A", "best_label": "B"}  # noqa: E731
    turns = [
        {"turn": 1, "luck_p1": 0.10, "sides": {"p1": side("best", 0.0), "p2": side("mistake", 12.0)}},
        {"turn": 2, "luck_p1": -0.05, "sides": {"p1": side("forced", 0.0), "p2": side("blunder", 30.0)}},
    ]
    final = SimpleNamespace(sides={"p1": SimpleNamespace(name="A"), "p2": SimpleNamespace(name="B")})
    s = summarize(turns, final)
    assert s["p1"]["graded_turns"] == 1 and s["p1"]["accuracy"] == pytest.approx(100, abs=0.1)
    assert s["p2"]["counts"]["blunder"] == 1 and s["p2"]["counts"]["mistake"] == 1
    assert s["p2"]["worst"][0]["turn"] == 2
    assert s["p1"]["luck_points"] == 5.0 and s["p2"]["luck_points"] == -5.0
    assert s["biggest_luck"][0] == {"turn": 1, "luck_p1_points": 10.0}


def test_supported():
    rb = load_replay(RANDBATS_ID)
    assert supported({"inputlog": rb["inputlog"], "gametype": "singles", "format_id": "gen9randombattle"}) is None
    assert "inputlog" in supported({"inputlog": None, "gametype": "doubles", "format_id": "gen9vgc"})
    assert "Random Battle" in supported({"inputlog": "x", "gametype": "doubles", "format_id": "gen9championsvgc"})


def test_analysis_api_gates(client, fake):  # noqa: F811
    fake.add(load_replay(VGC_ID), uploadtime=1)
    client.post("/api/import/url", json={"url": VGC_ID})
    assert client.get(f"/api/games/{VGC_ID}/analysis").json() == {"status": "none"}
    r = client.post(f"/api/games/{VGC_ID}/analysis").json()
    assert r["status"] == "unsupported"
    assert client.post(f"/api/games/{VGC_ID}/analysis", json={"seeds": 1}).status_code == 422
    assert client.get("/api/games/nope-1/analysis").status_code == 404


SIM = ROOT / "data" / "sim" / "ps" / "cbdc8519ef"


@pytest.mark.skipif(not (SIM / "dist" / "sim" / "battle-stream.js").exists(),
                    reason="needs the Showdown build for the fixture's commit (data/sim/ps/cbdc8519ef)")
def test_engine_replays_and_expands():
    from server.review.engine import ReviewEngine

    rb = load_replay(RANDBATS_ID)
    with ReviewEngine(SIM) as eng:
        loaded = eng.load(rb["inputlog"])
        t1 = loaded["turns"][0]
        assert t1["played"]["p1"] in t1["options"]["p1"] and t1["played"]["p2"] in t1["options"]["p2"]
        pair = (t1["played"]["p1"], t1["played"]["p2"])
        a = eng.expand(t1["turn"], [pair], seeds=2)
        b = eng.expand(t1["turn"], [pair], seeds=2)
        assert len(a) == 2 and not any(c["invalid"] for c in a)
        assert [c["branches"][0]["lines"] for c in a] == [c["branches"][0]["lines"] for c in b]  # seeded
