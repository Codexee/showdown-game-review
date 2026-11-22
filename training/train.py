"""Train the eval model (vault spec-eval-model, ADR-0005, benchmark-best-in-class).

    # small test run (minutes)
    uv run python -m training.train --data medium --run test3 --minutes 12
    # full run (overnight); safe to stop and resume
    uv run python -m training.train --data full --run main --hours 9 --resume

Writes data/models/<run>/: last.pt (resume point), best.pt (best validation value loss:
what the eval bar uses; includes the fitted temperature), best_policy.pt, metrics.jsonl,
config.json. Stops cleanly at the time limit or on Ctrl-C / SIGTERM, saving last.pt.
"""
from __future__ import annotations

import argparse
import json
import math
import queue
import signal
import threading
import time

import numpy as np
import torch
import torch.nn.functional as F

from server.config import ROOT
from training.build_dataset import load
from training.metrics import fit_temperature, value_report
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
        yield b, {
            "ids": np.asarray(data["ids"][b], dtype=np.int64), "mon": np.asarray(data["mon"][b], dtype=np.float32),
            "field": np.asarray(data["field"][b], dtype=np.float32), "value": np.asarray(data["value"][b], dtype=np.float32),
            "policy": np.asarray(data["policy"][b], dtype=np.int64), "opp_policy": np.asarray(data["opp_policy"][b], dtype=np.int64),
            "opp_set": np.asarray(data["opp_set"][b], dtype=np.int64),
        }


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


def to_dev(batch: dict, device) -> dict:
    return {k: torch.from_numpy(v).to(device, non_blocking=True) for k, v in batch.items()}


def placeholder(mon: torch.Tensor) -> torch.Tensor:
    """server/evaluate.py's remaining-HP estimate, on encoded samples."""
    hp = mon[:, :12, 0] * (1 - mon[:, :12, 1])
    return torch.sigmoid(0.5 * (hp[:, :6].sum(1) - hp[:, 6:].sum(1)))


