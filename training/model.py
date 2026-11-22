"""Eval model: a small transformer over 13 tokens (6 own Pokemon, 6 opposing, field).

Heads (vault spec-eval-model):
- value: logit of "the player whose view this is wins" -> the eval bar.
- policy: logits over [every move id..., switch to own slot 0-5] -> later, move review.
Within a side the tokens have no order (no position embedding): only own / opponent /
field type embeddings, so the model can't learn anything from team order.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

from training.features import N_FIELD, N_MON, N_SWITCH, SIZES


@dataclass
class ModelConfig:
    d: int = 256
    layers: int = 4
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
        in_dim = cfg.species_dim + cfg.item_dim + cfg.ability_dim + cfg.move_dim + cfg.type_dim + N_MON
        self.token_in = nn.Sequential(nn.Linear(in_dim, cfg.d), nn.GELU(), nn.Linear(cfg.d, cfg.d))
        self.field_in = nn.Sequential(nn.Linear(N_FIELD, cfg.d), nn.GELU(), nn.Linear(cfg.d, cfg.d))
        self.kind = nn.Embedding(3, cfg.d)  # 0 own, 1 opponent, 2 field
        layer = nn.TransformerEncoderLayer(cfg.d, cfg.heads, cfg.ff, cfg.dropout, batch_first=True, norm_first=True,
                                           activation="gelu")
        self.encoder = nn.TransformerEncoder(layer, cfg.layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(cfg.d)
        self.value_head = nn.Sequential(nn.Linear(2 * cfg.d, cfg.d), nn.GELU(), nn.Linear(cfg.d, 1))
        self.move_head = nn.Sequential(nn.Linear(2 * cfg.d, cfg.d), nn.GELU(), nn.Linear(cfg.d, SIZES["moves"]))
        self.switch_head = nn.Sequential(nn.Linear(2 * cfg.d, cfg.d), nn.GELU(), nn.Linear(cfg.d, 1))
        self.register_buffer("kinds", torch.tensor([0] * 6 + [1] * 6 + [2]), persistent=False)

    def forward(self, ids: torch.Tensor, mon: torch.Tensor, field: torch.Tensor):
        """ids [B,13,8] long, mon [B,13,N_MON] float, field [B,N_FIELD] float."""
        pk = ids[:, :12]
        moves = self.move(pk[..., 3:7]).mean(dim=2)
        tok = torch.cat([self.species(pk[..., 0]), self.item(pk[..., 1]), self.ability(pk[..., 2]), moves,
                         self.tera(pk[..., 7]), mon[:, :12]], dim=-1)
        x = torch.cat([self.token_in(tok), self.field_in(field).unsqueeze(1)], dim=1) + self.kind(self.kinds)
        x = self.norm(self.encoder(x))
        field_out = x[:, 12]
        pooled = torch.cat([field_out, x[:, :12].mean(dim=1)], dim=-1)
        value = self.value_head(pooled).squeeze(-1)

        own = x[:, :6]
        active = mon[:, :6, 2]
        # the player's active Pokemon (slot a); fall back to slot 0 if none is marked
        idx = torch.where(active.sum(1) > 0, active.argmax(1), torch.zeros_like(active[:, 0], dtype=torch.long))
        act = own[torch.arange(own.shape[0], device=own.device), idx]
        move_logits = self.move_head(torch.cat([act, field_out], dim=-1))
        switch_logits = self.switch_head(torch.cat([own, field_out.unsqueeze(1).expand(-1, 6, -1)], dim=-1)).squeeze(-1)
        switch_logits = switch_logits.masked_fill(~switch_mask(mon), float("-inf"))
        return value, torch.cat([move_logits, switch_logits], dim=-1)


def switch_mask(mon: torch.Tensor) -> torch.Tensor:
    """Which own slots can be switched to: seen, not fainted, not active; plus the first
    unseen slot (a Pokemon not revealed yet)."""
    seen, fainted, active = mon[:, :6, 3] > 0.5, mon[:, :6, 1] > 0.5, mon[:, :6, 2] > 0.5
    ok = seen & ~fainted & ~active
    first_unseen = torch.zeros_like(ok)
    n_seen = seen.sum(1)
    has_room = n_seen < N_SWITCH
    rows = torch.arange(mon.shape[0], device=mon.device)[has_room]
    first_unseen[rows, n_seen[has_room]] = True
    return ok | first_unseen


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
