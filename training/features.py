"""Turn a parsed battle state into model input, and a log into training samples.

Input (one sample = one turn start, seen by one player; vault spec-eval-model):
- 13 tokens: 6 for the player's own side, 6 for the opponent, 1 for the field.
- Each Pokemon token: 8 ids (species, item, ability, 4 moves, Tera type) and N_MON
  numbers (HP, status, boosts, ...). Unknown things use the UNK id; known-empty (no
  item) uses NONE. Pokemon not seen yet are "unseen" tokens.
- The model only gets what was public at that moment (the spectator view, which is
  also what reviewing a game gives us). Own exact HP is turned into a fraction anyway.

Targets: value = did this player win; policy = the action they chose that turn
(a move id, or which own slot they switched to), or -1 if not observed.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from server.battle.parser import LogParser, _split
from server.ids import to_id

VOCAB = json.loads((Path(__file__).parent / "vocab.json").read_text())
PAD, UNK, NONE = 0, 1, 2  # shared special ids for every vocabulary
_OFFSET = 3


def _index(names: list[str]) -> dict[str, int]:
    return {n: i + _OFFSET for i, n in enumerate(names)}


SPECIES = _index(VOCAB["species"])
MOVES = _index(VOCAB["moves"])
ITEMS = _index(VOCAB["items"])
ABILITIES = _index(VOCAB["abilities"])
TYPES = _index([to_id(t) for t in VOCAB["types"]])
SIZES = {"species": len(SPECIES) + _OFFSET, "moves": len(MOVES) + _OFFSET, "items": len(ITEMS) + _OFFSET,
         "abilities": len(ABILITIES) + _OFFSET, "types": len(TYPES) + _OFFSET}

STATUSES = ["brn", "par", "slp", "frz", "psn", "tox"]
BOOSTS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
VOLATILES = ["substitute", "confusion", "leechseed", "taunt", "encore", "yawn", "perishsong"]
WEATHERS = ["raindance", "sunnyday", "sandstorm", "snowscape", "desolateland", "primordialsea", "deltastream"]
TERRAINS = ["electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
PSEUDO = ["trickroom", "gravity", "magicroom", "wonderroom"]
SIDE_CONDS = ["stealthrock", "spikes", "toxicspikes", "stickyweb", "reflect", "lightscreen", "auroraveil",
              "tailwind", "safeguard"]
LAYER_MAX = {"spikes": 3, "toxicspikes": 2}

N_TOKENS = 13
N_IDS = 8          # species, item, ability, move1-4, tera
N_MON = 7 + len(STATUSES) + len(BOOSTS) + len(VOLATILES)   # 27
N_FIELD = 1 + len(WEATHERS) + len(TERRAINS) + len(PSEUDO) + 2 * len(SIDE_CONDS) + 2 + 6  # 42
N_SWITCH = 6       # policy: switch to own slot 0-5


def _lookup(table: dict[str, int], name: str | None) -> int:
    if name is None:
        return UNK
    if name == "":
        return NONE
    return table.get(to_id(name), UNK)


def _mon_ids(m: dict) -> list[int]:
    moves = [MOVES.get(mv, UNK) for mv in m["moves"][:4]]
    moves += [UNK] * (4 - len(moves))  # not revealed yet
    tera = TYPES.get(to_id(m["tera_type"]), UNK) if m["tera_type"] else NONE
    return [SPECIES.get(to_id(m["species"]), UNK), _lookup(ITEMS, m["item"]),
            _lookup(ABILITIES, m["ability"]), *moves, tera]


def _mon_nums(m: dict, own: bool) -> list[float]:
    hp = 0.0 if m["fainted"] else m["hp"] / (m["maxhp"] or 100)
    out = [hp, float(m["fainted"]), float(m["active"]), 1.0, float(own), m["level"] / 100.0,
           float(bool(m["tera_type"]))]
    out += [float(m["status"] == s) for s in STATUSES]
    out += [m["boosts"].get(b, 0) / 6.0 for b in BOOSTS]
    out += [float(v in m["volatiles"]) for v in VOLATILES]
    return out


def _unseen(own: bool) -> tuple[list[int], list[float]]:
    nums = [0.0] * N_MON
    nums[0] = 1.0           # assume full HP
    nums[3] = 0.0           # not seen
    nums[4] = float(own)
    return [UNK] * N_IDS, nums


def encode(state: dict, side: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """ids [13, 8] int16, mon [13, N_MON] float32, field [N_FIELD] float32, own slot names."""
    other = "p2" if side == "p1" else "p1"
    ids = np.zeros((N_TOKENS, N_IDS), dtype=np.int16)
    mon = np.zeros((N_TOKENS, N_MON), dtype=np.float32)
    own_names: list[str] = []
    for block, s in enumerate((side, other)):
        team = [m for m in state["sides"][s]["team"] if m["seen"]][:6]
        if block == 0:
            own_names = [m["name"] for m in team]
        for i in range(6):
            row = block * 6 + i
            if i < len(team):
                ids[row] = _mon_ids(team[i])
                mon[row] = _mon_nums(team[i], block == 0)
            else:
                ids[row], mon[row] = _unseen(block == 0)
    ids[12] = PAD
    f = state["field"]
    field = [min(state["turn"], 100) / 50.0]
    field += [float(f["weather"] == w) for w in WEATHERS]
    field += [float(f["terrain"] == t) for t in TERRAINS]
    field += [float(p in f["pseudo_weather"]) for p in PSEUDO]
    for s in (side, other):
        conds = state["sides"][s]["conditions"]
        field += [min(conds.get(c, 0), LAYER_MAX.get(c, 1)) / LAYER_MAX.get(c, 1) for c in SIDE_CONDS]
    for s in (side, other):
        field.append(float(any(m["tera_type"] or m.get("tera_known") for m in state["sides"][s]["team"])))
    # Totals per side (own, then opponent): remaining HP, Pokemon alive, Pokemon unseen.
    # The placeholder eval uses only the HP lead; giving these directly lets the model
    # start from there instead of having to learn to add up HP (test run 2026-11-22).
    for block in (0, 1):
        rows = mon[block * 6:(block + 1) * 6]
        hp = rows[:, 0] * (1 - rows[:, 1])
        field += [float(hp.sum()) / 6, float((rows[:, 1] < 0.5).sum()) / 6, float((rows[:, 3] < 0.5).sum()) / 6]
    return ids, mon, np.asarray(field, dtype=np.float32), own_names


# ---------------------------------------------------------------- actions from a log
def turn_actions(log: str) -> dict[int, dict[str, tuple[str, str]]]:
    """{turn: {side: ("move", move_id) | ("switch", name)}} for the choice made at the
    start of that turn. Pivot switches ([from] U-turn), switches after a faint, and
    moves called by other moves are not choices; |cant| leaves the turn unobserved."""
    out: dict[int, dict[str, tuple[str, str]]] = {}
    turn = 0
    fainted: set[str] = set()
    for line in log.splitlines():
        if not line.startswith("|"):
            continue
        kind, args, tags = _split(line)
        if kind == "turn":
            turn = int(args[0])
            fainted = set()
            continue
        if turn == 0 or not args or args[0][:2] not in ("p1", "p2"):
            continue
        side = args[0][:2]
        acts = out.setdefault(turn, {})
        if side in acts:
            continue
        if kind == "faint":
            fainted.add(side)
        elif kind == "cant":
            acts[side] = ("none", "")
        elif kind == "move" and len(args) > 1:
            if "from" in tags and not tags["from"].startswith("lockedmove"):
                continue
            acts[side] = ("move", to_id(args[1]))
        elif kind == "switch" and "from" not in tags and side not in fainted:
            acts[side] = ("switch", args[0].partition(": ")[2])
    return out


def policy_target(action: tuple[str, str] | None, own_names: list[str]) -> int:
    """Index into [moves..., switch slot 0..5], or -1 if there is no usable target."""
    if action is None or action[0] == "none":
        return -1
    if action[0] == "move":
        idx = MOVES.get(action[1])
        return idx if idx is not None else -1
    name = action[1]
    if name in own_names:
        return SIZES["moves"] + own_names.index(name)
    slot = len(own_names)  # first unseen slot: switching to a Pokemon not seen yet
    return SIZES["moves"] + slot if slot < N_SWITCH else -1


def game_samples(log: str, rng: np.random.Generator | None = None, both_sides: bool = False):
    """Yield (ids, mon, field, value_label, policy_label) for each turn of a finished
    singles game. One random side per turn unless both_sides."""
    parser = LogParser()
    for line in log.splitlines():
        parser.feed(line)
    states = parser.result.states
    if not states:
        return
    final = parser.state
    if not final.ended or final.winner is None or final.gametype != "singles":
        return
    winner_side = next((s for s, sd in final.sides.items() if sd.name == final.winner), None)
    if winner_side is None:
        return
    actions = turn_actions(log)
    rng = rng or np.random.default_rng()
    for st in states:
        if st["ended"]:
            continue
        sides = ("p1", "p2") if both_sides else (("p1", "p2")[rng.integers(2)],)
        for side in sides:
            ids, mon, field, own_names = encode(st, side)
            pol = policy_target(actions.get(st["turn"], {}).get(side), own_names)
            yield ids, mon, field, float(side == winner_side), pol
