---
title: Architecture
type: wiki
status: draft
tags: [area/ui, area/model, area/data]
updated: 2026-11-22
---

# Architecture (draft)

Nothing is built yet. This is the planned shape, from [[ADR-0001-local-web-app]] and the specs.

```mermaid
flowchart LR
  subgraph Showdown["Showdown (internet)"]
    RS[replay server<br/>search.json, .json, .log]
    US[user API<br/>users/&lt;id&gt;.json]
    CL[play.pokemonshowdown.com<br/>+ our userscript]
  end
  subgraph Local["This Mac"]
    SYNC[replay sync<br/>poller + importer]
    DB[(archive<br/>SQLite + raw .log files)]
    PARSE[log parser<br/>per-side battle state]
    MODEL[eval model<br/>PyTorch, MPS]
    API[local Python server<br/>HTTP API]
    UI[browser UI<br/>pixel-art replay viewer]
    PS[local Showdown server<br/>self-play]
    TRAIN[training pipeline]
  end
  RS --> SYNC
  US --> SYNC
  CL -- finished battle log --> API
  API --> DB
  SYNC --> DB
  DB --> PARSE --> MODEL
  MODEL --> API --> UI
  DB --> API
  PS --> TRAIN
  DB --> TRAIN --> MODEL
```

## Components
| Component | Job | Spec |
|---|---|---|
| Replay sync | Pull the user's ratings and new replays (public and private) | [[spec-replay-sync]] |
| Userscript | Runs on Showdown's site; posts each finished battle's log to `/api/ingest` | [[spec-replay-sync]], [[ADR-0006-replay-archive]] |
| Archive | SQLite index plus the raw `.log` file per game; never deleted | [[spec-replay-sync]], [[ADR-0006-replay-archive]] |
| Log parser | Turn a Showdown protocol log into a battle state per turn, from each player's view | [[spec-eval-model]] |
| Eval model | Value (win chance) and policy (move ranking) per turn | [[spec-eval-model]] |
| Local server | Serves the UI and an HTTP API: games list, replay, evals | [[spec-review-app]] |
| UI | Game list, replay player, eval bar, eval graph, move labels | [[spec-review-app]], [[visual-style]] |
| Training | Small test run, then an overnight run | [[spec-eval-model]], [[ADR-0005-overnight-training-budget]] |

Stack: FastAPI, Vite + TypeScript, SQLite ([[ADR-0007-app-stack]]).

## Planned code layout (draft)
```
server/      Python (FastAPI): API, sync, ingest, parser, model inference
training/    Python: datasets, training loops, self-play
web/         Vite + TypeScript frontend
userscript/  the Showdown userscript
data/        archive (git-ignored)
vault/       this vault
```

## Related
- [[project-overview]] · [[roadmap]] · [[data-sources]]
