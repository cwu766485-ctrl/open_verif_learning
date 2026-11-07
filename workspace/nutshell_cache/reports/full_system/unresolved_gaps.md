# Unresolved Full-System Verification Gaps

Status snapshot: 2026-11-07 (Asia/Singapore)
Tested source SHA: `e4eb73cb8040559f6880e7299c511213f43a7d4c`
Decision: **OPEN — candidate evidence is not final sign-off**

See [`docs/dv/closure_phase2_1_phase3_execution_2026-11-07.md`](../../docs/dv/closure_phase2_1_phase3_execution_2026-11-07.md) for commands, source provenance, checked evidence, and the detailed CR01–CR10 matrix.

## Cross-agent scenarios

The generated full-system artifact contains passing checked instances for CR01–CR10. Each closure row requires its planned monitor events, transaction references, overlap window, and independent checker PASS. This means the particular recorded scenario instances are verified; it does not close every randomized Core/address/data/stall combination.

| Scenario | Evidence | Remaining scope |
| --- | --- | --- |
| CR01 Owner transfer × refill × APB | Strict overlap at cycle 163, four correlated transactions, checker PASS. | Directed instance has no recorded seed; randomized address and stall breadth OPEN. |
| CR02 Shared upgrade × MMIO pending | Seed 49154, cycle 90–92 overlap, checker PASS. | Broader variation OPEN. |
| CR03 Dirty L1 victim × AXI writeback stall | Seeds 49155, 49411; overlap, PutM/victim and AXI AW/W/B checked. | Broader variation OPEN. |
| CR04 Dirty L2 victim × snoop × APB | Seeds 49156, 49412; three-way event relationship checked. | Broader variation OPEN. |
| CR05 Same-set Directory conflict × AXI stall | Seeds 49413, 49415; conflict/AR stall/refill correlated. | Broader variation OPEN. |
| CR06 Dual cold miss × OoO AXI R × APB | Seed 49158; paired MSHR/refill lifecycle and reversed first-two R order checked. | One seeded directed instance; repeated ordering/stall variation OPEN. |
| CR07 Hit-under-miss × remote snoop | Strict overlap cycles 67–78, five transactions and checker PASS. | Directed instance has no recorded seed; randomized address/stall breadth OPEN. |
| CR08 Reset × Directory/snoop pending | Seeds 59248–59251; pending-upgrade/snoop overlap and recovery checked. | Other reset phases OPEN. |
| CR09 AXI error × fail-stop × reset | Seeds 59248–59251; error/recovery overlap and post-reset behavior checked. | Additional error/channel combinations OPEN. |
| CR10 Ownership ping-pong × MMIO/APB | Seeds 49168, 49424; ownership/MMIO/APB checker PASS. | Broader variation OPEN. |

## Raw RTL coverage

The primary subsystem raw Verilator dataset remains 843/998 line, 461/556 branch, 19980/27474 toggle, 30/54 FSM state, and 7/48 FSM arc hits. The closure matrix has 1,026 dataset-scoped zero-count records, all OPEN; zero waivers are approved. Independent AXI and block-top denominators remain separate. Python functional coverage does not substitute for source-instrumented RTL coverage.

The Python Hit-under-Miss/AXI-top tests pass, but their elaborated coverage dataset is separate from the primary subsystem LCOV session. Their functional result does not close the subsystem raw line/branch points.

## Replay and remaining risk

- The requested 280-case full-system stress campaign passes without a DUT failure seed. A controlled injected checker mismatch independently proves failure capture, same-seed replay, and operation-level reduction from five operations to a legal owner-store prelude plus remote-owner-read trigger.
- The minimizer preserves operation order and legal prelude; it is not a general cycle-by-cycle interleaving minimizer.
- Local full regressions pass on source SHA `e4eb73c`. GitHub Actions was still running on the pre-refresh PR head at the time of the report; remote CI must pass on the published candidate.
- No unbounded whole-system formal proof is claimed. 2-entry L1 MSHR and PPA/STA/physical SRAM sign-off are outside this phase.
