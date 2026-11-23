"""Install a trained run's best checkpoint for the app: data/models/current.pt.

    uv run python -m training.export --run main

Keeps only what inference needs (weights, model config) plus a short summary that the
review screen shows. The server picks the new file up on the next review request.
"""
from __future__ import annotations

import argparse
import json

import torch

from server.config import ROOT

MODELS = ROOT / "data" / "models"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--which", default="best", choices=["best", "last"])
    ap.add_argument("--test-data", default="test_pinned", help="dataset name the run was scored on")
    args = ap.parse_args()
    ck = torch.load(MODELS / args.run / f"{args.which}.pt", map_location="cpu", weights_only=False)
    m = ck.get("metrics", {})
    # Prefer the score on future games (training.test_model) over same-period validation:
    # validation overstated the value head's edge in the first test run.
    test_file = MODELS / args.run / f"test_{args.test_data}.json"
    t = json.loads(test_file.read_text()) if test_file.exists() else {}
    src, label = (t, "newer games it never saw") if t.get("value_acc") is not None else (m, "held-out games")
    if t.get("two_view"):  # the bar averages both players' views (server/model_eval.py), so quote that score
        src = {**t, "value_acc": t["two_view"]["acc"]}
    info = {
        "run": args.run, "step": ck["step"], "val_value_loss": m.get("value_loss"),
        "val_acc": m.get("value_acc"), "baseline_val_acc": m.get("baseline_value_acc"),
        "test_acc": t.get("value_acc"), "baseline_test_acc": t.get("baseline_value_acc"),
        "val_acc_text": f"{src['value_acc']:.0%} of the time on {label} (placeholder: {src['baseline_value_acc']:.0%})"
        if src.get("value_acc") is not None and src.get("baseline_value_acc") is not None else "n/a",
        "policy_top3": m.get("policy_top3"),
    }
    tmp = MODELS / "current.pt.tmp"
    torch.save({"model": ck["model"], "config": ck["config"], "info": info,
                "temperature": float(ck.get("temperature", 1.0))}, tmp)
    tmp.replace(MODELS / "current.pt")
    print(f"installed {args.run}/{args.which}.pt (step {ck['step']}) as data/models/current.pt: {info}")


if __name__ == "__main__":
    main()
