"""Local replay archive: SQLite index plus raw files on disk. Nothing is ever deleted.

Layout (see vault ADR-0006):
    <data>/archive.sqlite3
    <data>/replays/<formatid>/<id>.json      the replay record as received
    <data>/replays/<formatid>/<id>.log       protocol log
    <data>/replays/<formatid>/<id>.inputlog  random formats only
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .ids import to_id
from .logsummary import result_for, summarize, user_side

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id            TEXT PRIMARY KEY,   -- replay id, e.g. gen9randombattle-2705718015, or upload-<hash>
    format_id     TEXT NOT NULL,
    format        TEXT NOT NULL,
    p1            TEXT NOT NULL,
    p2            TEXT NOT NULL,
    uploadtime    INTEGER,            -- from the replay server; NULL for uploads
    played_at     INTEGER,            -- first |t:| in the log
    rating        INTEGER,            -- replay server's rating field
    private       INTEGER NOT NULL DEFAULT 0,
    password      TEXT,
    has_inputlog  INTEGER NOT NULL DEFAULT 0,
    source        TEXT NOT NULL,      -- poller | url | upload | userscript
    summary_json  TEXT NOT NULL,
    team_paste    TEXT,               -- the user's own team, Showdown export format
    added_at      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS games_played ON games(played_at DESC);
CREATE INDEX IF NOT EXISTS games_format ON games(format_id);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Archive:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.replay_dir = self.data_dir / "replays"
        self.db_path = self.data_dir / "archive.sqlite3"
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    # ---- settings ---------------------------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._db() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    # ---- writing ----------------------------------------------------------
    def has(self, game_id: str) -> bool:
        with self._db() as db:
            return db.execute("SELECT 1 FROM games WHERE id=?", (game_id,)).fetchone() is not None

    def save_replay(self, replay: dict, source: str) -> bool:
        """Store a replay record (the replay server's .json shape).

        Returns True if the game is new. Saving a game that is already stored changes
        nothing, except that a later copy with an inputlog adds the inputlog.
        """
        game_id = replay["id"]
        log = replay.get("log") or ""
        if not log:
            raise ValueError(f"Replay {game_id} has no log")
        summary = summarize(log)
        format_id = replay.get("formatid") or to_id(summary.format) or "unknown"
        inputlog = replay.get("inputlog") or ""

        existing = None
        with self._db() as db:
            existing = db.execute(
                "SELECT has_inputlog, format_id FROM games WHERE id=?", (game_id,)
            ).fetchone()
        if existing and (existing["has_inputlog"] or not inputlog):
            return False

        folder = self.replay_dir / format_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{game_id}.json").write_text(json.dumps(replay, ensure_ascii=False))
        (folder / f"{game_id}.log").write_text(log)
        if inputlog:
            (folder / f"{game_id}.inputlog").write_text(inputlog)

        with self._db() as db:
            if existing:
                db.execute("UPDATE games SET has_inputlog=1 WHERE id=?", (game_id,))
                return False
            db.execute(
                """INSERT INTO games (id, format_id, format, p1, p2, uploadtime, played_at, rating,
                       private, password, has_inputlog, source, summary_json, added_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    game_id,
                    format_id,
                    replay.get("format") or summary.format or format_id,
                    summary.p1.name or (replay.get("players") or ["", ""])[0],
                    summary.p2.name or (replay.get("players") or ["", ""])[-1],
                    replay.get("uploadtime"),
                    summary.started_at,
                    replay.get("rating"),
                    1 if replay.get("private") else 0,
                    replay.get("password"),
                    1 if inputlog else 0,
                    source,
                    json.dumps(summary.to_dict()),
                    int(time.time()),
                ),
            )
        return True

    def set_team_paste(self, game_id: str, paste: str | None) -> bool:
        with self._db() as db:
            cur = db.execute("UPDATE games SET team_paste=? WHERE id=?", (paste or None, game_id))
            return cur.rowcount > 0

    # ---- reading ----------------------------------------------------------
    def _row_to_game(self, row: sqlite3.Row, username: str) -> dict:
        summary = json.loads(row["summary_json"])
        mine = user_side(summary, username)
        opp = {"p1": "p2", "p2": "p1"}.get(mine or "")
        return {
            "id": row["id"],
            "format_id": row["format_id"],
            "format": row["format"],
            "p1": row["p1"],
            "p2": row["p2"],
            "played_at": row["played_at"],
            "uploadtime": row["uploadtime"],
            "private": bool(row["private"]),
            "has_inputlog": bool(row["has_inputlog"]),
            "source": row["source"],
            "has_team_paste": bool(row["team_paste"]),
            "turns": summary["turns"],
            "gametype": summary["gametype"],
            "user_side": mine,
            "opponent": summary[opp]["name"] if opp else None,
            "result": result_for(summary, username),
            "rating_before": summary[mine]["rating_before"] if mine else None,
            "rating_after": summary[mine]["rating_after"] if mine else None,
            "teams": {"p1": summary["p1"]["team"], "p2": summary["p2"]["team"]},
            "analyzed": False,  # set once a model scores the game (roadmap stage 5)
        }

    def list_games(
        self,
        username: str,
        format_id: str | None = None,
        result: str | None = None,
        opponent: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        sql = "SELECT * FROM games"
        args: list = []
        if format_id:
            sql += " WHERE format_id=?"
            args.append(format_id)
        sql += " ORDER BY COALESCE(played_at, uploadtime, added_at) DESC"
        with self._db() as db:
            rows = db.execute(sql, args).fetchall()
        games = [self._row_to_game(r, username) for r in rows]
        if result:
            games = [g for g in games if g["result"] == result]
        if opponent:
            oid = to_id(opponent)
            games = [g for g in games if oid in to_id(g["opponent"] or "")]
        return games[offset : offset + limit]

    def get_game(self, game_id: str, username: str) -> dict | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        if not row:
            return None
        game = self._row_to_game(row, username)
        folder = self.replay_dir / row["format_id"]
        game["log"] = (folder / f"{game_id}.log").read_text()
        inputlog = folder / f"{game_id}.inputlog"
        game["inputlog"] = inputlog.read_text() if inputlog.exists() else None
        game["team_paste"] = row["team_paste"]
        game["summary"] = json.loads(row["summary_json"])
        return game

    def formats(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute(
                "SELECT format_id, MAX(format) AS format, COUNT(*) AS n FROM games "
                "GROUP BY format_id ORDER BY n DESC"
            ).fetchall()
        return [dict(r) for r in rows]
