---
title: Session log 2026-11-22
type: log
date: 2026-11-22
tags: [area/vault]
---

# Session log: 2026-11-22

- **Main planning session** (transcript f510bfb3): found local Showdown bots; copied 33 skills from PatriotHacks into `.claude/skills/`; added the every-prompt skill hook; checked hardware; researched Champions formats, Smogon stats, replay API and bots ([[2026-11-22-research-findings]]); ran interview round 1 ([[2026-11-22-interview-round-1]]).
- **Side session** (transcript 8ebed2c6, forked): explained why a web app comes before an extension. Reasoning now in [[ADR-0001-local-web-app]].
- **This session** (transcript 15119347): the user sent the input answer they had skipped by accident, plus the pixel-art request and the second-brain guide. Recovered the round-1 answers and research from the main session's transcript, because the new session did not have them. Built this vault, wrote ADR-0001 to ADR-0006 and the three specs, searched for a pixel-art tool (found SpriteCook), ran `git init` and made the first commit.

- **Same session, later:** interview rounds 2 and 3 ([[2026-11-22-interview-round-2]]). Settled: standard Gen 9 Random Battle; save every finished game from now on, with no backfill, private games included; list all formats; URL, file and team-paste input; keep 1.5% for VGC; FastAPI + Vite/TS. Accepted [[ADR-0006-replay-archive]], added [[ADR-0007-app-stack]]. What's left in [[open-questions]] is mostly research.

- **Research round 2** ([[2026-11-22-research-round-2]]): solved all four research items from the open questions. Big find: random-battle replays include an inputlog with seeds and the Showdown commit, so full hidden information may be rebuildable ([[ADR-0009-randbats-full-info-reconstruction]], proposed). Added [[ADR-0008-python-313]].

- **Stage 2a built** ([[module-map]]): uv venv on 3.13; FastAPI backend (archive, poller, imports, API); Vite/TS game list page; 18 tests pass. Fixed a team-parsing bug ([[2026-11-22-bug-forme-change-team]]). Live check: the profile loaded (most-played: gen8randombattle, gen9randombattle), the first sync set the archive start to 2026-11-22 06:37, and two older games were added by URL. Codexe's newest upload is a Champions VGC Reg M-C game.

- **Stage 2b built:** userscript plus ingest routes, an install panel in the app, and [[ADR-0010-local-api-origin-guard]]. Fixed two problems found while designing: the poller stopped at the first known game, which would hide uploads once the userscript adds games first (now a high-water mark, with a regression test); and uploaded `.json` ids could escape `data/` (now validated). 27 Python + 7 Node tests pass; an end-to-end run against a throwaway server worked. Not yet run on the real Showdown site.

- **Rebuild prototype** ([[2026-11-22-rebuild-prototype-results]]): 61/61 `gen9randombattle` replays rebuilt exactly at their commit; a wrong commit gives visible and silent errors. The user accepted ADR-0009 ([[2026-11-22-adr-0009-decision]]). Also fixed `parse_replay_ref` to accept side-server ids (`impulse-…`, `smogtours-…`).

- **Stage 3 built** ([[battle-parser]]): log parser + per-player view + `/turns` API, graded against Showdown's simulator: 99.4% of turn states exact on 100 unseen games, 100% on all 261 after fixes ([[2026-11-22-parser-accuracy-results]]). Doubles (VGC) parse plausibly but are unverified.

- **Stage 4 built** ([[spec-review-app]], [[visual-style]], [[ADR-0011-review-screen-battle-view]]): the user chose our own turn-by-turn view, CSS pixel art now with SpriteCook later, and a /frontend-design pass ([[2026-11-22-stage4-answers]]). DS two-screen review layout, placeholder eval, cached sprites, games page restyled. Pixelify Sans was dropped for DotGothic16 after the screenshots showed 5 reading as S. Checked in the browser: singles and doubles, light and dark, phone width, keyboard. 68 Python tests.

- **Stage 5 pipeline built** ([[spec-eval-model]], [[ADR-0012-training-data-v1]], [[2026-11-22-training-test-runs]]): 2.0M-game HF dataset downloaded; inputlog collector running (14 days); rebuild pipeline (1,283/1,283 exact after ignoring `|error|` lines); features, model, training, export, app integration. Test model `test2` installed: 66% vs 64% placeholder on future games. The first test model lost to the placeholder until per-side totals were added. Overnight run waiting for the user's go.

- **Prior-art research** ([[2026-11-22-prior-art-research]], [[benchmark-best-in-class]]): PS Dashboard is the bar (simulator search, calibrated win%, 5/10/20 regret bands, decision vs luck, paired bootstrap gate, engine protocol); ps-ppo (1900+ randbats Elo) shows property features, priors and last-turn events. Ranked gaps P0–P2; P0 waits on the user. Also fixed: the review page scrolled on every turn step (`scrollIntoView` scrolled the window).

- **Jaxcalibur and mikumiku37** ([[2026-11-22-prior-art-jaxcalibur-mikumiku]]): the #1 bots in our two formats, both ~8.5M-param self-play transformers on custom fast engines, with one-ply / pUCT search over sampled worlds. P0 gains auxiliary heads and a smaller model; stage 6's matrix-over-worlds plan is confirmed; self-play needs a fast engine. Added [[ADR-0013-post-game-analysis-only]].

- **P0 done** ([[2026-11-22-p0-ab-results]]): dex property tables, randbats priors, last-turn events, opponent-choice and hidden-set heads, smaller model, temperature, by-phase / bootstrap / 1500+ metrics, pinned bank, paired gate. p0 beats test2 on future games (log-loss −0.011 [−0.018, −0.004]; late game −0.040) and is installed. Found the train/test rating gap (median 1676 vs 1427).

