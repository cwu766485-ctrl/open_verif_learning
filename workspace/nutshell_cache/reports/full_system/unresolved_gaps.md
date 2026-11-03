# Unresolved Full-System Verification Gaps

Status snapshot: 2026-11-03 (Asia/Singapore)
Verification base SHA: `fa7a9ef`; this report records the local DV upgrade relative to that baseline.
Product RTL changes in the full-system DV implementation: none

This list records work not evidenced as complete by the current tests. It does
not classify these items as confirmed RTL defects.

## Integrated full-system gaps

| Area | Current evidence | Remaining gap / risk |
| --- | --- | --- |
| CPU concurrency | Distinct cold misses overlap as two AXI IDs; paired same-line writes and exact same-address writes are checked against observed Directory acceptance order and final architectural data. | The integrated CPU API has two blocking lanes, so four CPU misses cannot be outstanding. The independent Directory MSHR bank test does fill all four contexts, route out-of-order refill responses, sustain progress around a snoop-blocked context, and cancel all four on reset. This is Block-level evidence, not four-requestor system-level evidence. |
| AXI read/write | Integrated read refill and two-ID out-of-order reads pass. Integrated dirty writeback checks AW, eight ordered W beats, full strobes, B association, serialized completion and backing-memory data. Integrated BRESP fail-stop and reset cancellation pass. AXI adapter Python regression passes four outstanding IDs, out-of-order B completion, channel backpressure, error and reset/ID reuse. | SharedLineEngine emits one cache victim write at a time, so integrated B reordering is not generated. The subsystem also ties RREADY high; receiver-side R backpressure is adapter-level only. |
| MMIO | Masked register writes/readback, dual-core requests, readonly APB error checks and MMIO/cache overlap are exercised. | Broader MMIO boundary, reset cancellation, and independent request/response stall combinations need expansion. |
| APB | Integrated test checks exact Hit/Miss/Snoop/Completed deltas, positive access-cycle accumulation, dirty-writeback count against observed AXI writes, error status after BRESP failure, and reset-to-zero for all CSR offsets. APB read during AXI refill remains covered. | Counter overflow/wrap behavior and an exhaustive APB/cache/AXI timing cross matrix are not tested. |
| Backpressure | Selected CPU, memory, and protocol stalls are exercised. | Complete per-channel AR/R/AW/W/B, MMIO, APB, snoop, grant, refill, and directory-ready cross coverage is not closed by the integrated run. |
| Replacement / Snoop | Integrated same-set dirty L1 replacement racing a remote GetS checks PutM, Snoop accept/response, both CPU results and protocol status. A selected live inclusive L2 victim with a resident clean L1 sharer checks back-invalidation, metadata commit to I, and subsequent refill. Dirty L2 replacement separately checks each writeback beat and backing-memory data. A legal cross-line owner-Snoop/refill overlap also passes. | The integrated suite does not yet force a dirty L2 victim while a dirty L1 owner remains live, or exhaustively cross both cores, all victim MESI states, and every Snoop/Put timing point. The same-line owner/refill case is not a legal independent memory-refill path because the M owner is the authoritative data source. |
| Reference model | CPU-visible data, byte masks, selected MESI/Directory commits, exact same-address store ordering, and dirty writeback contents are checked independently. | Full independent prediction/correlation of every MSHR allocation/retirement and every L2 victim/directory transition is not complete. |
| Random feedback | Reproducible seeded scenarios and checked coverage run; extended stress is 20 × 500 CPU operations, 20 × 10 mixed CPU/MMIO/APB/AXI rounds, and 20 resource-aware same/distinct-set seeds. | The scheduler does not adapt across all Directory, Snoop, MSHR, L2, AXI, MMIO, and APB bins. Larger planned tiers (100×500, 200×2000, 500×4000) were not run in this evidence set. |
| Replay | A committed 103-event trace was replayed successfully with scenario selection and configuration. | Scheduling is reevaluated at runtime; a general waveform exporter and failure-trace minimizer are not implemented. Replay is not cycle-identical. |
| Formal | Existing component/bounded Formal targets in `coherence_verify` pass. | No new unbounded proof of the complete integrated system is claimed. |

