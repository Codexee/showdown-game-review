---
title: Open questions
type: spec
status: active
tags: [area/vault]
updated: 2026-11-22
---

# Open questions

Items wait here until the user answers. When answered: record the answer in a `raw/` note, update the affected notes, and move the item to **Resolved**.

## Open

1. **Which "Gen 9 randbats"?** Standard [Gen 9] Random Battle (`gen9randombattle`) or [Gen 9 Champions] Random Battle? Recommendation: standard Gen 9 Random Battle (more games, foul-play support), unless the plan is to reuse the Champions mod for VGC M-C. ([[formats]])
2. **Does the 1.5% usage rule still apply?** It was set for Champions OU. Randbats sets come from a generator, so it mostly doesn't apply. For VGC M-C it probably does. ([[project-overview]])
3. **Your Showdown username(s)** for [[spec-replay-sync]].
4. **"Auto save all replays": which games?** The server only has games that were uploaded. Options: (a) poll your public uploaded replays by username; (b) also catch games you never upload, which needs a small browser userscript on play.pokemonshowdown.com that sends each finished battle log to the local server. (b) conflicts a little with choosing a web app over an extension ([[ADR-0001-local-web-app]]), but it is a small add-on. ([[ADR-0006-replay-archive]])
5. **Private replays.** Do you upload private (password) replays? Fetching them needs your login, and the method is unknown. ([[data-sources]])
6. **Which games to list.** Only the target formats, or every format you play? Recommendation: save every format, list all, analyze only formats with a model.
7. **Other ways to load a game** (the round-1 input question): paste a replay URL, upload a saved log/HTML file, add your own team paste. Pulling by username is chosen; the others are not decided.
8. **Python version** that PyTorch, poke-env and poke-engine all support on this Mac. Check before setup. ([[environment]])
9. **Server and frontend stack.** FastAPI plus a plain or Vite frontend is the likely pick. ([[architecture]])
10. **Install SpriteCook** when the UI stage starts? ([[tooling]])

## Resolved
- **Format target** → Gen 9 randbats, then VGC Reg M-C ([[ADR-0002-format-order]]), 2026-11-22.
- **Training time** → overnight 8–12 h ([[ADR-0005-overnight-training-budget]]), 2026-11-22.
- **Where the app runs** → local web app, pixel-art style ([[ADR-0001-local-web-app]], [[ADR-0004-pixel-art-style]]), 2026-11-22.
- **Loading games** → pull by username, list games with details, save all replays ([[spec-replay-sync]]), 2026-11-22.

## Related
- [[index]] · [[2026-11-22-interview-round-1]]
