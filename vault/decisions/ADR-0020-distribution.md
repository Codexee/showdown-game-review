---
title: ADR-0020 Distribution: public GitHub repo, local app with easy setup
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/vault]
---

# ADR-0020: Publish the code on GitHub; the app stays a local web app with one-command setup

## Context
- The user asked to publish to GitHub and host on Pages, then on Vercel, then chose a local web app with easy setup instead ([[2026-11-23-publish-answers]], [[2026-11-23-local-app-not-hosted]]).
- Static hosts can't run the server: the game archive needs a disk, PyTorch is far larger than serverless limits, move review runs Showdown's simulator for minutes, and the poller runs in the background. Browsers also block a public site from calling the user's computer. This matches [[ADR-0001-local-web-app]].

## Decision
1. **Public repository** `Codexee/showdown-game-review` ([[ADR-0019-project-name]]).
2. **History cleaned before the first push:** the third-party skills in `.claude/skills/` (each under its own license) and old Obsidian window-state files are removed from every commit and ignored from now on (the skills stay on disk for Claude); every commit's email is rewritten to the GitHub noreply address, and the repo's git config uses it for new commits.
3. **Easy setup:** `./start.sh` (runs `./setup.sh` on first use: `uv sync --no-dev`, web build, `data/`), then serves on `127.0.0.1:8765` and opens the browser. `PORT=` picks another port. Needs uv, Node.js 20+ and git.
4. **Fresh installs start with no username** (`SGR_USERNAME` default empty): sync asks for one; the profile is empty until then.
5. **No model is published.** Without `data/models/current.pt`, the eval bar uses the remaining-HP estimate and move review is off; the README points to the training pipeline.

## Consequences
- Commit ids change with the rewrite: hashes quoted in older vault notes (raw notes, logs) refer to the pre-publication history and no longer resolve.
- Publishing the trained model (for example as a release asset) is a separate decision; **Unknown:** whether the user wants it ([[open-questions]]).
- Checked: a fresh clone runs `./setup.sh` and `./start.sh` and serves the app; 104 Python and 7 userscript tests pass.

## Related
- [[ADR-0001-local-web-app]] · [[ADR-0019-project-name]] · [[module-map]]
