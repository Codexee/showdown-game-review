"""Background move-review jobs: one worker thread, results cached in data/analysis/.

A result is tied to the model that produced it; when a different model is installed the
old result is reported as stale and can be re-run.
"""
from __future__ import annotations

import json
import queue
import threading
import time
import traceback
from pathlib import Path

from server import model_eval
from server.review.analyze import ANALYSIS_VERSION, analyze
from server.review.engine import ReviewEngine, sim_for


def supported(game: dict) -> str | None:
    """None if the game can be reviewed, else the reason it can't."""
    if not game.get("inputlog"):
        return ("Move review needs the replay's full battle data (inputlog), which Showdown only keeps for "
                "random formats. Add the replay by URL or sync it after uploading.")
    if game.get("gametype") != "singles" or "randombattle" not in game.get("format_id", ""):
        return "Move review currently supports Gen 9 Random Battle (singles) only."
    return None


class Jobs:
    def __init__(self, data_dir: Path, get_game):
        self.dir = Path(data_dir) / "analysis"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path(data_dir)
        self.get_game = get_game          # game_id -> dict with log, inputlog (archive.get_game)
        self.status: dict[str, dict] = {}
        self.q: queue.Queue = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def _path(self, game_id: str) -> Path:
        return self.dir / f"{game_id}.json"

    def model_tag(self) -> str | None:
        m = model_eval.load(self.data_dir)
        if m is None:
            return None
        info = m.info
        return f"{info.get('run')}@{info.get('step')}"

    def get(self, game_id: str) -> dict:
        with self.lock:
            st = dict(self.status.get(game_id, {}))
        if st.get("status") in ("queued", "running"):
            return st
        p = self._path(game_id)
        if p.exists():
            res = json.loads(p.read_text())
            stale = res.get("model") != self.model_tag() or res.get("version") != ANALYSIS_VERSION
            return {"status": "done", "stale": stale, "result": res}
        if st.get("status") == "error":
            return st
        return {"status": "none"}

    def start(self, game_id: str, seeds: int = 16, top_k: int = 6, mode: str = "worlds") -> dict:
        game = self.get_game(game_id)
        if game is None:
            return {"status": "error", "error": "No such game"}
        why = supported(game)
        if why:
            return {"status": "unsupported", "error": why}
        if model_eval.load(self.data_dir) is None:
            return {"status": "unsupported", "error": "No trained model is installed (data/models/current.pt)."}
        with self.lock:
            if self.status.get(game_id, {}).get("status") in ("queued", "running"):
                return self.status[game_id]
            self.status[game_id] = {"status": "queued", "progress": [0, 0]}
        self.q.put((game_id, seeds, top_k, mode))
        return self.status[game_id]

    def _set(self, game_id: str, **kw) -> None:
        with self.lock:
            self.status[game_id] = {**self.status.get(game_id, {}), **kw}

    def _worker(self) -> None:
        while True:
            game_id, seeds, top_k, mode = self.q.get()
            self._set(game_id, status="running", started=time.time())
            try:
                game = self.get_game(game_id)
                replay = {"log": game["log"], "inputlog": game["inputlog"]}
                model = model_eval.load(self.data_dir)
                with ReviewEngine(sim_for(replay["inputlog"])) as engine:
                    res = analyze(replay, model, engine, seeds=seeds, top_k=top_k, mode=mode,
                                  progress=lambda done, total: self._set(game_id, progress=[done, total]))
                res["model"] = self.model_tag()
                res["finished"] = int(time.time())
                tmp = self._path(game_id).with_suffix(".tmp")
                tmp.write_text(json.dumps(res))
                tmp.replace(self._path(game_id))
                with self.lock:
                    self.status.pop(game_id, None)
            except Exception as e:  # report, keep the worker alive
                traceback.print_exc()
                self._set(game_id, status="error", error=f"{type(e).__name__}: {e}")
