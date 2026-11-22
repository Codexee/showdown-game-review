---
title: ADR-0008 Python 3.13 in a uv venv
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/infra]
---

# ADR-0008: Use Python 3.13 in a uv-managed venv

## Context
- System `python3` is Anaconda 3.14.6 ([[environment]]).
- torch 2.15.0 has macOS arm64 wheels for 3.11–3.15. poke-env 0.17.0 needs ≥3.10. FastAPI 0.165.0 needs ≥3.11 ([[2026-11-22-research-round-2]]).
- poke-engine 0.0.48 has **no wheels**. It builds from source with Rust (pyo3 0.29). foul-play's own Docker image builds and runs it on **Python 3.13** ([[2026-11-22-research-round-2]]).
- Rust 1.99.1 is installed.

## Decision
- One project venv created with `uv` on CPython 3.13 (`uv python install 3.13`). Do not use the Anaconda Python.
- Install poke-engine with the Gen 9 feature, the same way foul-play does: `--config-settings="build-args=--features poke-engine/terastallization --no-default-features"`.

## Options considered
- **3.13 (chosen):** the version foul-play is tested on, and every dependency supports it.
- **3.14:** probably works (torch has wheels, pyo3 0.29 likely supports it), but foul-play's poke-engine build is not tested on it. (unverified)
- **3.12:** already installed through uv; also fine, but there's no reason to pick an older version.

## Consequences
- The first `uv sync` compiles poke-engine, which takes a few minutes.

## Related
- [[environment]] · [[bot-landscape]] · [[ADR-0007-app-stack]]