- **Main run** ([[2026-11-22-main-run-results]]): 672k games / 15.8M samples; stopped at epoch 2.7 (value overfitting after 1.2); step-9000 model beats p0 in every slice and is installed: 67.4% vs 62.9% placeholder on future games.

- **Stage 6 built** ([[ADR-0014-move-review-method]], [[2026-11-22-stage6-results]]): a Node sim service replays the inputlog and plays every top-K choice pair from each turn start; the value head scores the leaves; regret matching+ solves the matrix; 5/10/20 bands, per-turn luck, Lichess accuracy; background jobs and a review UI. Test game: Codexe 93.2 vs 96.6, one mistake (T18 switch to Venusaur, −14.6). Fixed a snapshot-mutation bug, played-choice format, and an ignored request body. 91 Python tests. Limit: grades use the real hidden sets ([[open-questions]] #6).

- **Collector crash:** the 14-day inputlog crawl stopped at 16,700 replays (2026-11-10 11:15 UTC) on one connection reset. Cause: the Mac was asleep with the lid closed on battery, waking for 2 s every 16 min. Added retries with backoff and resumed it; it needs the lid open to finish ([[environment-quirks]]).

- **Sampled worlds** ([[ADR-0015-move-review-sampled-worlds]], [[2026-11-22-worlds-vs-perfect-results]]): move review now grades each player over 16 sampled versions of the opponent's hidden set parts (randbats role data), with a matrix per world; luck stays in the real game. On 12 games, 79% of verdicts match the real-set grading and 6% of flags change, about 3× the sampling noise. 95 tests.
- **Collector finished:** 14-day crawl done, 18,975 replays with inputlogs in `data/train/inputlog`.

- **Next training run planned** ([[plan-run-v12]]): the user asked for a plan. Levers: add 2025 games (563k), dropout/wd, value-loss schedule; four 4-epoch tests on `medium` first, then a 9 h run. Waiting for the go-ahead. The user said go: tests started detached ([[2026-11-22-v12-tests-go]]). Correction: the first run started at 22:41:53 per `data/models/v12tests.log`, not about 22:20 as that raw note says.

## Lesson
Facts that exist only in a chat transcript are easy to lose when a question is skipped or work moves to a new session. Write answers to `raw/` as soon as they arrive ([[ADR-0003-vault-as-memory]]).

## Next
- User: install the userscript and play one game ([[open-questions]] #1).
- Next: fix value overfitting in the next training run (now with 18,975 inputlog replays); consider sampling unseen opposing species in move review.
- Then: stage 7, VGC Reg M-C.
- 23:50 EST: status check. v12a done (best val value 0.5707 at step 3600, epoch 2.3; then up to 0.5818 at epoch 4; pinned bank log-loss 0.6008). v12b at step 5200, best so far 0.5696 at 3600. The Mac is on AC power now. The user's direction (Codex review, VGC picks, usage stats, VGC team import in the UI stage, stay on model testing) is in [[2026-11-22-direction-codex-review]] and [[roadmap]]. Codex review started (read-only).
- 00:15 EST (2026-11-23): Codex review finished ([[2026-11-23-codex-review]]). Checked: overnight gate bug, two-view gain (−0.00258 on `main`), compare_runs key intersection. Proposed changes in [[plan-run-v12]]; waiting on the user ([[open-questions]] #6).
- 00:20–00:45 EST (2026-11-23): Codex fixes 1–3 built ([[ADR-0016-two-view-scoring-strict-gate]]): two-view bar, test report and gate; strict pairing; overnight script safety (new run name, dated dataset check, install only if better, dry run). Checked: dry runs refuse RUN=main, refuse an existing run, refuse a dataset with other dates, and keep `main` when B is worse; bar equals the grader leaf on Codexe's game; 97 tests pass. Two-view A vs B: no difference (0.59736 vs 0.59734).
- 03:05 EST (2026-11-23): v1.2 tests done and eval-gain tests done ([[2026-11-23-v12-tests-and-eval-gains-results]]). C beats B, D beats B and C; all trail `main`. One-turn search blend beats the network by 0.0083 (fair worlds mode). Ensembles, calibration, symmetry and rating gap: no gain. Custom-rule games found ([[2026-11-23-bug-custom-rules-randbats]]). Overnight run and search-based bar wait on the user ([[open-questions]] #9, #10).
- 03:25 EST (2026-11-23): search-blended eval bar built ([[ADR-0017-eval-bar-search-blend]]); 98 tests pass; checked in the app on Codexe's game (re-analysed in worlds mode; bar, graph and method text switched to the blend; no console errors). Server restarted via the preview tool. Fresh 100-game check of the weight running (`data/models/search_eval/worlds-fresh.jsonl`).
- 03:56 EST (2026-11-23): overnight script smoke-tested on `small` (settings passed, gate said worse, `main` kept); overnight run `v12` started (since 2025-01-01, dropout 0.2, wd 0.1, value floor 0.2, 3 epochs, 9 h). Endgame goals recorded ([[goals-endgame]]).
- 04:25 EST (2026-11-23): user adopted "grade quality, then UI" after `v12` ([[ADR-0018-grade-quality-before-ui]]); roadmap reordered; [[plan-grade-quality]] drafted. `v12` training at 0.61 s/step, about 7 h.
- 2026-11-23: desktop one-screen layout for the review screen (user request, [[2026-11-23-desktop-one-screen-layout]]). Checked with no page scroll at 1440×900, 1366×650, 1920×960 (doubles), light and dark; phone width stacks with no sideways scroll; arrow keys scroll the turn list inside its panel. `index.html` now `no-cache` (a stale cached page loaded the old UI once). 98 tests pass.
