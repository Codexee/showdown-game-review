from server.ids import full_replay_id, parse_replay_ref, to_id
from server.logsummary import result_for, summarize

from .conftest import RANDBATS_ID, VGC_ID, load_replay

import pytest


def test_randbats_summary():
    s = summarize(load_replay(RANDBATS_ID)["log"])
    assert s.format == "[Gen 9] Random Battle"
    assert s.gametype == "singles"
    assert s.p1.name == "Codexe" and s.p2.name == "charizardslayer1"
    assert (s.p1.rating_before, s.p1.rating_after) == (1827, 1804)
    assert (s.p2.rating_before, s.p2.rating_after) == (1780, 1803)
    assert s.winner == "charizardslayer1" and s.finished and not s.tie
    assert s.turns > 0
    assert s.started_at == 1793202321
    # randbats has no team preview: teams come from switch-ins
    assert s.p1.team[:2] == ["Dedenne", "Metagross"]
    assert "Palafin" in s.p2.team and "Palafin-Hero" not in s.p2.team
    assert len(s.p1.team) <= 6 and len(s.p2.team) <= 6
    assert result_for(s.to_dict(), "Codexe") == "loss"
    assert result_for(s.to_dict(), "charizard slayer1") == "win"
    assert result_for(s.to_dict(), "someone else") is None


def test_vgc_summary_uses_team_preview():
    s = summarize(load_replay(VGC_ID)["log"])
    assert s.gametype == "doubles"
    assert s.p1.team == ["Sinistcha", "Delphox", "Incineroar", "Kingambit", "Sneasler", "Floette-Eternal"]
    assert len(s.p2.team) == 6
    assert (s.p1.rating_before, s.p1.rating_after) == (1192, 1161)
    assert result_for(s.to_dict(), "codexe") == "loss"


def test_unfinished_log():
    s = summarize("|player|p1|A|1|\n|player|p2|B|2|\n|start\n|turn|1\n")
    assert not s.finished and s.winner is None
    assert result_for(s.to_dict(), "A") is None


def test_to_id():
    assert to_id("Zuri 2") == "zuri2"
    assert to_id("☆Codexe") == "codexe"


@pytest.mark.parametrize("ref,expected", [
    ("https://replay.pokemonshowdown.com/gen9randombattle-2705718015", ("gen9randombattle-2705718015", None)),
    ("https://replay.pokemonshowdown.com/gen9randombattle-2705718015.json", ("gen9randombattle-2705718015", None)),
    ("replay.pokemonshowdown.com/gen9ou-1-abc123pw", None),  # no scheme: treated as a path
    ("gen9ou-12-abc123pw", ("gen9ou-12", "abc123")),
    ("https://replay.pokemonshowdown.com/smogtours-gen9ou-123", None),
    ("https://evil.example.com/gen9ou-123", None),
    ("not a replay", None),
])
def test_parse_replay_ref(ref, expected):
    if ref == "replay.pokemonshowdown.com/gen9ou-1-abc123pw":
        assert parse_replay_ref(ref) == ("gen9ou-1", "abc123")
        return
    if expected is None:
        with pytest.raises(ValueError):
            parse_replay_ref(ref)
    else:
        assert parse_replay_ref(ref) == expected
    assert full_replay_id("gen9ou-12", "abc") == "gen9ou-12-abcpw"
