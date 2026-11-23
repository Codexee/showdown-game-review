---
title: ADR-0021 Publish the win-chance model as a GitHub release
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/model]
---

# ADR-0021: The installed model is published as a release; setup downloads and verifies it

## Context
- New users had no model, so no eval bar beyond the HP estimate and no move review ([[ADR-0020-distribution]], [[open-questions]] #14).
- The user chose to publish it ([[2026-11-23-publish-model]]).
- The strongest bots withheld weights over cheating concerns ([[ADR-0013-post-game-analysis-only]]); this model is a review model for finished games (it calls the winner 67% of the time), and the app only analyses finished games.

## Decision
1. Release `model-main-9000` on `Codexee/showdown-game-review`, marked latest, with `current.pt` (28,637,071 bytes, `main@9000`) and `current.pt.sha256` (`92dba5d84c5959718acf573dd84048b6793734a3b73171886e9227d126588955`). The file holds only weights, config, a score summary and the temperature.
2. `setup.sh` downloads `releases/latest/download/current.pt` when no model is installed, checks the SHA-256 and installs it only on a match (`NO_MODEL=1` skips; `MODEL_URL` picks another release).
3. The app loads the installed model with `torch.load(..., weights_only=True)` (no code runs from the file).

## Consequences
- A future model that passes the gate (for example `v12`) is published as a new release; setup then fetches it for new installs. Existing installs keep theirs.
- Checked: a fresh clone from GitHub downloads, verifies and loads the model; a file with a wrong checksum is refused.

## Related
- [[ADR-0020-distribution]] · [[spec-eval-model]] · [[ADR-0013-post-game-analysis-only]]
