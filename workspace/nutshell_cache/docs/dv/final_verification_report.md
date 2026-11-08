# NutShell Cache v1.1 Verification Release Candidate

**Decision: OPEN.** The existing v1.1 design has a substantial passing DV baseline, but the raw RTL coverage review is incomplete. This report is not an ASIC, FPGA, or tapeout sign-off.

## Candidate identity and reproducibility

- Repository: `cwu766485-ctrl/open_verif_learning`
- Tested product and DV source snapshot: `92d6373cf1bb25e3efe8a82bba9c6dde162de5e9`
- PR: [#1](https://github.com/cwu766485-ctrl/open_verif_learning/pull/1), targeting `cache_coherence`
- Product RTL manifest: 18 sources in `rtl/Coherence.files.f`, SHA-256 `06af9024a62bc60b30f2bf33550d1c3d9e0362f231377d964e6a9ce64bfcc667`
- Tool versions and every local gate result are recorded in [`verification_run_manifest.json`](../../reports/final/verification_run_manifest.json).
- The raw Verilator dataset provenance is in [`coverage_provenance.md`](../../reports/coherence/coverage_provenance.md). Per-run logs and raw `.dat`/`.info` coverage files are machine-local and ignored by Git because of their size. The manifest records each raw file's SHA-256 and byte count; the committed coverage matrices and summaries preserve the audited counts. The stress seed CSV and controlled replay trace are checked in.

The published report candidate was commit `9bbef4c17c899758408fe1fdc90dfa62181009ec`. GitHub Actions [run #81](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42456792418) completed successfully on that exact PR head: both `cache-regression` and `coherence-regression` passed, including Formal, integrated full-system regression, and the strict checked-cross Evidence Gate. The run checked out the same product/DV source tree tested locally at `92d6373cf1bb25e3efe8a82bba9c6dde162de5e9`; the report-candidate commit added evidence and reports. This report is being updated in a documentation-only follow-up, which triggers a fresh CI run. PR #1 remains open and unmerged; no release tag has been created.

## RTL architecture and claimed scope

The DUT is a dual-L1 MESI cache subsystem with private L1 data caches, a shared inclusive L2 and directory, four directory transaction contexts, four memory refill MSHRs, a 64-bit AXI4 line-memory adapter transferring eight beats per 64-byte line, and APB performance counters. Each L1 CPU interface is blocking. Directory contexts and refill MSHRs do not imply four simultaneous CPU misses: shared L2/data/write resources and same-set admission still constrain progress.

This verification scope exercises CPU data-cache coherence, snoop/ownership transfer, refill and dirty eviction, AXI memory traffic and errors, MMIO, APB counters, reset cancellation, and selected concurrent traffic. It does not claim real CPU/SoC integration, I-cache or DMA coherence, LR/SC or AMO, arbitrary CPU response reordering, 2-entry L1 MSHRs, physical SRAM mapping, PPA, STA, or physical implementation.

## Verification platform

The full-system environment uses Python, pytest, Toffee, Picker and Verilator, with four active agents: dual-core CPU, AXI backing memory, MMIO slave, and APB master. A passive monitor observes external handshakes and selected L1, Directory, Snoop, MSHR and L2 internal events. Expected data and MESI/Directory state come from independent reference models and scoreboards; coverage is credited only after the required monitor and checker evidence passes.

This is a Python/Toffee UVM-style environment, not SystemVerilog UVM. Standalone block tests and bounded component formal harnesses remain separate evidence sources. Their coverage denominators are not added to the subsystem denominator.

## Regression results at the tested source SHA

All required local gates passed at source SHA `92d6373cf1bb25e3efe8a82bba9c6dde162de5e9`:

| Gate | Result |
| --- | --- |
| `coherence_verify` | PASS as nested prerequisite of `coherence_full_system_verify` |
| `coherence_full_system_verify` | PASS; 70 full-system tests passed, one saved-failure replay test skipped because no DUT failure trace was saved |
| `coherence_hit_under_miss` | PASS; two Python directed tests and three AXI-top directed tests |
| `coherence_full_system_cross_closure` | PASS; 21 tests |
| `coherence_full_system_stress` | PASS; 280 seeded environments across six campaigns |
| `coherence_coverage_audit` | PASS; seven independent Verilator datasets collected |
| `coherence_full_system_evidence_gate` | PASS; 69 checked runs, 53/53 Required Functional and 35/35 Required Cross bins |
| `coherence_full_system_replay_closure` | PASS; controlled checker-fault replay and legal-prelude operation reduction |

The standalone Python coherence closure separately reports 49/49 functional bins and 19/19 cross bins. Strict evidence negative tests passed 40/40; four RTL mutations were detected (4/4); checker fault injection detected 9/9 injected faults. These are distinct plans and do not add to the full-system 53/35 counts.

Formal runs in `coherence_verify` are component-level and bounded/inductive proofs. They do not prove the entire cache subsystem without a bound. Full commands and log paths are listed in the run manifest.

## Cross-agent scenarios

CR01–CR10 each have at least one checked representative instance with observed events, a same-window or transaction-correlation check, and an independent checker. The exact seeds, cycles and remaining variation are in [`verification_traceability_matrix.md`](verification_traceability_matrix.md).

| ID | Scenario | Current evidence |
| --- | --- | --- |
| CR01 | Dirty owner transfer × independent refill × APB | Directed overlap and checked transaction correlation |
| CR02 | Shared upgrade × MMIO pending | Seeded checked overlap |
| CR03 | Dirty L1 victim × AXI writeback stall | Two checked stall seeds |
| CR04 | Dirty L2 victim × Snoop × APB | Two checked dirty-victim seeds |
| CR05 | Same-set Directory conflict × AXI stall | Checked same-set conflict and refill lifecycle |
| CR06 | Dual cold miss × out-of-order AXI R × APB | Refill IDs and reverse response completion checked |
| CR07 | Hit-under-miss × remote Snoop | Directed overlapping miss, resident hit and remote-owner transfer |
| CR08 | Reset × Directory/Snoop pending | Seeded reset epochs and recovery checks |
| CR09 | AXI error × fail-stop × reset | Injected read errors, suppressed success, reset and retry |
| CR10 | Ownership ping-pong × MMIO/APB | Checked owner transitions alongside MMIO/APB activity |

These results verify the recorded instances, not every Core direction, address/set relationship, stall position, error beat, response order or reset phase.

## Stress, replay and performance evidence

The stress suite passed 280/280 environments: 100 CPU-random seeds × 500 operations, 100 mixed CPU/MMIO/APB/AXI seeds × 500 rounds, and four 20-seed resource/recovery campaigns. [`stress_seed_summary.csv`](../../reports/full_system/stress_seed_summary.csv) retains seed/configuration and checked event deltas. The randomized campaign had no DUT failure, so it has no failing-seed trace to minimize.

A separate controlled checker-fault test used seed 61857. It captured the injected expected-data mismatch, replayed the same failure signature on RTL, and reduced the operation trace from five operations to two while preserving the legal owner-store prelude. This is operation-level minimization; it does not preserve a universal cycle-by-cycle interleaving.

The existing Hit-under-Miss A/B workload uses synthetic memory latency of 80 cycles, one cold miss and 24 resident reads. The baseline completes the observation window in 185 cycles (0.135135 operations/cycle); the bypass version takes 113 cycles (0.221239 operations/cycle), a 38.92% shorter window and 63.72% higher workload throughput. The cold-miss latency remains 113 cycles in both runs, and all response data is checked. This is cycle-level Verilator simulation, not physical bandwidth, application IPC, Fmax or PPA. Source values: [`rtl_opt_p1_hit_under_miss_ab.json`](../../benchmarks/results/rtl_opt_p1_hit_under_miss_ab.json).

## Raw RTL coverage

The same-top primary subsystem dataset now includes the Hit-under-Miss SV scenario. It hits `DualL1MesiCluster.sv` lines 419–422 and 425–427; Python functional coverage is not used to fill RTL points. Raw results for each top are kept separate:

| Dataset | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `CoherentCacheSubsystem_tb` | 850/998 | 468/556 | 19996/27474 | 30/54 | 7/48 |
| AXI subsystem E2E | 901/1074 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| DirectoryController block | 117/188 | 30/42 | 236/612 | 9/10 | 2/9 |
| DirectoryMshrBank block | 167/292 | 100/128 | 1063/2904 | 31/40 | 11/36 |
| SharedLineEngine block | 101/104 | 44/52 | 304/648 | N/A | N/A |
| MesiL1Controller block | 104/132 | 40/46 | 629/1804 | 7/7 | 2/6 |
| SharedL2DirectoryArray block | 75/79 | 65/74 | 197/1778 | N/A | N/A |
| Bus blocks | 67/68 | 70/76 | 1100/2450 | N/A | N/A |

There are 1,012 dataset-scoped zero-count point records; all remain OPEN, no coverage waiver is approved, and reviewed/eligible percentages are not computed. A hit in one elaborated top does not close a point in another. Verilator FSM N/A means no FSM points were extracted in that build, not that the RTL lacks state. See [`rtl_coverage_signoff.md`](../../reports/final/rtl_coverage_signoff.md), [`coverage_closure_matrix.csv`](../../reports/final/coverage_closure_matrix.csv), [`coverage_closure_raw_runs.md`](../../reports/coherence/coverage_closure_raw_runs.md), and [`coverage_provenance.md`](../../reports/coherence/coverage_provenance.md).

## Remaining gaps and decision

1. All 1,012 raw zero-count records need point-specific reachability, checker, proof, or reviewed disposition. Legal recovery paths and protocol/error protection are not automatically waived.
2. CR01–CR10 have representative checked instances, but broad cross-dimension variation remains open.
3. Full-system coverage does not independently predict every MSHR lifecycle or every L2-directory transition. Four Directory contexts do not mean four concurrent CPU misses.
4. No unbounded full-subsystem formal proof is claimed. A saved-DUT-failure replay was skipped in the general suite; controlled checker-failure replay passed separately.
5. PPA, STA, physical SRAM macro mapping, real CPU/application benchmarking, and chip-level physical implementation are out of scope.
6. GitHub Actions run #81 passed both required jobs at report-candidate SHA `9bbef4c17c899758408fe1fdc90dfa62181009ec`. A documentation-only follow-up to record this result is undergoing its own CI; the PR description tracks the latest head and run.

**Final decision: OPEN.** Functional regressions and candidate-SHA CI pass, but raw RTL point review and broad cross-dimension closure remain incomplete. Do not describe this as ASIC/tapeout sign-off.

## Reproduction

From `workspace/nutshell_cache`:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_full_system_verify
make COHERENCE_JOBS=2 coherence_hit_under_miss
make COHERENCE_JOBS=2 coherence_full_system_cross_closure
make COHERENCE_JOBS=2 coherence_full_system_stress
make COHERENCE_JOBS=2 coherence_coverage_audit
make COHERENCE_JOBS=2 coherence_full_system_evidence_gate
make COHERENCE_JOBS=2 coherence_full_system_replay_closure
```
