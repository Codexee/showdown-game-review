"""Dex facts for the review screen's info cards (2026-11-23): each Pokemon's types and base
stats, each move's type / category / power / accuracy / priority, and, for Random Battle,
the possible sets (roles with move, ability, item and Tera odds).

Sources: training/dex.json (Showdown's dex at the training commit) and
training/randbats_gen9.json (pkmn randbats stats), via server/review/worlds.py.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import ROOT
from ..ids import to_id


@lru_cache(maxsize=1)
def _dex() -> dict:
    return json.loads((ROOT / "training" / "dex.json").read_text())


def _species(name: str, base: str | None) -> dict | None:
    """Types and base stats; a forme entry without its own falls back to its base species."""
    sp = _dex()["species"]
    found: dict = {}
    for cand in (name, base or "", name.split("-")[0]):
        e = sp.get(to_id(cand)) or {}
        for k in ("types", "bs"):
            if k not in found and e.get(k):
                found[k] = e[k]
        if e.get("base") and e["base"] != to_id(cand):
            b = sp.get(e["base"]) or {}
            for k in ("types", "bs"):
                if k not in found and b.get(k):
                    found[k] = b[k]
        if "types" in found and "bs" in found:
            return found
    return found or None


def _odds(d: dict | None) -> dict[str, float]:
    return {k: round(float(v), 4) for k, v in (d or {}).items()}


def dex_for_game(states: list[dict], events: dict[int, list[dict]], format_id: str) -> dict:
    """{species: {name: {types, bs}}, moves: {id: {name, type, cat, bp, acc, pri}}, sets: {name: …}}."""
    from ..review.worlds import entry_for   # randbats set data

    random = "random" in format_id
    species: dict[str, dict] = {}
    sets: dict[str, dict] = {}
    move_ids: set[str] = set()
    names: dict[str, str] = {}
    for turn_events in events.values():
        for e in turn_events:
            if e.get("kind") == "move" and e.get("move") and " used " in e["text"]:
                nm = e["text"].split(" used ", 1)[1]
                nm = nm.split(" on ", 1)[0].rstrip(".").split(". It missed")[0]
                names.setdefault(e["move"], nm)
                move_ids.add(e["move"])
    for st in states:
        for side in st["sides"].values():
            for m in side["team"]:
                if not m.get("seen"):
                    continue
                move_ids.update(m.get("moves") or [])
                key = m["species"]
                if key not in species:
                    e = _species(key, m.get("base_species"))
                    species[key] = {"types": (e or {}).get("types", []), "bs": (e or {}).get("bs", {})}
                if random and key not in sets:
                    entry = entry_for(m)
                    if entry:
                        roles = []
                        for rname, r in (entry.get("roles") or {}).items():
                            mv = {}
                            for nm, p in (r.get("moves") or {}).items():
                                mid = to_id(nm)
                                names.setdefault(mid, nm)
                                move_ids.add(mid)
                                mv[mid] = round(float(p), 4)
                            roles.append({"name": rname, "weight": float(r.get("weight", 1)), "moves": mv,
                                          "abilities": _odds(r.get("abilities")), "items": _odds(r.get("items")),
                                          "tera": _odds(r.get("teraTypes"))})
                        sets[key] = {"level": entry.get("level"), "roles": roles}
    dm = _dex()["moves"]
    moves = {}
    for mid in sorted(move_ids):
        e = dm.get(mid)
        if e:
            moves[mid] = {"name": names.get(mid, mid), "type": e["type"], "cat": e["cat"], "bp": e["bp"],
                          "acc": e["acc"], "pri": e["pri"]}
    return {"species": species, "moves": moves, "sets": sets}
