# DV Closure Phase 2.1 / Phase 3 Execution Record

Date: 2026-11-07 (Asia/Singapore)
Repository: `cwu766485-ctrl/open_verif_learning`
PR: [#1 — dv-closure-phase2](https://github.com/cwu766485-ctrl/open_verif_learning/pull/1)
Tested source snapshot: `e4eb73cb8040559f6880e7299c511213f43a7d4c`
Tested source tree: `107b37cbfd31768dea217bbffcaf2b145de7c80b`

## Decision

The v1.1 candidate has broad local simulation, formal, mutation, stress, checked functional/cross, and replay evidence. **Final sign-off remains OPEN** because the primary subsystem raw Verilator scope still has unhit RTL points whose point-by-checker review is incomplete, and current GitHub Actions has not completed on this tested source snapshot. No RTL behavior or interface was changed in this phase. The verification-plan, report-generation, and replay infrastructure were updated.

The local tested source SHA is distinct from the remote PR head observed before publication (`a5413d46cd6081e7559e1a6071d770d8e926dfa9`). Do not attribute local regression results to that older remote SHA. The local result logs are `/tmp/nutshell_*_phase3.log`; the committed reports below preserve the summarized evidence and source SHA.

## Gate 1 — strict evidence contract

The full-system plan has `checked_cross_v1` contracts for the strict scenarios. The CI workflow runs `coherence_full_system_coverage` and then the standalone `coherence_full_system_evidence_gate` step in the coherence job. The full-system verification run also executes evidence-gate/checker unit tests.

At tested source SHA `e4eb73c`, the generated closure artifact reports **53/53 required full-system functional bins and 35/35 required full-system cross bins**, with no missing required IDs. It stores per-test checker status, monitor event references, transaction IDs, cycle overlap, and reset epoch. The evidence-gate negative tests passed (40 tests): missing monitor references, incorrect/missing overlap or cycle data, testcase mapping mismatch, and checker failure are rejected. This is not evidence that every parameter combination is covered; it proves the checked instances represented in the artifact satisfy the contract.

Python/Toffee coherence closure is reported separately as **49/49 functional and 19/19 cross**. It is not added to the full-system counts or RTL source coverage.

## Gate 2 — CR01–CR10 cross-agent scenarios

All ten scenario IDs have passing checked evidence for at least one concrete instance. The table distinguishes that evidence from scenario breadth; `seed —` means the directed test did not record a randomized seed.

| Scenario | Current checked evidence | Assessment |
| --- | --- | --- |
| CR01 Owner transfer × refill × APB | Checked overlap at cycle 163; three protocol roles and four transactions; independent checker PASS; seed not recorded. | Verified for the recorded distinct-set directed instance; randomized address/stall breadth OPEN. |
| CR02 Shared upgrade × MMIO pending | Seed 49154; cycles 90–92; upgrade/MMIO/snoop events, three transactions; checker PASS. | Verified for seeded instance; broader variation OPEN. |
| CR03 Dirty L1 victim × AXI writeback stall | Seeds 49155 and 49411; overlaps 705–744 and 705–749; replacement/PutM/L2 victim/AW/W/B event chain checked. | Verified for two seeded instances; broader variation OPEN. |
| CR04 Dirty L2 victim × snoop × APB | Seeds 49156 and 49412; overlap at cycles 443 and 454; victim, snoop, APB events checked. | Verified for two seeded instances; broader variation OPEN. |
| CR05 same-set Directory conflict × AXI stall | Seeds 49413 and 49415; cycles 113 and 110; same-set conflict, AR stall, refill correlated. | Verified for two seeded instances; broader variation OPEN. |
| CR06 dual cold miss × out-of-order AXI R × APB | Seed 49158; two MSHR/refill contexts with reversed first-two R completions; independent data/ID/order checker PASS. | Verified for the directed seeded instance; repeated randomized ordering breadth OPEN. |
| CR07 hit-under-miss × remote snoop | Checked overlap cycles 67–78; another-line refill and owner snoop; five transactions; checker PASS; seed not recorded. | Verified for the directed AXI-top instance; seed/address/stall breadth OPEN. |
| CR08 reset × Directory/snoop pending | Seeds 59248–59251; pending upgrade/snoop overlap cycles 90–91; reset/recovery checkers PASS. | Verified for four recovery seeds; other reset phase combinations OPEN. |
| CR09 AXI error × fail-stop × reset | Seeds 59248–59251; error/recovery overlaps recorded; injected response errors and post-reset recovery checked. | Verified for four recovery seeds; additional error/channel combinations OPEN. |
| CR10 ownership ping-pong × MMIO/APB | Seeds 49168 and 49424; cycle 93 overlap; ownership, MMIO, APB and data/state checks PASS. | Verified for two seeded instances; broader variation OPEN. |

CR01/CR07 have strict event/overlap evidence but no recorded seed; CR06 is a single deterministic seeded testcase. Thus the per-instance evidence is closed, while the task’s request for randomized Core/address/data/stall breadth is not fully closed. The cross plan and generated evidence are in `dv/coverage/full_system_coverage_plan.json` and `reports/full_system/full_system_coverage_closure.json`.

## Gate 3 — raw RTL coverage

Source manifest: 18/18 product RTL sources match the compiled source manifest. LCOV categorization reconciles exactly: Product RTL 843/998 lines, Testbench 738/748, Generated/Other 0/0; combined 1581/1746 hit and 165 unhit. The product subsystem raw metrics are:

| Metric | Hit / total | Unhit |
| --- | ---: | ---: |
| Line | 843 / 998 | 155 |
| Branch | 461 / 556 | 95 |
| Toggle | 19,980 / 27,474 | 7,494 |
| FSM state | 30 / 54 | 24 |
| FSM arc | 7 / 48 | 41 |

Independent AXI and block-top denominators are listed separately in `reports/final/rtl_coverage_signoff.md`; they are not summed with the subsystem denominator. The point-level CSV currently has 1,026 dataset-scoped zero-count records, all `OPEN`, and `coverage_waivers.json` contains no waivers. A hit in a separate top or Python functional test is retained as provenance, not silently credited to this raw source dataset. Reviewed/eligible percentage is not computed.

The Python Hit-under-Miss tests and the separate AXI-top tests establish functional behavior, but they do not feed the subsystem LCOV run: the wrappers/elaborated tops and source-instrumentation sessions differ. Raw code coverage remains an independent obligation. There was no product RTL change in this phase.

## Gate 4 — stress, replay, final regression

Full requested local regression was run on the tested source snapshot:

| Command | Result |
| --- | --- |
| `source scripts/env.sh && make COHERENCE_JOBS=2 coherence_verify` | PASS; formal/block/coherence/Python regression, RTL mutation 4/4, benchmark v4 completed. |
| `make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS; 70 passed, 1 skipped. The skip is the replay-smoke case; controlled replay closure was run separately. |
| `make COHERENCE_JOBS=2 coherence_hit_under_miss` | PASS; Python and AXI-top directed tests passed. |
| `make COHERENCE_JOBS=2 coherence_full_system_cross_closure` | PASS; 21 passed. |
| `make COHERENCE_JOBS=2 coherence_full_system_stress` | PASS; 280 passed in 1661.41 s. |
| `make COHERENCE_JOBS=2 coherence_coverage_audit` | PASS; seven separate raw scopes collected. |

The stress campaign comprises 100 CPU-random seeds × 500 configured operations, 100 mixed CPU/MMIO/APB/AXI seeds × 500 rounds, 20 resource-aware snoop/refill seeds, 20 reset-phase seeds, 20 CR09 error/recovery seeds, and 20 CR08 reset/snoop-pending seeds. No DUT failure seed occurred in that campaign. Per-seed configuration, coverage delta, transaction/error counts, and replay command are in `reports/full_system/stress_seed_summary.csv`; aggregate counts are in `reports/full_system/stress_campaign_summary.md`.

A separate controlled checker-fault replay was run and recorded in `reports/full_system/replay_closure/controlled_checker_failure.json`: seed 61857, same-seed replay matched the failure signature and cycle, and a five-operation trace reduced to the legal `owner_store` prelude plus `remote_owner_read` trigger. Each accepted candidate was rerun against RTL. This proves the controlled checker-failure capture/replay/reduction path. It does not claim cycle-by-cycle minimization of arbitrary concurrent interleavings; the reducer preserves operation order and required legal prelude.

## CI / PR status

Before publishing the refreshed reports, remote PR #1 pointed at `a5413d46cd6081e7559e1a6071d770d8e926dfa9`; Actions run 42368205033 (#73) completed with **failure**. The `coherence-regression` job failed during “Run integrated Python full-system coverage regression”; its strict evidence-gate step was skipped. The `cache-regression` job failed during “Run regression and coverage closure”. Setup, tool installation, and formal proof steps passed. This old-head result is not attributed to local SHA `e4eb73c`. The new PR-head Actions run must complete before remote sign-off. The PR is not merged by this execution record.

## Remaining gaps and sign-off

- **OPEN:** 1,026 dataset-scoped raw RTL zero-count points; point-level reachability/checker/proof review is incomplete.
- **OPEN:** random variation breadth for CR01/CR06/CR07 and broader dimensions for all ten cross scenarios.
- **OPEN:** full-system stress did not generate a DUT failure; the successful controlled injected checker failure validates replay mechanics only.
- **OPEN:** remote CI must pass at the published PR candidate SHA.
- **Not in scope:** 2-entry L1 MSHR, new product RTL behavior, PPA, STA, physical SRAM macro validation, and chip-level implementation.

**Final decision: verification candidate, not final sign-off.** The Python and full-system checked functional/cross closure evidence passes; raw RTL coverage and random cross breadth remain explicitly open. No waiver or coverage-denominator reduction was used.