## RTL code-coverage gaps

The Product RTL raw audit reports line 858/1006, branch 450/536, toggle
19916/26978, FSM state 30/54, and FSM arc 7/48. There are 148 missed Product
RTL executable LCOV lines. Four manifest sources did not produce executable
line points in the selected run; see
[`rtl_coverage_summary.md`](rtl_coverage_summary.md).

Missed lines have source-context labels in
[`docs/coverage_audit_phase1.md`](../../docs/coverage_audit_phase1.md), but
this is not a completed formal reachability or waiver review. The remaining
work is to map each line/branch/state/arc to a specification feature,
test/checker or proof; review defensive/error paths; then decide whether a
directed test, fault injection, proof, or justified waiver is appropriate. No
unresolved RTL point is automatically waived here.

## Requested scenario closure

The scenarios that prompted this sign-off are closed at the following verified
interfaces. The scope column is part of the claim.

| Scenario | Evidence | Status / scope limit |
| --- | --- | --- |
| Four concurrent MSHR contexts | `make coherence_directory_mshr_bank`: 4 contexts allocated together, refills routed by ID and completed out of order, duplicate suppression, progress around a snoop-blocked context, reset cancellation; MSHR bounded Formal also passes in `coherence_verify` | **Closed at DirectoryMshrBank block level.** The integrated CPU has two blocking lanes, so four CPU misses cannot be issued simultaneously. |
| AXI dirty write, error, reset and OoO response | `test_apb_counters_writeback_and_reset_semantics` checks integrated AW, eight ordered W beats, matching B and backing-memory data; `test_axi_bresp_error_fails_stop_on_dirty_victim_writeback` and `test_reset_cancels_integrated_axi_writeback_before_b` cover BRESP fail-stop and reset cancellation; `test_axi4_four_outstanding_bursts_id_ordering_and_backpressure` checks four write IDs and out-of-order B at the adapter | **Closed at system/adapter boundaries.** Integrated writebacks are serialized by SharedLineEngine; B reordering is adapter-level, not integrated-top behavior. |
| APB event counters and reset | `test_apb_counters_writeback_and_reset_semantics` checks exact Hit/Miss/Snoop/Completed deltas, dirty writeback count against accepted AXI writes, nonzero access cycles, error status and reset-to-zero for each CSR offset | **Closed for specified event/reset semantics.** Counter wrap/saturation is not tested. |
| Same-address dual-core ordering | `test_same_address_dual_core_store_serialization` observes both Directory accepts, advances the independent data model in that order, and checks final readback against the last accepted writer | **Closed for the two-lane paired-store case.** No claim is made about an external CPU memory model beyond the interface contract. |
| Replacement and Snoop races | `test_l1_replacement_putm_races_remote_snoop` checks dirty PutM versus peer GetS/Snoop and data; `test_live_l2_victim_back_invalidates_resident_l1` checks a live clean L1 sharer is invalidated and later refilled; `test_owner_snoop_overlaps_independent_memory_refill` checks legal cross-line overlap | **Closed for these directed scenarios.** Exhaustive core × victim MESI state × timing combinations and dirty live L2 victim with a resident dirty owner remain outside this sign-off. |

## Closure boundary

- The sign-off scenario run closes 38/38 implemented Required functional bins
  and 10/10 implemented Required cross bins. Planned/unreachable full-system
  features remain uncounted; in particular `FS.MSHR.OCCUPANCY_4` remains a
  Block-level result, not a system-level bin.
- Existing Legacy, Block, AXI, Formal, Stress, and mutation entry points remain
  available with their independent scopes.
- PPA, STA, real SRAM macro mapping, silicon/physical integration, and
  application-level CPU benchmarks are outside this verification result.
- No final system sign-off or release freeze is claimed while the gaps above
  remain.

## Remote status

The local regression results are recorded for the scenario sign-off delta. A
GitHub Actions result for its commit has not been verified; local Regression
PASS is not remote CI PASS.
