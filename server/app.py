"""FastAPI app: archive API, sync, imports, and the built frontend.

Run:  uv run uvicorn server.app:app --port 8765
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

import time
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from .archive import Archive
from .battle import parse_log, view_for
from .battle.narrate import events_by_turn
from .config import ROOT, Config, load_config
from .evaluate import METHOD as EVAL_METHOD
from .evaluate import METHOD_TEXT as EVAL_METHOD_TEXT
from .evaluate import win_chance
from .model_eval import load as load_model
from .review.analyze import SEARCH_BLEND, search_value_p1
from .review.jobs import Jobs
from .ids import parse_replay_ref, to_id
from .imports import record_from_file
from .ingest import BattleIn, PrivateListIn, ingest_battle, ingest_private
from .showdown import ShowdownClient, ShowdownError, make_http
from .sprites import SpriteCache, sprite_id
from .sync import refresh_profile, sync_user

# Pages allowed to call the ingest routes from the browser (the userscript's fallback
# path when GM_xmlhttpRequest isn't available). Everything else under /api only
# accepts requests from this app's own pages on localhost.
SHOWDOWN_ORIGINS = {"https://play.pokemonshowdown.com", "https://replay.pokemonshowdown.com"}
USERSCRIPT_FILE = ROOT / "userscript" / "showdown-game-review.user.js"


def _is_local_origin(origin: str) -> bool:
    host = urlparse(origin).hostname or ""
    return host in ("127.0.0.1", "localhost", "::1")

log = logging.getLogger("showdown_game_review")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class SettingsBody(BaseModel):
    username: str | None = Field(default=None, max_length=18)
    poll_minutes: float | None = Field(default=None, ge=1, le=24 * 60)
    auto_analyze: bool | None = None


class AnalyzeBody(BaseModel):
    seeds: int = Field(default=16, ge=4, le=128)
    top_k: int = Field(default=6, ge=2, le=13)
    mode: Literal["worlds", "perfect"] = "worlds"   # vault ADR-0015


class ImportUrlBody(BaseModel):
    url: str = Field(max_length=500)


class TeamBody(BaseModel):
    paste: str = Field(default="", max_length=10_000)


def search_by_turn(analysis: dict) -> dict[int, float]:
    """p1's searched win chance per turn from a finished, current, worlds-mode move review;
    empty otherwise (perfect mode uses the real hidden sets, so it isn't used for the bar)."""
    if analysis.get("status") != "done" or analysis.get("stale"):
        return {}
    res = analysis.get("result") or {}
    if res.get("mode", "worlds") != "worlds":
        return {}
    out = {}
    for t in res.get("turns", []):
        v = search_value_p1(t)
        if v is not None:
            out[int(t["turn"])] = v
    return out


def create_app(config: Config | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    config = config or load_config()
    archive = Archive(config.data_dir)
    sprites = SpriteCache(config.data_dir)
    jobs = Jobs(config.data_dir, lambda gid: _game_for_review(archive, gid))

    def auto_analyze_on() -> bool:
        return archive.get_setting("auto_analyze", "1") == "1"   # on unless turned off

    def auto_analyze(game_id: str) -> None:
        """Queue a move review for a game that was just saved, if the setting is on and the
        game can be reviewed. Games already reviewed with the current model are left alone."""
        if not auto_analyze_on():
            return
        cur = jobs.get(game_id)
        if cur.get("status") in ("queued", "running") or (cur.get("status") == "done" and not cur.get("stale")):
            return
        res = jobs.start(game_id)
        if res.get("status") == "queued":
            log.info("auto-analyze: queued %s", game_id)

    archive.on_saved = auto_analyze
    state: dict = {"sync_lock": asyncio.Lock(), "last_result": None}

    def username() -> str:
        return archive.get_setting("username") or config.default_username

    def poll_minutes() -> float:
        return float(archive.get_setting("poll_minutes") or config.poll_minutes)

    async def run_sync() -> dict:
        if not to_id(username()):
            raise HTTPException(400, "Set your Showdown username first")
        async with state["sync_lock"]:
            result = await sync_user(state["client"], archive, username())
            state["last_result"] = result.to_dict()
            return state["last_result"]

    async def poller() -> None:
        while True:
            try:
                if to_id(username()):   # nothing to sync until a username is set
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

    app = FastAPI(title="Showdown Game Review", lifespan=lifespan)
    app.state.archive = archive

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        """Block other websites from calling the local API (CSRF).

        Browsers send an Origin header on cross-site requests and on same-site POST/PUT.
        Requests with no Origin (curl, GM_xmlhttpRequest, same-page GETs) pass.
        """
        path = request.url.path
        origin = request.headers.get("origin")
        if not path.startswith("/api/") or not origin:
            return await call_next(request)
        ingest = path in ("/api/ingest", "/api/ingest-private")
        if _is_local_origin(origin):
            return await call_next(request)
        if ingest and origin in SHOWDOWN_ORIGINS:
            cors = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Private-Network": "true",
                "Vary": "Origin",
            }
            if request.method == "OPTIONS":
                return Response(status_code=204, headers=cors)
            response = await call_next(request)
            response.headers.update(cors)
            return response
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)

    def require_json(request: Request) -> None:
        # A JSON content type forces a CORS preflight for cross-site page requests,
        # so a plain HTML form on some other site can't post here.
        if not request.headers.get("content-type", "").startswith("application/json"):
            raise HTTPException(415, "Send application/json")

    def sync_start() -> int:
        """The no-backfill start time; set it now if no sync has run yet."""
        key = f"sync_start:{to_id(username())}"
        value = archive.get_setting(key)
        if value is None:
            value = str(int(time.time()))
            archive.set_setting(key, value)
        return int(value)

    # ---- settings and profile ---------------------------------------------
    @app.get("/api/settings")
    def get_settings():
        uid = to_id(username())
        return {
            "username": username(),
            "poll_minutes": poll_minutes(),
            "sync_start": _int(archive.get_setting(f"sync_start:{uid}")),
            "last_sync": _int(archive.get_setting(f"last_sync:{uid}")),
            "last_ingest": _int(archive.get_setting("last_ingest")),
            "last_ingest_private": _int(archive.get_setting("last_ingest_private")),
            "poller_enabled": config.poller_enabled,
            "auto_analyze": auto_analyze_on(),
        }

    @app.put("/api/settings")
    def put_settings(body: SettingsBody):
        if body.username is not None:
            if not to_id(body.username):
                raise HTTPException(400, "Username must contain letters or digits")
            archive.set_setting("username", body.username.strip())
        if body.poll_minutes is not None:
            archive.set_setting("poll_minutes", str(body.poll_minutes))
        if body.auto_analyze is not None:
            archive.set_setting("auto_analyze", "1" if body.auto_analyze else "0")
        return get_settings()

    @app.get("/api/profile")
    async def get_profile(refresh: bool = False):
        uid = to_id(username())
        if not uid:
            return {"username": "", "ratings": {}}
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

    @app.get("/api/games/{game_id}/turns")
    def get_turns(game_id: str, side: str | None = None):
        """Battle state at the start of every turn (stage 3 parser).

        side=p1|p2 gives that player's view (opponent HP as Showdown showed it);
        side=all gives everything the log reveals. Default: your side if you played.
        """
        game = archive.get_game(game_id, username())
        if not game:
            raise HTTPException(404, "No such game")
        result = parse_log(game["log"])
        perspective = side or game["user_side"] or "all"
        if perspective not in ("p1", "p2", "all"):
            raise HTTPException(400, "side must be p1, p2 or all")
        states = result.states if perspective == "all" else \
            [view_for(s, perspective, result.format_id) for s in result.states]
        return {"id": game_id, "format_id": result.format_id, "perspective": perspective,
                "turns": states, "warnings": result.warnings}

    @app.get("/api/games/{game_id}/review")
    def get_review(game_id: str, side: str | None = None):
        """Everything the review screen needs, one step per turn start plus the end.

        Step k: the state at the start of that turn (from `side`'s view), the events
        that led to it (the leads for turn 1, the previous turn otherwise), and the
        estimated win chance for `side`.
        """
        game = archive.get_game(game_id, username())
        if not game:
            raise HTTPException(404, "No such game")
        perspective = side or game["user_side"] or "p1"
        if perspective not in ("p1", "p2"):
            raise HTTPException(400, "side must be p1 or p2")
        result = parse_log(game["log"])
        events = events_by_turn(game["log"])
        # The trained model if installed (singles only), else the remaining-HP placeholder.
        model = load_model(config.data_dir) if result.states and result.states[0]["gametype"] == "singles" else None
        model_values: list[float] = []
        if model is not None:
            try:
                from training.features import turn_events
                model_values = model.win_chances([s for s in result.states if not s["ended"]], perspective,
                                                 turn_events(game["log"]))
            except Exception as e:  # fall back rather than break the screen
                result.warnings.append(f"model failed: {e}")
                model = None
        method, method_text = EVAL_METHOD, EVAL_METHOD_TEXT
        # After a move review (worlds mode, current model), blend its one-turn search in.
        search = search_by_turn(jobs.get(game_id)) if model is not None else {}
        if model is not None:
            info = model.info
            method = "model"
            method_text = (f"Trained model ({info.get('run', 'unnamed run')}): predicted win chance from what both "
                           f"players could see. It calls the winner {info.get('val_acc_text', 'n/a')}.")
            if search:
                method = "model+search"
                method_text = (f"Trained model ({info.get('run', 'unnamed run')}) plus the move review's one-turn search: "
                               f"each turn's chance is {SEARCH_BLEND:.0%} the searched value (both players' best choices, "
                               f"on what each could see) and {1 - SEARCH_BLEND:.0%} the model. On new games this predicted "
                               f"the winner better than the model alone.")
        values = iter(model_values)
        steps = []
        for i, state in enumerate(result.states):
            view = view_for(state, perspective, result.format_id)
            for s in view["sides"].values():
                for mon in s["team"]:
                    mon["sprite"] = sprite_id(mon["species"])
            turn = state["turn"]
            led_by = 0 if i == 0 else (result.states[i - 1]["turn"])
            ev = next(values) if model is not None and not state["ended"] else win_chance(state, perspective)
            step = {
                "turn": turn,
                "ended": state["ended"],
                "state": view,
                # first step: the leads; end step: the last turn; otherwise the previous turn
                "events": events.get(led_by, []),
                "eval": round(ev, 4),
            }
            if not state["ended"] and turn in search:
                s_val = search[turn] if perspective == "p1" else 1 - search[turn]
                step.update(eval=round(SEARCH_BLEND * s_val + (1 - SEARCH_BLEND) * ev, 4),
                            eval_model=round(ev, 4), eval_search=round(s_val, 4))
            steps.append(step)
        game.pop("log", None)
        game.pop("inputlog", None)
        from .battle.dexinfo import dex_for_game
        try:
            dex = dex_for_game(result.states, events, result.format_id)
        except Exception as e:  # the info cards are extra: never break the review for them
            result.warnings.append(f"dex info failed: {e}")
            dex = {"species": {}, "moves": {}, "sets": {}}
        return {"game": game, "perspective": perspective, "format_id": result.format_id,
                "eval_method": method, "eval_method_text": method_text,
                "steps": steps, "warnings": result.warnings, "dex": dex}

    # ---- move review (stage 6) ------------------------------------------------
    @app.get("/api/games/{game_id}/analysis")
    def get_analysis(game_id: str):
        if archive.get_game(game_id, username()) is None:
            raise HTTPException(404, "No such game")
        return jobs.get(game_id)

    @app.post("/api/games/{game_id}/analysis")
    def post_analysis(game_id: str, body: AnalyzeBody | None = None):
        body = body or AnalyzeBody()
        res = jobs.start(game_id, seeds=body.seeds, top_k=body.top_k, mode=body.mode)
        if res.get("status") == "error" and res.get("error") == "No such game":
            raise HTTPException(404, "No such game")
        return res

    @app.get("/sprites/{folder}/{name}.json", include_in_schema=False)
    async def sprite_meta(folder: str, name: str):
        """Frame size, count and durations of an animated sprite strip (see server/sprites.py)."""
        try:
            path = await sprites.get(state["client"].http, folder, name)
        except httpx.HTTPError:
            path = None
        meta = sprites.meta_path(folder, name)
        if path is None or meta is None or not meta.exists():
            # Many formes have no animated sprite: "null" (not a 404) keeps the console clean;
            # the page shows the still sprite.
            return Response("null", media_type="application/json", headers={"Cache-Control": "public, max-age=86400"})
        return FileResponse(meta, media_type="application/json",
                            headers={"Cache-Control": "public, max-age=604800"})

    @app.get("/sprites/{folder}/{name}.png", include_in_schema=False)
    async def sprite(folder: str, name: str):
        try:
            path = await sprites.get(state["client"].http, folder, name)
        except httpx.HTTPError:
            path = None
        if path is None:
            raise HTTPException(404, "No sprite")
        return FileResponse(path, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})

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

    # ---- userscript (stage 2b) -----------------------------------------------
    @app.post("/api/ingest")
    def post_ingest(body: BattleIn, request: Request):
        require_json(request)
        try:
            result = ingest_battle(archive, body)
        except ValueError as e:
            raise HTTPException(400, str(e))
        archive.set_setting("last_ingest", str(int(time.time())))
        return result

    @app.post("/api/ingest-private")
    async def post_ingest_private(body: PrivateListIn, request: Request):
        require_json(request)
        if to_id(body.username) != to_id(username()):
            raise HTTPException(409, f"Private list is for {body.username}, but the app is set to {username()}")
        result = await ingest_private(state["client"], archive, body, sync_start())
        archive.set_setting("last_ingest_private", str(int(time.time())))
        return result

    @app.get("/userscript/showdown-game-review.user.js", include_in_schema=False)
    def userscript():
        # Tampermonkey offers to install any URL ending in .user.js.
        return FileResponse(USERSCRIPT_FILE, media_type="text/javascript")

    # ---- frontend (built by `npm run build` in web/) --------------------------
    dist = ROOT / "web" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = (dist / path).resolve()
            if path and target.is_file() and dist.resolve() in target.parents:
                return FileResponse(target)
            # Always revalidate the page itself: its asset names change on every build, so a
            # cached copy would keep loading the old UI (seen 2026-11-23).
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def _game_for_review(archive: Archive, game_id: str) -> dict | None:
    game = archive.get_game(game_id, "")
    if game is None:
        return None
    return {"log": game["log"], "inputlog": game["inputlog"], "gametype": game["gametype"],
            "format_id": game["format_id"]}


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
