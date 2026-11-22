---
title: Data sources
type: wiki
status: active
tags: [area/data]
updated: 2026-11-22
---

# Data sources

## Showdown replay server
Official notes: `WEB-API.md` in smogon/pokemon-showdown-client. Server code: smogon/pokemon-showdown-loginserver `src/replays.ts` and `src/actions.ts` ([[2026-11-22-research-round-2]]).

| Endpoint | Returns |
|---|---|
| `https://replay.pokemonshowdown.com/search.json?user=<id>&format=<id>` | Up to 51 public replays, newest first (`uploadtime`, `id`, `format`, `players`, `rating`, `private`, `password`) |
| `…&user2=<id>` | Games between two users |
| `…&before=<uploadtime>` | Next page. Use the `uploadtime` of the last result; a 51st result means another page exists. `page=` is "poorly supported". |
| `https://replay.pokemonshowdown.com/<id>.json` | Metadata plus `log`, and `inputlog` for random formats |
| `<id>.log` / `<id>.inputlog` | Raw log / inputlog |
| `/api/replays/searchprivate?username=<id>` | The user's **private** replays. Needs a login session; only for your own username. Uses `page=` only, max 100 pages. |

- All public APIs send `Access-Control-Allow-Origin: *` ([[2026-11-22-research-round-2]]).
- Do not scrape the replay **HTML** pages (WEB-API.md asks this). Use the `.json` endpoints, with a delay between requests ([[environment-quirks]]).
- **Private replays:** search results include a `password`. The full id is `<id>-<password>pw`, and `<fullid>.json` works **without** a login. Only the search needs the login.
- **Inputlog:** included for formats ending in `randombattle`, `randomdoublesbattle`, `challengecup`, `battlefactory`, `bssfactory`, `hackmonscup`. It holds the Showdown commit, the battle seed, both team seeds and every choice. See [[ADR-0009-randbats-full-info-reconstruction]].
- Only uploaded games exist on the server. 3,000 Champions OU replays covered only about 10 days ([[2026-11-22-research-findings]]).
- Python's default user agent gets HTTP 403 ([[environment-quirks]]).

## Showdown user data
- `https://pokemonshowdown.com/users/<userid>.json`: profile and ladder ratings (listed in WEB-API.md). Exact fields not checked yet.
- `https://pokemonshowdown.com/ladder/<format>.json`: ladder top list.
- `userid` = lowercased name with non-alphanumerics removed (`toID` in the server code). `Codexe` → `codexe`.

## Random Battle set data
- Source of truth: `data/random-battles/gen9/sets.json` plus the item/ability logic in `teams.ts` (smogon/pokemon-showdown). 509 species; each role gives a move pool, abilities and Tera types; items are picked in code ([[2026-11-22-research-round-2]]).
- **Use for priors:** `https://data.pkmn.cc/randbats/stats/gen9randombattle.json` from pkmn/randbats, with role weights and per-role frequencies of moves, items, abilities and Tera types, plus EVs. Updated with Showdown (last push 2026-11-20).
- `https://data.pkmn.cc/randbats/gen9randombattle.json`: the same without probabilities.

## Hugging Face replay dataset (training data, [[ADR-0012-training-data-v1]])
- **HolidayOugi/pokemon-showdown-replays**: `[Gen 9] RANDOMBATTLE_part1..11.parquet`, 4.49 GB, 2,012,698 logs to 2026-10-05. No inputlog; no license stated (local training only). Download: `training/download_hf.sh` → `data/hf/`.
- Also on HF: jakegrigsby/metamon-raw-replays, milkkarten/pokemon-showdown-replays-merged ([[2026-11-22-training-test-runs]]).
- About 34 public gen9randombattle replays are uploaded to Showdown per hour.

## Smogon usage stats (for VGC Reg M-C)
- `https://www.smogon.com/stats/<YYYY-MM>/<format>-<cutoff>.txt`, cutoffs 0 / 1500 / 1630 / 1760; latest month 2026-10 ([[2026-11-22-research-findings]]).
- `moveset/` and `chaos/` files give per-species moves, items, spreads and teammates. (unverified)

## Training data
- `gen9randombattle` public replays, scraped by format with the same code as [[spec-replay-sync]]. Each one is rebuilt to full information from its inputlog ([[ADR-0009-randbats-full-info-reconstruction]]).
- Self-play games on a local Showdown server ([[spec-eval-model]]).

## Related
- [[formats]] · [[spec-replay-sync]] · [[architecture]] · [[spec-eval-model]]
