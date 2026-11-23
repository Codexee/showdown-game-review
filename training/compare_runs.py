"""Paired gate (PS Dashboard practice, vault benchmark-best-in-class): compare two
models' predictions on the SAME samples before installing the new one.

    uv run python -m training.compare_runs --a test2 --b p0 --data test

Reads data/models/<run>/preds_<data>.npz (from training.test_model), checks that both
files cover exactly the same samples with the same labels, and reports b - a for log-loss
and Brier with 90% bootstrap bands over games, overall and per phase. b passes the gate
only if the whole band is below zero.

By default both models are scored from both players' views (`--view two`,
training.metrics.two_view), the way the eval bar and the move review use them. `--view
single` scores each row from its own side only (the scoring before 2026-11-23).
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from training.metrics import PHASES, paired, two_view
from training.train import MODELS


def load_preds(run: str, data: str) -> dict[str, np.ndarray]:
    z = np.load(MODELS / run / f"preds_{data}.npz")
    return {k: z[k] for k in z.files}


def check_same(a: dict, b: dict) -> None:
    """Both files must describe exactly the same samples, in the same order, with the same
    labels. (Before 2026-11-23 the keys were intersected silently; vault 2026-11-23-codex-review.)"""
    for name, z in (("a", a), ("b", b)):
        if len(np.unique(z["key"])) != len(z["key"]):
            raise SystemExit(f"{name}: duplicate sample keys in the prediction file")
    if len(a["key"]) != len(b["key"]) or not np.array_equal(a["key"], b["key"]):
        only_a = len(np.setdiff1d(a["key"], b["key"]))
        only_b = len(np.setdiff1d(b["key"], a["key"]))
        raise SystemExit(f"the prediction files cover different samples ({only_a} only in a, {only_b} only in b, "
                         f"or a different order): re-run training.test_model for both on the same dataset")
    if not np.allclose(a["label"], b["label"]):
        raise SystemExit("labels differ for the same keys: the two prediction files don't describe the same games")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="current model run")
    ap.add_argument("--b", required=True, help="candidate model run")
    ap.add_argument("--data", default="test")
    ap.add_argument("--view", choices=["two", "single"], default="two")
    args = ap.parse_args()
    a, b = load_preds(args.a, args.data), load_preds(args.b, args.data)
    check_same(a, b)
    if args.view == "two":
        for z in (a, b):
            z["p"] = two_view(z["p"], z["label"], z["game"])
    report = {"view": args.view, "overall": paired(a, b)}
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
    suffix = "" if args.view == "two" else "_single"
    out = MODELS / args.b / f"gate_vs_{args.a}_{args.data}{suffix}.json"
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
