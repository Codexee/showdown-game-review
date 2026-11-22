"""Small async client for Showdown's public JSON APIs (see vault: data-sources)."""
from __future__ import annotations

import asyncio
import time

import httpx

from .ids import full_replay_id, to_id

REPLAY_BASE = "https://replay.pokemonshowdown.com"
SITE_BASE = "https://pokemonshowdown.com"


class ShowdownError(RuntimeError):
    pass


class ShowdownClient:
    def __init__(self, http: httpx.AsyncClient, request_delay: float = 1.0):
        self.http = http
        self.request_delay = request_delay
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        # Space requests out. Showdown is a free service; don't hammer it.
        async with self._lock:
            wait = self._last + self.request_delay - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                resp = await self.http.get(url, params=params)
            finally:
                self._last = time.monotonic()
        return resp

    async def get_user(self, username: str) -> dict:
        resp = await self._get(f"{SITE_BASE}/users/{to_id(username)}.json")
        if resp.status_code != 200:
            raise ShowdownError(f"user lookup failed: HTTP {resp.status_code}")
        return resp.json()

    async def search_user_replays(self, username: str, before: int | None = None) -> list[dict]:
        """One page (up to 51) of a user's public replays, newest first."""
        params: dict = {"user": to_id(username)}
        if before:
            params["before"] = before
        resp = await self._get(f"{REPLAY_BASE}/search.json", params)
        if resp.status_code != 200:
            raise ShowdownError(f"replay search failed: HTTP {resp.status_code}")
        return resp.json()

    async def get_replay(self, replay_id: str, password: str | None = None) -> dict:
        resp = await self._get(f"{REPLAY_BASE}/{full_replay_id(replay_id, password)}.json")
        if resp.status_code == 404:
            raise ShowdownError(f"replay {replay_id} not found (or wrong password)")
        if resp.status_code != 200:
            raise ShowdownError(f"replay fetch failed: HTTP {resp.status_code}")
        return resp.json()


def make_http(user_agent: str, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        transport=transport,
    )
