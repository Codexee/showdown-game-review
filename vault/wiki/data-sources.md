---
title: Data sources
type: wiki
status: active
tags: [area/data]
updated: 2026-11-22
---

# Data sources

## Showdown replay server
| Endpoint | Returns | Checked? |
|---|---|---|
| `https://replay.pokemonshowdown.com/search.json?format=<id>` | 51 replays per page, newest first, with `uploadtime` and rating | Yes ([[2026-11-22-research-findings]]) |
| `search.json?user=<userid>` (optionally `&format=<id>`) | One user's public replays | (unverified) |
| `search.json?...&before=<uploadtime>` | Next page | (unverified; paging worked in research but the parameter name was not recorded) |
| `https://replay.pokemonshowdown.com/<replay-id>.json` | Replay metadata plus the full `log` | (unverified) |
| `https://replay.pokemonshowdown.com/<replay-id>.log` | Raw battle log, one protocol line per row | (unverified) |

- Public replays go back only about 10 days per 3,000 games in Champions OU ([[2026-11-22-research-findings]]). Old games disappear from the search fast; this is why [[spec-replay-sync]] saves everything locally.
- **Only uploaded replays exist on the server.** A game the user never uploaded (or whose upload expired) cannot be fetched. (unverified, but this matches how Showdown works) See [[ADR-0006-replay-archive]].
- Private replays need the user's login. **Unknown:** how the search API returns them. Logged in [[open-questions]].
- Send a normal user agent. Python's default user agent gets HTTP 403 ([[environment-quirks]]).

## Showdown user data
- `https://pokemonshowdown.com/users/<userid>.json`: rating per format (Elo, GXE, Glicko). (unverified)
- The user id is the username lowercased with non-alphanumerics removed. (unverified)

## Smogon usage stats
- `https://www.smogon.com/stats/<YYYY-MM>/<format>-<cutoff>.txt`, cutoffs 0 / 1500 / 1630 / 1760. Latest month as of 2026-11-22: 2026-10 ([[2026-11-22-research-findings]]).
- Moveset files (`moveset/<format>-<cutoff>.txt`) and `chaos/<format>-<cutoff>.json` give per-species moves, items, spreads and teammates. (unverified)
- Used for set priors in [[spec-eval-model]].

## Training data
- Public replays (above), scraped and stored by [[spec-replay-sync]].
- Self-play games on a local Showdown server ([[spec-eval-model]]).
- Metamon publishes 5M+ reconstructed trajectories, but not for Champions or the formats in scope ([[bot-landscape]]).

## Related
- [[formats]] · [[spec-replay-sync]] · [[architecture]]
