"""Protocol log -> BattleState at the start of every turn.

Reference: sim/SIM-PROTOCOL.md in smogon/pokemon-showdown. Only messages that change
state are handled; the rest (crit, supereffective, miss, chat, ...) are ignored.
Accuracy is checked against Showdown's simulator in server/tests/test_battle_parser.py.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..ids import to_id
from .state import BattleState, FieldState, PokemonState, SideState

STAT_IDS = ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
# Volatiles the parser tracks (announced with -start/-end and kept until switch-out).
TRACKED_VOLATILES = {
    "substitute", "confusion", "leechseed", "encore", "taunt", "yawn", "disable",
    "focusenergy", "torment", "attract", "curse", "nightmare", "embargo", "healblock",
    "magnetrise", "aquaring", "ingrain", "saltcure", "syrupbomb", "smackdown",
    "stockpile", "perishsong", "protosynthesis", "quarkdrive",
    "flashfire", "charge", "throatchop", "noretreat", "octolock", "tarshot", "gastroacid",
    "imprison", "powertrick", "laserfocus", "glaiverush", "dragoncheer", "leechseed",
}
# Volatiles with `duration: 2` in the simulator: still there at the start of the next
# turn, gone at the one after (unless renewed). They end silently.
TWO_TURN_VOLATILES = {"laserfocus", "glaiverush"}
VOLATILE_ALIASES = {"perish0": "perishsong", "perish1": "perishsong", "perish2": "perishsong",
                    "perish3": "perishsong", "stockpile1": "stockpile", "stockpile2": "stockpile",
                    "stockpile3": "stockpile"}
SIDE_LAYERS = {"spikes", "toxicspikes"}
_HP_RE = re.compile(r"^(\d+)(?:/(\d+))?[a-z]?$")


@dataclass
class ParseResult:
    states: list[dict] = field(default_factory=list)   # one per turn start, plus the final state
    format: str = ""
    format_id: str = ""
    warnings: list[str] = field(default_factory=list)


_TAG_RE = re.compile(r"^\[([a-z]+)\]\s*(.*)$")  # [from] x, [of] y, [silent]; not "[Gen 9] ..."


def _split(line: str) -> tuple[str, list[str], dict[str, str]]:
    """'|kind|a|b|[from] x|[of] y' -> ('kind', ['a', 'b'], {'from': 'x', 'of': 'y'})."""
    parts = line.split("|")[1:]
    kind = parts[0] if parts else ""
    args: list[str] = []
    tags: dict[str, str] = {}
    for p in parts[1:]:
        m = _TAG_RE.match(p)
        if m:
            tags[m.group(1)] = m.group(2).strip()
        else:
            args.append(p)
    return kind, args, tags


# Major (no dash) message kinds this parser handles. Minor kinds start with "-".
MAJOR = {"player", "teamsize", "gametype", "gen", "tier", "poke", "turn", "win", "tie",
         "switch", "drag", "replace", "detailschange", "swap", "faint", "move", "cant"}
AS_ONE = {"calyrexshadow": "asonespectrier", "calyrexice": "asoneglastrier"}
# In-battle formes with exactly one ability (Megas, Primals, Terapagos, ...): the forme
# change sets the ability without logging it. Generated from Showdown's data/pokedex.ts
# (MIT) at commit ac7b7da0f9; regenerate when new Megas are added.
FORME_ABILITIES: dict[str, str] = json.loads(
    (Path(__file__).parent / "data" / "forme_abilities.json").read_text())
AS_ONE_PARTS = {"unnerve", "grimneigh", "chillingneigh"}


def _strip_effect(effect: str) -> tuple[str, str]:
    """'item: Leftovers' -> ('item', 'leftovers'); 'Spikes' -> ('', 'spikes')."""
    if ": " in effect:
        kind, _, name = effect.partition(": ")
        if kind in ("move", "item", "ability", "pokemon"):
            return kind, to_id(name)
    return "", to_id(effect)


def _parse_details(details: str) -> dict:
    parts = [p.strip() for p in details.split(",")]
    out = {"species": parts[0], "level": 100, "gender": "", "shiny": False, "tera": ""}
    for p in parts[1:]:
        if p.startswith("L") and p[1:].isdigit():
            out["level"] = int(p[1:])
        elif p in ("M", "F"):
            out["gender"] = p
        elif p == "shiny":
            out["shiny"] = True
        elif p.startswith("tera:"):
            out["tera"] = p[5:]
    return out


def _parse_hp(text: str) -> tuple[int, int | None, str, bool]:
    """'261/261 par' -> (261, 261, 'par', False); '0 fnt' -> (0, None, '', True);
    '20/100y' (Champions colour suffix) -> (20, 100, '', False)."""
    hp_part, _, status = text.strip().partition(" ")
    if status == "fnt" or hp_part == "0":
        return 0, None, "", True
    m = _HP_RE.match(hp_part)
    if not m:
        return 0, None, status, False
    hp = int(m.group(1))
    maxhp = int(m.group(2)) if m.group(2) else None
    return hp, maxhp, status, False


class LogParser:
    def __init__(self) -> None:
        self.state = BattleState()
        self.result = ParseResult()
        self._pre_switch: dict[int, PokemonState] = {}  # id(pokemon) -> copy at switch-in (Illusion)
        self._last_move: dict[str, str] = {}             # side -> last move id used (Baton Pass etc.)
        self._timed: dict[tuple[int, str], int] = {}     # (id(pokemon), volatile) -> turn started

    # ------------------------------------------------------------------ helpers
    def _side(self, ident: str) -> SideState:
        return self.state.sides[ident[:2]]

    def _ident(self, ident: str) -> tuple[SideState, int | None, str]:
        """'p1a: Name' -> (side, 0, 'Name'); 'p1: Name' -> (side, None, 'Name')."""
        pos_part, _, name = ident.partition(": ")
        side = self.state.sides[pos_part[:2]]
        position = ord(pos_part[2]) - ord("a") if len(pos_part) > 2 else None
        return side, position, name.strip()

    def _mon(self, ident: str) -> PokemonState | None:
        if not ident or ident[:2] not in self.state.sides:
            return None
        side, position, name = self._ident(ident)
        mon = side.find(name)
        if mon is None and position is not None:
            mon = side.active_at(position)
        return mon

    def _get_or_create(self, side: SideState, name: str, details: dict) -> PokemonState:
        mon = side.find(name)
        if mon is None:
            # A team-preview entry has no nickname yet: match it by species.
            for p in side.team:
                if not p.seen and to_id(p.base_species.split("-")[0]) == to_id(details["species"].split("-")[0]) \
                        and p.name == p.base_species:
                    p.name = name
                    mon = p
                    break
        if mon is None:
            mon = PokemonState(name=name, species=details["species"], base_species=details["species"])
            side.team.append(mon)
        return mon

    def _set_hp(self, mon: PokemonState, text: str) -> None:
        if not text.strip():
            return  # e.g. |-formechange|p1a: Minior|Minior-Meteor||[from] ability: Shields Down
        hp, maxhp, status, fainted = _parse_hp(text)
        if fainted:
            mon.hp, mon.fainted, mon.status = 0, True, ""
            return
        mon.hp = hp
        if maxhp is not None:
            mon.maxhp = maxhp
            mon.hp_exact = maxhp != 100 or mon.hp_exact
        if hp > 0:
            mon.fainted = False
        mon.status = status if status in ("brn", "par", "slp", "frz", "psn", "tox") else ""

    def _reveal_item(self, mon: PokemonState | None, item: str, acquired: bool = False) -> None:
        if mon is not None and item:
            mon.item = item
            if mon.orig_item is None and not acquired:
                mon.orig_item = item

    def _reveal_ability(self, mon: PokemonState | None, ability: str) -> None:
        if mon is None or not ability:
            return
        if ability == "asone":
            ability = AS_ONE.get(to_id(mon.species), "asonespectrier")
        if (mon.ability or "").startswith("asone") and ability in AS_ONE_PARTS:
            return  # As One announces itself, then acts as Unnerve + Grim/Chilling Neigh
        mon.ability = ability
        if mon.base_ability is None:
            mon.base_ability = ability

    def _apply_from(self, kind: str, target: PokemonState | None, tags: dict[str, str]) -> None:
        """Reveal the item or ability named in a [from] tag.

        [from] item: X / ability: X usually belongs to the [of] Pokemon if one is given
        (Rocky Helmet, Rough Skin, Drought, Intimidate), else to the line's Pokemon.
        Exception: on -heal, absorbing abilities (Volt Absorb) list the attacker as [of].
        """
        src = tags.get("from", "")
        if not src:
            return
        etype, eid = _strip_effect(src)
        if etype not in ("item", "ability"):
            return
        owner = target
        if "of" in tags and kind != "-heal":
            owner = self._mon(tags["of"]) or target
        if owner is None:
            return
        if etype == "item":
            # Only fills in an unknown item: a berry's |-heal|...|[from] item: Sitrus Berry
            # comes right after the |-enditem| that used it up.
            if owner.item is None:
                self._reveal_item(owner, eid)
        elif owner.ability is None or owner.ability == eid or owner.ability.startswith("asone"):
            self._reveal_ability(owner, eid)

    def _switch_out(self, mon: PokemonState) -> None:
        mon.active = False
        mon.position = None
        mon.boosts = {}
        mon.volatiles = []
        mon.transformed = False
        mon.species = mon.base_species  # temporary formes (-formechange) revert
        if mon.base_ability is not None and mon.ability != mon.base_ability:
            mon.ability = mon.base_ability  # traced / skill-swapped abilities revert
        # Silent switch-out effects of known abilities (nothing is logged for these).
        if not mon.fainted and mon.ability == "regenerator" and mon.hp_exact:
            mon.hp = min(mon.maxhp, mon.hp + mon.maxhp // 3)
        if not mon.fainted and mon.ability == "naturalcure":
            mon.status = ""

    def _snapshot(self) -> None:
        self.result.states.append(self.state.snapshot())

    # ------------------------------------------------------------------ main loop
    def feed(self, line: str) -> None:
        if not line.startswith("|"):
            return
        kind, args, tags = _split(line)
        if not kind.startswith("-") and kind not in MAJOR:
            return  # e.g. |start (battle start) must not reach the -start volatile handler
        handler = getattr(self, "_on_" + kind.lstrip("-").replace("-", "_"), None)
        if handler is not None:
            try:
                handler(args, tags, kind)
            except (IndexError, KeyError, ValueError) as e:
                self.result.warnings.append(f"{line[:80]}: {type(e).__name__}: {e}")

    # ---- setup
    def _on_player(self, args, tags, kind):
        if len(args) >= 2 and args[0] in self.state.sides and args[1]:
            self.state.sides[args[0]].name = args[1]

    def _on_teamsize(self, args, tags, kind):
        self.state.sides[args[0]].team_size = int(args[1])

    def _on_gametype(self, args, tags, kind):
        self.state.gametype = args[0]

    def _on_gen(self, args, tags, kind):
        self.state.gen = int(args[0])

    def _on_tier(self, args, tags, kind):
        self.result.format = args[0]
        self.result.format_id = to_id(args[0])

    def _on_poke(self, args, tags, kind):
        side = self.state.sides[args[0]]
        d = _parse_details(args[1])
        species = d["species"].replace("-*", "")
        side.team.append(PokemonState(name=species, species=species, base_species=species,
                                      level=d["level"], gender=d["gender"], shiny=d["shiny"]))

    # ---- turn structure
    def _on_turn(self, args, tags, kind):
        self.state.turn = int(args[0])
        for (mon_id, vid), started in list(self._timed.items()):
            if self.state.turn - started >= 2:
                del self._timed[(mon_id, vid)]
                for side in self.state.sides.values():
                    for mon in side.team:
                        if id(mon) == mon_id and vid in mon.volatiles:
                            mon.volatiles = [v for v in mon.volatiles if v != vid]
        self._snapshot()

    def _add_timed_volatile(self, mon: PokemonState, vid: str) -> None:
        if vid not in mon.volatiles:
            mon.volatiles = sorted(mon.volatiles + [vid])
        self._timed[(id(mon), vid)] = self.state.turn

    def _on_singlemove(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None and len(args) > 1 and to_id(args[1]) == "glaiverush":
            self._add_timed_volatile(mon, "glaiverush")

    def _on_win(self, args, tags, kind):
        self.state.ended = True
        self.state.winner = args[0] if args else None

    def _on_tie(self, args, tags, kind):
        self.state.ended = True

    # ---- switching and formes
    def _on_switch(self, args, tags, kind):
        side, position, name = self._ident(args[0])
        d = _parse_details(args[1])
        old = side.active_at(position or 0)
        incoming = self._get_or_create(side, name, d)
        passed_boosts: dict[str, int] = {}
        passed_volatiles: list[str] = []
        if old is not None and old is not incoming:
            last = self._last_move.get(side.id)
            if last == "batonpass":
                passed_boosts = dict(old.boosts)
                passed_volatiles = [v for v in old.volatiles if v in ("substitute", "leechseed", "confusion",
                                                                     "curse", "aquaring", "ingrain", "focusenergy",
                                                                     "magnetrise", "perishsong")]
            elif last == "shedtail":
                passed_volatiles = ["substitute"] if "substitute" in old.volatiles else []
            self._switch_out(old)
        self._last_move.pop(side.id, None)
        self._pre_switch[id(incoming)] = copy.deepcopy(incoming)
        incoming.active, incoming.position, incoming.seen = True, position or 0, True
        incoming.species = d["species"]
        if to_id(incoming.base_species) != to_id(d["species"]) and "-" in d["species"]:
            # e.g. Palafin-Hero switching back in: a permanent forme seen on switch
            incoming.base_species = d["species"]
        incoming.level, incoming.gender, incoming.shiny = d["level"], d["gender"], d["shiny"]
        if d["tera"]:
            incoming.tera_type = incoming.tera_known = d["tera"]
        incoming.boosts = passed_boosts
        incoming.volatiles = passed_volatiles
        self._set_hp(incoming, args[2])

    _on_drag = _on_switch

    def _on_replace(self, args, tags, kind):
        """Illusion ended: the Pokemon in this slot was really `args[0]`."""
        side, position, name = self._ident(args[0])
        d = _parse_details(args[1])
        disguise = side.active_at(position or 0)
        real = self._get_or_create(side, name, d)
        if disguise is not None and disguise is not real:
            before = self._pre_switch.get(id(disguise))
            gained_moves = [m for m in disguise.moves if before is None or m not in before.moves]
            real.boosts, real.volatiles = disguise.boosts, disguise.volatiles
            if before is not None:
                restored = copy.deepcopy(before)
                restored.active, restored.position = False, None
                idx = side.team.index(disguise)
                side.team[idx] = restored
            else:
                self._switch_out(disguise)
            for m in gained_moves:
                if m not in real.moves:
                    real.moves.append(m)
        real.active, real.position, real.seen = True, position or 0, True
        real.species = real.base_species = d["species"]
        real.level, real.gender, real.shiny = d["level"], d["gender"], d["shiny"]
        self._reveal_ability(real, "illusion")
        if len(args) > 2 and args[2]:
            self._set_hp(real, args[2])
        elif disguise is not None and disguise is not real:
            # |replace| carries no HP: the HP shown for the disguise was the real one.
            real.hp, real.maxhp, real.hp_exact = disguise.hp, disguise.maxhp, disguise.hp_exact
            real.status = disguise.status

    def _on_detailschange(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        d = _parse_details(args[1])
        mon.species = mon.base_species = d["species"]
        if d["tera"]:
            mon.tera_type = mon.tera_known = d["tera"]
        forme_ability = FORME_ABILITIES.get(to_id(d["species"]))
        if forme_ability:  # permanent (Mega, Terapagos): the new ability stays
            if not mon.forme_ability:
                mon.pre_forme_ability = mon.base_ability
            mon.ability = mon.base_ability = mon.forme_ability = forme_ability
        elif mon.forme_ability:
            # Back to a normal forme (Terapagos / Ogerpon revert when they faint, with a
            # [silent] detailschange): the ability from before the forme change returns.
            mon.ability = mon.base_ability = mon.pre_forme_ability
            mon.forme_ability = None
        if len(args) > 2:
            self._set_hp(mon, args[2])

    def _on_formechange(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        mon.species = _parse_details(args[1])["species"]
        self._apply_from(kind, mon, tags)
        forme_ability = FORME_ABILITIES.get(to_id(mon.species))
        if forme_ability:  # temporary: reverts with the forme on switch-out
            mon.ability = forme_ability
        if len(args) > 2:
            self._set_hp(mon, args[2])

    def _on_transform(self, args, tags, kind):
        mon, target = self._mon(args[0]), self._mon(args[1]) if len(args) > 1 else None
        self._apply_from(kind, mon, tags)  # [from] ability: Imposter -> its original ability
        if mon is not None and target is not None:
            mon.species = target.species
            mon.boosts = dict(target.boosts)
            mon.transformed = True  # moves it uses now are the target's, not its own
            # It copies the target's ability too; unknown if the target's is unknown.
            if mon.base_ability is None and mon.ability is not None:
                mon.base_ability = mon.ability
            mon.ability = target.ability

    def _on_swap(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None or len(args) < 2 or not args[1].isdigit():
            return
        side = self._side(args[0])
        new_pos = int(args[1])
        other = side.active_at(new_pos)
        if other is not None and other is not mon:
            other.position = mon.position
        mon.position = new_pos

    def _on_faint(self, args, tags, kind):
        # Matches the simulator's faint handling (sim/battle.ts faintMessages): the Pokemon
        # leaves the field, loses volatiles and boosts, and is no longer Terastallized.
        mon = self._mon(args[0])
        if mon is not None:
            mon.hp, mon.fainted, mon.status = 0, True, ""
            mon.active, mon.position, mon.boosts, mon.volatiles = False, None, {}, []
            mon.transformed, mon.tera_type = False, ""
            mon.species = mon.base_species
            if mon.base_ability is not None:
                mon.ability = mon.base_ability  # e.g. a traced ability reverts to Trace

    # ---- moves
    def _on_move(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None or len(args) < 2:
            return
        move = to_id(args[1])
        self._last_move[mon_side(args[0])] = move
        # A [from] tag means another move called this one (Sleep Talk, Metronome, Copycat),
        # except [from] lockedmove (Outrage turns 2-3), which is still the user's own move.
        called = "from" in tags and not tags["from"].startswith("lockedmove")
        if not called and not mon.transformed and "zeffect" not in tags and move not in ("struggle", "recharge") and move not in mon.moves:
            mon.moves.append(move)
        self._apply_from(kind, mon, tags)

    def _on_cant(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        etype, eid = _strip_effect(args[1]) if len(args) > 1 else ("", "")
        if etype == "ability":
            self._reveal_ability(mon, eid)
        elif etype == "item":
            self._reveal_item(mon, eid)
        if len(args) > 2 and args[2]:
            # |cant|X|Disable|Protect: X's move. But with [of] (Queenly Majesty, Dazzling,
            # Armor Tail) the line names the protecting Pokemon and the move is the attacker's.
            owner = self._mon(tags["of"]) if "of" in tags else mon
            m = to_id(args[2])
            if owner is not None and m and m not in owner.moves and not owner.transformed:
                owner.moves.append(m)

    # ---- HP and status
    def _on_damage(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        self._set_hp(mon, args[1])
        self._apply_from(kind, mon, tags)

    _on_heal = _on_damage

    def _on_sethp(self, args, tags, kind):
        # |-sethp|POKEMON|HP  (older logs can list two pokemon/hp pairs)
        for i in range(0, len(args) - 1, 2):
            mon = self._mon(args[i])
            if mon is not None:
                self._set_hp(mon, args[i + 1])

    def _on_status(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.status = args[1]
        self._apply_from(kind, mon, tags)

    def _on_curestatus(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.status = ""
        self._apply_from(kind, mon, tags)

    def _on_cureteam(self, args, tags, kind):
        side = self._side(args[0])
        for mon in side.team:
            mon.status = ""

    # ---- boosts
    def _boost(self, mon: PokemonState, stat: str, delta: int) -> None:
        value = max(-6, min(6, mon.boosts.get(stat, 0) + delta))
        if value:
            mon.boosts[stat] = value
        else:
            mon.boosts.pop(stat, None)

    def _on_boost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        amount = int(args[2]) if len(args) > 2 and args[2].lstrip("-").isdigit() else 0
        self._boost(mon, args[1], -amount if kind == "-unboost" else amount)
        self._apply_from(kind, mon, tags)

    _on_unboost = _on_boost

    def _on_setboost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        mon.boosts.pop(args[1], None)
        self._boost(mon, args[1], int(args[2]))
        self._apply_from(kind, mon, tags)

    def _on_clearboost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.boosts = {}

    def _on_clearallboost(self, args, tags, kind):
        for side in self.state.sides.values():
            for mon in side.team:
                mon.boosts = {}

    def _on_clearpositiveboost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.boosts = {k: v for k, v in mon.boosts.items() if v < 0}

    def _on_clearnegativeboost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.boosts = {k: v for k, v in mon.boosts.items() if v > 0}

    def _on_invertboost(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.boosts = {k: -v for k, v in mon.boosts.items()}

    def _on_copyboost(self, args, tags, kind):
        mon, target = self._mon(args[0]), self._mon(args[1])
        if mon is not None and target is not None:
            mon.boosts = dict(target.boosts)

    def _on_swapboost(self, args, tags, kind):
        a, b = self._mon(args[0]), self._mon(args[1])
        if a is None or b is None:
            return
        stats = [s.strip() for s in args[2].split(",")] if len(args) > 2 and args[2] else list(STAT_IDS)
        for s in stats:
            va, vb = a.boosts.pop(s, 0), b.boosts.pop(s, 0)
            if vb:
                a.boosts[s] = vb
            if va:
                b.boosts[s] = va

    # ---- items and abilities
    def _on_item(self, args, tags, kind):
        mon = self._mon(args[0])
        src = tags.get("from", "")
        # An item gained from Trick / Switcheroo / Thief / Bestow isn't the one it started with.
        self._reveal_item(mon, to_id(args[1]) if len(args) > 1 else "", acquired=src.startswith("move:"))
        etype, eid = _strip_effect(src) if src else ("", "")
        if etype == "ability" and "of" in tags:
            self._reveal_ability(self._mon(tags["of"]), eid)  # Frisk, Pickpocket...
        elif etype == "ability":
            self._reveal_ability(mon, eid)

    def _on_enditem(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None:
            return
        # The item was used up, knocked off, stolen or flung: either way it's gone now.
        if mon.orig_item is None and len(args) > 1 and mon.item is None:
            mon.orig_item = to_id(args[1])  # first we hear of it is losing it: it was the original
        mon.item = ""
        src = tags.get("from", "")
        etype, eid = _strip_effect(src) if src else ("", "")
        if etype == "ability" and "of" in tags:
            self._reveal_ability(self._mon(tags["of"]), eid)  # e.g. Magician, Pickpocket

    def _on_ability(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None or len(args) < 2:
            return
        ability = to_id(args[1])
        src = tags.get("from", "")
        etype, eid = _strip_effect(src) if src else ("", "")
        if etype == "ability" and eid in ("trace", "receiver", "powerofalchemy"):
            if mon.base_ability is None:
                mon.base_ability = eid
            mon.ability = ability
            return
        if etype in ("move", "ability"):
            # Role Play, Entrainment, Mummy, Wandering Spirit...: the ability was changed
            # by an effect, so this isn't its original ability.
            mon.ability = ability
            return
        self._reveal_ability(mon, ability)

    def _on_endability(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None:
            mon.volatiles = sorted(set(mon.volatiles) | {"gastroacid"})

    def _on_mega(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None and len(args) > 2:
            self._reveal_item(mon, to_id(args[2]))

    def _on_terastallize(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is not None and len(args) > 1:
            mon.tera_type = mon.tera_known = args[1]

    def _on_activate(self, args, tags, kind):
        mon = self._mon(args[0]) if args else None
        if len(args) < 2:
            return
        etype, eid = _strip_effect(args[1])
        if etype == "item":
            # Only fills in an unknown item: |-activate|X|item: Leppa Berry|...|[consumed]
            # comes after the |-enditem| that used it up.
            if mon is not None and mon.item is None:
                self._reveal_item(mon, eid)
        elif etype == "ability":
            self._reveal_ability(mon, eid)
        elif etype == "move" and eid == "skillswap" and mon is not None and "of" in tags:
            other = self._mon(tags["of"])
            if len(args) >= 4 and other is not None:
                # |-activate|SOURCE|move: Skill Swap|SOURCE_NEW|TARGET_NEW|[of] TARGET
                mon.ability, other.ability = to_id(args[2]), to_id(args[3])
        # Trick / Switcheroo are followed by |-item| lines for both sides; nothing to do here.
        self._apply_from(kind, mon, tags)

    def _on_block(self, args, tags, kind):
        mon = self._mon(args[0]) if args else None
        if len(args) > 1:
            etype, eid = _strip_effect(args[1])
            if etype == "ability":
                self._reveal_ability(mon, eid)
            elif etype == "item":
                self._reveal_item(mon, eid)

    def _on_immune(self, args, tags, kind):
        self._apply_from(kind, self._mon(args[0]) if args else None, tags)

    _on_fail = _on_immune
    _on_prepare = _on_immune

    # ---- volatiles
    def _volatile_id(self, effect: str) -> str:
        _, eid = _strip_effect(effect)
        eid = VOLATILE_ALIASES.get(eid, eid)
        for prefix in ("protosynthesis", "quarkdrive"):
            if eid.startswith(prefix):
                return prefix
        return eid

    def _on_start(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None or len(args) < 2:
            return
        vid = self._volatile_id(args[1])
        if vid in TWO_TURN_VOLATILES:
            self._add_timed_volatile(mon, vid)
        elif vid in TRACKED_VOLATILES and vid not in mon.volatiles:
            mon.volatiles = sorted(mon.volatiles + [vid])
        self._apply_from(kind, mon, tags)
        if vid in ("protosynthesis", "quarkdrive") and "fromitem" in tags:
            mon.item = "boosterenergy"

    def _on_end(self, args, tags, kind):
        mon = self._mon(args[0])
        if mon is None or len(args) < 2:
            return
        vid = self._volatile_id(args[1])
        if vid in mon.volatiles:
            mon.volatiles = [v for v in mon.volatiles if v != vid]
        self._apply_from(kind, mon, tags)

    # ---- field and sides
    def _on_weather(self, args, tags, kind):
        weather = to_id(args[0]) if args else ""
        if "upkeep" in tags:
            return
        self.state.field.weather = "" if weather == "none" else weather
        self._apply_from(kind, None, tags)

    def _on_fieldstart(self, args, tags, kind):
        _, eid = _strip_effect(args[0])
        if eid.endswith("terrain"):
            self.state.field.terrain = eid
        elif eid not in self.state.field.pseudo_weather:
            self.state.field.pseudo_weather = sorted(self.state.field.pseudo_weather + [eid])
        self._apply_from(kind, None, tags)

    def _on_fieldend(self, args, tags, kind):
        _, eid = _strip_effect(args[0])
        if eid.endswith("terrain"):
            if self.state.field.terrain == eid:
                self.state.field.terrain = ""
        else:
            self.state.field.pseudo_weather = [p for p in self.state.field.pseudo_weather if p != eid]

    def _on_sidestart(self, args, tags, kind):
        side = self.state.sides[args[0][:2]]
        _, cid = _strip_effect(args[1])
        if cid in SIDE_LAYERS:
            side.conditions[cid] = side.conditions.get(cid, 0) + 1
        else:
            side.conditions[cid] = 1
        self._apply_from(kind, None, tags)

    def _on_sideend(self, args, tags, kind):
        side = self.state.sides[args[0][:2]]
        _, cid = _strip_effect(args[1])
        side.conditions.pop(cid, None)

    def _on_swapsideconditions(self, args, tags, kind):
        a, b = self.state.sides["p1"], self.state.sides["p2"]
        swappable = {"spikes", "toxicspikes", "stealthrock", "stickyweb", "reflect", "lightscreen",
                     "auroraveil", "tailwind", "safeguard", "mist", "luckychant", "gmaxsteelsurge",
                     "firepledge", "grasspledge", "waterpledge"}
        a_keep = {k: v for k, v in a.conditions.items() if k not in swappable}
        b_keep = {k: v for k, v in b.conditions.items() if k not in swappable}
        a_move = {k: v for k, v in a.conditions.items() if k in swappable}
        b_move = {k: v for k, v in b.conditions.items() if k in swappable}
        a.conditions = {**a_keep, **b_move}
        b.conditions = {**b_keep, **a_move}


def mon_side(ident: str) -> str:
    return ident[:2]


def parse_log(log: str) -> ParseResult:
    parser = LogParser()
    for line in log.splitlines():
        parser.feed(line)
    final = parser.state.snapshot()
    if not parser.result.states or parser.result.states[-1] != final:
        parser.result.states.append(final)
    return parser.result
