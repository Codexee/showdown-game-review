---
title: Interview round 1 (questions and answers)
type: raw
date: 2026-11-22
source: main planning session (transcript f510bfb3) plus the user's follow-up message in session 15119347
---

# Interview round 1: raw questions and answers

Do not edit. Synthesized into [[project-overview]], [[ADR-0001-local-web-app]], [[ADR-0002-format-order]], [[ADR-0004-pixel-art-style]], [[ADR-0005-overnight-training-budget]] and [[spec-replay-sync]].

## Earlier requests from the user (same day, before the interview)

> i want to make an analysis tool for pokemon showdown that lets me analyze replays similar to lichess's feature. use documentation of cutting edge pokemon neural networks (found on github and smogon forums) in addition to poke-env to make a powerful bot for vgc using the same process that they do. then, let the bot interface with pokemon showdown replays and show eval bars.

> ... train the network on local machine to save usage (test small scale training and then run the full training without too much interaction to save usage). remember that the target format is champions ou. focus on training on the highest usage pokemon and moves. realistically anything below 1.5% usage is not too relevant

## Questions asked (round 1)

1. **Format.** Showdown's [Gen 9 Champions] OU is a 6v6 singles format with Mega Evolution, not VGC (doubles). Which format is the target? Options: Champions OU singles (recommended) / Champions VGC Reg M-C / Both, OU first.
2. **Train time.** How long can the Mac train without you, in one run? Options: Overnight 8–12 h (recommended) / A weekend 24–48 h / 2–4 h sessions.
3. **UI.** Where should the review tool run? Options: Local web app (recommended) / Overlay on Showdown's site / Both.
4. **Input** (multi-select). How do you want to load a game to review? Options: Paste a replay URL (recommended) / Upload a saved log or HTML file / Add my own team paste / Pull my recent games by username.

## Answers as recorded by the question tool

- Format: "try gen9 randbats, then vgc m-c."
- Train time: "Overnight, 8–12 h (Recommended)"
- UI: "Local web app (Recommended)"
- Input: "[No preference]" (the user says this was an accidental skip)

## Follow-up message from the user (correcting the skip)

> i clicked skip by accident.
> > Where should the review tool run? Local web app, make it a bit more aesthetic than showdown (gen4-5 pixel art style, find and use a pixel art skill for when we get to this)
> > Should pull user data and list each game with some details, and also auto save all replays.

The same message asked for this vault. See [[2026-11-22-second-brain-guide]].
