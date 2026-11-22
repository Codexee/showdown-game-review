---
title: Project overview
type: wiki
status: active
tags: [area/vault]
updated: 2026-11-22
---

# Project overview

## Goal
A review tool for Pokémon Showdown games that works like Lichess's game analysis. ([[2026-11-22-interview-round-1]])

- A neural network, trained on this Mac, scores each turn. The app shows the score as an **eval bar** (win chance now) and an **eval graph** (win chance over the game).
- The method follows current open-source Pokémon networks found on GitHub and the Smogon forums, built on poke-env. See [[bot-landscape]] and [[spec-eval-model]].
- The app is a **local web app** ([[ADR-0001-local-web-app]]) in a **Gen 4–5 pixel-art style**, a bit nicer to look at than Showdown ([[ADR-0004-pixel-art-style]]).
- It **pulls your user data by username, lists each game with details, and saves every replay locally** ([[spec-replay-sync]]).

## Format order
1. Gen 9 Random Battle first, then
2. [Gen 9 Champions] VGC 2026 Reg M-C (doubles).

This replaces the earlier target of Champions OU. See [[ADR-0002-format-order]] and [[formats]]. Which "Gen 9 randbats" is meant is still open: [[open-questions]].

## Constraints
- Train locally to save Claude usage. Test at small scale first, then run the full training with little interaction ([[2026-11-22-interview-round-1]]).
- One training run is overnight, 8–12 h ([[ADR-0005-overnight-training-budget]]).
- Focus training on species and moves at ≥1.5% usage. The user set this rule for Champions OU; whether it carries over to the new formats is in [[open-questions]].
- Hardware: [[environment]].

## How the project is documented
This vault is the project memory ([[ADR-0003-vault-as-memory]]). Rules: [[CLAUDE]].

## Related
- [[index]] · [[roadmap]] · [[architecture]] · [[open-questions]]
