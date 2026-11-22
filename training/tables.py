"""Fixed lookup tables the model reads by id (vault benchmark-best-in-class, P0 items 1-2).

- Pokemon properties: base stats and types (Showdown dex at ac7b7da0f9, training/dex.json).
- Move properties: base power, accuracy, category, priority, type, a few effect flags.
- Randbats priors per species: how likely each move / item / ability / Tera type is
  (pkmn/randbats stats for gen9randombattle, MIT, training/randbats_gen9.json; species
  level = sum over roles of role weight x role frequency).
These depend only on ids, so they live in the model as buffers, not in the dataset.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from server.ids import to_id
from training.features import ABILITIES, ITEMS, MOVES, SIZES, SPECIES, TYPES, VOCAB

HERE = Path(__file__).parent
TYPE_LIST = [to_id(t) for t in VOCAB["types"]]
CATEGORIES = ["physical", "special", "status"]
MOVE_FLAGS = ["sec", "drain", "heal", "recoil", "pivot", "boosts", "status", "multihit"]
N_SPECIES_PROPS = 6 + len(TYPE_LIST)
N_MOVE_PROPS = 3 + len(CATEGORIES) + 1 + len(TYPE_LIST) + len(MOVE_FLAGS)
K_MOVES, K_ITEMS, K_ABILITIES, K_TERA = 12, 4, 3, 4


def _type_vec(types: list[str]) -> list[float]:
    ids = {to_id(t) for t in types}
    return [float(t in ids) for t in TYPE_LIST]


@lru_cache(maxsize=1)
def build() -> dict[str, np.ndarray]:
    dex = json.loads((HERE / "dex.json").read_text())
    species_props = np.zeros((SIZES["species"], N_SPECIES_PROPS), dtype=np.float32)
    for sid, row in SPECIES.items():
        s = dex["species"].get(sid)
        if not s or not s.get("bs"):
            s = dex["species"].get(s["base"]) if s else None  # some formes inherit stats in the dex
        if s and s.get("bs"):
            bs = s["bs"]
            species_props[row] = [bs["hp"] / 255, bs["atk"] / 255, bs["def"] / 255, bs["spa"] / 255,
                                  bs["spd"] / 255, bs["spe"] / 255, *_type_vec(s["types"])]
    move_props = np.zeros((SIZES["moves"], N_MOVE_PROPS), dtype=np.float32)
    for mid, row in MOVES.items():
        m = dex["moves"].get(mid)
        if m:
            always = m["acc"] == 101
            move_props[row] = [m["bp"] / 150, 1.0 if always else m["acc"] / 100, float(always),
                               *[float(to_id(m["cat"]) == c) for c in CATEGORIES], m["pri"] / 5,
                               *_type_vec([m["type"]]), *[float(m[f]) for f in MOVE_FLAGS]]

    priors = json.loads((HERE / "randbats_gen9.json").read_text())
    out = {"species_props": species_props, "move_props": move_props}
    for name, k in (("moves", K_MOVES), ("items", K_ITEMS), ("abilities", K_ABILITIES), ("tera", K_TERA)):
        out[f"prior_{name}_ids"] = np.zeros((SIZES["species"], k), dtype=np.int64)
        out[f"prior_{name}_p"] = np.zeros((SIZES["species"], k), dtype=np.float32)
    by_id = {to_id(k): v for k, v in priors.items()}
    for sid, row in SPECIES.items():
        entry = by_id.get(sid) or by_id.get(dex["species"].get(sid, {}).get("base", ""))
        if not entry:
            continue
        moves: dict[str, float] = {}
        tera: dict[str, float] = {}
        for role in entry.get("roles", {}).values():
            w = role.get("weight", 0)
            for mv, p in role.get("moves", {}).items():
                moves[to_id(mv)] = moves.get(to_id(mv), 0) + w * p
            for t, p in role.get("teraTypes", {}).items():
                tera[to_id(t)] = tera.get(to_id(t), 0) + w * p
        tables = (("moves", moves, MOVES, K_MOVES),
                  ("items", {to_id(k): v for k, v in entry.get("items", {}).items()}, ITEMS, K_ITEMS),
                  ("abilities", {to_id(k): v for k, v in entry.get("abilities", {}).items()}, ABILITIES, K_ABILITIES),
                  ("tera", tera, TYPES, K_TERA))
        for name, dist, vocab, k in tables:
            top = sorted(((p, vocab[i]) for i, p in dist.items() if i in vocab), reverse=True)[:k]
            for j, (p, idx) in enumerate(top):
                out[f"prior_{name}_ids"][row, j] = idx
                out[f"prior_{name}_p"][row, j] = p
    return out
