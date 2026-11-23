---
title: ADR-0018 Close model testing; grade quality before the UI
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/model, area/ui]
---

# ADR-0018: After the overnight run, close model testing and work on grade quality, then the UI

## Context
- Training gains are flattening: regularisation alone changed nothing on future games; the value schedule gave −0.0018 and doubling the games −0.0079 at small scale ([[2026-11-23-v12-tests-and-eval-gains-results]]).
- The one-turn search beat every training change: −0.0083 on 199 games and −0.0063 on 100 fresh games ([[2026-11-23-search-blend-fresh-check]]).
- The move review's grades have known fairness problems and no direct measure of correctness ([[2026-11-23-codex-review]] findings 6–7). PS Dashboard re-searches flagged mistakes one depth deeper ([[2026-11-22-prior-art-research]]); the user named the one-turn limit as the project's main gap ([[2026-11-23-endgame-goals-and-overnight-go]]).
- The user adopted this order ([[2026-11-23-adopt-grade-quality-next]]).

## Decision
1. **Model testing ends** once the overnight run `v12` is read and the gate has decided whether it installs. No further training tests in this stage (distillation, history tokens and the rest stay listed in [[plan-model-gains]] and [[goals-endgame]]).
2. **Next stage: grade quality** ([[plan-grade-quality]]): a verdict bank, the worlds fairness fix, and a depth-2 re-check of flagged choices that may only lower a choice's regret.
3. **Then the UI stage**, with the VGC team import ([[roadmap]]).
4. This replaces the order in [[2026-11-22-direction-codex-review]] item 10 ("after model testing, go back to the UI"): grade quality now comes between them.

## Consequences
- What users see (verdicts) gets measured and fixed before more polish.
- The depth-2 re-check is the first step toward the deeper search in [[goals-endgame]].

## Related
- [[roadmap]] · [[plan-grade-quality]] · [[goals-endgame]] · [[plan-run-v12]]
