"""Pokemon sprites from Showdown's sprite server, cached on disk (vault ADR-0011).

GET /sprites/gen5/<spriteid>.png and /sprites/gen5-back/<spriteid>.png. The first view
downloads the file into <data>/sprites/; after that it works offline.
"""
from __future__ import annotations

import re
from pathlib import Path

import httpx

from .ids import to_id

SPRITE_BASE = "https://play.pokemonshowdown.com/sprites"
FOLDERS = {"gen5", "gen5-back"}
_SAFE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Species whose own name has a hyphen: Showdown writes these without one.
HYPHENATED = {"hooh", "porygonz", "jangmoo", "hakamoo", "kommoo", "chiyu", "tinglu", "wochien",
              "chienpao", "nidoranf", "nidoranm"}


def sprite_id(species: str) -> str:
    """'Palafin-Hero' -> 'palafin-hero'; 'Ho-Oh' -> 'hooh'; 'Tapu Koko' -> 'tapukoko'."""
    parts = species.split("-")
    # A hyphenated base name ("Ho-Oh", "Kommo-o"), possibly followed by a forme ("Kommo-o-Totem").
    if len(parts) >= 2 and to_id(parts[0] + parts[1]) in HYPHENATED:
        base, formes = to_id(parts[0] + parts[1]), parts[2:]
    else:
        base, formes = to_id(parts[0]), parts[1:]
    forme = to_id("".join(formes))
    return f"{base}-{forme}" if forme else base


class SpriteCache:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "sprites"

    def path(self, folder: str, name: str) -> Path | None:
        if folder not in FOLDERS or not _SAFE.match(name):
            return None
        return self.root / folder / f"{name}.png"

    async def get(self, http: httpx.AsyncClient, folder: str, name: str) -> Path | None:
        """Cached file path, downloading it first if needed. None if Showdown has no sprite."""
        target = self.path(folder, name)
        if target is None:
            return None
        if target.exists():
            return target
        missing = target.with_suffix(".missing")
        if missing.exists():
            return None
        resp = await http.get(f"{SPRITE_BASE}/{folder}/{name}.png")
        target.parent.mkdir(parents=True, exist_ok=True)
        if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
            if resp.status_code == 404:
                missing.touch()  # don't ask again for sprites that don't exist
            return None
        tmp = target.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(target)
        return target
