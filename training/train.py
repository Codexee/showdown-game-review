"""Train the eval model (vault spec-eval-model, ADR-0005).

    # small test run (minutes)
    uv run python -m training.train --data small --run test --minutes 5
    # full run (overnight); safe to stop and resume
    uv run python -m training.train --data full --run main --hours 10 --resume

Writes data/models/<run>/: last.pt (resume point), best.pt (best validation loss),
metrics.jsonl (one line per evaluation), config.json. Stops cleanly at the time limit
or on Ctrl-C / SIGTERM, saving last.pt first.
"""
from __future__ import annotations

import argparse
import json
import math
import signal
import threading
import time
import queue
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from server.config import ROOT
from training.build_dataset import load
from training.model import EvalNet, ModelConfig, count_params

MODELS = ROOT / "data" / "models"


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def batches(data: dict, idx: np.ndarray, bs: int, rng: np.random.Generator, shuffle: bool):
    order = rng.permutation(idx) if shuffle else idx
    for i in range(0, len(order) - (bs - 1 if shuffle else 0), bs):
        b = np.sort(order[i:i + bs])  # sorted reads are kinder to the memory map
        yield (np.asarray(data["ids"][b], dtype=np.int64), np.asarray(data["mon"][b], dtype=np.float32),
               np.asarray(data["field"][b], dtype=np.float32), np.asarray(data["value"][b], dtype=np.float32),
               np.asarray(data["policy"][b], dtype=np.int64), np.asarray(data["field"][b, 0], dtype=np.float32))


def prefetch(gen, depth: int = 6):
    """Read batches from disk on a background thread while the GPU trains."""
    q: queue.Queue = queue.Queue(depth)
    done = object()

    def run():
        for item in gen:
            q.put(item)
        q.put(done)
    threading.Thread(target=run, daemon=True).start()
    while (item := q.get()) is not done:
        yield item


def placeholder(mon: torch.Tensor) -> torch.Tensor:
    """server/evaluate.py's remaining-HP estimate, on encoded samples."""
    hp = mon[:, :12, 0] * (1 - mon[:, :12, 1])
    return torch.sigmoid(0.5 * (hp[:, :6].sum(1) - hp[:, 6:].sum(1)))


def valid_policy(p_logit: torch.Tensor, policy: torch.Tensor) -> torch.Tensor:
    """Samples with a policy target the model can score. A few targets point at a slot
    the switch mask rules out (e.g. a fainted Pokemon brought back by Revival Blessing);
    those are skipped rather than giving an infinite loss."""
    m = policy >= 0
    target_logit = p_logit.gather(1, policy.clamp(min=0).unsqueeze(1)).squeeze(1)
    return m & torch.isfinite(target_logit)


def to_dev(batch, device):
    return [torch.from_numpy(x).to(device, non_blocking=True) for x in batch]


