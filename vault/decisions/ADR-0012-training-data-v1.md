---
title: ADR-0012 Training data and inputs for eval model v1
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model, area/data]
---

# ADR-0012: Model v1 trains on public replay logs from a Hugging Face dataset, using the public view

## Context
- ADR-0009 plans training on games rebuilt to full information from inputlogs. Only replays fetched from Showdown's API have inputlogs, and Showdown uploads about **34 public `gen9randombattle` replays per hour** (measured on 256 recent replays, 2026-11-22). Fetching a large set at a polite 1 request/s takes days.
- **HolidayOugi/pokemon-showdown-replays** on Hugging Face has **2,012,698 `[Gen 9] RANDOMBATTLE` replay logs** (99.5% main server; 2022-12 to 2026-10-05; about 575k from 2026-03 on). It has `log` but **no `inputlog`** (schema checked 2026-11-22), and no license is stated. It was published so people don't have to re-download from Showdown.
- The review screen gets the public view of a game (your own full team is usually not attached).

## Decision
- **Model v1 trains on the Hugging Face logs**, recent months only (`--since`), main-server ids only.
- **Input = the public view** at each turn start: everything both players could see, from one player's side. This is what reviewing any game gives, so training and use match.
- **Targets:** value = that player won; policy = the move or switch they chose (pivot switches, post-faint switches, called moves and `|cant|` turns are not choices).
- **Test set = future games:** replays collected from Showdown's API with inputlogs for the 14 days before 2026-11-22, all after the dataset's cutoff. They also feed the full-information rebuild ([[ADR-0009-randbats-full-info-reconstruction]]), which v1 uses for testing only.
- **Full-information targets (ADR-0009) move to model v2:** e.g. an auxiliary head that predicts the opponent's hidden sets, trained on the rebuilt games.
- Vocabulary (species, moves, items, abilities, types) comes from Showdown's data files (`training/vocab.json`), not from counting the training set.

## Options considered
- **Scrape Showdown only:** full-information data, but days of requests for a few tens of thousands of games.
- **HF logs only, public view (chosen for v1):** 100k+ games available now; matches how the model is used.
- **HF logs with guessed full information:** not possible without inputlogs.

## Consequences
- The HF dataset's license is unknown; it is used locally for training only and not redistributed.
- Usernames are in the dataset; they are not features and are never shown.
- v1 says nothing about hidden sets; it scores positions from public information.

## Related
- [[spec-eval-model]] · [[ADR-0009-randbats-full-info-reconstruction]] · [[ADR-0005-overnight-training-budget]] · [[data-sources]]
