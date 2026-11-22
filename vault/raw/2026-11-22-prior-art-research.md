---
title: Prior art research (similar tools, models, papers)
type: raw
date: 2026-11-22
source: web searches, GitHub API and repository docs read in session 15119347
---

# Prior art research (raw)

Do not edit. Synthesized into [[benchmark-best-in-class]].

## PS Dashboard (closest analogue; the benchmark)
- https://github.com/FullLifeGames/PSDashboard (MIT, TypeScript/React; created 2026-06-26, pushed 2026-11-22; 3 stars). Smogon thread: https://www.smogon.com/forums/threads/ps-dashboard-a-chess-engine-for-your-showdown-replays.3790619/ . Hosted: fulllifegames.com/Tools/PSDashboard. Same author as Showdown Replay Scouter and BattleHelper. Much of the code written with AI help (author's statement).
- Features (README): load URL / id / private pw / smogtours / .html / raw log; both teams with every field labelled **revealed / sheet / guessed / manual**; hidden info from usage stats (data.pkmn.cc) and Smogon sets, **EV spreads fitted to observed damage**, Choice Scarf inferred from move order; **search on the real simulator** over every legal choice pair, matrix solved as a zero-sum game by regret matching; depth 1 / depth 2 / MCTS (DUCT); **win probability calibrated on real outcomes**; `Analyze game` graph; turn verdicts; decision vs luck split; report with accuracy scores, key moments, "biggest roll"; play your own line from any turn (variations); edit/import sets; embed (deep link, `?embed=1`, postMessage); **engine protocol `ps-dashboard-engine/1` over HTTP** so outside engines/models evaluate positions; report-issue with state file. Covers singles, doubles, VGC, Champions. Needs the network (viewer and sprites from Showdown).
- EVALUATION.md, key points:
  - Chance priced by outcome classes (hit-nokill, miss, hit-kill, +burn…) with accuracy/kill odds from `@smogon/calc`, secondaries from the simulator.
  - Score in win-probability units: one sigmoid fitted to real outcomes at the leaf; **phase-aware** (claims more per point of edge as Pokémon faint); shown percentages pass a **second calibration stage** fitted on the corpus and checked out of sample. Race and endgame terms; a **forced-win prover** on small boards; an exact **endgame solver** (≤3 Pokémon a side) used as truth to grade estimators.
  - Static weight tables per rule set, fitted on a pinned corpus of **~5,600 tournament and ladder games**; a third of doubles/Champions games held out.
  - **Verdict bands on equilibrium-EV regret in win probability: inaccuracy 5 points, mistake 10, blunder 20.** Soften one tier once a side is at ≥85%. Every flagged mistake/blunder re-searched one depth deeper: "can acquit a move, never convict it". Sacrifice and stay-in rules; full paralysis/sleep/flinch = no blame. **Sensitivity probes**: if a plausible hidden item flips the verdict, soften and say so ("a grade that depends on hidden information is not a grade"). Optional "Read" line from a softmax opponent model (advice, not grade).
  - Report: chess-style **accuracy per player, volatility-weighted**; **net luck**, decided-game resolution kept apart from luck; "biggest roll" with both chances.
  - Measurement: changes pass a **paired gate** (old vs new engine on the same bank positions; paired Brier and log-loss deltas with a **90% bootstrap band over replays**; pooled rows decide, phase cells warn); calibration bank of 130 pinned replays with sign accuracy, confidence calibration, per-phase Brier, an `hq` line (tournament + 1700+ ladder) and a luck-adjusted line; an expert-feedback drift suite.
  - Known limits: hidden info guessed; branches can diverge; not self-contained offline.
- Engineering: 22 ADRs, AGENTS.md/CLAUDE.md, lint ceilings (300 lines/file, 60/function, complexity 15) with a shrink-only ratchet, import-zone lint, knip, Vitest + Playwright e2e + build smoke, CI on every push, published npm packages (replay-core, eval-engine) with provenance.

