from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
RANDBATS_ID = "gen9randombattle-2705718015"
VGC_ID = "gen9championsvgc2026regmc-2717776258"


def load_replay(replay_id: str) -> dict:
    return json.loads((FIXTURES / f"{replay_id}.json").read_text())


class FakeShowdown:
    """Stands in for replay.pokemonshowdown.com and pokemonshowdown.com/users."""

    def __init__(self):
        self.replays: dict[str, dict] = {}  # full id (with -pw suffix if private) -> record
        self.search_items: list[dict] = []  # newest first
        self.requests: list[httpx.Request] = []

    def add(self, record: dict, uploadtime: int, password: str | None = None) -> None:
        record = dict(record, uploadtime=uploadtime, password=password, private=1 if password else 0)
        full = f"{record['id']}-{password}pw" if password else record["id"]
        self.replays[full] = record
        self.search_items.append({k: record[k] for k in
                                  ("uploadtime", "id", "format", "players", "rating", "private", "password")})
        self.search_items.sort(key=lambda r: -r["uploadtime"])

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.url.host == "pokemonshowdown.com" and path.startswith("/users/"):
            return httpx.Response(200, json={"username": "Codexe", "userid": "codexe", "ratings": {}})
        if path == "/search.json":
            before = int(request.url.params.get("before", 0)) or None
            items = [r for r in self.search_items if before is None or r["uploadtime"] < before]
            return httpx.Response(200, json=items[:51])
        if path.endswith(".json"):
            rec = self.replays.get(path[1:-5])
            return httpx.Response(200, json=rec) if rec else httpx.Response(404, text="")
        return httpx.Response(404, text="")


@pytest.fixture
def fake() -> FakeShowdown:
    return FakeShowdown()


@pytest.fixture
def transport(fake) -> httpx.MockTransport:
    return httpx.MockTransport(fake.handler)
