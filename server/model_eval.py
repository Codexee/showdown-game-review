"""Win chances from the trained eval model (stage 5), if one is installed.

The model file is data/models/current.pt, written by `python -m training.export`.
Without it (or for doubles, which the model wasn't trained on) the review screen keeps
the remaining-HP placeholder from server/evaluate.py.
"""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

_lock = threading.Lock()
_cache: dict[str, object] = {}


class ModelEval:
    def __init__(self, path: Path):
        import torch
        from training.model import EvalNet, ModelConfig

        # Safe loading (tensors and plain values only): the model may be downloaded from a release.
        ck = torch.load(path, map_location="cpu", weights_only=True)
        self.model = EvalNet(ModelConfig(**ck["config"]))
        self.model.load_state_dict(ck["model"])
        self.model.eval()
        self.info = ck.get("info", {})
        self.temperature = float(ck.get("temperature", 1.0))  # fitted on validation (calibration)
        self.torch = torch

    def win_chances(self, states: list[dict], side: str, events: dict | None = None) -> list[float]:
        """`events` = training.features.turn_events(log): what happened each turn, which the
        model reads for the turn after (last moves, who moved first...)."""
        from training.features import encode

        if not states:
            return []
        ev = events or {}
        other = "p2" if side == "p1" else "p1"
        # Both players' views, averaged: side's chance = (side's view + 1 - other's view) / 2.
        # The same estimate as the move review's leaf; on the pinned bank it beat one view,
        # log-loss 0.58543 -> 0.58285 for main@9000 (vault 2026-11-23-codex-review).
        enc = [encode(s, who, ev.get(s["turn"] - 1) if s["turn"] > 1 else None)
               for who in (side, other) for s in states]
        t = self.torch
        with t.no_grad():
            ids = t.from_numpy(np.stack([e[0] for e in enc]).astype(np.int64))
            mon = t.from_numpy(np.stack([e[1] for e in enc]))
            field = t.from_numpy(np.stack([e[2] for e in enc]))
            value, _ = self.model(ids, mon, field)
            p = t.sigmoid(value / self.temperature).numpy()
        n = len(states)
        return ((p[:n] + 1 - p[n:]) / 2).tolist()


def load(data_dir: Path) -> ModelEval | None:
    """The installed model, loaded once and reloaded if the file changes."""
    path = Path(data_dir) / "models" / "current.pt"
    if not path.exists():
        return None
    stamp = path.stat().st_mtime_ns
    with _lock:
        if _cache.get("stamp") != stamp:
            try:
                _cache["model"] = ModelEval(path)
            except Exception as e:  # a broken file shouldn't take the review screen down
                print(f"could not load {path}: {e}", flush=True)
                _cache["model"] = None
            _cache["stamp"] = stamp
        return _cache["model"]  # type: ignore[return-value]
