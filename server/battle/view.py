"""What one player could see at a given moment.

Replay logs show exact HP for both sides. A player only sees the opponent's HP as a
percentage, rounded the way Showdown's server rounds it (sim/pokemon.ts getHealth):
- Champions formats: floor(100 * hp / maxhp), at least 1.
- Everything else from Gen 7 on (and HP Percentage Mod): ceil(100 * hp / maxhp),
  but 99 if not at full HP.
Everything else in the parsed state (revealed moves, items, abilities, field) is public.
"""
from __future__ import annotations

import copy
import math


def shown_percent(hp: int, maxhp: int, format_id: str = "") -> int:
    if hp <= 0:
        return 0
    if maxhp <= 0:
        return 0
    if format_id.startswith("gen9champions"):
        return math.floor(100 * hp / maxhp) or 1
    pct = math.ceil(100 * hp / maxhp)
    if pct == 100 and hp < maxhp:
        pct = 99
    return pct


def view_for(state: dict, side: str, format_id: str = "") -> dict:
    """Copy of a parsed state as `side` ('p1' or 'p2') saw it."""
    if side not in ("p1", "p2"):
        raise ValueError("side must be p1 or p2")
    out = copy.deepcopy(state)
    out["perspective"] = side
    opp = "p2" if side == "p1" else "p1"
    for mon in out["sides"][opp]["team"]:
        if mon["hp_exact"]:
            mon["hp"] = shown_percent(mon["hp"], mon["maxhp"], format_id)
            mon["maxhp"] = 100
            mon["hp_exact"] = False
    return out
