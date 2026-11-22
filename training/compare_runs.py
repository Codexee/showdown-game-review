"""Paired gate (PS Dashboard practice, vault benchmark-best-in-class): compare two
models' predictions on the SAME samples before installing the new one.

    uv run python -m training.compare_runs --a test2 --b p0 --data test

Reads data/models/<run>/preds_<data>.npz (from training.test_model), aligns by sample
key, and reports b - a for log-loss and Brier with 90% bootstrap bands over games,
overall and per phase. b passes the gate only if the whole band is below zero.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from training.metrics import PHASES, paired
from training.train import MODELS


def load_preds(run: str, data: str) -> dict[str, np.ndarray]:
    z = np.load(MODELS / run / f"preds_{data}.npz")
    return {k: z[k] for k in z.files}


def align(a: dict, b: dict) -> tuple[dict, dict]:
    common, ia, ib = np.intersect1d(a["key"], b["key"], return_indices=True)
    return ({k: v[ia] for k, v in a.items()}, {k: v[ib] for k, v in b.items()})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="current model run")
    ap.add_argument("--b", required=True, help="candidate model run")
    ap.add_argument("--data", default="test")
    args = ap.parse_args()
    a, b = align(load_preds(args.a, args.data), load_preds(args.b, args.data))
    if not np.allclose(a["label"], b["label"]):
        raise SystemExit("labels differ for the same keys: the two prediction files don't describe the same games")
    report = {"overall": paired(a, b)}
    for name, (lo, hi) in PHASES.items():
        m = (a["fainted"] >= lo) & (a["fainted"] <= hi)
        if m.sum() > 100:
            report[name] = paired({k: v[m] for k, v in a.items()}, {k: v[m] for k, v in b.items()}, boot=500)
    hq = np.maximum(a["rating"], b["rating"]) >= 1500  # older prediction files have no ratings
    if hq.sum() > 100:
        report["rating 1500+"] = paired({k: v[hq] for k, v in a.items()}, {k: v[hq] for k, v in b.items()}, boot=500)
    o = report["overall"]
    report["verdict"] = ("b is better (whole 90% band below zero)" if o["delta_log_loss_ci90"][1] < 0 else
                         "b is worse (whole 90% band above zero)" if o["delta_log_loss_ci90"][0] > 0 else
                         "no clear difference (band crosses zero)")
    out = MODELS / args.b / f"gate_vs_{args.a}_{args.data}.json"
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
