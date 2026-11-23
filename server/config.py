"""Paths and defaults. Override with environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    data_dir: Path
    default_username: str
    poll_minutes: float
    request_delay: float  # seconds between requests to Showdown
    poller_enabled: bool
    user_agent: str = "Mozilla/5.0 (compatible; showdown-game-review/0.1; local replay archive)"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "archive.sqlite3"

    @property
    def replay_dir(self) -> Path:
        return self.data_dir / "replays"


def load_config() -> Config:
    return Config(
        data_dir=Path(os.environ.get("SGR_DATA_DIR", ROOT / "data")),
        default_username=os.environ.get("SGR_USERNAME", ""),   # each user sets theirs in the app
        poll_minutes=float(os.environ.get("SGR_POLL_MINUTES", "5")),
        request_delay=float(os.environ.get("SGR_REQUEST_DELAY", "1.0")),
        poller_enabled=os.environ.get("SGR_POLLER", "1") != "0",
    )
