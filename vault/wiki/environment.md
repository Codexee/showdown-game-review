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
- **Python:** system `python3` is 3.14.6 from Anaconda. The project uses a **uv venv on CPython 3.13** ([[ADR-0008-python-313]]). uv also sees 3.14.10 (Homebrew), 3.12.16 (uv) and 3.9.6 (system) ([[2026-11-22-research-round-2]]).
- **Node:** v24.18.0, npm 12.2.1: enough to run a local Showdown server and the replay rebuild step ([[ADR-0009-randbats-full-info-reconstruction]]).
- **Rust:** rustc / cargo 1.99.1 installed. poke-engine is source-only and builds with it ([[2026-11-22-research-round-2]]).
- **Other:** git 2.50.1, gh 2.102.0, codex-cli 0.169.0, Homebrew 7.0.14, conda 26.5.3.
- **Overnight runs:** keep the Mac on AC power with keep-awake on ([[ADR-0005-overnight-training-budget]]).

## Related
- [[environment-quirks]] · [[spec-eval-model]] · [[tooling]]
