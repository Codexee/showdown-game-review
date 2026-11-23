"""Short, readable lines for what happened in each turn (for the review screen).

events_by_turn(log) -> {turn: [Event, ...]}. Turn 0 holds the leads; turn N holds what
happened after the |turn|N line. HP is written as a percentage, the way players see it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..ids import to_id
from .parser import _parse_hp, _split

STATUS_TEXT = {"brn": "was burned", "par": "was paralyzed", "psn": "was poisoned",
               "tox": "was badly poisoned", "slp": "fell asleep", "frz": "was frozen solid"}
STAT_NAMES = {"atk": "Attack", "def": "Defense", "spa": "Sp. Atk", "spd": "Sp. Def", "spe": "Speed",
              "accuracy": "accuracy", "evasion": "evasiveness"}
WEATHER_TEXT = {"raindance": "It started to rain.", "sunnyday": "The sunlight turned harsh.",
                "sandstorm": "A sandstorm kicked up.", "snowscape": "It started to snow.",
                "desolateland": "The sunlight turned extremely harsh.",
                "primordialsea": "A heavy rain began to fall.", "deltastream": "Strong winds appeared."}


@dataclass
class Event:
    text: str
    side: str | None = None   # p1 / p2: whose Pokemon or side it is about
    kind: str = ""            # move, switch, damage, heal, faint, status, boost, field, info, end
    # For move events (used by the review screen's move effects):
    move: str | None = None   # move id, e.g. "knockoff"
    pos: int | None = None    # user's slot (0 = a, 1 = b)
    target: str | None = None  # target's side, p1 / p2 (None: no target, or itself)
    target_pos: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("move", "pos", "target", "target_pos"):   # only on move events
            if d[k] is None:
                del d[k]
        return d


def _slot(ident: str) -> int | None:
    """'p1a: Pikachu' -> 0, 'p2b: X' -> 1."""
    return {"a": 0, "b": 1, "c": 2}.get(ident[2:3]) if len(ident) > 2 and ident[:2] in ("p1", "p2") else None


def _name(ident: str) -> str:
    return ident.partition(": ")[2] or ident


def _pct(hp_text: str) -> str:
    hp, maxhp, _, fainted = _parse_hp(hp_text)
    if fainted or not maxhp:
        return "0%"
    return f"{round(100 * hp / maxhp)}%"


def _effect_name(effect: str) -> str:
    return effect.partition(": ")[2] if ": " in effect else effect


def events_by_turn(log: str) -> dict[int, list[dict]]:
    players: dict[str, str] = {}
    turn = 0
    out: dict[int, list[dict]] = {0: []}

    def add(text: str, side: str | None = None, kind: str = "", **extra) -> None:
        out.setdefault(turn, []).append(Event(text, side, kind, **extra).to_dict())

    for line in log.splitlines():
        if not line.startswith("|"):
            continue
        kind, args, tags = _split(line)
        side = args[0][:2] if args and args[0][:2] in ("p1", "p2") else None
        src = tags.get("from", "")
        why = f" ({_effect_name(src)})" if src else ""
        try:
            if kind == "player" and len(args) >= 2 and args[1]:
                players[args[0]] = args[1]
            elif kind == "turn":
                turn = int(args[0])
                out.setdefault(turn, [])
            elif kind in ("switch", "drag"):
                who = players.get(side or "", side or "")
                verb = "sent out" if kind == "switch" else "had dragged out"
                add(f"{who} {verb} {_name(args[0])} ({_pct(args[2])}).", side, "switch")
            elif kind == "replace":
                add(f"The Illusion ended: it was {_name(args[0])}.", side, "switch")
            elif kind == "move":
                target = f" on {_name(args[2])}" if len(args) > 2 and args[2] and args[2] != args[0] else ""
                miss = " It missed." if "miss" in tags else ""
                tgt = args[2] if len(args) > 2 and args[2] and args[2] != args[0] and args[2][:2] in ("p1", "p2") else ""
                add(f"{_name(args[0])} used {args[1]}{target}.{miss}", side, "move", move=to_id(args[1]),
                    pos=_slot(args[0]), target=tgt[:2] or None, target_pos=_slot(tgt) if tgt else None)
            elif kind == "cant":
                add(f"{_name(args[0])} couldn't move ({_effect_name(args[1])}).", side, "move")
            elif kind == "-damage":
                add(f"{_name(args[0])} fell to {_pct(args[1])}{why}.", side, "damage")
            elif kind == "-heal":
                add(f"{_name(args[0])} recovered to {_pct(args[1])}{why}.", side, "heal")
            elif kind == "faint":
                add(f"{_name(args[0])} fainted.", side, "faint")
            elif kind == "-crit":
                add("A critical hit!", side, "info")
            elif kind == "-supereffective":
                add("It's super effective.", side, "info")
            elif kind == "-resisted":
                add("It's not very effective.", side, "info")
            elif kind == "-immune":
                add(f"It doesn't affect {_name(args[0])}{why}.", side, "info")
            elif kind == "-miss" and len(args) > 1:
                add(f"{_name(args[1])} avoided the attack.", args[1][:2], "info")
            elif kind == "-fail":
                add(f"It failed{why}.", side, "info")
            elif kind == "-status":
                add(f"{_name(args[0])} {STATUS_TEXT.get(args[1], 'got ' + args[1])}{why}.", side, "status")
            elif kind == "-curestatus":
                add(f"{_name(args[0])} was cured{why}.", side, "status")
            elif kind in ("-boost", "-unboost") and len(args) >= 3:
                n = int(args[2]) if args[2].lstrip("-").isdigit() else 0
                stat = STAT_NAMES.get(args[1], args[1])
                if n == 0:
                    add(f"{_name(args[0])}'s {stat} won't go any {'higher' if kind == '-boost' else 'lower'}.", side, "boost")
                else:
                    sign = "+" if kind == "-boost" else "−"
                    verb = "rose" if kind == "-boost" else "fell"
                    add(f"{_name(args[0])}'s {stat} {verb} ({sign}{n}){why}.", side, "boost")
            elif kind == "-weather" and "upkeep" not in tags:
                w = to_id(args[0])
                add("The weather cleared." if w == "none" else WEATHER_TEXT.get(w, f"Weather: {args[0]}."),
                    None, "field")
            elif kind == "-fieldstart":
                add(f"{_effect_name(args[0])} started{why}.", None, "field")
            elif kind == "-fieldend":
                add(f"{_effect_name(args[0])} ended.", None, "field")
            elif kind == "-sidestart":
                who = players.get(args[0][:2], args[0][:2])
                add(f"{_effect_name(args[1])} was set on {who}'s side.", args[0][:2], "field")
            elif kind == "-sideend":
                who = players.get(args[0][:2], args[0][:2])
                add(f"{_effect_name(args[1])} ended on {who}'s side.", args[0][:2], "field")
            elif kind == "-terastallize":
                add(f"{_name(args[0])} Terastallized into the {args[1]} type.", side, "info")
            elif kind == "-mega":
                add(f"{_name(args[0])} Mega Evolved.", side, "info")
            elif kind == "-enditem":
                how = "was knocked off" if "knockoff" in to_id(src) else "was used up" if "eat" in tags or not src else "was lost"
                add(f"{_name(args[0])}'s {args[1]} {how}.", side, "info")
            elif kind == "-item":
                add(f"{_name(args[0])} has {args[1]}{why}.", side, "info")
            elif kind == "-ability" and len(args) > 1:
                add(f"{_name(args[0])}'s ability: {args[1]}.", side, "info")
            elif kind == "win":
                add(f"{args[0]} won the battle.", None, "end")
            elif kind == "tie":
                add("The battle ended in a tie.", None, "end")
        except (IndexError, ValueError):
            continue
    return out