def valid_choice(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Samples whose choice target the model can score (some point at a slot the switch
    mask rules out, e.g. a fainted Pokemon revived by Revival Blessing; skipped)."""
    m = target >= 0
    t = logits.gather(1, target.clamp(min=0).unsqueeze(1)).squeeze(1)
    return m & torch.isfinite(t)


def choice_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor | None:
    m = valid_choice(logits, target)
    return F.cross_entropy(logits[m], target[m]) if m.any() else None


def set_losses(out: dict, opp_set: torch.Tensor) -> dict[str, torch.Tensor]:
    """Auxiliary: predict each opposing Pokemon's item / ability / Tera / moves as revealed
    by the end of the game. Unknown labels (-1) are ignored. Moves use a multi-positive
    cross-entropy (each revealed move is a target), because 'not revealed' isn't 'absent'."""
    losses = {}
    for j, key in ((0, "set_item"), (1, "set_ability"), (2, "set_tera")):
        t = opp_set[..., j]
        m = t >= 0
        if m.any():
            losses[key] = F.cross_entropy(out[key][m], t[m])
    moves = opp_set[..., 3:]
    has = (moves >= 0).any(-1)
    if has.any():
        logp = F.log_softmax(out["set_moves"][has], dim=-1)
        t = moves[has]
        mm = t >= 0
        picked = logp.gather(1, t.clamp(min=0)) * mm
        losses["set_moves"] = -(picked.sum(1) / mm.sum(1)).mean()
    return losses


@torch.no_grad()
def collect(model, data, idx, device, bs=4096, max_samples=200_000) -> dict:
    """Run the model over samples; return per-sample arrays and aux accuracies."""
    model.eval()
    if len(idx) > max_samples:
        idx = np.random.default_rng(0).choice(idx, max_samples, replace=False)
    idx = np.sort(idx)
    cols = {k: [] for k in ("logit", "label", "base", "fainted", "pol_ok", "pol_top1", "pol_top3",
                            "opp_ok", "opp_top1", "opp_top3", "pol_loss")}
    aux_hits = {"item": [0, 0], "ability": [0, 0], "tera": [0, 0], "moves_top4": [0, 0]}
    for _, batch in batches(data, idx, bs, np.random.default_rng(0), False):
        t = to_dev(batch, device)
        v, p, out = model(t["ids"], t["mon"], t["field"], aux=True)
        cols["logit"].append(v.float().cpu().numpy())
        cols["label"].append(batch["value"])
        cols["base"].append(placeholder(t["mon"]).cpu().numpy())
        cols["fainted"].append(batch["mon"][:, :12, 1].sum(1).round().astype(np.int16))
        for name, logits, target in (("pol", p, t["policy"]), ("opp", out["opp_policy"], t["opp_policy"])):
            m = valid_choice(logits, target)
            top3 = logits.topk(3, dim=-1).indices
            cols[f"{name}_ok"].append(m.cpu().numpy())
            cols[f"{name}_top1"].append((top3[:, 0] == target).cpu().numpy())
            cols[f"{name}_top3"].append((top3 == target.unsqueeze(1)).any(1).cpu().numpy())
            if name == "pol":
                ce = torch.zeros_like(v)
                if m.any():
                    ce[m] = F.cross_entropy(logits[m], target[m], reduction="none")
                cols["pol_loss"].append(ce.cpu().numpy())
        # Score set prediction only on what was NOT revealed yet at that turn (a revealed
        # item is in the input, so predicting it is trivial).
        s = t["opp_set"]
        seen_ids = t["ids"][:, 6:12]                                      # [B,6,8] opponent tokens
        for j, key, name, col in ((0, "set_item", "item", 1), (1, "set_ability", "ability", 2), (2, "set_tera", "tera", 7)):
            m = (s[..., j] >= 0) & (seen_ids[..., col] != s[..., j])
            aux_hits[name][0] += int((out[key].argmax(-1)[m] == s[..., j][m]).sum())
            aux_hits[name][1] += int(m.sum())
        top4 = out["set_moves"].topk(4, dim=-1).indices
        mv = s[..., 3:]
        revealed = (mv.unsqueeze(-1) == seen_ids[..., 3:7].unsqueeze(-2)).any(-1)
        m = (mv >= 0) & ~revealed
        hit = (mv.unsqueeze(-1) == top4.unsqueeze(-2)).any(-1) & m
        aux_hits["moves_top4"][0] += int(hit.sum())
        aux_hits["moves_top4"][1] += int(m.sum())
    model.train()
    arr = {k: np.concatenate(v) for k, v in cols.items()}
    arr["idx"] = idx
    arr["game"] = np.asarray(data["game"][idx])
    arr["rating"] = np.asarray(data["rating"][idx])
    arr["aux"] = {k: (h / n if n else None) for k, (h, n) in aux_hits.items()}
    return arr


def summarize(arr: dict, temperature: float | None = None, boot: int = 0) -> dict:
    """Metrics from collect(). Temperature is fitted here unless given (use the
    validation-fitted one when scoring a test set)."""
    t = fit_temperature(arr["logit"], arr["label"]) if temperature is None else temperature
    rep = value_report(arr["logit"], arr["label"], arr["base"], arr["game"], arr["fainted"], arr["rating"],
                       temperature=t, boot=boot)
    raw = value_report(arr["logit"], arr["label"], arr["base"], arr["game"], arr["fainted"], arr["rating"],
                       temperature=1.0, boot=0)["model"]
    pol_ok, opp_ok = arr["pol_ok"], arr["opp_ok"]
    return {
        "value_loss": raw["log_loss"], "value_acc": raw["acc"], "ece_raw": raw["ece"], "temperature": t,
        "calibrated": rep,
        "policy_loss": float(arr["pol_loss"][pol_ok].mean()) if pol_ok.any() else None,
        "policy_top1": float(arr["pol_top1"][pol_ok].mean()), "policy_top3": float(arr["pol_top3"][pol_ok].mean()),
        "opp_policy_top1": float(arr["opp_top1"][opp_ok].mean()), "opp_policy_top3": float(arr["opp_top3"][opp_ok].mean()),
        "set_prediction": arr["aux"], "samples": int(len(arr["label"])),
        # names the export step reads
        "baseline_value_acc": rep["placeholder"]["acc"], "baseline_value_loss": rep["placeholder"]["log_loss"],
    }


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
    ap.add_argument("--opp-weight", type=float, default=0.25, help="opponent's-choice auxiliary loss")
    ap.add_argument("--set-weight", type=float, default=0.1, help="each opponent-set auxiliary loss")
    ap.add_argument("--eval-every", type=int, default=2000, help="steps")
    ap.add_argument("--d", type=int, default=256)
    ap.add_argument("--layers", type=int, default=6)
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
        frac = min(1.0, (step - warmup) / max(1, total_steps - warmup))
        return args.lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * frac)))

    step, best, best_policy, elapsed_before = 0, float("inf"), float("inf"), 0.0
    if args.resume and (out / "last.pt").exists():
        ck = torch.load(out / "last.pt", map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step, best, elapsed_before = ck["step"], ck["best"], ck.get("elapsed", 0.0)
        best_policy = ck.get("best_policy", float("inf"))
        print(f"resumed at step {step} (best val value loss {best:.4f})", flush=True)

    (out / "config.json").write_text(json.dumps({"model": cfg.to_dict(), "args": vars(args) | {"resume": False},
                                                 "data": args.data, "params": count_params(model)}, indent=1))
    print(f"device {device}; {count_params(model) / 1e6:.2f}M params; train {len(train_idx)} / val {len(val_idx)} "
          f"samples; {steps_per_epoch} steps per epoch", flush=True)

    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    t0 = time.time()
    run_loss = float("nan")

    def save(name: str, extra: dict | None = None):
        tmp = out / f"{name}.tmp"
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": step, "best": best,
                    "elapsed": elapsed_before + time.time() - t0, "config": cfg.to_dict(), **(extra or {})}, tmp)
        tmp.replace(out / f"{name}.pt")

    def log_eval():
        nonlocal best, best_policy
        m = summarize(collect(model, data, val_idx, device))
        m.update(step=step, epoch=round(step / max(1, steps_per_epoch), 3), lr=lr_at(step),
                 minutes=round((elapsed_before + time.time() - t0) / 60, 1), train_loss=round(run_loss, 4))
        with open(out / "metrics.jsonl", "a") as f:
            f.write(json.dumps(m) + "\n")
        c = m["calibrated"]
        sp = m["set_prediction"]
        print(f"step {step} ep {m['epoch']} | train {run_loss:.4f} | val value {m['value_loss']:.4f} acc {m['value_acc']:.3f} "
              f"(T={m['temperature']:.2f} -> {c['model']['log_loss']:.4f}, ece {c['model']['ece']:.3f}; placeholder "
              f"{c['placeholder']['log_loss']:.4f}/{c['placeholder']['acc']:.3f}) | policy {m['policy_top1']:.3f}/"
              f"{m['policy_top3']:.3f} opp {m['opp_policy_top1']:.3f}/{m['opp_policy_top3']:.3f} | sets: item "
              f"{sp['item'] or 0:.2f} ability {sp['ability'] or 0:.2f} tera {sp['tera'] or 0:.2f} moves@4 "
              f"{sp['moves_top4'] or 0:.2f} | {m['minutes']} min", flush=True)
        if m["value_loss"] < best:
            best = m["value_loss"]
            save("best", {"metrics": m, "temperature": m["temperature"]})
        if m["policy_loss"] is not None and m["policy_loss"] < best_policy:
            best_policy = m["policy_loss"]
            save("best_policy", {"metrics": m})
        save("last", {"best_policy": best_policy})

    model.train()
    done = False
    while not done:
        for _, batch in prefetch(batches(data, train_idx, args.bs, rng, True)):
            t = to_dev(batch, device)
            for g in opt.param_groups:
                g["lr"] = lr_at(step)
            v, p, aux = model(t["ids"], t["mon"], t["field"], aux=True)
            loss = F.binary_cross_entropy_with_logits(v, t["value"])
            for weight, l in ((args.policy_weight, choice_loss(p, t["policy"])),
                              (args.opp_weight, choice_loss(aux["opp_policy"], t["opp_policy"]))):
                if l is not None:
                    loss = loss + weight * l
            for sl in set_losses(aux, t["opp_set"]).values():
                loss = loss + args.set_weight * sl
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            step += 1
            if step % 50 == 0:
                lv = loss.item()
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
