"""Pokemon sprites from Showdown's sprite server, cached on disk (vault ADR-0011).

GET /sprites/gen5/<spriteid>.png and /sprites/gen5-back/<spriteid>.png. The first view
downloads the file into <data>/sprites/; after that it works offline.

Animated sprites (2026-11-23): /sprites/gen5ani[-back]/<id>.png is Showdown's animated GIF
turned into a horizontal strip of frames, with /sprites/gen5ani[-back]/<id>.json giving the
frame size, count and durations, so the page can step through them at its own pace.
The substitute doll: /sprites/sub/substitute.png and /sprites/sub-back/substitute.png.
Item icons: /sprites/item/<id>.png (e.g. poke-ball, for party slots not seen yet).
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import httpx

from .ids import to_id

SPRITE_BASE = "https://play.pokemonshowdown.com/sprites"
FOLDERS = {"gen5", "gen5-back", "gen5ani", "gen5ani-back", "sub", "sub-back", "item"}
ANIMATED = {"gen5ani", "gen5ani-back"}
REMOTE = {"sub": "substitutes/gen5", "sub-back": "substitutes/gen5-back", "item": "itemicons"}  # ours -> Showdown's
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
        if folder in ANIMATED:
            return await self._get_animated(http, folder, name, target, missing)
        resp = await http.get(f"{SPRITE_BASE}/{REMOTE.get(folder, folder)}/{name}.png")
        target.parent.mkdir(parents=True, exist_ok=True)
        if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
            if resp.status_code == 404:
                missing.touch()  # don't ask again for sprites that don't exist
            return None
        tmp = target.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(target)
        return target

    def meta_path(self, folder: str, name: str) -> Path | None:
        p = self.path(folder, name)
        return p.with_suffix(".json") if p is not None and folder in ANIMATED else None

    async def _get_animated(self, http: httpx.AsyncClient, folder: str, name: str, target: Path,
                            missing: Path) -> Path | None:
        resp = await http.get(f"{SPRITE_BASE}/{folder}/{name}.gif")
        target.parent.mkdir(parents=True, exist_ok=True)
        if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
            if resp.status_code == 404:
                missing.touch()
            return None
        strip, meta = gif_to_strip(resp.content)
        tmp = target.with_suffix(".part")
        strip.save(tmp, format="PNG")
        target.with_suffix(".json").write_text(json.dumps(meta))
        tmp.replace(target)
        return target


def gif_to_strip(data: bytes):
    """An animated GIF -> (one RGBA image with the frames side by side, {w, h, frames, ms})."""
    from PIL import Image, ImageSequence

    im = Image.open(io.BytesIO(data))
    w, h = im.size
    frames, ms = [], []
    for fr in ImageSequence.Iterator(im):
        frames.append(fr.convert("RGBA"))       # composited with the GIF's disposal rules
        ms.append(int(fr.info.get("duration") or 100))
    strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        strip.paste(fr, (i * w, 0))
    return strip, {"w": w, "h": h, "frames": len(frames), "ms": ms}
