---
title: "Bug: sim snapshot mutated by deserializeBattle"
type: log
status: fixed
date: 2026-11-22
tags: [area/model]
---

# Bug: sim snapshot mutated by deserializeBattle

## Symptom
While building move review, 1,319 of 1,352 simulated cells came back invalid (choices rejected), though the same choices were legal when the replay was played ([[2026-11-22-stage6-results]]).

## Root cause
Showdown's `State.deserializeBattle(state)` changes the object it is given while it rebuilds the battle. `tools/review-engine.cjs` kept one parsed snapshot per turn and passed the same object to every cell, so only the first cell started from a clean state.

## Fix
Store each turn-start snapshot as a JSON string (`JSON.stringify(State.serializeBattle(battle))`) and pass the string to `deserializeBattle` for every cell, so each cell parses a fresh copy. Committed with stage 6.

## How to spot it next time
If the first cell from a snapshot works and later ones fail, suspect shared mutable state. Never reuse a deserialized or parsed sim object across runs.

## Related
- [[environment-quirks]] · [[ADR-0014-move-review-method]] · [[module-map]]
