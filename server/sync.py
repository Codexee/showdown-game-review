"""Poll a user's uploaded replays into the archive.

No backfill (vault ADR-0006): the first sync records a start time and only replays
uploaded after it are saved. Older games can still be added one at a time by URL.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from .archive import Archive
from .ids import to_id
from .showdown import ShowdownClient, ShowdownError

MAX_PAGES = 20  # safety stop: 20 pages x 50 = 1000 replays per sync


@dataclass
class SyncResult:
    username: str
    started_at: int
    first_sync: bool = False
    seen: int = 0
    added: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    profile_ok: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _start_key(username: str) -> str:
    return f"sync_start:{to_id(username)}"


async def refresh_profile(client: ShowdownClient, archive: Archive, username: str) -> dict:
    profile = await client.get_user(username)
    archive.set_setting(f"profile:{to_id(username)}", json.dumps(profile))
    archive.set_setting(f"profile_at:{to_id(username)}", str(int(time.time())))
    return profile


async def sync_user(client: ShowdownClient, archive: Archive, username: str) -> SyncResult:
    start = archive.get_setting(_start_key(username))
    if start is None:
        start_at = int(time.time())
        archive.set_setting(_start_key(username), str(start_at))
        first = True
    else:
        start_at = int(start)
        first = False
    result = SyncResult(username=username, started_at=start_at, first_sync=first)

    try:
        await refresh_profile(client, archive, username)
        result.profile_ok = True
    except ShowdownError as e:
        result.errors.append(str(e))

    before: int | None = None
    for _ in range(MAX_PAGES):
        try:
            page = await client.search_user_replays(username, before)
        except ShowdownError as e:
            result.errors.append(str(e))
            break
        stop = False
        for item in page[:50]:  # the 51st result only signals that another page exists
            result.seen += 1
            if item["uploadtime"] < start_at or archive.has(item["id"]):
                stop = True
                break
            try:
                replay = await client.get_replay(item["id"], item.get("password"))
                if archive.save_replay(replay, source="poller"):
                    result.added.append(item["id"])
            except (ShowdownError, ValueError) as e:
                result.errors.append(f"{item['id']}: {e}")
        if stop or len(page) <= 50:
            break
        before = page[49]["uploadtime"]
    archive.set_setting(f"last_sync:{to_id(username)}", str(int(time.time())))
    return result
