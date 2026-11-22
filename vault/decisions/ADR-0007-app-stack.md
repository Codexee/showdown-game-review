---
title: ADR-0007 App stack
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/ui, area/infra]
---

# ADR-0007: FastAPI server and a Vite + TypeScript frontend

## Context
The local web app ([[ADR-0001-local-web-app]]) needs a server and a frontend. The user chose "FastAPI + Vite/TS (Recommended)" ([[2026-11-22-interview-round-2]]).

## Decision
- **Server:** Python with FastAPI. It shares code with the log parser and the model (also Python), serves the API from [[spec-review-app]], and receives logs from the userscript ([[ADR-0006-replay-archive]]).
- **Frontend:** TypeScript built with Vite, in `web/`. In development, Vite's dev server proxies `/api` to FastAPI. For daily use, FastAPI serves the built files.
- **Database:** SQLite.

## Options considered
- **FastAPI + Vite/TS (chosen):** typed frontend, fast reloads, room to grow into the pixel-art UI.
- **FastAPI + plain HTML/JS:** no build step, but harder to grow.

## Consequences
- Two toolchains: `uv` for Python and `npm` for `web/` ([[environment]]).
- **Unknown:** whether to use a UI framework (Preact, Svelte, none). Decide at the UI stage with `/frontend-design`.

## Related
- [[architecture]] · [[spec-review-app]] · [[visual-style]]
