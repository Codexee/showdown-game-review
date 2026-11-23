---
title: Tooling (skills and plugins)
type: wiki
status: active
tags: [area/vault, area/infra]
updated: 2026-11-22
---

# Tooling

## Project skills (`.claude/skills/`, copied from the PatriotHacks project on 2026-11-22)
- Planning: `/interview` (spec questions), `/prototype`, `/parallelize` (needs git; now set up), `/handoff`, `/systematic-debugging`.
- Code review: `/codex` (needs the Codex CLI; installed, 0.169.0).
- UI: `/frontend-design`, `/impeccable`, `/better-interface` and the `/better-*` family, `/animate`, `/agentation`.
- Testing: `/agent-browser`, `/webapp-testing`.
- Writing: `/ste`, `/humanizer`.

## Project hook
`.claude/hooks/skill_suggest.py` runs on every prompt. It makes Claude open each reply with one line naming the skills that fit. Keyword hints live in `.claude/skill-triggers.json`.

## Vault tooling
- The **claude-obsidian** plugin is installed (`/claude-obsidian:wiki`, `wiki-ingest`, `wiki-lint`, `wiki-query`, `save`, `canvas`). Its `wiki-lint` agent can check this vault for broken links. Not used yet.

## Pixel art
- **SpriteCook** plugin (Anthropic plugin directory, community publisher): sprites, UI kits, tilesets, short animations, with an MCP server. **Installed 2026-11-23; its MCP server needs sign-in before its tools work** ([[2026-11-23-spritecook-new-sprites-auth]]). The user chose to build the stage 4 UI with CSS pixel art first and add SpriteCook later ([[2026-11-22-stage4-answers]], [[visual-style]]). Found by plugin search on 2026-11-22 ([[2026-11-22-research-findings]]).
- No standalone pixel-art skill turned up in the skill search.

## Related
- [[environment]] · [[visual-style]] · [[CLAUDE]]
