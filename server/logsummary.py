"""Read the game-list details out of a Showdown battle log.

Only what the game list needs: players, ratings, result, turn count, teams, times.
The full per-turn battle state is a separate parser (roadmap stage 3).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .ids import to_id

_RATING_RAW = re.compile(
    r"^(?P<name>.+?)'s rating: (?P<before>\d+) &rarr; <strong>(?P<after>\d+)</strong>"
)


@dataclass
class Side:
    name: str = ""
    rating_before: int | None = None
    rating_after: int | None = None
    team: list[str] = field(default_factory=list)  # species, in order first seen


@dataclass
class Summary:
    format: str = ""
    gametype: str = ""
    gen: int | None = None
    rated: bool = False
    p1: Side = field(default_factory=Side)
    p2: Side = field(default_factory=Side)
    winner: str | None = None  # player name; None for a tie or an unfinished game
    tie: bool = False
    finished: bool = False
    turns: int = 0
    started_at: int | None = None  # unix seconds, first |t:| line
    ended_at: int | None = None  # unix seconds, last |t:| line

    def to_dict(self) -> dict:
        return asdict(self)


def _species(details: str) -> str:
    """'Palafin-Hero, L77, F' -> 'Palafin-Hero'."""
    return details.split(",")[0].strip()


def _add(team: list[str], species: str) -> None:
    if species and species not in team:
        team.append(species)


def summarize(log: str) -> Summary:
    s = Summary()
    sides = {"p1": s.p1, "p2": s.p2}
    seen_preview = {"p1": False, "p2": False}
    # Each Pokemon is identified by its nickname within a side ("p2a: Palafin"), which stays
    # the same through forme changes, so key on that and keep the first species seen.
    by_nick: dict[str, dict[str, str]] = {"p1": {}, "p2": {}}
    for line in log.splitlines():
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        kind = parts[1] if len(parts) > 1 else ""
        if kind == "player" and len(parts) >= 4 and parts[2] in sides:
            side = sides[parts[2]]
            if parts[3]:
                side.name = parts[3]
            if len(parts) >= 6 and parts[5].strip().isdigit() and side.rating_before is None:
                side.rating_before = int(parts[5])
        elif kind == "tier" and len(parts) >= 3:
            s.format = parts[2]
        elif kind == "gametype" and len(parts) >= 3:
            s.gametype = parts[2]
        elif kind == "gen" and len(parts) >= 3 and parts[2].isdigit():
            s.gen = int(parts[2])
        elif kind == "rated":
            s.rated = True
        elif kind == "poke" and len(parts) >= 4 and parts[2] in sides:
            seen_preview[parts[2]] = True
            _add(sides[parts[2]].team, _species(parts[3]))
        elif kind in ("switch", "drag", "replace") and len(parts) >= 4:
            slot = parts[2][:2]
            nick = parts[2].split(":", 1)[-1].strip()
            # With team preview, the |poke| list is already the full team.
            if slot in sides and not seen_preview[slot] and nick not in by_nick[slot]:
                by_nick[slot][nick] = _species(parts[3])
                _add(sides[slot].team, by_nick[slot][nick])
        elif kind == "turn" and len(parts) >= 3 and parts[2].isdigit():
            s.turns = int(parts[2])
        elif kind == "win":
            s.winner = parts[2] if len(parts) >= 3 else None
            s.finished = True
        elif kind == "tie":
            s.tie = True
            s.finished = True
        elif kind == "t:" and len(parts) >= 3 and parts[2].isdigit():
            t = int(parts[2])
            if s.started_at is None:
                s.started_at = t
            s.ended_at = t
        elif kind == "raw" and len(parts) >= 3:
            m = _RATING_RAW.match(parts[2])
            if m:
                for side in sides.values():
                    if to_id(side.name) == to_id(m["name"]):
                        side.rating_before = int(m["before"])
                        side.rating_after = int(m["after"])
    return s


def result_for(summary: dict, username: str) -> str | None:
    """'win', 'loss', 'tie', or None if the user didn't play or the game didn't finish."""
    uid = to_id(username)
    names = {to_id(summary["p1"]["name"]), to_id(summary["p2"]["name"])}
    if uid not in names:
        return None
    if summary.get("tie"):
        return "tie"
    if not summary.get("finished") or summary.get("winner") is None:
        return None
    return "win" if to_id(summary["winner"]) == uid else "loss"


def user_side(summary: dict, username: str) -> str | None:
    uid = to_id(username)
    for slot in ("p1", "p2"):
        if to_id(summary[slot]["name"]) == uid:
            return slot
    return None
