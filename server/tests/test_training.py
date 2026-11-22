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
    mask = switch_mask(torch.from_numpy(mon[None]))[0].tolist()
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
