"""Score a trained model on a built dataset it never trained on (e.g. the future games
collected with inputlogs), next to the remaining-HP placeholder.

    uv run python -m training.test_model --run main --data test

Writes data/models/<run>/test_<data>.json and prints a summary.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch

from training.build_dataset import load
from training.model import EvalNet, ModelConfig
from training.train import MODELS, evaluate, pick_device


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--which", default="best")
    args = ap.parse_args()
    device = pick_device()
    ck = torch.load(MODELS / args.run / f"{args.which}.pt", map_location=device, weights_only=False)
    model = EvalNet(ModelConfig(**ck["config"])).to(device)
    model.load_state_dict(ck["model"])
    data = load(args.data)
    idx = np.arange(len(data["value"]))
    m = evaluate(model, data, idx, device, max_samples=10**9)
    m.update(run=args.run, checkpoint=args.which, step=ck["step"], data=args.data)
    (MODELS / args.run / f"test_{args.data}.json").write_text(json.dumps(m, indent=1))
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
