"""FastAPI app: archive API, sync, imports, and the built frontend.

Run:  uv run uvicorn server.app:app --port 8765
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .archive import Archive
from .config import ROOT, Config, load_config
from .ids import parse_replay_ref, to_id
from .imports import record_from_file
from .showdown import ShowdownClient, ShowdownError, make_http
from .sync import refresh_profile, sync_user

log = logging.getLogger("showdown_review")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class SettingsBody(BaseModel):
    username: str | None = Field(default=None, max_length=18)
    poll_minutes: float | None = Field(default=None, ge=1, le=24 * 60)


class ImportUrlBody(BaseModel):
    url: str = Field(max_length=500)


class TeamBody(BaseModel):
    paste: str = Field(default="", max_length=10_000)


def create_app(config: Config | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    config = config or load_config()
    archive = Archive(config.data_dir)
    state: dict = {"sync_lock": asyncio.Lock(), "last_result": None}

    def username() -> str:
        return archive.get_setting("username") or config.default_username

    def poll_minutes() -> float:
        return float(archive.get_setting("poll_minutes") or config.poll_minutes)

    async def run_sync() -> dict:
        async with state["sync_lock"]:
            result = await sync_user(state["client"], archive, username())
            state["last_result"] = result.to_dict()
            return state["last_result"]

    async def poller() -> None:
        while True:
            try:
                r = await run_sync()
                log.info("sync: %d new, %d errors", len(r["added"]), len(r["errors"]))
            except Exception:  # keep polling after an unexpected error
                log.exception("sync failed")
            await asyncio.sleep(poll_minutes() * 60)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = make_http(config.user_agent, transport)
        state["client"] = ShowdownClient(http, config.request_delay)
        task = asyncio.create_task(poller()) if config.poller_enabled else None
        try:
            yield
        finally:
            if task:
                task.cancel()
            await http.aclose()

    app = FastAPI(title="Showdown Review", lifespan=lifespan)
    app.state.archive = archive

    # ---- settings and profile ---------------------------------------------
    @app.get("/api/settings")
    def get_settings():
        uid = to_id(username())
        return {
            "username": username(),
            "poll_minutes": poll_minutes(),
            "sync_start": _int(archive.get_setting(f"sync_start:{uid}")),
            "last_sync": _int(archive.get_setting(f"last_sync:{uid}")),
            "poller_enabled": config.poller_enabled,
        }

    @app.put("/api/settings")
    def put_settings(body: SettingsBody):
        if body.username is not None:
            if not to_id(body.username):
                raise HTTPException(400, "Username must contain letters or digits")
            archive.set_setting("username", body.username.strip())
        if body.poll_minutes is not None:
            archive.set_setting("poll_minutes", str(body.poll_minutes))
        return get_settings()

    @app.get("/api/profile")
    async def get_profile(refresh: bool = False):
        uid = to_id(username())
        cached = archive.get_setting(f"profile:{uid}")
        if refresh or not cached:
            try:
                return await refresh_profile(state["client"], archive, username())
            except ShowdownError as e:
                if not cached:
                    raise HTTPException(502, str(e))
        return json.loads(cached)

    # ---- sync --------------------------------------------------------------
    @app.post("/api/sync")
    async def post_sync():
        return await run_sync()

    @app.get("/api/sync")
    def get_sync():
        return {"last_result": state["last_result"]}

    # ---- games -------------------------------------------------------------
    @app.get("/api/formats")
    def get_formats():
        return archive.formats()

    @app.get("/api/games")
    def get_games(format: str | None = None, result: str | None = None, opponent: str | None = None,
                  limit: int = 200, offset: int = 0):
        if result not in (None, "win", "loss", "tie"):
            raise HTTPException(400, "result must be win, loss or tie")
        return archive.list_games(username(), to_id(format) or None, result, opponent,
                                  min(max(limit, 1), 1000), max(offset, 0))

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str):
        game = archive.get_game(game_id, username())
        if not game:
            raise HTTPException(404, "No such game")
        return game

    @app.put("/api/games/{game_id}/team")
    def put_team(game_id: str, body: TeamBody):
        if not archive.set_team_paste(game_id, body.paste.strip()):
            raise HTTPException(404, "No such game")
        return {"ok": True}

    # ---- imports -----------------------------------------------------------
    @app.post("/api/import/url")
    async def import_url(body: ImportUrlBody):
        try:
            replay_id, password = parse_replay_ref(body.url)
        except ValueError as e:
            raise HTTPException(400, str(e))
        try:
            replay = await state["client"].get_replay(replay_id, password)
        except ShowdownError as e:
            raise HTTPException(502, str(e))
        added = archive.save_replay(replay, source="url")
        return {"id": replay["id"], "added": added}

    @app.post("/api/import/file")
    async def import_file(file: UploadFile):
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File is larger than 5 MB")
        try:
            record = record_from_file(file.filename or "upload.log", data)
            added = archive.save_replay(record, source="upload")
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(400, str(e))
        return {"id": record["id"], "added": added}

    # ---- frontend (built by `npm run build` in web/) --------------------------
    dist = ROOT / "web" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = (dist / path).resolve()
            if path and target.is_file() and dist.resolve() in target.parents:
                return FileResponse(target)
            return FileResponse(dist / "index.html")

    return app


def _int(v: str | None) -> int | None:
    return int(v) if v else None


def __getattr__(name: str):
    # `uvicorn server.app:app` builds the app on first access, not at import time,
    # so tests can import this module without touching ./data.
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
