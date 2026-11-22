"""Win-chance estimate per turn for the eval bar.

PLACEHOLDER until the model exists (roadmap stage 5, vault spec-eval-model): a logistic
curve on the difference in remaining team HP. Unseen opposing Pokemon count as full HP.
It is crude and the UI says so; it only exists so the review screen has real numbers.
"""
from __future__ import annotations

import math

METHOD = "placeholder"
METHOD_TEXT = "Rough estimate from remaining HP. The trained model replaces this later."
_PER_MON = 0.5  # logistic units per Pokemon of HP lead: 1 ahead ~ 62%, 3 ahead ~ 82%


def _team_hp(side: dict, default_size: int) -> float:
    size = side.get("team_size") or default_size
    seen = [m for m in side["team"] if m["seen"]]
    total = sum(0.0 if m["fainted"] else m["hp"] / (m["maxhp"] or 100) for m in seen)
    total += max(0, size - len(seen))  # not yet seen: assume full HP
    return total / max(size, 1)


def win_chance(state: dict, side: str) -> float:
    """Estimated chance that `side` wins, from 0 to 1."""
    if state.get("ended"):
        winner = state.get("winner")
        if winner is None:
            return 0.5
        return 1.0 if state["sides"][side]["name"] == winner else 0.0
    other = "p2" if side == "p1" else "p1"
    size = 4 if state.get("gametype") == "doubles" else 6
    # _team_hp is a fraction of the team, so diff * size is the lead in "Pokemon worth of HP".
    diff = _team_hp(state["sides"][side], size) - _team_hp(state["sides"][other], size)
    return 1 / (1 + math.exp(-_PER_MON * diff * size))
