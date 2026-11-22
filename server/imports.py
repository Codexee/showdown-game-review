"""Turn an uploaded file (.log, replay .json, or a saved replay .html) into a replay record."""
from __future__ import annotations

import hashlib
import html
import json
import re

from .ids import to_id
from .logsummary import summarize

# Saved Showdown replay pages keep the log in <script type="text/plain" class="battle-log-data">
_HTML_LOG = re.compile(
    r'<script[^>]*class="battle-log-data"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)
# Saved replay pages may name the replay in a link or meta tag
_HTML_ID = re.compile(r"replay\.pokemonshowdown\.com/([a-z0-9]+-\d+)")


def record_from_file(filename: str, data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    name = filename.lower()

    if name.endswith(".json"):
        record = json.loads(text)
        if not isinstance(record, dict) or "log" not in record:
            raise ValueError("JSON file is not a Showdown replay (no 'log' field)")
        if "id" not in record:
            record["id"] = _upload_id(record["log"])
        return record

    if name.endswith((".html", ".htm")) or "<html" in text[:500].lower():
        m = _HTML_LOG.search(text)
        if not m:
            raise ValueError("HTML file has no battle log (expected a saved Showdown replay)")
        log = html.unescape(m.group(1)).strip("\n")
        id_match = _HTML_ID.search(text)
        replay_id = id_match.group(1) if id_match else _upload_id(log)
    else:
        log = text
        if "|" not in log:
            raise ValueError("File doesn't look like a Showdown battle log")
        replay_id = _upload_id(log)

    summary = summarize(log)
    if not summary.p1.name and not summary.p2.name:
        raise ValueError("Couldn't find any players in the log")
    return {
        "id": replay_id,
        "format": summary.format,
        "formatid": to_id(summary.format) or "unknown",
        "players": [summary.p1.name, summary.p2.name],
        "log": log,
        "uploadtime": None,
        "rating": None,
        "private": 0,
        "password": None,
    }


def _upload_id(log: str) -> str:
    return "upload-" + hashlib.sha1(log.encode()).hexdigest()[:16]