## ps-ppo / PokemonTransformer (Nebraskinator)
- https://github.com/Nebraskinator/ps-ppo (MIT, created 2025-12, pushed 2026-07). Gen 9 Random Battle. Behavioural cloning from poke-env heuristic bots, then PPO self-play (>250M states, 2 days on an RTX 3090). Reports **>85% vs SimpleHeuristicsPlayer and >1900 Elo on the Gen 9 Random Battle ladder**, no tree search at inference.
- State: 1 field token + 12 Pokémon tokens (plus separate actor and critic CLS tokens, attention-masked so state tokens can't see them). Per Pokémon: species/item ids, **possible ability ids (4)**, move ids, **move scalars (base power, accuracy, PP, type, category, priority)**, **base stats**, types multi-hot, boosts one-hot, status, volatiles; **"number banks"** (HP%, level, accuracy, stats, BP as embedded integers); weather duration two-hot; **previous-turn transition flags** (who moved first, crits, super-effective, moves used); 14-action mask (4 moves, 6 switches, 4 Tera+move). Value head: **51-bin categorical (distributional)**. Pre-LN transformer, GELU.

## Metamon (UT-Austin-RPL)
- https://github.com/UT-Austin-RPL/metamon (pushed 2026-07-23). Paper arXiv 2504.04395 (RLC 2025). 5M+ reconstructed human trajectories + 20M+ self-play. Actor-critic transformers up to 200M params; "value classification". Gen 1–4 OU + Gen 9 OU; best public model Kakuna; TaurosEnsemble #1 on the Gen1OU human ladder. Earlier paper reported Gen 4 Random Battle 1756 Glicko / 79.5% GXE. PokéAgent Challenge benchmark: arXiv 2603.15563 (2026).

## Other projects
- **Hindsight** (influxtion, Chrome extension, pushed 2026-06): momentum graph = remaining team HP (unseen = healthy) adjusted for hazards (scaled by Pokémon left), status (burn by physical lean, paralysis by base Speed), boosts, screens/Tailwind, weather/terrain/Trick Room credited to setter, item loss, faint penalty, active type matchup, observed speed edge; hover shows factor breakdown. **Luck ledger**: every provable chance event (crits, misses, full para, flinch, sleep/freeze turns, confusion, secondaries) weighted by improbability × swing; accuracy credits both ways so playing to the odds nets zero.
- **Showdown Luck Analyzer** (influxtion): generation-correct probabilities (accuracy modifiers, crit rates per gen), significance test (p-value, z-score) on net luck.
- **Pokémon Battle Predictor** (aed3; active 2020-04 → 2023-09, unmaintained): TensorFlow.js extension, models trained on 2M+ battles, win chance on live battles and replays; author reported ~8% 95% CI; a side-swap bug once flipped replay percentages.
- **alpha-poke** (freiz; found in search, repo now 404): Gen 9 OU, tree search over hidden sets + 742k-param transformer (move prior + win prob) + a game-review app; claimed 71.7% winner prediction on held-out positions. Unverified.
- **FutureSight AI** (prayush-sinha): simultaneous expectiminimax + Set-Transformer pruning (ONNX), inverse damage calc, Smogon priors.
- **PokaiTrainer** (arXiv 2608.29197, 2026): belief-state equilibrium search for VGC, 72–74 GXE on the live ladder. **VGC-Bench** (arXiv 2506.10326).
- Older Smogon threads: neural net predicting battle results (2018, in progress), Replay Analyzer (claduva; singles, not randbats), Chinchow Battle Analyzer (Gen 7–8 standard), Random Battles winrates (monthly stats), Unluckiest Player of the Week.
- **@pkmn/client** (pkmn/ps, MIT): protocol battle-state tracker forked from Showdown's client; **@pkmn/engine** (Zig, fast sim).

## Lichess conventions
- Win% = 50 + 50·(2/(1+e^(−0.00368208·cp)) − 1); accuracy from win% drops (harmonic-mean style aggregation reported by users); review labels on win-chance drop: **inaccuracy 10, mistake 20, blunder 30** (community quotes of the source; a regression on Lichess games). https://lichess.org/page/accuracy
