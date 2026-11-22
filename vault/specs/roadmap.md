---
title: Roadmap
type: spec
status: draft
tags: [area/vault]
updated: 2026-11-22
---

# Roadmap (draft)

The order follows the dependencies in [[architecture]]. Stages are not locked until the interview finishes ([[open-questions]]).

1. **Vault and repo.** This vault, git, project `CLAUDE.md`. *Done 2026-11-22.*
2. **Replay sync and archive.** *2a and 2b built 2026-11-22 ([[module-map]]); 2b still needs one real-browser test.* (a) Poller for `Codexe`'s new uploaded replays, plus the archive, game list, URL paste and file upload. (b) Userscript that sends every finished battle. Useful by itself. The same scraper also collects `gen9randombattle` training data. [[spec-replay-sync]], [[ADR-0006-replay-archive]]
3. **Log parser.** Protocol log → battle state per turn, from each side's view. *Done 2026-11-22: 99.4% of turn states exact on unseen games, 100% after fixes ([[battle-parser]]). Doubles unverified.*
4. **Review app shell.** Game list plus replay player with a placeholder eval (for example, remaining HP). Pixel-art style. [[spec-review-app]], [[visual-style]] *Done 2026-11-22 ([[ADR-0011-review-screen-battle-view]]).*
5. **Eval model, Gen 9 Random Battle.** Small test training, then the overnight run. Plug into the eval bar. [[spec-eval-model]] *Pipeline built 2026-11-22; test model installed (66% vs 64% on future games); overnight run pending.* *P0 upgrades done; full run `main` installed 2026-11-22 (67.4% vs 62.9% on future games, [[2026-11-22-main-run-results]]).*
6. **Move review.** Best move, labels such as "mistake", win chance after each choice. *Design from the benchmark: regret over a simulator-backed choice matrix with our value as the leaf; 5/10/20 bands; decision vs luck; luck ledger; accuracy score ([[benchmark-best-in-class]]).*
7. **VGC 2026 Reg M-C.** Doubles parser and model. [[ADR-0002-format-order]]

## Related
- [[index]] · [[project-overview]]
