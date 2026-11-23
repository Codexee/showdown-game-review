"""Sampled hidden information for move review (vault ADR-0015).

A "world" fills in what the grading player could not see at the start of a turn: for
each opposing Pokemon that has been revealed, its unrevealed moves, item, ability and
Tera type, drawn from the Gen 9 Random Battle set data (training/randbats_gen9.json).
Revealed facts are kept. Opposing Pokemon that have not appeared yet keep their real
species and set (a known limit: changing a species inside the simulator is not done).
"""
from __future__ import annotations

import json
import random
from functools import lru_cache

from server.config import ROOT
from server.ids import to_id

FLOOR = 1e-3  # likelihood of a revealed fact the role data says never happens (data gaps)


@lru_cache(maxsize=1)
def priors() -> dict[str, dict]:
    raw = json.loads((ROOT / "training" / "randbats_gen9.json").read_text())
    return {to_id(k): v for k, v in raw.items()}


def entry_for(mon: dict) -> dict | None:
    """Set data for a parsed Pokemon: its species, then its base forme, then the name
    before the first hyphen (Palafin-Hero -> Palafin)."""
    p = priors()
    for name in (mon.get("species"), mon.get("base_species")):
        if not name:
            continue
        for cand in (name, name.split("-")[0]):
            e = p.get(to_id(cand))
            if e:
                return e
    return None


def _ids(d: dict | None) -> dict[str, float]:
    return {to_id(k): float(v) for k, v in (d or {}).items()}


def _pick(rng: random.Random, dist: dict[str, float]) -> str | None:
    items = [(k, w) for k, w in dist.items() if w > 0]
    if not items:
        return None
    total = sum(w for _, w in items)
    r = rng.random() * total
    for k, w in items:
        r -= w
        if r <= 0:
            return k
    return items[-1][0]


def known(mon: dict) -> dict:
    """What the log has revealed about this Pokemon's set."""
    return {
        "moves": [m for m in mon.get("moves", []) if m],
        "item": mon.get("orig_item") or mon.get("item") or None,
        "ability": mon.get("base_ability") or mon.get("ability") or None,
        "tera": to_id(mon["tera_known"]) if mon.get("tera_known") else None,
    }


def role_weights(entry: dict, kn: dict) -> dict[str, float]:
    """P(role | revealed facts), up to a constant: role weight times the chance of each
    revealed move, item, ability and Tera type under that role."""
    out = {}
    for name, role in entry.get("roles", {}).items():
        w = float(role.get("weight", 0))
        moves = _ids(role.get("moves"))
        for mv in kn["moves"]:
            w *= min(1.0, moves.get(mv, FLOOR))
        for key, field in (("item", "items"), ("ability", "abilities"), ("tera", "teraTypes")):
            if kn[key]:
                w *= _ids(role.get(field)).get(kn[key], FLOOR)
        out[name] = w
    return out


def sample_set(entry: dict, kn: dict, rng: random.Random) -> dict:
    """One plausible full set: revealed facts kept, the rest drawn from a role."""
    weights = role_weights(entry, kn)
    if not weights or sum(weights.values()) <= 0:
        return {}
    role = entry["roles"][_pick(rng, weights)]
    out: dict = {}
    if len(kn["moves"]) < 4:
        pool = {m: p for m, p in _ids(role.get("moves")).items() if m not in kn["moves"]}
        moves = list(kn["moves"])
        for m in [m for m, p in pool.items() if p >= 0.999]:  # moves this role always has
            if len(moves) < 4:
                moves.append(m)
                pool.pop(m)
        while len(moves) < 4 and pool:
            m = _pick(rng, pool)
            if m is None:
                break
            moves.append(m)
            pool.pop(m)
        out["moves"] = moves
    if not kn["item"]:
        item = _pick(rng, _ids(role.get("items")) or _ids(entry.get("items")))
        if item:
            out["item"] = item
    if not kn["ability"]:
        ab = _pick(rng, _ids(role.get("abilities")) or _ids(entry.get("abilities")))
        if ab:
            out["ability"] = ab
    if not kn["tera"]:
        tera = _pick(rng, {k: v for k, v in (role.get("teraTypes") or {}).items()})
        if tera:
            out["teraType"] = tera
    return out


def sample_worlds(state: dict, viewer: str, n: int, seed: int) -> list[dict]:
    """n worlds as the viewer sees the turn start: overrides for the opponent's revealed
    Pokemon. `state` is a parser snapshot (public information only)."""
    opp = "p2" if viewer == "p1" else "p1"
    rng = random.Random(seed)
    mons = [m for m in state["sides"][opp]["team"] if m.get("seen") and not m.get("transformed")]
    worlds = []
    for _ in range(n):
        ovs = []
        for m in mons:
            entry = entry_for(m)
            if entry is None:
                continue
            s = sample_set(entry, known(m), rng)
            if s:
                ovs.append({"name": m["name"], **s})
        worlds.append({opp: ovs})
    return worlds
