"""Games sent by the userscript (vault: spec-replay-sync, stage 2b).

/api/ingest          one finished (or abandoned) battle, as the browser client saw it
/api/ingest-private  the user's private replay list (ids + passwords), fetched in their
                     logged-in browser; the server downloads each replay itself
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from .archive import Archive
from .logsummary import summarize
from .showdown import ShowdownClient, ShowdownError

# battle-<formatid>-<number>, optionally -<password>pw for hidden rooms
ROOM_RE = re.compile(r"^battle-([a-z0-9]+)-(\d+)(?:-[a-z0-9]+pw)?$")
DROP_LINES = ("|init|", "|title|", "|request|", "|noinit|", "|deinit|", "|expire|")


class BattleIn(BaseModel):
    roomid: str = Field(max_length=200)
    log: str = Field(max_length=2_000_000)
    request: dict | None = None  # last |request| JSON the user's client received
    username: str | None = Field(default=None, max_length=40)
    incomplete: bool = False


class PrivateItem(BaseModel):
    id: str = Field(max_length=120)
    password: str | None = Field(default=None, max_length=64)
    uploadtime: int


class PrivateListIn(BaseModel):
    username: str = Field(max_length=40)
    items: list[PrivateItem] = Field(max_length=60)


def game_id_from_room(roomid: str) -> str:
    m = ROOM_RE.match(roomid.strip().lower())
    if not m:
        raise ValueError(f"Not a battle room id: {roomid!r}")
    return f"{m.group(1)}-{m.group(2)}"


def clean_log(log: str) -> str:
    """Drop client-only lines so the stored log looks like a replay log."""
    keep = [ln for ln in log.splitlines() if ln and not ln.startswith(DROP_LINES)]
    return "\n".join(keep) + "\n"


def ingest_battle(archive: Archive, body: BattleIn) -> dict:
    game_id = game_id_from_room(body.roomid)
    log = clean_log(body.log)
    summary = summarize(log)
    if not (summary.p1.name and summary.p2.name):
        raise ValueError("Log has no |player| lines")
    if not summary.finished and not body.incomplete:
        raise ValueError("Battle hasn't ended; send incomplete=true for abandoned games")
    record = {
        "id": game_id,
        "format": summary.format,
        "formatid": game_id.rsplit("-", 1)[0],
        "players": [summary.p1.name, summary.p2.name],
        "log": log,
        "uploadtime": None,
        "rating": None,
        "private": 0,
        "password": None,
    }
    added = archive.save_replay(record, source="userscript")
    side = (body.request or {}).get("side")
    if isinstance(side, dict) and isinstance(side.get("pokemon"), list):
        archive.set_own_team(game_id, json.dumps(side))
    return {"id": game_id, "added": added, "finished": summary.finished}


async def ingest_private(client: ShowdownClient, archive: Archive, body: PrivateListIn,
                         start_at: int | None) -> dict:
    added: list[str] = []
    skipped = 0
    errors: list[str] = []
    for item in body.items:
        if start_at is not None and item.uploadtime < start_at:  # no backfill (ADR-0006)
            skipped += 1
            continue
        if not archive.needs(item.id):
            skipped += 1
            continue
        try:
            replay = await client.get_replay(item.id, item.password)
            replay.setdefault("private", 1)
            if archive.save_replay(replay, source="poller"):
                added.append(item.id)
        except (ShowdownError, ValueError) as e:
            errors.append(f"{item.id}: {e}")
    return {"added": added, "skipped": skipped, "errors": errors}
