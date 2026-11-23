---
title: ADR-0016 Two-view scoring and a strict install gate
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/model]
---

# ADR-0016: Score positions from both players' views; install a model only if it is better

## Context
- The Codex review found that the eval bar scored a position from one player's view, while the move review averaged both. On the pinned bank the two views disagree on the winner in 12.4% of positions ([[2026-11-23-codex-review]] finding 2).
- Averaging both views improves `main@9000` with no retraining: log-loss 0.58543 → 0.58285, 90% band of the difference [−0.0027, −0.0025], accuracy 67.4% → 67.6% (Claude's recompute, same note).
- `training/overnight.sh` could install a model with no passing gate: its run name defaulted to the installed run's, which skipped the gate, and "no clear difference" also installed. `compare_runs` silently compared only the samples both files shared (finding 1 and 4, checked).
- The user approved fixes 1–3 ([[2026-11-23-codex-fixes-go]]).

## Decision
1. **Two-view estimate everywhere a model is scored or shown:** side X's chance = (X's view + 1 − other side's view) / 2. Used by the eval bar (`server/model_eval.py`), the move review's leaf (already, [[ADR-0014-move-review-method]]), `training/test_model.py` (`two_view` in the report) and the paired gate (`compare_runs --view two`, the default). `--view single` keeps the old scoring for comparison.
2. **Strict pairing:** `compare_runs` stops if the two prediction files have different keys, order, duplicates or labels.
3. **Install rule:** the overnight script installs only when the gate says "b is better" (the whole 90% band below zero). "No clear difference", a failed gate, or a missing or mismatched incumbent score keeps the installed model. `INSTALL_IF_TIE=1` overrides the tie case only. This replaces "install unless the gate calls it worse" in [[spec-eval-model]].
4. **Safe run setup:** `RUN` must be new (never the installed run; an existing run needs `RESUME=1`); the dataset is named after its dates and checked against `SINCE` / `RANGES`; dropout, weight decay and the value-weight floor are variables; `DRY_RUN=1` runs only the checks and the gate.

## Consequences
- The bar and the move review now agree on every position, and p1's and p2's bars add to 100% (checked on Codexe's game).
- Gates scored before 2026-11-23 used one view. Under two views, test B's edge over A disappears (0.59736 vs 0.59734 log-loss); B is still worse than `main` (+0.0145, band [+0.0103, +0.0186]).
- The installed model's text ("67% of the time") was written from one view; the two-view figure is 67.6%. It updates the next time a model is installed.
- Two-view scoring needs datasets built with `--both-sides` (the pinned bank is).
- **Not decided here:** what "public" should mean for the encoder (exact HP in uploaded logs, own unseen bench; Codex finding 2, second part). Unmeasured; see [[open-questions]].

## Related
- [[plan-run-v12]] · [[spec-eval-model]] · [[2026-11-23-codex-review]] · [[ADR-0005-overnight-training-budget]]
