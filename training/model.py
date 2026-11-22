"""Eval model v1.1: a small transformer over 13 tokens (6 own Pokemon, 6 opposing, field).

Inputs per Pokemon token (vault benchmark-best-in-class, P0):
- learned embeddings of species, item, ability, the 4 revealed moves and Tera type,
- fixed properties looked up by id: base stats and types; move power, accuracy,
  category, priority, type and effect flags (ps-ppo, mikumiku: "static dex data"),
- randbats priors for what isn't revealed yet: a probability-weighted mix of the
  species' likely moves / items / abilities / Tera types,
- numbers: HP, status, boosts, active, fainted, seen, volatiles.
Field token: field numbers, last turn's events, and the last move each side used.

Heads:
- value: logit of "the player whose view this is wins" -> the eval bar.
- policy: [every move id..., switch to own slot 0-5] -> move review (stage 6).
- auxiliary (Jaxcalibur): the opponent's choice this turn, and each opposing
  Pokemon's item / ability / Tera type / moves as revealed by the end of the game.
No position embedding within a side: only own / opponent / field type embeddings.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

from training.features import N_FIELD, N_MON, N_SWITCH, SIZES
from training.tables import N_MOVE_PROPS, N_SPECIES_PROPS, build


@dataclass
class ModelConfig:
    d: int = 256
    layers: int = 6
    heads: int = 8
    ff: int = 1024
    dropout: float = 0.1
    species_dim: int = 96
    item_dim: int = 48
    ability_dim: int = 48
    move_dim: int = 64
    type_dim: int = 24

    def to_dict(self) -> dict:
        return asdict(self)


class EvalNet(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.species = nn.Embedding(SIZES["species"], cfg.species_dim)
        self.item = nn.Embedding(SIZES["items"], cfg.item_dim)
        self.ability = nn.Embedding(SIZES["abilities"], cfg.ability_dim)
        self.move = nn.Embedding(SIZES["moves"], cfg.move_dim)
        self.tera = nn.Embedding(SIZES["types"], cfg.type_dim)
        for name, arr in build().items():  # fixed tables, saved with the weights
            self.register_buffer(name, torch.from_numpy(arr), persistent=True)
        move_vec = cfg.move_dim + N_MOVE_PROPS
        in_dim = (cfg.species_dim + N_SPECIES_PROPS + 2 * cfg.item_dim + 2 * cfg.ability_dim
                  + 2 * move_vec + 2 * cfg.type_dim + N_MON)
        self.token_in = nn.Sequential(nn.Linear(in_dim, cfg.d), nn.GELU(), nn.Linear(cfg.d, cfg.d))
        self.field_in = nn.Sequential(nn.Linear(N_FIELD + 2 * move_vec, cfg.d), nn.GELU(), nn.Linear(cfg.d, cfg.d))
        self.kind = nn.Embedding(3, cfg.d)  # 0 own, 1 opponent, 2 field
        layer = nn.TransformerEncoderLayer(cfg.d, cfg.heads, cfg.ff, cfg.dropout, batch_first=True, norm_first=True,
                                           activation="gelu")
        self.encoder = nn.TransformerEncoder(layer, cfg.layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(cfg.d)
        two = 2 * cfg.d
        self.value_head = nn.Sequential(nn.Linear(two, cfg.d), nn.GELU(), nn.Linear(cfg.d, 1))
        self.move_head = nn.Sequential(nn.Linear(two, cfg.d), nn.GELU(), nn.Linear(cfg.d, SIZES["moves"]))
        self.switch_head = nn.Sequential(nn.Linear(two, cfg.d), nn.GELU(), nn.Linear(cfg.d, 1))
        self.opp_move_head = nn.Sequential(nn.Linear(two, cfg.d), nn.GELU(), nn.Linear(cfg.d, SIZES["moves"]))
        self.opp_switch_head = nn.Sequential(nn.Linear(two, cfg.d), nn.GELU(), nn.Linear(cfg.d, 1))
        self.set_item = nn.Linear(cfg.d, SIZES["items"])
        self.set_ability = nn.Linear(cfg.d, SIZES["abilities"])
        self.set_tera = nn.Linear(cfg.d, SIZES["types"])
        self.set_moves = nn.Linear(cfg.d, SIZES["moves"])
        self.register_buffer("kinds", torch.tensor([0] * 6 + [1] * 6 + [2]), persistent=False)

    # ---------------------------------------------------------------- inputs
    def _move_vec(self, ids: torch.Tensor) -> torch.Tensor:
        return torch.cat([self.move(ids), self.move_props[ids]], dim=-1)

    @staticmethod
    def _mix(vecs: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        """Probability-weighted mean over the last-but-one dim."""
        return (vecs * p.unsqueeze(-1)).sum(-2) / p.sum(-1, keepdim=True).clamp(min=1e-6)

    def _tokens(self, ids: torch.Tensor, mon: torch.Tensor) -> torch.Tensor:
        pk = ids[:, :12]
        sp = pk[..., 0]
        known_moves = self._move_vec(pk[..., 3:7]).mean(dim=2)
        prior_moves = self._mix(self._move_vec(self.prior_moves_ids[sp]), self.prior_moves_p[sp])
        return torch.cat([
            self.species(sp), self.species_props[sp],
            self.item(pk[..., 1]), self._mix(self.item(self.prior_items_ids[sp]), self.prior_items_p[sp]),
            self.ability(pk[..., 2]), self._mix(self.ability(self.prior_abilities_ids[sp]), self.prior_abilities_p[sp]),
            known_moves, prior_moves,
            self.tera(pk[..., 7]), self._mix(self.tera(self.prior_tera_ids[sp]), self.prior_tera_p[sp]),
            mon[:, :12],
        ], dim=-1)

    def encode(self, ids: torch.Tensor, mon: torch.Tensor, field: torch.Tensor) -> torch.Tensor:
        """ids [B,13,8] long, mon [B,13,N_MON], field [B,N_FIELD] -> token states [B,13,d]."""
        last_moves = self._move_vec(ids[:, 12, :2]).flatten(1)  # own and opponent's last move
        x = torch.cat([self.token_in(self._tokens(ids, mon)),
                       self.field_in(torch.cat([field, last_moves], dim=-1)).unsqueeze(1)], dim=1)
        return self.norm(self.encoder(x + self.kind(self.kinds)))

    # ---------------------------------------------------------------- heads
    @staticmethod
    def _active(team: torch.Tensor, mon_block: torch.Tensor) -> torch.Tensor:
        active = mon_block[..., 2]
        idx = torch.where(active.sum(1) > 0, active.argmax(1), torch.zeros_like(active[:, 0], dtype=torch.long))
        return team[torch.arange(team.shape[0], device=team.device), idx]

    def _choice_logits(self, team, mon_block, field_out, move_head, switch_head):
        act = self._active(team, mon_block)
        moves = move_head(torch.cat([act, field_out], dim=-1))
        sw = switch_head(torch.cat([team, field_out.unsqueeze(1).expand(-1, 6, -1)], dim=-1)).squeeze(-1)
        return torch.cat([moves, sw.masked_fill(~switch_mask(mon_block), float("-inf"))], dim=-1)

    def forward(self, ids, mon, field, aux: bool = False):
        x = self.encode(ids, mon, field)
        field_out = x[:, 12]
        value = self.value_head(torch.cat([field_out, x[:, :12].mean(dim=1)], dim=-1)).squeeze(-1)
        policy = self._choice_logits(x[:, :6], mon[:, :6], field_out, self.move_head, self.switch_head)
        if not aux:
            return value, policy
        opp = x[:, 6:12]
        out = {
            "opp_policy": self._choice_logits(opp, mon[:, 6:12], field_out, self.opp_move_head, self.opp_switch_head),
            "set_item": self.set_item(opp), "set_ability": self.set_ability(opp),
            "set_tera": self.set_tera(opp), "set_moves": self.set_moves(opp),
        }
        return value, policy, out


def switch_mask(mon_block: torch.Tensor) -> torch.Tensor:
    """For a side's 6 slots [B,6,N_MON]: which can be switched to. Seen, not fainted, not
    active; plus the first unseen slot (a Pokemon not revealed yet)."""
    seen, fainted, active = mon_block[..., 3] > 0.5, mon_block[..., 1] > 0.5, mon_block[..., 2] > 0.5
    ok = seen & ~fainted & ~active
    first_unseen = torch.zeros_like(ok)
    n_seen = seen.sum(1)
    has_room = n_seen < N_SWITCH
    rows = torch.arange(mon_block.shape[0], device=mon_block.device)[has_room]
    first_unseen[rows, n_seen[has_room]] = True
    return ok | first_unseen


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
