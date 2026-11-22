---
title: Interview rounds 2 and 3 (questions and answers)
type: raw
date: 2026-11-22
source: question tool in session 15119347
---

# Interview rounds 2 and 3: raw questions and answers

Do not edit. Synthesized into [[formats]], [[ADR-0002-format-order]], [[ADR-0006-replay-archive]], [[ADR-0007-app-stack]], [[spec-replay-sync]], [[spec-eval-model]] and [[open-questions]].

## Round 2

1. **Q:** You said "try gen9 randbats" first. Showdown has two Gen 9 random formats. Which one? Options: [Gen 9] Random Battle (recommended) / [Gen 9 Champions] Random Battle / Both.
   **A:** "[Gen 9] Random Battle (Recommended)"
2. **Q:** "Auto save all replays": Showdown's server only keeps games that were uploaded. Which games should the app save? Options: Uploaded now, all later (recommended): start by polling your uploaded replays by username; later add a small userscript on play.pokemonshowdown.com that sends every finished battle to the local app, including ones you never upload / Uploaded replays only / Every game from day one.
   **A:** "do this optoin: Uploaded now, all later (Recommended) Start by polling your uploaded replays by username. Later, add a small userscript on play.pokemonshowdown.com that sends every finished battle to the local app, including ones you never upload. but don't worry about prevous games. just send every finished game to the app going frward"
3. **Q:** Which of your games should the app save and list? Options: Save and list all (recommended) / Target formats only.
   **A:** "Save and list all (Recommended)"
4. **Q (multi-select):** Besides pulling games by username, which other ways to load a game do you want? Options: Paste a replay URL / Upload a saved log or HTML / Add my own team paste / Username only.
   **A:** "Paste a replay URL, Upload a saved log or HTML, Add my own team paste"

## Round 3

5. **Q:** What Showdown username(s) should the app pull?
   **A:** "Codexe"
6. **Q:** Do you upload private (password-protected) replays that the app should also save? Options: No, public is fine (recommended) / Yes, include private.
   **A:** "Yes, include private"
7. **Q:** For VGC Reg M-C (the second stage), keep your rule of ignoring species and moves under 1.5% usage? Options: Yes, 1.5% for VGC (recommended) / Lower cutoff / No cutoff.
   **A:** "Yes, 1.5% for VGC (Recommended)"
8. **Q:** Which stack should the local app use? Options: FastAPI + Vite/TS (recommended) / FastAPI + plain HTML/JS / Your call.
   **A:** "FastAPI + Vite/TS (Recommended)"
