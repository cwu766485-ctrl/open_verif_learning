# Full-System Gray-box DV — Phase 0 Baseline Freeze

Date: 2026-11-02 (Asia/Singapore)

## Repository baseline

- Repository: `open_verif_learning`
- Project: `workspace/nutshell_cache`
- Working branch created for this task: `codex/full-system-graybox-closure`
- Source branch at task start: local `cache_coherence`
- Baseline source SHA: `6dd9637d5c92a9e23becb4643434905eecc1d812`
- At task start, local `cache_coherence` was 14 commits ahead of
  `origin/cache_coherence`; work is based on the local tip and does not replace
  or reset those commits.
- The task branch was clean when created. The tracked Benchmark and coherence
  result files modified by baseline commands are generated outputs and are not
  part of the verification-platform change.

## Tool environment

Collected with `source scripts/env.sh`:

| Tool | Version |
| --- | --- |
| Python | 3.12.3 |
| pytest | 9.1.1 |
| Picker | 0.9.0-HEAD-c100874 (2026-08-06) |
| Verilator | 5.053 devel, rev v5.052-521-g6388139f7 |
| SymbiYosys | 0.70 |
| Toffee | Import succeeds in the project virtual environment |

## Pre-change validation

| Command | Result | Notes |
| --- | --- | --- |
| `make doctor` | PASS | Python, pytest, Toffee, Picker, Verilator, and SBY were available. |
| `make COHERENCE_JOBS=2 coherence_verify` | PASS | Completed before this task's code edits. Block, AXI, Formal, subsystem, Python, stress, mutation, and Benchmark v4 targets reached their passing completion messages. This baseline execution was terminal-only; the existing checked-in compressed log is from SHA `9b1d89e`, so it is not cited as an artifact for baseline SHA `6dd9637`. |
| `make coherence_full_system_coverage` | PASS | Existing full-system tests completed. The checked run result was 17 passed, 1 skipped; the skip is replay without a selected trace. |

The earlier full-system 19/19 functional and 6/6 cross closure applies only to
the then-implemented plan scope. It is not evidence that all planned four-agent
scenarios or all cross-interface cases were closed.

## Baseline gaps recorded before edits

1. The existing MMIO/cache overlap test issued an MMIO **write**, not the
   planned delayed MMIO read, and its APB access read Access Cycles rather than
   the Miss Counter.
2. That test did not assert cycle ordering between the APB access, AXI final R
   beat, and MMIO response.
3. `Axi4BackingMemoryAgent.r_stall_period` was unused. The integrated
   `CoherentCacheSubsystem` drives refill data ready as `!reset`, so its AXI
   adapter keeps `RREADY` asserted outside reset; a memory slave cannot force a
   receiver-side R stall on this top.
4. APB and MMIO handshake events could be missed by the passive monitor when
   the active Toffee agent retired pins on the same scheduler edge.
5. Monitor records did not carry a Reset Epoch, so traces could not directly
   distinguish pre-reset and post-reset transactions.
6. Random scheduling favored missing CPU read/write bins, but did not select
   among protocol-level targets such as dual cold misses and out-of-order AXI
   completions.

These are verification-platform gaps. No product RTL behavior or interface is
changed by the planned work.
