# Vault schema (read this before touching the vault)

This vault is the project's long-term engineering memory. It is an Obsidian vault: plain Markdown with `[[wikilinks]]`. Chat history is not memory. If a fact, decision or bug matters later, it goes here.

Start every session at [[index]]. Follow links from there; do not read every file.

## Folders

| Folder | Holds | Who edits |
|---|---|---|
| `raw/` | Unprocessed inputs: interview answers, pasted guides, research dumps, error output. | Add new files only. **Never edit a file after it is written.** Name: `YYYY-MM-DD-topic.md`. |
| `wiki/` | Synthesized notes: overview, formats, data sources, bots, architecture, module maps. | Claude edits freely. Every claim cites a `raw/` note, an ADR or a URL. |
| `decisions/` | ADRs. One decision per file: `ADR-NNNN-short-name.md`. | Add new ADRs. To change a decision, write a new ADR that supersedes the old one, and set the old one's `status: superseded`. Do not delete or rewrite old ADRs. |
| `specs/` | Feature specs, plans, task breakdowns, [[open-questions]]. | Claude edits. A spec with `status: locked` changes only after the user agrees. |
| `logs/` | Session logs, root-cause notes for bugs, environment quirks. | Add new entries. Fix factual errors in place and say so. |
| `templates/` | Note templates. | Rarely. |

## Note format

Every note starts with YAML frontmatter:

```yaml
---
title: Short title
type: wiki | adr | spec | log | raw | moc
status: draft | active | locked | superseded | done   # wiki/spec/adr only
tags: [area/ui, area/model, area/data, area/vault]
updated: YYYY-MM-DD
---
```

- Link with `[[file-name]]` (no `.md`, no folder). File names are unique across the vault, kebab-case.
- Link liberally. A link to a note that doesn't exist yet is fine: it marks a note worth writing.
- Each wiki/spec note ends with a `## Related` list of links.
- Dates are absolute (`2026-11-22`), never "yesterday" or "last week".

## Rules for facts

1. **Cite.** Each factual claim in `wiki/` or `specs/` names its source: `([[2026-11-22-research-findings]])`, `([[ADR-0002-format-order]])` or a URL.
2. **Mark confidence.** Facts checked against a live source get no mark. Facts from memory or unchecked get `(unverified)`.
3. **Surface conflicts. Do not overwrite.** If new input contradicts a note, add a `> [!warning] Conflict` callout naming both sources, and add the item to [[open-questions]]. Only the user resolves it.
4. **Flag unknowns.** Write `**Unknown:**` and add it to [[open-questions]]. Do not guess.

## What Claude may edit

- **May edit:** `vault/wiki/`, `vault/specs/`, `vault/logs/`, `vault/index.md`, new files in `vault/raw/` and `vault/decisions/`, and project code.
- **Read-only:** existing files in `vault/raw/`; accepted ADRs (except the `status` and `superseded_by` fields); `.claude/skills/` (copied from another project).
- **Ask first:** changing a `locked` spec; deleting any vault file.

## Workflows

- **Ingest:** a new raw input lands in `raw/` → update the affected `wiki/` and `specs/` notes → add ADRs for any decision → update [[index]] → add a line to the day's session log in `logs/`.
- **Before a big change:** read the module's wiki note and its ADRs.
- **After a change lands:** update the wiki note, the spec status and the [[index]]. Commit the vault with the code.
- **Bug with a non-obvious cause:** write `logs/YYYY-MM-DD-bug-short-name.md` using [[template-debug-log]].
