---
title: Index (map of content)
type: moc
tags: [area/vault]
updated: 2026-11-22
---

# Showdown Game Review (`showdown-game-review`): index

A local, Lichess-style review tool for Pokémon Showdown games. A trained network gives an eval bar and an eval graph for each turn. The app pulls games for `Codexe` and saves every finished game from now on. The UI uses a Gen 4–5 pixel-art style. First format: [Gen 9] Random Battle; then VGC 2026 Reg M-C.

Rules for this vault: [[CLAUDE]].

## Start here
- Code: https://github.com/Codexee/showdown-game-review (public; run locally with `./start.sh`, [[ADR-0020-distribution]])
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
- [[ADR-0016-two-view-scoring-strict-gate]]: accepted (both players' views; install only if better)
- [[ADR-0017-eval-bar-search-blend]]: accepted (eval bar = 75% search + 25% network after a move review)
- [[ADR-0018-grade-quality-before-ui]]: accepted (close model testing after `v12`; grade quality, then the UI)
- [[ADR-0019-project-name]]: accepted (one name: `showdown-game-review`)
- [[ADR-0020-distribution]]: accepted (public GitHub repo; local app with one-command setup)
- [[ADR-0021-publish-model]]: accepted (model `main@9000` as a release; setup downloads and verifies it)

## Specs
- [[spec-review-app]]: review screen and games page (built; eval from the trained model; move review for randbats)
- [[spec-replay-sync]]: pull user data, list games, auto-save replays (draft)
- [[plan-grade-quality]]: next stage: verdict bank, worlds fairness fix, depth-2 re-check (draft)
- [[goals-endgame]]: long-range goals set by the user (deeper search than PS Dashboard at its speed, and more)
- [[plan-model-gains]]: eval gains beyond more training (ensembles, calibration, search as the eval)
- [[plan-run-v12]]: next training run, fixing value overfitting (tests running; overnight run waits on the user)
- [[spec-eval-model]]: the network and training pipeline (v1 built; overnight run pending)

## Logs
- [[2026-11-22-session-log]]
- [[environment-quirks]]
- [[2026-11-22-bug-forme-change-team]]
- [[2026-11-22-bug-sim-snapshot-mutation]]
- [[2026-11-23-bug-custom-rules-randbats]]

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
- [[2026-11-22-worlds-vs-perfect-results]]
- [[2026-11-22-v12-tests-go]]
- [[2026-11-22-direction-codex-review]]
- [[2026-11-23-codex-review]]
- [[2026-11-23-codex-fixes-go]]
- [[2026-11-23-v12-tests-and-eval-gains-results]]
- [[2026-11-23-search-bar-first]]
- [[2026-11-23-endgame-goals-and-overnight-go]]
- [[2026-11-23-search-blend-fresh-check]]
- [[2026-11-23-adopt-grade-quality-next]]
- [[2026-11-23-desktop-one-screen-layout]]
- [[2026-11-23-games-page-one-block]]
- [[2026-11-23-less-text-symbols-motion]]
- [[2026-11-23-turn-motion-and-team-paste]]
- [[2026-11-23-theme-motion-switches]]
- [[2026-11-23-auto-analyze]]
- [[2026-11-23-battle-extras]]
- [[2026-11-23-battle-extras-feedback]]
- [[2026-11-23-icons-over-text-rule]]
- [[2026-11-23-review-elo-pokeball]]
- [[2026-11-23-layout-v3-faint-hp]]
- [[2026-11-23-official-sprites-and-space]]
- [[2026-11-23-no-names-in-battle-box]]
- [[2026-11-23-side-tags-no-turn-repeat]]
- [[2026-11-23-official-means-pokemon-sprites]]
- [[2026-11-23-sprite-overlaps]]
- [[2026-11-23-remove-field-layers]]
- [[2026-11-23-name-showdown-game-review]]
- [[2026-11-23-publish-answers]]
- [[2026-11-23-local-app-not-hosted]]
- [[2026-11-23-publish-model]]
- [[2026-11-23-bigger-vgc-sprites-and-design-audit]]
- [[2026-11-23-design-audit-codex-claude]]
- [[2026-11-23-audit-fixes-go-sprite-project-official]]
- [[2026-11-23-open-questions-2-to-5]]
- [[2026-11-22-second-brain-guide]]
