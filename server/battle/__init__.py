"""Per-turn battle state from a Showdown protocol log (roadmap stage 3).

    from server.battle import parse_log, view_for
    result = parse_log(log)            # every turn, everything the log reveals
    mine = view_for(result.states[5], "p1", result.format_id)   # what p1 could see

Ground truth for tests comes from Showdown's own simulator (tools/sim-states.cjs).
"""
from .parser import ParseResult, parse_log
from .view import view_for

__all__ = ["ParseResult", "parse_log", "view_for"]
