"""Showdown id helpers."""
from __future__ import annotations

import re
from urllib.parse import urlparse

_NON_ID = re.compile(r"[^a-z0-9]+")
# replay id: [<server>-]<formatid>-<number>, optionally followed by -<password>pw.
# Side servers upload to the same replay site with a prefix, e.g. impulse-gen9randombattle-13297.
_REPLAY_ID = re.compile(r"^((?:[a-z0-9]+-)?[a-z0-9]+-\d+)(?:-([a-z0-9]+)pw)?$")


def to_id(text: str | None) -> str:
    """Same rule as Showdown's toID: lowercase, keep only a-z and 0-9."""
    return _NON_ID.sub("", (text or "").lower())


def parse_replay_ref(ref: str) -> tuple[str, str | None]:
    """Turn a replay URL or id into (replay_id, password or None).

    Accepts e.g. https://replay.pokemonshowdown.com/gen9randombattle-123,
    the same with a -<pw>pw suffix or a .json/.log/.inputlog extension, or a bare id.
    Raises ValueError for anything else.
    """
    ref = ref.strip()
    if "://" in ref:
        parsed = urlparse(ref)
        if not parsed.hostname or not parsed.hostname.endswith("pokemonshowdown.com"):
            raise ValueError("Not a pokemonshowdown.com URL")
        ref = parsed.path
    ref = ref.strip("/").split("/")[-1]
    ref = re.sub(r"\.(json|log|inputlog)$", "", ref).lower()
    m = _REPLAY_ID.match(ref)
    if not m:
        raise ValueError(f"Not a replay id: {ref!r}")
    return m.group(1), m.group(2)


def full_replay_id(replay_id: str, password: str | None) -> str:
    return f"{replay_id}-{password}pw" if password else replay_id
