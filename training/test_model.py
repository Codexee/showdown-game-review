"""Score a trained model on a dataset it never trained on (the future games collected
with inputlogs), next to the remaining-HP placeholder, with 90% bootstrap intervals over
games, by phase and on the high-rating slice. Uses the temperature fitted on validation.

    uv run python -m training.test_model --run main --data test

Writes data/models/<run>/test_<data>.json (report; `two_view` = both players' views
averaged, for datasets built with --both-sides) and preds_<data>.npz (per-sample
predictions keyed by game id and sample number, for training.compare_runs).
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch

from training.build_dataset import load
from training.metrics import sigmoid, two_view_report
from training.model import EvalNet, ModelConfig
from training.train import MODELS, collect, pick_device, summarize
from server.config import ROOT


def sample_keys(data_name: str, game_index: np.ndarray) -> np.ndarray:
    """'<game id>#<n>' for the n-th sample of each game: stable across dataset rebuilds."""
    ids = json.loads((ROOT / "data" / "train" / "ds" / data_name / "game_ids.json").read_text())
    keys, counts = [], {}
    for g in game_index:
        n = counts.get(int(g), 0)
        counts[int(g)] = n + 1
        keys.append(f"{ids[int(g)]}#{n}")
    return np.asarray(keys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--which", default="best")
    ap.add_argument("--boot", type=int, default=500)
    args = ap.parse_args()
    device = pick_device()
    ck = torch.load(MODELS / args.run / f"{args.which}.pt", map_location=device, weights_only=False)
    model = EvalNet(ModelConfig(**ck["config"])).to(device)
    model.load_state_dict(ck["model"])
    data = load(args.data)
    arr = collect(model, data, np.arange(len(data["value"])), device, max_samples=10**9)
    temperature = float(ck.get("temperature", 1.0))
    m = summarize(arr, temperature=temperature, boot=args.boot)
    m.update(run=args.run, checkpoint=args.which, step=ck["step"], data=args.data)
    # Both players' views averaged, as the eval bar and move review use the model (2026-11-23).
    m["two_view"] = two_view_report(sigmoid(arr["logit"] / temperature), arr["label"], arr["game"], boot=args.boot)
    (MODELS / args.run / f"test_{args.data}.json").write_text(json.dumps(m, indent=1))
    np.savez_compressed(MODELS / args.run / f"preds_{args.data}.npz", key=sample_keys(args.data, arr["game"]),
                        p=sigmoid(arr["logit"] / temperature), p_raw=sigmoid(arr["logit"]), label=arr["label"], game=arr["game"],
                        fainted=arr["fainted"], rating=arr["rating"])
    c = m["calibrated"]
    print(json.dumps({"model": c["model"], "placeholder": c["placeholder"], "ci90_log_loss": c.get("model_log_loss_ci90"),
                      "ci90_acc": c.get("model_acc_ci90"), "model_minus_placeholder_ci90": c.get("model_minus_placeholder_ci90"),
                      "by_phase": {k: {"model_acc": v["model"]["acc"], "placeholder_acc": v["placeholder"]["acc"]}
                                   for k, v in c["by_phase"].items()},
                      "rating_1500_plus": c.get("rating_1500_plus"), "policy_top1": m["policy_top1"],
                      "policy_top3": m["policy_top3"], "opp_policy_top3": m["opp_policy_top3"],
                      "set_prediction": m["set_prediction"], "temperature": temperature,
                      "two_view": m["two_view"]}, indent=1))


if __name__ == "__main__":
    main()
