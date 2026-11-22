---
title: Research findings from the planning session
type: raw
date: 2026-11-22
source: tool output in the main planning session (transcript f510bfb3), copied out on 2026-11-22
---

# Research findings (raw)

Do not edit. Synthesized into [[formats]], [[data-sources]], [[bot-landscape]] and [[environment]].

## Hardware and tools (checked with shell commands)
- Apple M5 Pro, 16-core GPU, 24 GB memory (25769803776 bytes), 15 CPU cores reported by `hw.ncpu`, macOS 26.5.1.
- Disk: 926 GiB total, 496 GiB free.
- python3 3.14.6 (Anaconda at /opt/anaconda3), no python3.11 or 3.12 on PATH. uv 0.13.9, conda 26.5.3, node v24.18.0, npm 12.2.1, git 2.50.1, gh 2.102.0, codex-cli 0.169.0, Homebrew 7.0.14.
- PyTorch not installed (`ModuleNotFoundError: No module named 'torch'`).
- On AC power at the time.

## Showdown formats (from `config/formats.ts` on smogon/pokemon-showdown master)
Champions section contains: [Gen 9 Champions] Random Battle, OU, UU, Doubles, BSS Reg M-C, BSS Reg M-B, Random Doubles Battle, VGC 2026 Reg M-C, VGC 2026 Reg M-C (Bo3), VGC 2026 Reg M-B, VGC 2026 Reg M-B (Bo3), Custom Game, Doubles Custom Game, 4v4 Doubles UU.

```
name: "[Gen 9 Champions] Random Battle", mod: 'champions', team: 'random', bestOfDefault: true,
ruleset: ['Obtainable', 'Species Clause', 'Cancel Mod', 'Sleep Clause Mod', 'Illusion Level Mod', 'Level Clause Mod'],

name: "[Gen 9 Champions] OU", mod: 'champions', ruleset: ['Standard'],
banlist: ['AG', 'Uber', 'Moody', 'Damp Rock', 'King\'s Rock', 'Light Clay', 'Quick Claw', 'Baton Pass', 'Last Respects', 'Shed Tail'],
```

## Smogon usage stats (smogon.com/stats)
- Latest month available: 2026-10. Months listed include 2026-07 through 2026-10.
- Champions files present for 2026-10 include `gen9championsou-{0,1500,1630,1760}.txt`, `gen9championsvgc2026regmc-{0,1500,1630,1760}.txt`, `gen9championsbssregmc-*`, `gen9championsuu-*`, `gen9championsmegaevolutionbattle-*`.
- gen9championsou-1500 total battles: 2026-08: 94,600; 2026-09: 145,642; 2026-10: 106,694.
- Species at ≥1.5% usage in gen9championsou-1500, 2026-10: 66.
- Top of the 2026-10 gen9championsou-1500 list: Corviknight 39.56%, Garchomp 36.37%, Samurott-Hisui 28.28%, Slowking-Galar 21.78%, Glimmora 19.06%, Rillaboom 16.68%, Excadrill 15.61%, Kingambit 15.25%, Golisopod-Mega 14.96%, Dragapult 14.42%, Hatterene 13.95%, Sneasler 13.34%, Primarina 12.89%, Rotom-Wash 12.85%, Aegislash 11.27%, Volcarona 11.13%, Cinderace 10.67%, Absol-Mega-Z 9.96%, Garchomp-Mega-Z 9.69%, Clefable 9.59%.

## Replay API
- `https://replay.pokemonshowdown.com/search.json?format=gen9championsou` returned 51 replays per page with `uploadtime` fields. Sample ratings: 1018, 1440, 1470, 1391, 1351, 1176, 1210, 1197.
- Paging back 3,000 public replays reached 2026-11-12 (about 10 days).
- Python `urllib` with its default user agent got **HTTP 403 Forbidden**. `curl` worked.

## Bots (GitHub API, 2026-11-22)
- pmariglia/foul-play: pushed 2026-10-12, 385 stars. Has `tests/test_champions.py`; `fp/format_spec.py` treats Champions as its own generation (`gen9champions`). Uses poke-engine (Rust; must be built from source with a generation feature flag). README examples use `--pokemon-format gen9randombattle`. Singles only.
- hsahovic/poke-env: pushed 2026-11-15, 541 stars. Champions appears only in `fixture_data/teams.json` in code search.
- UT-Austin-RPL/metamon: pushed 2026-07-23, 149 stars. No Champions support found. README: datasets of 5M+ reconstructed human trajectories and 20M+ self-play; checkpoints on Hugging Face `jakegrigsby/metamon`; needs `amago`; tested on Linux, Python 3.10+. Paper: "Human-Level Competitive Pokémon via Scalable Offline RL with Transformers" (RLC 2025, arXiv 2504.04395).
- davidemodolo/alphamon: "transformer-based Pokemon Showdown doubles AI that combines autoregressive policy/value modeling with Monte Carlo rollout search, trained on large-scale replay data." Updated 2026-11-07.
- prayush-sinha/pokemon-showdown-bot (FutureSight AI): simultaneous expectiminimax, Set-Transformer policy pruning (ONNX), inverse damage calcs, Smogon priors.
- taylorhansen/pokemonshowdown-ai: RL, Gen 4 random battles only.

## Plugins and skills search
- Plugin search for pixel art (2026-11-22, this session): **SpriteCook** ("Generate sprites, cohesive UI kits, textures, and short animations in Claude with SpriteCook's guided game-art workflows."). Skills: generate-sprites, build-ui-kits, animate-assets, generate-tilesets, use-presets, workflow-essentials, plus an MCP server. Not installed. Community publisher.
- Skill search for "pixel art", "sprite", "retro ui": no results.