@torch.no_grad()
def evaluate(model, data, idx, device, bs=4096, max_samples=200_000) -> dict:
    model.eval()
    if len(idx) > max_samples:
        idx = np.random.default_rng(0).choice(idx, max_samples, replace=False)
    n = 0
    sums = {"value_loss": 0.0, "value_acc": 0.0, "brier": 0.0, "policy_loss": 0.0, "top1": 0.0, "top3": 0.0, "pol_n": 0,
            "base_loss": 0.0, "base_acc": 0.0}
    bins = np.zeros((10, 3))  # count, sum predicted, sum actual
    by_turn = {"turns 1-5": [0, 0], "turns 6-15": [0, 0], "turns 16+": [0, 0]}
    for ids, mon, field, value, policy, turn in batches(data, np.sort(idx), bs, np.random.default_rng(0), False):
        ids_t, mon_t, field_t, value_t, policy_t = to_dev([ids, mon, field, value, policy], device)
        v_logit, p_logit = model(ids_t, mon_t, field_t)
        p = torch.sigmoid(v_logit)
        sums["value_loss"] += F.binary_cross_entropy_with_logits(v_logit, value_t, reduction="sum").item()
        correct = ((p > 0.5).float() == value_t).float()
        base = placeholder(mon_t)  # the remaining-HP placeholder, for comparison
        sums["base_loss"] += F.binary_cross_entropy(base.clamp(1e-6, 1 - 1e-6), value_t, reduction="sum").item()
        sums["base_acc"] += ((base > 0.5).float() == value_t).float().sum().item()
        sums["value_acc"] += correct.sum().item()
        sums["brier"] += ((p - value_t) ** 2).sum().item()
        m = valid_policy(p_logit, policy_t)
        if m.any():
            sums["policy_loss"] += F.cross_entropy(p_logit[m], policy_t[m], reduction="sum").item()
            top3 = p_logit[m].topk(3, dim=-1).indices
            sums["top1"] += (top3[:, 0] == policy_t[m]).sum().item()
            sums["top3"] += (top3 == policy_t[m].unsqueeze(1)).any(1).sum().item()
            sums["pol_n"] += int(m.sum().item())
        pn, vn, cn = p.cpu().numpy(), value, correct.cpu().numpy()
        b = np.minimum((pn * 10).astype(int), 9)
        np.add.at(bins, b, np.stack([np.ones_like(pn), pn, vn], 1))
        t = turn * 50
        for name, sel in (("turns 1-5", t <= 5.5), ("turns 6-15", (t > 5.5) & (t <= 15.5)), ("turns 16+", t > 15.5)):
            by_turn[name][0] += int(cn[sel].sum())
            by_turn[name][1] += int(sel.sum())
        n += len(value)
    model.train()
    pol_n = max(sums.pop("pol_n"), 1)
    out = {"value_loss": sums["value_loss"] / n, "value_acc": sums["value_acc"] / n, "brier": sums["brier"] / n,
           "policy_loss": sums["policy_loss"] / pol_n, "policy_top1": sums["top1"] / pol_n,
           "policy_top3": sums["top3"] / pol_n, "samples": n,
           "baseline_value_loss": sums["base_loss"] / n, "baseline_value_acc": sums["base_acc"] / n}
    nz = bins[:, 0] > 0
    out["ece"] = float(np.sum(np.abs(bins[nz, 1] - bins[nz, 2])) / n)  # expected calibration error
    out["acc_by_turn"] = {k: (c / t if t else None) for k, (c, t) in by_turn.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dataset name in data/train/ds/")
    ap.add_argument("--run", required=True)
    ap.add_argument("--hours", type=float, default=0)
    ap.add_argument("--minutes", type=float, default=0)
    ap.add_argument("--epochs", type=float, default=100)
    ap.add_argument("--bs", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--wd", type=float, default=0.05)
    ap.add_argument("--policy-weight", type=float, default=0.5)
    ap.add_argument("--eval-every", type=int, default=2000, help="steps")
    ap.add_argument("--d", type=int, default=256)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=8)
    ap.add_argument("--ff", type=int, default=1024)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    budget = args.hours * 3600 + args.minutes * 60 or float("inf")
    out = MODELS / args.run
    out.mkdir(parents=True, exist_ok=True)
    device = pick_device()
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    data = load(args.data)
    split = np.asarray(data["split"])
    train_idx, val_idx = np.flatnonzero(split == 0), np.flatnonzero(split == 1)
    steps_per_epoch = len(train_idx) // args.bs
    total_steps = max(1, int(steps_per_epoch * args.epochs))

    cfg = ModelConfig(d=args.d, layers=args.layers, heads=args.heads, ff=args.ff)
    model = EvalNet(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd, betas=(0.9, 0.98))
    warmup = min(2000, total_steps // 20 + 1)

    def lr_at(step: int) -> float:
        if step < warmup:
            return args.lr * (step + 1) / warmup
        # cosine to 10% over the planned steps (or the time budget, whichever ends first)
        frac = min(1.0, (step - warmup) / max(1, planned_steps - warmup))
        return args.lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * frac)))

    step, best, best_policy, elapsed_before = 0, float("inf"), float("inf"), 0.0
    if args.resume and (out / "last.pt").exists():
        ck = torch.load(out / "last.pt", map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step, best, elapsed_before = ck["step"], ck["best"], ck.get("elapsed", 0.0)
        best_policy = ck.get("best_policy", float("inf"))
        print(f"resumed at step {step} (best val loss {best:.4f})", flush=True)
    planned_steps = total_steps

    (out / "config.json").write_text(json.dumps({"model": cfg.to_dict(), "args": vars(args) | {"resume": False},
                                                 "data": args.data, "params": count_params(model)}, indent=1))
    print(f"device {device}; {count_params(model) / 1e6:.2f}M params; train {len(train_idx)} / val {len(val_idx)} "
          f"samples; {steps_per_epoch} steps per epoch", flush=True)

    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))

    def save(name: str, extra: dict | None = None):
        tmp = out / f"{name}.tmp"
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": step, "best": best,
                    "elapsed": elapsed_before + time.time() - t0, "config": cfg.to_dict(), **(extra or {})}, tmp)
        tmp.replace(out / f"{name}.pt")

    def log_eval():
        nonlocal best, best_policy
        m = evaluate(model, data, val_idx, device)
        m.update(step=step, epoch=round(step / max(1, steps_per_epoch), 3), lr=lr_at(step),
                 minutes=round((elapsed_before + time.time() - t0) / 60, 1), train_loss=round(run_loss, 4))
        with open(out / "metrics.jsonl", "a") as f:
            f.write(json.dumps(m) + "\n")
        print(f"step {step} ep {m['epoch']} | train {run_loss:.4f} | val value_loss {m['value_loss']:.4f} "
              f"acc {m['value_acc']:.3f} ece {m['ece']:.3f} (placeholder {m['baseline_value_loss']:.4f} / "
              f"{m['baseline_value_acc']:.3f}) | policy top1 {m['policy_top1']:.3f} "
              f"top3 {m['policy_top3']:.3f} | {m['minutes']} min", flush=True)
        # best.pt = best value loss (what the eval bar uses); best_policy.pt = best policy
        # loss (stage 6 move review). Value peaks early, policy keeps improving (test run).
        if m["value_loss"] < best:
            best = m["value_loss"]
            save("best", {"metrics": m})
        if m["policy_loss"] < best_policy:
            best_policy = m["policy_loss"]
            save("best_policy", {"metrics": m})
        save("last", {"best_policy": best_policy})

    t0 = time.time()
    run_loss = float("nan")
    model.train()
    done = False
    while not done:
        for batch in prefetch(batches(data, train_idx, args.bs, rng, True)):
            ids, mon, field, value, policy, _ = to_dev(batch, device)
            for g in opt.param_groups:
                g["lr"] = lr_at(step)
            v_logit, p_logit = model(ids, mon, field)
            loss = F.binary_cross_entropy_with_logits(v_logit, value)
            m = valid_policy(p_logit, policy)
            if m.any():
                loss = loss + args.policy_weight * F.cross_entropy(p_logit[m], policy[m])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            step += 1
            lv = loss.item() if step % 50 == 0 else None
            if lv is not None:
                run_loss = lv if math.isnan(run_loss) else 0.95 * run_loss + 0.05 * lv
            if step % args.eval_every == 0:
                log_eval()
            if stop["flag"] or time.time() - t0 > budget or step >= total_steps:
                done = True
                break
    log_eval()
    print(f"finished at step {step}; best val value loss {best:.4f}, policy loss {best_policy:.4f}; "
          f"checkpoints in {out}", flush=True)


if __name__ == "__main__":
    main()
