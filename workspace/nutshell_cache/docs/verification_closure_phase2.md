# Verification Closure Phase 2 — RTL Coverage Gap Audit

## Decision

**Status: OPEN.** This phase refreshes independent raw RTL coverage and improves the source-linked closure inventory. It does not claim RTL coverage sign-off, declare unhit points unreachable, approve waivers, or change RTL behavior.

## Run provenance

- Repository branch: `dv-closure-phase2`
- Code baseline for this audit run: `b8f0aa8` (`reports: refresh full-system coverage evidence`)
- Product RTL manifest: `rtl/Coherence.files.f` (18 source files)
- Command: `source scripts/env.sh && make COHERENCE_JOBS=2 coherence_coverage_audit`
- Tool: Verilator 5.053 development build; Python 3.12 environment
- Result: all seven independently elaborated coverage tops built and ran successfully.
- The main coherent-subsystem `coverage.dat` and `coverage.info` predate this run (2026-11-04); RTL sources are unchanged, but the final regression must regenerate them before a final candidate decision.

## Independent raw coverage

These are separate elaborations and denominators. Do not sum their metrics or treat another top's hit as a hit in this dataset.

| Dataset | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| Main coherent subsystem (existing 2026-11-04 run) | 843/998 | 461/556 | 19980/27474 | 30/54 | 7/48 |
| AXI subsystem E2E, five fixed seeds | 901/1074 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| DirectoryController block | 117/188 | 30/42 | 236/612 | 9/10 | 2/9 |
| DirectoryMshrBank block | 167/292 | 100/128 | 1063/2904 | 31/40 | 11/36 |
| SharedLineEngine block | 101/104 | 44/52 | 304/648 | N/A | N/A |
| MesiL1Controller block | 104/132 | 40/46 | 629/1804 | 7/7 | 2/6 |
| SharedL2DirectoryArray block | 75/79 | 65/74 | 197/1778 | N/A | N/A |
| Bus blocks | 67/68 | 70/76 | 1100/2450 | N/A | N/A |

`N/A` means that the selected Verilator build emitted no FSM points for that top. It does not mean the RTL contains no FSM. Raw toggle points only include signals emitted by the tool and its instrumentation filters.

## Closure matrix

`reports/final/coverage_closure_matrix.csv` is generated from the raw artifacts and preserves one record per zero-count point per dataset. It contains source path/line, Block, metric and point identity, related feature/spec, observed reason (zero in this dataset), reachability/protocol-protection review, current testcase/checker/formal references, independent-run evidence, recommended action, risk, and closure status.

- Total dataset-scoped zero-count records: **1,026** across the available runs.
- Main subsystem records: 155 line, 95 branch, 24 FSM state, and 41 FSM arc.
- Every record currently has status `OPEN`; the only allowed states are `OPEN`, `COVERED`, `PROVEN_UNREACHABLE`, `REVIEWED_WAIVER`, and `BLOCKED`.
- A matching point observed in a different top is recorded as separate evidence; it does not promote the row to `COVERED`.
- Approved waivers: **0**. No automatic waiver, RTL deletion, denominator change, or Feature/Cross Bin change was made.
- `1026` is a count of dataset-scoped observations, not unique design defects or a requirement for 1,026 new tests.

Some points have hand-authored source-range review and concrete follow-up test suggestions. The rest remain source/path mapped only. The matrix intentionally does not treat source keywords or a nearby error signal as proof of unreachability or error classification. FSM arc line mapping is linked to source state labels where the Verilator state name resolves; any unresolved mapping must remain open for manual review.

### Hit-under-Miss evidence boundary

The instrumented subsystem RTL datasets leave `DualL1MesiCluster.sv` lines 419–427 unhit (and the corresponding ready/ID control around lines 249–276 is absent from this SV-top line dataset). The full-system Python/Toffee regression separately runs `tests/full_system/test_hit_under_miss_axi.py`, which checks a pending AXI miss while a resident hit returns, response payload hold, transaction-ID noncollision and wrap, snoop progress, and reset cancellation. This is functional evidence for the feature, but it is not merged into Verilator raw coverage. The dataset-scoped RTL rows therefore stay `OPEN` until the instrumented SV top runs an equivalent sequence or the coverage review explicitly accepts the different evidence scope.

## Priority follow-up

1. Re-run the main subsystem raw coverage from the final Phase 6 regression and regenerate all coverage reports at the same source SHA.
2. For `DualL1MesiCluster`, `MesiL1Controller`, `DirectoryController`, `SharedLineEngine`, and `DirectoryMshrBank`, map legal zero-count points to directed or random scenarios and independent checkers. In particular, preserve Hit-under-Miss as evidence only for the matching elaborated top; do not merge Python functional bins into RTL raw metrics.
3. Exercise block-boundary protocol guards using fault injection where the existing block interface allows it; otherwise keep them open until a formal argument or reviewed disposition exists.
4. Review each remaining line/branch/FSM point against its exact condition and effects. Do not infer reachability from textual patterns.

## Reproduction

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_coverage_audit
PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.coverage_raw_runs
PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.coverage_closure_matrix
PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.rtl_coverage_closure
```

The raw Verilator `.dat` files, LCOV files, build logs, and summary files are generated under ignored `reports/coherence/`; they are not source-controlled. The source-linked closure CSV and this review are the review artifacts.
