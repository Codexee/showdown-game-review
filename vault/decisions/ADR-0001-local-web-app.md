---
title: ADR-0001 Local web app
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/ui]
---

# ADR-0001: The review tool is a local web app

## Context
The model needs a local process either way, because a browser extension cannot run a PyTorch network or a simulator by itself. The user picked "Local web app (Recommended)" ([[2026-11-22-interview-round-1]]).

## Decision
A Python server on this Mac runs the model and the replay archive and serves a browser page. Showdown's site is not modified.

## Options considered
- **Local web app (chosen):** one codebase; we control the page; room for an eval graph and move list; works offline and with any log; easy to test with Playwright.
- **Overlay on Showdown's site:** one click from a replay you are already watching, but it still needs the local server, it breaks when Showdown changes its page, and requests from Showdown's page to localhost are cross-origin.
- **Both:** web app first, overlay later.

## Consequences
- An optional small userscript can still be added later to send games to the local server. That may be needed to save games that were never uploaded ([[ADR-0006-replay-archive]], [[open-questions]]).

## Related
- [[architecture]] · [[spec-review-app]] · [[ADR-0004-pixel-art-style]]
