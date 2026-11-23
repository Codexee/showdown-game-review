---
title: Index (map of content)
type: moc
tags: [area/vault]
updated: 2026-11-22
---

# Showdown Game Review: index

A local, Lichess-style review tool for Pokémon Showdown games. A trained network gives an eval bar and an eval graph for each turn. The app pulls games for `Codexe` and saves every finished game from now on. The UI uses a Gen 4–5 pixel-art style. First format: [Gen 9] Random Battle; then VGC 2026 Reg M-C.

Rules for this vault: [[CLAUDE]].

## Start here
- [[project-overview]]: what we are building and why
- [[open-questions]]: decisions still waiting on the user
- [[roadmap]]: build order

## Wiki (synthesized knowledge)
- [[formats]]: Showdown formats in scope (Gen 9 Random Battle, Champions VGC Reg M-C, Champions OU)
- [[data-sources]]: replay API, user API, Smogon usage stats
- [[bot-landscape]]: foul-play, poke-env, Metamon, AlphaMon and others
- [[architecture]]: components and data flow
- [[module-map]]: what each code file does, and how to run it
- [[battle-parser]]: per-turn battle state from a log; accuracy and limits
- [[benchmark-best-in-class]]: how we compare with PS Dashboard, Jaxcalibur, mikumiku37, ps-ppo, Metamon and others; ranked gaps
- [[environment]]: this Mac's hardware and installed tools
- [[tooling]]: Claude skills and plugins used for this project
- [[visual-style]]: Gen 4–5 pixel-art direction

## Decisions (ADRs)
- [[ADR-0001-local-web-app]]: accepted
- [[ADR-0002-format-order]]: accepted, supersedes Champions OU as the first target
- [[ADR-0003-vault-as-memory]]: accepted
- [[ADR-0004-pixel-art-style]]: accepted
- [[ADR-0005-overnight-training-budget]]: accepted
- [[ADR-0006-replay-archive]]: accepted
- [[ADR-0007-app-stack]]: accepted
- [[ADR-0008-python-313]]: accepted
- [[ADR-0009-randbats-full-info-reconstruction]]: accepted (prototype 61/61)
- [[ADR-0010-local-api-origin-guard]]: accepted
- [[ADR-0011-review-screen-battle-view]]: accepted
- [[ADR-0012-training-data-v1]]: accepted
- [[ADR-0013-post-game-analysis-only]]: accepted (formalizes current behavior)
- [[ADR-0014-move-review-method]]: accepted (stage 6: regret over a simulated choice matrix)
- [[ADR-0015-move-review-sampled-worlds]]: accepted (grade on what each player could see; amends ADR-0014)

## Specs
- [[spec-review-app]]: review screen and games page (built; eval from the trained model; move review for randbats)
- [[spec-replay-sync]]: pull user data, list games, auto-save replays (draft)
- [[plan-run-v12]]: next training run, fixing value overfitting (tests running; overnight run waits on the user)
- [[spec-eval-model]]: the network and training pipeline (v1 built; overnight run pending)

## Logs
- [[2026-11-22-session-log]]
- [[environment-quirks]]
- [[2026-11-22-bug-forme-change-team]]
- [[2026-11-22-bug-sim-snapshot-mutation]]

## Raw inputs
- [[2026-11-22-interview-round-1]]
- [[2026-11-22-interview-round-2]]
- [[2026-11-22-research-findings]]
- [[2026-11-22-research-round-2]]
- [[2026-11-22-rebuild-prototype-results]]
- [[2026-11-22-adr-0009-decision]]
- [[2026-11-22-parser-accuracy-results]]
- [[2026-11-22-stage4-answers]]
- [[2026-11-22-training-test-runs]]
- [[2026-11-22-prior-art-research]]
- [[2026-11-22-prior-art-jaxcalibur-mikumiku]]
- [[2026-11-22-p0-ab-results]]
- [[2026-11-22-main-run-results]]
- [[2026-11-22-stage6-results]]
- [[2026-11-22-v12-tests-go]]
- [[2026-11-22-second-brain-guide]]
