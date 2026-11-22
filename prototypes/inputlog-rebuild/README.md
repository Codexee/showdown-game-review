# Prototype: rebuild random battles from inputlogs

Throwaway test for vault ADR-0009. Results: `vault/raw/2026-11-22-rebuild-prototype-results.md`.

```bash
# one Showdown checkout per commit named in the inputlogs' >version line
git clone --filter=blob:none --no-checkout https://github.com/smogon/pokemon-showdown.git data/proto/ps-repo
(cd data/proto/ps-repo && git worktree add --detach ../ps/<sha10> <full-sha>)
(cd data/proto/ps/<sha10> && npm install --omit=dev && node build)   # ~5 s

node prototypes/inputlog-rebuild/rebuild.cjs data/proto/ps/<sha10> path/to/replay.json ...
```

Prints one JSON line per replay: `match` (the rebuilt log equals the replay's log, ignoring server-only lines), `firstDiff`, `channel`, `winner`, `turns`, and `teams` (both sides' full sets).
