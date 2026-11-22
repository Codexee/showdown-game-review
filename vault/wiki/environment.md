---
title: Environment (this Mac)
type: wiki
status: active
tags: [area/infra]
updated: 2026-11-22
---

# Environment

From [[2026-11-22-research-findings]].

- **Machine:** Apple M5 Pro, 16-core GPU, 24 GB unified memory, macOS 26.5.1. 496 GiB free disk.
- **Training backend:** PyTorch with the MPS (Metal) backend. **Not installed yet.**
- **Python:** system `python3` is 3.14.6 from Anaconda. No 3.11/3.12 on PATH. Use `uv` to create a project venv on a version that PyTorch, poke-env and poke-engine all support. **Unknown:** the newest Python version all three support. See [[open-questions]].
- **Node:** v24.18.0, npm 12.2.1: enough to run a local Showdown server.
- **Rust:** not checked. foul-play's poke-engine must be built from source with Rust ([[bot-landscape]]).
- **Other:** git 2.50.1, gh 2.102.0, codex-cli 0.169.0, Homebrew 7.0.14, conda 26.5.3.
- **Overnight runs:** keep the Mac on AC power with keep-awake on ([[ADR-0005-overnight-training-budget]]).

## Related
- [[environment-quirks]] · [[spec-eval-model]] · [[tooling]]
