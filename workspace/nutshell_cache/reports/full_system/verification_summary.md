# Full-System Verification Summary

Date: 2026-11-03 (Asia/Singapore)
Branch: `codex/full-system-graybox-closure`
Verification base: `fa7a9ef`; this report records the current local DV upgrade.

## Scope

The Python/Toffee environment targets `CoherentCacheAxiSubsystem` through a
verification-only wrapper. It coordinates dual CPU lanes, AXI backing memory,
MMIO and APB agents; observes internal protocol events; checks CPU data,
coherence transitions and transaction lifecycles; records checked functional
coverage; and supports seeded random tests and JSONL replay. Product RTL
behavior and interfaces are unchanged. This is UVM-style organization, not SV
UVM.

## Regression results

| Command / test | Result | Evidence |
| --- | --- | --- |
| `make coherence_full_system_coverage` | PASS, 35 passed / 1 skipped; 38/38 Required bins and 10/10 Required crosses | Current JSON/Markdown coverage reports |
| `make coherence_full_system_stress` | PASS, 60 passed; 20 × 500 CPU operations, 20 × 10 mixed-agent rounds, 20 resource-aware seeds | Seeded stress regression |
| `make COHERENCE_JOBS=2 coherence_directory_mshr_bank` | PASS; four contexts simultaneously active, response routing/reordering, blocked-context progress and reset cancellation | Directed block simulation output |
| `make COHERENCE_JOBS=2 coherence_axi_python_test` | PASS, 3 passed; four outstanding reads/writes, out-of-order R/B, five-channel backpressure, errors/reset/ID reuse | Pytest output |
| `source scripts/env.sh && make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS, exit 0: bounded Formal jobs; block/AXI checks; Python coherence 36 passed / 1 deselected, 49/49 functional bins and 9/9 checker fault injections; AXI Python 3 passed; regular/dense stress 20/20 each; mutation 4/4; Benchmark v4 24 rows; full-system 35 passed / 1 replay skipped, 38/38 bins and 10/10 crosses | Current local regression output |

The default replay case is skipped when no trace path is supplied. The
integrated closure covers only
Required entries marked `implemented` in
[`dv/coverage/full_system_coverage_plan.json`](../../dv/coverage/full_system_coverage_plan.json).
Four-context MSHR occupancy is verified at the MSHR block; four concurrent
CPU misses are not possible through the current two-lane blocking interface.
Out-of-order B responses are verified at the AXI adapter; integrated cache
writeback remains serialized by the line engine.

## Coverage separation

Python functional/cross coverage is not combined with RTL line, branch, toggle
or FSM coverage. Raw RTL coverage remains the separately audited snapshot in
[`rtl_coverage_summary.md`](rtl_coverage_summary.md); no RTL coverage closure
or sign-off is claimed by this update.

## Reproduction

Run from `workspace/nutshell_cache`:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_full_system_verify
make coherence_full_system_stress
FULL_SYSTEM_RANDOM_SEED_COUNT=20 FULL_SYSTEM_RANDOM_OPERATIONS=500 \
FULL_SYSTEM_RANDOM_BASE_SEED=0x57E55 \
PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -q \
  tests/full_system/test_full_system_random.py
```

## Release boundary

This local evidence is not GitHub Actions evidence. The integrated scenarios
listed as Open or Partial in
[`docs/dv/full_system_scenario_testplan.md`](../../docs/dv/full_system_scenario_testplan.md)
remain outside the closed coverage slice. PPA, STA, physical SRAM macros,
chip-level integration, and unbounded full-system formal proof are excluded.
