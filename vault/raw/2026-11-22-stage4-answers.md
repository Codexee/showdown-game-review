---
title: Stage 4 answers (review screen)
type: raw
date: 2026-11-22
source: question tool in session 15119347
---

# Stage 4 answers (raw)

Do not edit. Applied in [[ADR-0011-review-screen-battle-view]], [[visual-style]] and [[spec-review-app]].

1. **Q:** SpriteCook (the pixel-art plugin) isn't installed. How should I handle the pixel art for the review screen? Options: Build now, SpriteCook later (recommended) / Wait for SpriteCook.
   **A:** "Build now, SpriteCook later (Recommended)"
2. **Q:** How should the battle itself be shown on the review screen? Options: Our own turn-by-turn view (recommended): a Gen 4–5 style battle box drawn from our parsed state, with sprites, HP bars, status, field and that turn's events as text, stepping turn by turn in sync with the eval bar and graph, and working offline (sprites cached locally) / Embed Showdown's replay player.
   **A:** "Our own turn-by-turn view (Recommended)"
3. **Q:** Run /frontend-design first to settle the visual direction (palette, type, layout) before building?
   **A:** "Yes, run /frontend-design (Recommended)"
