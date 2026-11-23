---
title: ADR-0019 Project name showdown-game-review
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/vault]
---

# ADR-0019: The project is named `showdown-game-review`

## Context
- The project carried several names: "Showdown Review" (page title, heading, API title, userscript), `showdown-review` (package, userscript file and namespace, user agent), `showdown_review` (logger), the `SR_` prefix (environment variables) and `sr-` (saved display settings), next to "Showdown Game Review" in `CLAUDE.md` and the vault index.
- The user asked for one name everywhere, also on GitHub ([[2026-11-23-name-showdown-game-review]]).

## Decision
1. Identifiers use **`showdown-game-review`**: Python package, userscript file (`userscript/showdown-game-review.user.js`, served at `/userscript/showdown-game-review.user.js`) and namespace (`showdown-game-review.local`), user agent, the GitHub repository. Logger: `showdown_game_review`. Userscript hook: `__showdownGameReview`.
2. Human-facing titles use the same name written for display: **Showdown Game Review** (page title, heading, API title, userscript name).
3. Abbreviations follow: environment variables `SGR_DATA_DIR`, `SGR_USERNAME`, `SGR_POLL_MINUTES`, `SGR_REQUEST_DELAY`, `SGR_POLLER`; saved display settings `sgr-theme`, `sgr-motion`.
4. Not renamed: raw notes and accepted ADR bodies (read-only by the vault rules, [[CLAUDE]]), the copied `.claude/skills/`, and the folder on disk (`showdown game review`; renaming it would break the session and memory paths).

## Consequences
- Old `SR_*` variables and the old userscript URL no longer work; nothing used them outside this project (the userscript is not installed yet, [[open-questions]] #1).
- A dark/light or motion choice saved under the old `sr-` keys is not carried over: pick it once again.

## Related
- [[index]] · [[module-map]]
