"""Battle state as revealed by a protocol log.

Conventions
- Names of moves, items, abilities, conditions and weather are stored as Showdown ids
  (lowercase alphanumerics, `to_id`), the same as the simulator uses.
- Unknown vs known-empty: `item is None` means not revealed yet; `item == ""` means
  revealed to have no item (knocked off, consumed, or flung).
- HP: `maxhp` is the real max when the log shows exact HP (replay logs do, for both
  sides). When a log only shows percentages, `maxhp` is 100 and `hp_exact` is False.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field


@dataclass
class PokemonState:
    name: str                       # nickname as in the log ident (unique per side)
    species: str                    # current forme, e.g. "Palafin-Hero"
    base_species: str               # forme after permanent changes (mega, Palafin-Hero)
    level: int = 100
    gender: str = ""
    shiny: bool = False
    hp: int = 100
    maxhp: int = 100
    hp_exact: bool = False
    status: str = ""                # "", brn, par, slp, frz, psn, tox
    fainted: bool = False
    active: bool = False
    position: int | None = None     # 0 = slot a, 1 = slot b (doubles)
    seen: bool = False              # has been on the field (not just team preview)
    boosts: dict[str, int] = field(default_factory=dict)
    volatiles: list[str] = field(default_factory=list)
    item: str | None = None
    ability: str | None = None      # current ability
    base_ability: str | None = None # ability it was revealed to have originally (e.g. trace)
    forme_ability: str | None = None      # set while in a forme that fixes the ability (Mega...)
    pre_forme_ability: str | None = None  # ability before that forme change (None = unknown)
    moves: list[str] = field(default_factory=list)  # revealed moves, in order seen
    transformed: bool = False       # Transform/Imposter: moves used now belong to the target
    tera_type: str = ""             # set while Terastallized (cleared on faint, like the sim)
    tera_known: str | None = None   # Tera type if revealed (same as tera_type once used)


@dataclass
class SideState:
    id: str                         # p1, p2
    name: str = ""
    team_size: int | None = None
    team: list[PokemonState] = field(default_factory=list)
    conditions: dict[str, int] = field(default_factory=dict)  # id -> layers (1 if no layers)

    def find(self, name: str) -> PokemonState | None:
        for p in self.team:
            if p.name == name:
                return p
        return None

    def active_at(self, position: int) -> PokemonState | None:
        for p in self.team:
            if p.active and p.position == position:
                return p
        return None


@dataclass
class FieldState:
    weather: str = ""
    terrain: str = ""
    pseudo_weather: list[str] = field(default_factory=list)


@dataclass
class BattleState:
    turn: int = 0
    gametype: str = "singles"
    gen: int | None = None
    sides: dict[str, SideState] = field(default_factory=lambda: {"p1": SideState("p1"), "p2": SideState("p2")})
    field: FieldState = field(default_factory=FieldState)
    ended: bool = False
    winner: str | None = None       # player name

    def snapshot(self) -> dict:
        return copy.deepcopy(asdict(self))
