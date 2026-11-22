"""The log parser (server/battle) against Showdown's own simulator.

fixtures/battles/ holds real gen9randombattle replays chosen to cover tricky mechanics,
and truth.jsonl holds the simulator's true state at every turn of each one
(made with `node tools/sim-states.cjs` at the commit in each replay's inputlog).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.battle import parse_log, view_for
from server.battle.parser import _parse_hp, _split
from server.battle.view import shown_percent
from tools.compare_parser import UNKNOWABLE, compare_replay

BATTLES = Path(__file__).parent / "fixtures" / "battles"
TRUTH = {json.loads(line)["id"]: json.loads(line) for line in open(BATTLES / "truth.jsonl")}
PROTO = Path(__file__).resolve().parents[2] / "data" / "proto"


def replay(rid: str) -> dict:
    return json.loads((BATTLES / f"{rid}.json").read_text())


@pytest.mark.parametrize("rid", sorted(TRUTH))
def test_matches_simulator(rid):
    checked, errs = compare_replay(replay(rid), TRUTH[rid])
    real = [f"{field}: {detail}" for field, detail in errs if field not in UNKNOWABLE]
    assert checked == len(TRUTH[rid]["states"])
    assert real == [], "\n".join(real[:10])


@pytest.mark.skipif(not (PROTO / "holdout2-truth.jsonl").exists(), reason="local prototype data not present")
@pytest.mark.parametrize("folder,truth_file", [("replays", "truth.jsonl"), ("holdout", "holdout-truth.jsonl"),
                                               ("holdout2", "holdout2-truth.jsonl")])
def test_matches_simulator_on_local_sets(folder, truth_file):
    """All 261 local games (data/proto, git-ignored). Skipped on machines without it."""
    bad = []
    for line in open(PROTO / truth_file):
        truth = json.loads(line)
        rep = json.loads((PROTO / folder / f"{truth['id']}.json").read_text())
        _, errs = compare_replay(rep, truth)
        bad += [f"{truth['id']} {f}: {d}" for f, d in errs if f not in UNKNOWABLE]
    assert bad == [], "\n".join(bad[:10])


def test_one_state_per_turn_plus_final():
    result = parse_log(replay("gen9randombattle-2705718015")["log"])
    turns = [s["turn"] for s in result.states]
    assert turns[:3] == [1, 2, 3] and turns[-1] == turns[-2] == 25
    assert result.states[-1]["ended"] and result.states[-1]["winner"] == "charizardslayer1"
    assert result.format_id == "gen9randombattle" and not result.warnings


def test_codexe_game_details():
    states = parse_log(replay("gen9randombattle-2705718015")["log"]).states
    t4 = states[3]
    p2 = {m["name"]: m for m in t4["sides"]["p2"]["team"]}
    assert p2["Ampharos"]["item"] == ""          # knocked off by Dedenne
    assert p2["Ampharos"]["hp"] == 186 and p2["Ampharos"]["maxhp"] == 302
    p1 = {m["name"]: m for m in t4["sides"]["p1"]["team"]}
    assert p1["Metagross"]["status"] == "par" and p1["Metagross"]["active"]


def test_as_one_and_imposter():
    calyrex = next(m for m in parse_log(replay("gen9randombattle-2717776712")["log"]).states[3]["sides"]["p2"]["team"]
                   if m["name"] == "Calyrex")
    assert calyrex["ability"] == "asonespectrier"  # not Unnerve / Grim Neigh
    ditto = next(m for m in parse_log(replay("gen9randombattle-2717780518")["log"]).states[-2]["sides"]["p2"]["team"]
                 if m["name"] == "Ditto")
    assert ditto["moves"] == []                    # moves used while transformed aren't Ditto's


def test_illusion_reveal_moves_hp_to_zoroark():
    states = parse_log(replay("gen9randombattle-2717793304")["log"]).states
    t8 = {m["name"]: m for m in states[7]["sides"]["p2"]["team"]}
    assert t8["Zoroark"]["active"] and (t8["Zoroark"]["hp"], t8["Zoroark"]["maxhp"]) == (187, 235)
    assert not t8["Mesprit"]["active"]


def test_glaive_rush_lasts_one_extra_turn():
    states = {s["turn"]: s for s in parse_log(replay("gen9randombattle-2717757320")["log"]).states if not s["ended"]}
    bax = lambda t: next(m for m in states[t]["sides"]["p1"]["team"] if m["name"] == "Baxcalibur")
    assert "glaiverush" in bax(10)["volatiles"]


def test_split_tags_and_hp():
    assert _split("|tier|[Gen 9] Random Battle") == ("tier", ["[Gen 9] Random Battle"], {})
    assert _split("|-heal|p1a: X|50/100|[from] item: Leftovers|[of] p2a: Y") == \
        ("-heal", ["p1a: X", "50/100"], {"from": "item: Leftovers", "of": "p2a: Y"})
    assert _parse_hp("261/261 par") == (261, 261, "par", False)
    assert _parse_hp("0 fnt") == (0, None, "", True)
    assert _parse_hp("20/100y") == (20, 100, "", False)  # Champions colour suffix


def test_view_rounds_opponent_hp_like_showdown():
    assert shown_percent(253, 253) == 100
    assert shown_percent(252, 253) == 99          # ceil, but never 100 unless full
    assert shown_percent(1, 253) == 1
    assert shown_percent(1, 400, "gen9championsvgc2026regmc") == 1  # floor, at least 1
    assert shown_percent(199, 200, "gen9championsvgc2026regmc") == 99
    state = parse_log(replay("gen9randombattle-2705718015")["log"]).states[3]
    mine = view_for(state, "p1", "gen9randombattle")
    amph = next(m for m in mine["sides"]["p2"]["team"] if m["name"] == "Ampharos")
    meta = next(m for m in mine["sides"]["p1"]["team"] if m["name"] == "Metagross")
    assert (amph["hp"], amph["maxhp"], amph["hp_exact"]) == (62, 100, False)  # 186/302 -> 62%
    assert meta["hp_exact"] and meta["maxhp"] == 256
    with pytest.raises(ValueError):
        view_for(state, "p3")
