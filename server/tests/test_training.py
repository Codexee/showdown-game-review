"""Stage 5: features, model shapes, and the app using an installed model."""
from __future__ import annotations

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Config
from training.features import (MOVES, N_FIELD, N_IDS, N_MON, N_TOKENS, SIZES, encode, game_samples,
                               policy_target, turn_actions)
from training.model import EvalNet, ModelConfig, switch_mask
from server.battle import parse_log

from .conftest import RANDBATS_ID, VGC_ID, load_replay


def test_turn_actions_skip_pivots_and_cant():
    acts = turn_actions(load_replay(RANDBATS_ID)["log"])
    assert acts[1] == {"p2": ("switch", "Ampharos"), "p1": ("move", "uturn")}  # Metagross came in via U-turn: not a choice
    assert acts[3]["p1"] == ("none", "")  # fully paralyzed


def test_encode_shapes_and_unknowns():
    state = parse_log(load_replay(RANDBATS_ID)["log"]).states[3]
    ids, mon, field, own = encode(state, "p1")
    assert ids.shape == (N_TOKENS, N_IDS) and mon.shape == (N_TOKENS, N_MON) and field.shape == (N_FIELD,)
    assert own[:2] == ["Dedenne", "Metagross"]
    assert ids[0, 0] > 2 and mon[1, 2] == 1.0          # Metagross is active
    # opponent showed Sawsbuck, Ampharos, Palafin by turn 4; slots 9-11 are still unseen (UNK)
    assert (mon[6:9, 3] == 1).all() and (ids[9:12, 0] == 1).all() and (mon[9:12, 3] == 0).all()
    assert policy_target(("move", "knockoff"), own) == MOVES["knockoff"]
    assert policy_target(("switch", "Dedenne"), own) == SIZES["moves"] + 0
    assert policy_target(("switch", "Lanturn"), own) == SIZES["moves"] + len(own)  # not seen yet: first unseen slot
    assert policy_target(("none", ""), own) == -1


def test_samples_only_from_finished_singles():
    samples = list(game_samples(load_replay(RANDBATS_ID)["log"], both_sides=True))
    assert len(samples) == 50 and {s[3] for s in samples} == {0.0, 1.0}
    assert list(game_samples(load_replay(VGC_ID)["log"])) == []  # doubles: not used for training


def test_model_forward_and_switch_mask():
    model = EvalNet(ModelConfig(d=32, layers=1, heads=4, ff=64))
    state = parse_log(load_replay(RANDBATS_ID)["log"]).states[3]
    ids, mon, field, _ = encode(state, "p1")
    v, p = model(torch.from_numpy(ids[None].astype(np.int64)), torch.from_numpy(mon[None]), torch.from_numpy(field[None]))
    assert v.shape == (1,) and p.shape == (1, SIZES["moves"] + 6)
    _, _, aux = model(torch.from_numpy(ids[None].astype(np.int64)), torch.from_numpy(mon[None]),
                      torch.from_numpy(field[None]), aux=True)
    assert aux["opp_policy"].shape == (1, SIZES["moves"] + 6)
    assert aux["set_item"].shape == (1, 6, SIZES["items"]) and aux["set_moves"].shape == (1, 6, SIZES["moves"])
    mask = switch_mask(torch.from_numpy(mon[None])[:, :6])[0].tolist()
    # Dedenne (bench) and the first unseen slot are valid; active Metagross is not
    assert mask[0] is True and mask[1] is False and mask[2] is True and mask[3:] == [False, False, False]


@pytest.fixture
def client_with_model(tmp_path, transport):
    cfg = ModelConfig(d=32, layers=1, heads=4, ff=64)
    (tmp_path / "models").mkdir()
    torch.save({"model": EvalNet(cfg).state_dict(), "config": cfg.to_dict(),
                "info": {"run": "unit-test", "val_acc_text": "n/a"}}, tmp_path / "models" / "current.pt")
    c = Config(data_dir=tmp_path, default_username="Codexe", poll_minutes=15, request_delay=0, poller_enabled=False)
    with TestClient(create_app(c, transport)) as client:
        yield client


