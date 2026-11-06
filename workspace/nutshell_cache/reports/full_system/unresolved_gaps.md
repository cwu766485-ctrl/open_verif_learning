# Unresolved Full-System Verification Gaps

Status snapshot: 2026-11-06 (Asia/Singapore)
Tested RTL/DV source SHA: `14542f52bef5a42560cc615a5db104e3122dbd33`
Decision: **OPEN**

This report records open evidence obligations, not confirmed RTL defects. See [`docs/dv/closure_phase2_execution_2026-11-06.md`](../../docs/dv/closure_phase2_execution_2026-11-06.md) for the six-phase execution record and actual regression outputs.

## Cross-Agent scenario gaps

| Scenario | Current evidence | Remaining gap |
| --- | --- | --- |
| CR01 Owner Transfer × AXI Refill × APB | Directed checked case and 100 random/mixed observations. | Closed for the tested distinct-set overlap only; no exhaustive address/stall matrix. |
| CR02 Shared Upgrade × MMIO Pending | Shared upgrade and MMIO/cache overlap are checked separately. | No same-window checker proving both lifecycles and data/order in one scenario. |
| CR03 Dirty L1 Victim × AXI Writeback Stall | Dirty L1 victim and source-side writeback stall tests pass. | Required overlap has not been established by a joint monitor/checker. |
| CR04 Dirty L2 Victim × Snoop × APB | L2 victim handling, Snoop, and APB checks exist in directed tests. | No checker proves the three-way timing/data relationship in one scenario. |
| CR05 Same-Set Directory Conflict × AXI Stall | Same-set conflict and AXI stall paths have evidence. | Same-transaction context correlation and overlap check are open. |
| CR06 Two Cold Misses × OoO R × APB | Two refill IDs/reverse R completion and APB-overlap tests pass separately. | Three-way same-window checker is open. |
| CR07 Hit-under-Miss × Remote Snoop | Directed AXI-top different-line owner Snoop during pending refill passes. | Closed for that cross-line scenario; exhaustive same-set and stall crosses remain open. |
| CR08 Reset × Directory/Snoop/Grant Pending | Reset during selected AXI/CPU/MMIO stalls and outstanding transactions passes. | Pending Directory/Snoop/Grant phase combinations are not fully constructed or checked. |
| CR09 AXI Error × Fail-Stop × Reset | Read and write response errors, fail-stop, reset and recovery have individual evidence. | Cross of RRESP/BRESP error kind with error lifecycle and reset epoch is open. |
| CR10 Ownership Ping-Pong × MMIO/APB | Ownership transfer and mixed-agent traffic are exercised. | No joint checker closes repeated ping-pong with concurrent MMIO and APB activity. |

Four Directory MSHR contexts are covered at the independent block boundary. The integrated CPU has two blocking lanes and cannot issue four simultaneous CPU misses. Integrated AXI RREADY/BREADY are tied high; APB PREADY is immediate; CPU has no upstream request tag; MMIO has no error response. These constraints are not counted as reachable system-level crosses.

## RTL coverage gaps

Primary coherent-subsystem raw results are 843/998 lines, 461/556 branches, 19980/27474 toggles, 30/54 FSM states, and 7/48 FSM arcs. The full point matrix contains 1,026 dataset-scoped zero-count records spanning separate subsystem/AXI/Block datasets. All are **OPEN**, none are auto-waived, and reviewed/eligible coverage is not calculated. The matrix keeps per-top denominators separate; Python functional coverage is not merged with Verilator source coverage.

For every point, resolution requires a source-linked feature/reachability review and test/checker, fault injection, formal evidence, reviewed waiver, or justified N/A. A source keyword or a hit in another top is not closure evidence.

## Other limits

- All six Phase 2 local regression gates passed; there were no failing seeds and thus no DUT failure trace to minimize.
- The trace minimizer is a unit-tested order-preserving primitive, not an automatic simulator callback.
- Formal evidence is component/bounded; no unbounded complete-system proof is claimed.
- Candidate branch CI is pending publication; the passing Actions run on base SHA `9b281f3` is not candidate evidence.
- PPA, STA, physical SRAM macro mapping, and chip-level implementation are excluded.
