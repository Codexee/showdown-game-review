---
title: ADR-0003 Vault as project memory
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/vault]
---

# ADR-0003: An Obsidian vault in the repo is the project memory

## Context
The user asked that all project information live in a web of cross-linked Markdown files, following the guide in [[2026-11-22-second-brain-guide]]. Earlier facts and answers were nearly lost when a question was skipped and work moved to a new session ([[2026-11-22-session-log]]).

## Decision
- The vault lives at `vault/` inside the project repo, with `raw/`, `wiki/`, `decisions/`, `specs/`, `logs/`, `templates/` and [[index]].
- Rules are in `vault/CLAUDE.md` ([[CLAUDE]]). The project's root `CLAUDE.md` points to it.
- The whole project, vault included, is one git repo, so vault edits show up in `git diff` next to the code they describe.

## Options considered
- **Vault inside the repo (chosen):** one git history; docs and code change in the same commit; Claude sees it without `--add-dir`.
- **Separate vault repo:** what the guide shows first, but it adds a second history to keep in sync, and this project is small.
- **Claude memory files only:** not visible in Obsidian, not linked, not reviewed in git.

## Consequences
- Open `vault/` as a vault in Obsidian to browse it.
- Every session reads [[index]] first and updates the vault after a change.

## Related
- [[CLAUDE]] · [[tooling]]
