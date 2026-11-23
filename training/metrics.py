"""Measurement in the style of PS Dashboard (vault benchmark-best-in-class, P0 item 4):
per-phase scores, bootstrap confidence intervals over GAMES (turns of one game are not
independent), a high-rating slice, the placeholder next to the model, and temperature
calibration fitted on validation.
"""
from __future__ import annotations

import numpy as np

HQ_RATING = 1500
PHASES = {"early (0-2 fainted)": (0, 2), "mid (3-6 fainted)": (3, 6), "late (7+ fainted)": (7, 12)}
EPS = 1e-6


def _ll(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def fit_temperature(logit: np.ndarray, y: np.ndarray) -> float:
    """Scalar T minimizing log-loss of sigmoid(logit / T); a coarse-to-fine grid is enough."""
    best_t, best = 1.0, float("inf")
    grid = np.exp(np.linspace(np.log(0.5), np.log(2.5), 41))
    for t in grid:
        v = _ll(sigmoid(logit / t), y).mean()
        if v < best:
            best_t, best = float(t), v
    for t in np.linspace(best_t * 0.95, best_t * 1.05, 21):
        v = _ll(sigmoid(logit / t), y).mean()
        if v < best:
            best_t, best = float(t), v
    return best_t


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    b = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for i in range(bins):
        m = b == i
        if m.any():
            total += abs(p[m].mean() - y[m].mean()) * m.sum()
    return float(total / max(len(p), 1))


def _scores(p: np.ndarray, y: np.ndarray) -> dict:
    return {"log_loss": float(_ll(p, y).mean()), "brier": float(((p - y) ** 2).mean()),
            "acc": float(((p > 0.5) == (y > 0.5)).mean()), "ece": ece(p, y), "n": int(len(y))}


def two_view(p: np.ndarray, y: np.ndarray, game: np.ndarray) -> np.ndarray:
    """Each position scored from both players' views, as the move review's leaf does:
    p1's chance = (p1's view + 1 - p2's view) / 2. Needs a dataset built with --both-sides,
    whose rows come in (p1, p2) pairs for the same position (training.features.game_samples).
    Measured on main@9000, pinned bank: log-loss 0.58543 -> 0.58285 (vault 2026-11-23-codex-review)."""
    if len(p) % 2 or not (np.array_equal(game[0::2], game[1::2]) and np.allclose(y[0::2] + y[1::2], 1)):
        raise ValueError("two-view scoring needs rows in (p1, p2) pairs of the same position (build with --both-sides)")
    avg = (p[0::2] + 1 - p[1::2]) / 2
    q = np.empty_like(p)
    q[0::2], q[1::2] = avg, 1 - avg
    return q


def is_paired(y: np.ndarray, game: np.ndarray) -> bool:
    return len(y) % 2 == 0 and np.array_equal(game[0::2], game[1::2]) and bool(np.allclose(y[0::2] + y[1::2], 1))


def two_view_report(p: np.ndarray, y: np.ndarray, game: np.ndarray, boot: int = 200) -> dict | None:
    """Scores of the two-view estimate (see two_view), or None if the rows aren't paired."""
    if not is_paired(y, game):
        return None
    q = two_view(p, y, game)
    out = _scores(q, y)
    if boot:
        out["log_loss_ci90"] = bootstrap(lambda w: float((_ll(q, y) * w).sum() / w.sum()), game, boot)
        out["acc_ci90"] = bootstrap(lambda w: float((((q > 0.5) == (y > 0.5)) * w).sum() / w.sum()), game, boot)
    return out


def bootstrap(stat, games: np.ndarray, n: int = 200, seed: int = 0, level: float = 0.9) -> tuple[float, float]:
    """Percentile interval of stat(mask) when resampling whole games with replacement."""
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(games, return_inverse=True)
    vals = []
    for _ in range(n):
        pick = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        w = pick[inv]
        vals.append(stat(w))
    lo, hi = np.percentile(vals, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def value_report(logit: np.ndarray, y: np.ndarray, base_p: np.ndarray, games: np.ndarray,
                 fainted: np.ndarray, rating: np.ndarray, temperature: float = 1.0, boot: int = 200) -> dict:
    """Model vs placeholder: overall with 90% CIs, by phase, and on the high-rating slice."""
    p = sigmoid(logit / temperature)
    out = {"temperature": temperature, "model": _scores(p, y), "placeholder": _scores(base_p, y)}
    d_ll = _ll(p, y) - _ll(base_p, y)
    out["model_minus_placeholder_log_loss"] = float(d_ll.mean())
    if boot:
        out["model_log_loss_ci90"] = bootstrap(lambda w: float((_ll(p, y) * w).sum() / w.sum()), games, boot)
        out["model_acc_ci90"] = bootstrap(lambda w: float((((p > 0.5) == (y > 0.5)) * w).sum() / w.sum()), games, boot)
        out["model_minus_placeholder_ci90"] = bootstrap(lambda w: float((d_ll * w).sum() / w.sum()), games, boot)
    out["by_phase"] = {}
    for name, (lo, hi) in PHASES.items():
        m = (fainted >= lo) & (fainted <= hi)
        if m.any():
            out["by_phase"][name] = {"model": _scores(p[m], y[m]), "placeholder": _scores(base_p[m], y[m])}
    hq = rating >= HQ_RATING
    if hq.any():
        out[f"rating_{HQ_RATING}_plus"] = {"model": _scores(p[hq], y[hq]), "placeholder": _scores(base_p[hq], y[hq])}
    return out


def paired(a: dict[str, np.ndarray], b: dict[str, np.ndarray], boot: int = 1000) -> dict:
    """Paired comparison of two models' predictions on the same samples (keys must match):
    mean differences b - a in log-loss and Brier, with 90% bootstrap bands over games.
    Negative = b is better."""
    assert np.array_equal(a["key"], b["key"]), "the two prediction files cover different samples"
    y = a["label"]
    dll = _ll(b["p"], y) - _ll(a["p"], y)
    dbr = (b["p"] - y) ** 2 - (a["p"] - y) ** 2
    games = a["game"]
    return {
        "n": int(len(y)), "games": int(len(np.unique(games))),
        "log_loss_a": float(_ll(a["p"], y).mean()), "log_loss_b": float(_ll(b["p"], y).mean()),
        "delta_log_loss": float(dll.mean()), "delta_log_loss_ci90": bootstrap(lambda w: float((dll * w).sum() / w.sum()), games, boot),
        "delta_brier": float(dbr.mean()), "delta_brier_ci90": bootstrap(lambda w: float((dbr * w).sum() / w.sum()), games, boot),
        "acc_a": float(((a["p"] > 0.5) == (y > 0.5)).mean()), "acc_b": float(((b["p"] > 0.5) == (y > 0.5)).mean()),
    }
