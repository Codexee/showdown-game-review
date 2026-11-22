---
title: Prior art: Jaxcalibur and mikumiku37 writeups
type: raw
date: 2026-11-22
source: https://jaxcalibur.github.io/ (read in full); Smogon thread https://www.smogon.com/forums/threads/3789199/ (posts #1–#21, read via web fetch); pkmn.ai/projects; search results
---

# Jaxcalibur and mikumiku37 (raw)

Do not edit. Synthesized into [[benchmark-best-in-class]]. Requested by the user on 2026-11-22.

## Jaxcalibur (Gen 9 Random Battle, our first format)
- Writeup: https://jaxcalibur.github.io/ ; Smogon thread "Jaxcalibur: A Gen 9 Randbats bot that reached #1 on the ladder" (3787537). Code and weights **not released** (author asking the community, citing cheating concerns).
- **Results:** on the gen9randombattle ladder Aug 6–27, 2026; top of the ladder ~20% of the time; **68% win rate vs other top players; peak 2557 Elo, peak GXE 95.3.** Foul Play peaked ~2341 Elo / 88 GXE (≈ top 50). One human (MichaelderBeste2) was on top 50% of the time, GXE 95.5.
- **Network:** 8.5M-parameter non-causal transformer, pre-RMSNorm, position-based mixture of experts (different MLP weights for Pokémon, move, event... positions). Tokens: 1 field; 2 active Pokémon (stats, moves, damage calcs); 5 candidate moves (+ Struggle); 6 own team; 6 opposing team (masked if unknown); **16 history tokens (last 16 game events: moves / switch-ins)**; **24 matchup tokens** (damage calcs for Pokémon pairs; each own Pokémon vs 4 opponents), concatenated halfway through the network so they benefit from fresh set predictions. Action logits: switch per team slot; two per move (move, Tera + move).
- "Smaller networks trained for longer outperformed larger networks trained for fewer steps" (one GPU; no full scaling study).
- **Training:** pure self-play PPO + GAE, reward 1 win / 0 loss, undiscounted; entropy bonus + a **zero-avoiding term** (KL toward uniform) so situational moves (Encore) keep some probability. **Auxiliary losses:** win probability (the value function); **each opposing Pokémon's item, ability, moves and Tera type** (kept across turns to remember reveals); **the opponent's next action** ("made the bot substantially stronger"). No search during training. ≈ one week on one H100, ≈100M self-play games.
- **Engine:** Pokémon battling reimplemented in pure JAX (vmap + jit on GPU); every step type is executed and masked so batches share structure. Built with Claude Code's help.
- **Search (test time only):** AlphaZero-style pUCT adapted: edges sampled ∝ max(Q−V, 0) + c·P/√N (tends to regret matching); no explicit tree, a dict {state hash → node}, HP binned into 10 buckets; every trajectory re-rolled with a new seed; **hidden info: sample "worlds" of the opponent's unknown sets from the network's predictions** (like Foul Play); opponent search truncated after a "surprising" own action (switch to unrevealed, move <65% likely) to avoid leaking hidden info. Depth 4 (≈2 turns), 20,480 rollouts over 32 worlds, a few seconds on a GPU. **Search adds ≈100–150 Elo; most strength is the network.**

## mikumiku37 (Champions VGC 2026 Reg M-C, our second format)
- Smogon: "mikumiku37: a self-play VGC bot reached #1 on the VGC Reg M-C ladder" by Shao, first post Oct 2, 2026. Weights and engine **not released** (laddering / tournament concerns); a technical writeup "coming up soon" (none linked as of Oct 28).
- **Results:** #1 on Oct 1, 2026 at **1857 Elo, 81.2% GXE, 1775 ± 25 Glicko**, in its 358th game; 248–110 (69.3%). Bo1 only; open team sheets supported. Without search the same network peaked at 1747 over 100 games. Anecdotes: top players found it "fundamentally sound" with some odd plays; exploitable patterns reported (never predicting a plain Kingambit attack; Perish team wins before a search bug fix).
- **Network:** ≈8.7M-parameter transformer from scratch. Inputs: its own-side view of the battle **plus static dex data (types, base stats, move data)**; **no damage calculator, usage stats or speed resolver**. Policy + value heads (no other heads mentioned). Doubles action: each slot's action includes its target; **slot 2 predicted conditioned on slot 1 through a pairwise term**, with legality masks on the pair.
- **Training:** PPO from scratch, **no human replays, terminal reward only**; league: ≈half games vs current policy, rest vs past snapshots weighted toward opponents it struggles with (PFSP-style; no ablation vs pure self-play). Teams: ≈1,260 public tournament teams (Reg M-B and M-C), some spreads guessed; ladder runs rotated the 10 best teams from training. ≈330M training games, **48.3 h on one RTX 5090**; 8,192 parallel battles × 32 steps per update; ≈100k steps/s collection; GPU compute-bound on learning. "Doesn't appear to be anywhere near saturating."
- **Engine:** custom **Rust** simulator, ≈650× faster than Showdown, ≈7k random battles/s on one core. Earlier, text-parsing Showdown gave ≈700 battles/min and used ≈0.5% of the GPU.
- **Search:** one-turn, AlphaZero-style: **16 sampled worlds; payoff table of top-8 joint actions × top-8 replies; each cell steps the real engine with several RNG seeds; value net averaged over seeds and worlds; matrix solved by regret matching, blending worst case with expected value.** 4 seeds gave nonsensical plays; 16 used; **64–128 seeds ideal**. Endgame deepening not significant.

## Others mentioned
- Nessie123 (VGC Bo3 ladder #1; Smogon thread 3789213), MysteriousWind, eevenator (pkmn.ai/projects lists them as active 2026 custom-engine projects). Not read.
- Community commentary (Candy, note.com): using such bots in tournaments is "a no-go"; verification and sparring uses could be valuable.
