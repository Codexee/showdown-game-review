---
title: Second-brain vault guide (pasted by the user)
type: raw
date: 2026-11-22
source: pasted by the user in chat. Google redirect citation links were removed; the text is otherwise unchanged.
---

# Second-brain guide (raw paste)

Do not edit. Applied in [[CLAUDE]] and [[ADR-0003-vault-as-memory]].

> Build a Claude "second brain" for large coding projects by pairing an Obsidian vault (plain Markdown files and backlinks) with Claude Code (which reads, searches, and updates the vault and codebase). For large codebases, use the vault as persistent engineering memory—architecture decisions, module maps, specs, and debugging logs—rather than relying on chat history.
>
> 1. Structure the Obsidian Vault
> Create a vault folder (either alongside your repo or as a dedicated engineering vault) with clean Markdown folders:
>
> * `raw/` or `inbox/`: Unprocessed specs, RFCs, meeting notes, error dumps, and research clips. Keep source files untouched.
> * `architecture/` or `wiki/`: Synthesized system overviews, data flows, dependency maps, and domain rules cross-linked with `[[wikilinks]]`.
> * `adr/` or `decisions/`: Architecture Decision Records noting trade-offs, chosen patterns, and superseded choices.
> * `specs/` or `projects/`: Feature specs, implementation plans, and task breakdowns.
> * `logs/` or `debugging/`: Root-cause notes for tricky bugs, incidents, and environment quirks.
> * `index.md` / Maps of Content (MOCs): Entry-point notes linking key areas so Claude can navigate large vaults without reading every file.
>
> As shown in a Reddit thread on r/ObsidianMD, there is a consensus on keeping vault structure modular—combining root or global rules with workspace/project-level READMEs or index files—so AI requests route cleanly without bloat.
>
> 2. Write a `CLAUDE.md` Schema
> Add a `CLAUDE.md` file at the vault root (and reference the vault path in your project's `CLAUDE.md`). Tell Claude Code:
>
> * Where raw inputs live versus compiled notes and ADRs.
> * How to format notes, tags, and `[[wikilinks]]`.
> * To cite supporting notes for factual claims, surface conflicts instead of silently overwriting them, and flag unknowns rather than guessing.
> * Which folders or code paths it may edit vs. keep read-only.
>
> For a practical walkthrough of writing a `CLAUDE.md` schema and navigating a vault with Claude Code, see Evgeni Rusev's guide on Medium.
>
> 3. Put the Vault Under Git
> Run `git init` inside the vault and commit early. Every edit Claude Code makes shows up as a readable `git diff` and is easy to roll back.
>
> 4. Connect Claude Code & Automate Workflows
> Open your terminal in the vault (or pass `--add-dir` / reference the vault path from your codebase session) and run `claude`. Obsidian watches file changes automatically.
>
> * Ingest & synthesize: Drop raw notes, PR summaries, or docs into `raw/` and ask Claude to update architecture notes, ADRs, and index pages.
> * Add custom commands/skills: Create reusable slash commands (such as `/adr`, `/spec-check`, or `/vault-sync`) for recurring documentation and planning steps.
> * Keep code and vault aligned: Ask Claude to check relevant vault notes before big refactors and update affected docs/ADRs after merging changes.
>
> See the Viable Edge setup guide for a step-by-step walkthrough of initializing the vault, putting it under Git, and configuring `CLAUDE.md`.
