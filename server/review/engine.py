"""Python side of tools/review-engine.cjs (a Node process running Showdown's simulator)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from server.config import ROOT

TOOL = ROOT / "tools" / "review-engine.cjs"


class ReviewEngine:
    """One Node process with Showdown built at the replay's commit."""

    def __init__(self, sim_dir: Path):
        self.proc = subprocess.Popen(["node", str(TOOL), str(sim_dir)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    def _ask(self, obj: dict) -> dict:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"review engine stopped: {err[-500:]}")
        out = json.loads(line)
        if "error" in out:
            raise RuntimeError(f"review engine: {out['error']}")
        return out

    def load(self, inputlog: str) -> dict:
        return self._ask({"cmd": "load", "inputlog": inputlog})

    def expand(self, turn: int, pairs: list[tuple[str, str]], seeds: int) -> list[dict]:
        return self._ask({"cmd": "expand", "turn": turn, "pairs": [list(p) for p in pairs], "seeds": seeds})["cells"]

    def options(self, turn: int, worlds: list[dict | None]) -> list[dict]:
        return self._ask({"cmd": "options", "turn": turn, "worlds": worlds})["worlds"]

    def expand_jobs(self, turn: int, jobs: list[dict]) -> list[dict]:
        """jobs: [{"world": {...}|None, "seed": k, "pairs": [(c1, c2), ...]}]"""
        return self._ask({"cmd": "expand_jobs", "turn": turn,
                          "jobs": [dict(j, pairs=[list(p) for p in j["pairs"]]) for j in jobs]})["cells"]

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def sim_for(inputlog: str) -> Path:
    """Built Showdown checkout at the commit named in the inputlog's >version line
    (vault ADR-0009: never a different commit)."""
    from training.rebuild import checkout

    first = inputlog.split("\n", 1)[0]
    if not first.startswith(">version "):
        raise ValueError("inputlog has no >version line")
    return checkout(first.split()[1])
