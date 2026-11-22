---
title: ADR-0010 Local API origin guard
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/infra, area/data]
---

# ADR-0010: Only this app's pages (and Showdown, for ingest) may call the local API

## Context
- The app listens on `127.0.0.1:8765`. Any website open in the browser can send requests to localhost. Without a check, a page could change settings, start syncs, or plant fake games through `/api/ingest`.
- The userscript must still be able to send games. Its main path is Tampermonkey's `GM_xmlhttpRequest`, which sends no page `Origin`. Its fallback path is a plain `fetch()` from play.pokemonshowdown.com ([[spec-replay-sync]], [[2026-11-22-research-round-2]]).

## Decision
Middleware in `server/app.py` checks the `Origin` header on every `/api/*` request:
- **No Origin** (curl, `GM_xmlhttpRequest`, same-page GETs): allowed.
- **Origin on localhost / 127.0.0.1 / ::1** (this app, the Vite dev server): allowed.
- **Origin `https://play.pokemonshowdown.com` or `https://replay.pokemonshowdown.com`:** allowed **only** on `/api/ingest` and `/api/ingest-private`, with CORS headers and `Access-Control-Allow-Private-Network`.
- **Anything else:** 403.

The ingest routes also require `Content-Type: application/json`, so a plain HTML form on another site can't post without a CORS preflight.

## Options considered
- **Shared secret token** in the userscript: stronger, but every install would need a copy-paste step. Not needed for a single-user local app.
- **No check:** easy, but any site could change the archive.

## Consequences
- A future browser extension would need its own origin added to the allow list.
- Tested in `server/tests/test_ingest.py::test_origin_guard`.

## Related
- [[ADR-0006-replay-archive]] · [[module-map]] · [[spec-replay-sync]]
