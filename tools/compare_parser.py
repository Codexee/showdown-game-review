"""Grade the log parser (server/battle) against Showdown's simulator.

    uv run python tools/compare_parser.py <replays-dir> <truth.jsonl>

truth.jsonl comes from `node tools/sim-states.cjs`. For every turn of every replay,
each field the parser knows is checked against the simulator's true state. Fields the
parser hasn't seen (an unrevealed item, say) are not counted as errors; revealing
something wrong is.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from server.battle import parse_log
from server.battle.parser import TRACKED_VOLATILES
from server.ids import to_id

FIELD_PSEUDO = {"trickroom", "gravity", "magicroom", "wonderroom", "fairylock", "iondeluge",
                "mudsport", "watersport"}


def compare_state(parsed: dict, truth: dict, disguised: dict[str, set[str]] | None = None) -> list[tuple[str, str]]:
    """Return (field, detail) for every disagreement."""
    errs: list[tuple[str, str]] = []
    t = f"turn {truth['turn']}{' end' if truth['ended'] else ''}"
    if parsed["field"]["weather"] != truth["weather"]:
        errs.append(("weather", f"{t}: {parsed['field']['weather']!r} vs {truth['weather']!r}"))
    if parsed["field"]["terrain"] != truth["terrain"]:
        errs.append(("terrain", f"{t}: {parsed['field']['terrain']!r} vs {truth['terrain']!r}"))
    tp = sorted(set(truth["pseudoWeather"]) & FIELD_PSEUDO)
    if sorted(parsed["field"]["pseudo_weather"]) != tp:
        errs.append(("pseudo_weather", f"{t}: {parsed['field']['pseudo_weather']} vs {tp}"))
    for tside in truth["sides"]:
        pside = parsed["sides"][tside["id"]]
        if pside["conditions"] != tside["sideConditions"]:
            errs.append(("side_conditions", f"{t} {tside['id']}: {pside['conditions']} vs {tside['sideConditions']}"))
        truth_mons = {m["name"]: m for m in tside["pokemon"]}
        for pm in pside["team"]:
            where = f"{t} {tside['id']} {pm['name']}"
            if not pm["seen"]:
                continue  # team-preview only (in best-of-3 the sim keeps only the chosen ones)
            tm = truth_mons.get(pm["name"])
            if tm is None:
                errs.append(("unknown_pokemon", where))
                continue
            checks = {
                "species": (to_id(pm["species"]), to_id(tm["species"])),
                "hp": ((pm["hp"], pm["maxhp"]) if not pm["fainted"] else (0,),
                       (tm["hp"], tm["maxhp"]) if not tm["fainted"] else (0,)),
                "fainted": (pm["fainted"], tm["fainted"]),
                "status": (pm["status"], "" if tm["fainted"] else tm["status"]),
                "active": (pm["active"], tm["active"]),
                "position": (pm["position"], tm["position"]),
                "boosts": (pm["boosts"], tm["boosts"]),
                "tera": (pm["tera_type"], tm["terastallized"]),
                "volatiles": (sorted(pm["volatiles"]),
                              sorted(v for v in tm["volatiles"] if v in TRACKED_VOLATILES)),
            }
            if pm["item"] is not None:
                checks["item"] = (pm["item"], tm["item"])
            if pm["ability"] is not None:
                checks["ability"] = (pm["ability"], tm["ability"])
            hide = (disguised or {}).get(tside["id"], set())
            checks["species"] = (HIDDEN_FORMES.get(checks["species"][0], checks["species"][0]),
                                 HIDDEN_FORMES.get(checks["species"][1], checks["species"][1]))
            bad_moves = [m for m in pm["moves"] if m not in tm["moves"]]
            if bad_moves:
                errs.append((_classify("moves", pm, tm, tside, hide), f"{where}: {bad_moves} not in {tm['moves']}"))
            for name, (a, b) in checks.items():
                if a != b:
                    errs.append((_classify(name, pm, tm, tside, hide), f"{where}: parsed {a!r} vs true {b!r}"))
    return errs


# Differences the log cannot reveal at that moment. They are reported separately and
# don't count as parser errors: the parser shows what a player could have known.
UNKNOWABLE = {"unknowable: silent Regenerator heal", "unknowable: Illusion not yet revealed",
              "unknowable: Illusion never revealed"}
# Formes the server shows under their base name in DETAILS (cosmetic to the player).
HIDDEN_FORMES = {"greninjabond": "greninja", "rockruffdusk": "rockruff"}


def _classify(name: str, pm: dict, tm: dict, tside: dict, disguised: set[str]) -> str:
    if name == "hp" and tm["ability"] == "regenerator" and pm["ability"] is None and tm["hp"] > pm["hp"]:
        return "unknowable: silent Regenerator heal"
    if pm["active"] and not tm["active"]:
        # The parser thinks this Pokemon is out because a Zoroark is wearing its name.
        if any(p["active"] and p["ability"] == "illusion" for p in tside["pokemon"]):
            return "unknowable: Illusion not yet revealed"
    if tm["active"] and not pm["active"] and tm["ability"] == "illusion":
        return "unknowable: Illusion not yet revealed"  # the disguised Zoroark itself
    if pm["name"] in disguised:
        # At some turn a Zoroark stood in this Pokemon's slot under its name, so what the
        # players saw under this name (HP, moves, ...) was partly the Zoroark's.
        return "unknowable: Illusion never revealed"
    return name


def disguised_names(result_states: list[dict], truth: dict) -> dict[str, set[str]]:
    """Per side: names the parser had on the field while the simulator had an Illusion user there."""
    by_turn = {s["turn"]: s for s in result_states if not s["ended"]}
    out: dict[str, set[str]] = {"p1": set(), "p2": set()}
    for ts in truth["states"]:
        ps = by_turn.get(ts["turn"])
        if ps is None:
            continue
        for tside in ts["sides"]:
            for z in tside["pokemon"]:
                if z["ability"] != "illusion" or not z["active"]:
                    continue
                for pm in ps["sides"][tside["id"]]["team"]:
                    if pm["active"] and pm["position"] == z["position"] and pm["name"] != z["name"]:
                        out[tside["id"]].add(pm["name"])
    return out


def compare_replay(replay: dict, truth: dict) -> tuple[int, list[tuple[str, str]]]:
    result = parse_log(replay["log"])
    parsed_by_turn = {s["turn"]: s for s in result.states if not s["ended"]}
    final = result.states[-1]
    errs: list[tuple[str, str]] = []
    checked = 0
    disguised = disguised_names(result.states, truth)
    for ts in truth["states"]:
        ps = final if ts["ended"] else parsed_by_turn.get(ts["turn"])
        if ps is None:
            errs.append(("missing_turn", f"turn {ts['turn']}"))
            continue
        checked += 1
        errs.extend(compare_state(ps, ts, disguised))
    errs.extend(("parser_warning", w) for w in result.warnings)
    return checked, errs


def main(replay_dir: str, truth_path: str) -> int:
    replays = {p.stem: json.loads(p.read_text()) for p in Path(replay_dir).glob("*.json")}
    totals: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    states = clean = games = clean_games = 0
    for line in open(truth_path):
        truth = json.loads(line)
        if "error" in truth or truth["id"] not in replays:
            continue
        games += 1
        checked, errs = compare_replay(replays[truth["id"]], truth)
        real = [(f, d) for f, d in errs if f not in UNKNOWABLE]
        states += checked
        bad_turns = {d.split(":")[0].split(" ")[1] for _, d in real if d.startswith("turn ")}
        clean += checked - len(bad_turns)
        clean_games += not real
        for field, detail in errs:
            totals[field] += 1
            if len(examples[field]) < 4:
                examples[field].append(f"{truth['id']} {detail}")
    errors = sum(n for f, n in totals.items() if f not in UNKNOWABLE)
    print(f"{games} games, {states} turn states checked")
    print(f"games with no parser error: {clean_games}/{games}; turn states with none: {clean}/{states}")
    print(f"parser errors: {errors}; not knowable from the log: {sum(totals[f] for f in UNKNOWABLE)}")
    for field, n in totals.most_common():
        print(f"\n{field}: {n}")
        for e in examples[field]:
            print("   ", e[:220])
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