def test_review_uses_installed_model_for_singles_only(client_with_model, fake):
    fake.add(load_replay(RANDBATS_ID), uploadtime=1)
    fake.add(load_replay(VGC_ID), uploadtime=2)
    client_with_model.post("/api/import/url", json={"url": RANDBATS_ID})
    client_with_model.post("/api/import/url", json={"url": VGC_ID})
    r = client_with_model.get(f"/api/games/{RANDBATS_ID}/review").json()
    assert r["eval_method"] == "model" and "unit-test" in r["eval_method_text"]
    assert all(0 <= s["eval"] <= 1 for s in r["steps"]) and r["steps"][-1]["eval"] == 0.0  # game over: exact
    vgc = client_with_model.get(f"/api/games/{VGC_ID}/review").json()
    assert vgc["eval_method"] == "placeholder"  # doubles: model not trained for it


def test_turn_events_and_set_labels():
    from training.features import ITEMS, turn_events
    log = load_replay(RANDBATS_ID)["log"]
    ev = turn_events(log)
    assert ev[3]["p2"] == {"moved_first": True} and ev[3]["last_move"] == {"p2": "flipturn"}  # Metagross fully paralyzed
    samples = list(game_samples(log, both_sides=True))
    ids, mon, field, value, pol, opp_pol, labels = samples[6]   # turn 4, p1's view
    assert ids[12, 1] == MOVES["flipturn"] and field[-6] == 1.0  # opponent's last move; opponent moved first
    # Ampharos's Assault Vest was knocked off on turn 2: the label still knows the original item
    assert labels[1, 0] == ITEMS["assaultvest"]
    assert opp_pol >= 0


def test_metrics_temperature_and_paired_gate():
    from training.metrics import fit_temperature, paired, sigmoid
    rng = np.random.default_rng(0)
    logit = rng.normal(0, 2, 20000)
    y = (rng.random(20000) < sigmoid(logit / 2.0)).astype(float)   # true temperature 2
    assert 1.8 < fit_temperature(logit, y) < 2.2
    games = np.repeat(np.arange(2000), 10)
    a = {"key": np.arange(20000), "p": sigmoid(logit), "label": y, "game": games}
    b = {"key": np.arange(20000), "p": sigmoid(logit / 2.0), "label": y, "game": games}
    r = paired(a, b, boot=200)
    assert r["delta_log_loss"] < 0 and r["delta_log_loss_ci90"][1] < 0   # the calibrated one wins clearly


# ---- two-view scoring and strict pairing (vault 2026-11-23-codex-review, fixes 2-3)
def test_two_view_averages_paired_rows():
    import numpy as np
    from training.metrics import two_view, two_view_report
    p = np.array([0.7, 0.4, 0.2, 0.9])      # rows: (p1, p2) of position 1, then of position 2
    y = np.array([1.0, 0.0, 0.0, 1.0])
    g = np.array([5, 5, 6, 6])
    q = two_view(p, y, g)
    assert np.allclose(q, [0.65, 0.35, 0.15, 0.85])
    assert two_view_report(p[1:], y[1:], g[1:]) is None   # unpaired rows: no two-view score
    try:
        two_view(p[1:], y[1:], g[1:])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_compare_runs_refuses_different_samples():
    import numpy as np
    import pytest
    from training.compare_runs import check_same
    a = {"key": np.array(["g#0", "g#1", "h#0", "h#1"]), "label": np.array([1.0, 0.0, 0.0, 1.0])}
    check_same(a, dict(a))
    with pytest.raises(SystemExit):
        check_same(a, {k: v[:2] for k, v in a.items()})
    with pytest.raises(SystemExit):
        check_same(a, {"key": a["key"][::-1], "label": a["label"][::-1]})
    with pytest.raises(SystemExit):
        check_same(a, {"key": a["key"], "label": 1 - a["label"]})
