# Showdown Game Review (`showdown-game-review`)

A local, Lichess-style review tool for Pokémon Showdown games, with an eval bar from a network trained on this Mac.

## Project memory lives in `vault/`

- **Start every session by reading `vault/index.md`**, then only the notes you need.
- **Follow the rules in `vault/CLAUDE.md`**: where raw inputs go, ADR format, citing sources, surfacing conflicts, flagging unknowns, which files are read-only.
- When the user answers a question or a decision is made, write it to `vault/raw/` and the right ADR/spec **in the same turn**. Chat history is not memory.
- Before changing a module, read its wiki note and ADRs. After a change lands, update the vault and commit it with the code.
- Open questions waiting on the user: `vault/specs/open-questions.md`.

## Conventions
- Every reply opens with one line naming the skills that fit (enforced by `.claude/hooks/skill_suggest.py`).
- Train locally. Run a small test before any long training run. Long runs go in the background ([[ADR-0005-overnight-training-budget]] in the vault).
- Data and model checkpoints go under `data/` and `checkpoints/` (git-ignored).
