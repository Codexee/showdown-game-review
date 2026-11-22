---
title: "Bug: forme changes added a 7th team member"
type: log
status: fixed
date: 2026-11-22
tags: [area/data]
---

# Bug: forme changes added a 7th team member

## Symptom
In the randbats fixture, charizardslayer1's team came out as 7 Pokémon: `… Palafin, Volbeat, Glaceon, Palafin-Hero, Baxcalibur`. Caught by `test_randbats_summary`.

## Root cause
`server/logsummary.py` built teams from the species in each `|switch|` line. Palafin changes to Palafin-Hero after switching out (`|detailschange|`) and keeps that form, so later switch-ins showed a new species string.

## Fix
Key each Pokémon on its nickname within the side (`p2a: Palafin` → `Palafin`), which stays the same through forme changes, and keep the first species seen. Teams with team preview (`|poke|` lines, e.g. VGC) don't use switch-ins at all.

## How to spot it next time
Any per-Pokémon tracking in the stage 3 parser must key on side + nickname, never on species. Forme changes include Palafin-Hero, Megas, Terapagos, Minior, Aegislash, Mimikyu-Busted and others.

## Related
- [[module-map]] · [[environment-quirks]]
