# Unresolved Full-System Verification Gaps

Status snapshot: 2026-11-03 (Asia/Singapore)
Verification base SHA: `f392908c5a1e682d357f074c20588e12e098864e`; this report records the local DV upgrade relative to that baseline.
Product RTL changes in the full-system DV implementation: none

This list records work not evidenced as complete by the current tests. It does
not classify these items as confirmed RTL defects.

## Integrated full-system gaps

| Area | Current evidence | Remaining gap / risk |
| --- | --- | --- |
| CPU concurrency | Distinct cold misses overlap as two AXI IDs; paired same-line writes and exact same-address writes are checked against observed Directory acceptance order and final architectural data. | The integrated CPU API has two blocking lanes, so four CPU misses cannot be outstanding. The independent Directory MSHR bank test does fill all four contexts, route out-of-order refill responses, sustain progress around a snoop-blocked context, and cancel all four on reset. This is Block-level evidence, not four-requestor system-level evidence. |
| AXI read/write | Integrated read refill and two-ID out-of-order reads pass. Integrated dirty writeback checks AW, eight ordered W beats, full strobes, B association, serialized completion and backing-memory data. Integrated BRESP fail-stop and reset cancellation pass. AXI adapter Python regression passes four outstanding IDs, out-of-order B completion, channel backpressure, error and reset/ID reuse. | SharedLineEngine emits one cache victim write at a time, so integrated B reordering is not generated. The subsystem also ties RREADY high; receiver-side R backpressure is adapter-level only. |
| MMIO | Masked register writes/readback, dual-core requests, readonly APB errors, MMIO/cache overlap, delayed-response reset, and request-side stall/reset are checked. | Request stall and delayed response are covered separately; all MMIO request/response timing combinations with both CPU lanes, cache traffic and APB sampling are not exhaustively crossed. |
| APB | Integrated tests check exact Hit/Miss/Snoop/Completed deltas, positive access-cycle accumulation, dirty-writeback count against observed AXI writes, error status after BRESP failure, reset-to-zero for all CSR offsets, and APB read during AXI refill. `make coherence_bus_blocks` seeds each 32-bit CSR counter at the boundary, increments through real event inputs, and checks modulo-2^32 APB readback. | **Closed for integrated event/reset behavior and block-level wrap.** No test accumulates 2^32 integrated cache events. APB PREADY is combinationally immediate, so PREADY backpressure is not a supported scenario. |
| Backpressure / reset cross | New directed full-system tests reset during AXI ARREADY stall, an AXI RVALID gap, AXI AWREADY stall, AXI WREADY stall, CPU response READY-low, and MMIO request READY-low. Existing directed tests exercise delayed MMIO response, refill, owner snoop, writeback and Directory request stalls. | The tested reset/stall points pass, but this is not a complete Cartesian cross. Integrated AXI RREADY/BREADY are tied high and APB PREADY is immediate, so those receiver-side stalls cannot be generated at this top. Snoop/Grant/Directory stalls are not all crossed with reset and unrelated traffic. |
| Replacement / Snoop | Integrated same-set dirty L1 replacement racing a remote GetS checks PutM, Snoop accept/response, both CPU results and protocol status. Clean and dirty live inclusive L2 victim tests check independent victim identity/Directory prediction, resident L1 invalidation, and (for a live U owner) all eight owner-data beats, AXI writeback contents and later refill. A legal cross-line owner-Snoop/refill overlap also passes. | **Closed for these directed clean-sharer, dirty-owner, and cross-line overlap scenarios.** Exhaustively crossing both cores, every victim MESI state, and every Snoop/Put timing point remains open. |
| Reference model | CPU-visible data, byte masks, selected MESI/Directory commits, exact same-address store ordering, and dirty writeback contents are checked independently. Serial L2 replacement now compares the model's predicted victim line, Directory state/owner/sharers, resident L1 invalidations, and live-owner writeback data against observed events. | This victim checker is called from the serialized `cpu_access` path. Full independent correlation of paired-lane L2 replacements and every internal MSHR allocation/retirement remains open. |
| Random feedback | Reproducible seeded scenarios and checked coverage run; extended stress passed 20 × 500 CPU operations, 20 × 10 mixed CPU/MMIO/APB/AXI rounds, and 20 resource-aware same/distinct-set seeds. The integrated coverage suite closes 38/38 implemented Required bins and 16/16 implemented Required crosses, including six explicit reset × supported-stall crosses. | The scheduler does not adapt across every Directory, Snoop, MSHR, L2, AXI, MMIO, and APB bin. Larger planned tiers (100×500, 200×2000, 500×4000) were not run in this evidence set. |
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
| Four concurrent MSHR contexts | `make coherence_directory_mshr_bank`: 4 contexts allocated together, refills routed by ID and completed out of order, duplicate suppression, progress around a snoop-blocked context, reset cancellation; MSHR bounded Formal passes in `coherence_verify` | **Closed at DirectoryMshrBank block level.** The integrated CPU has two blocking lanes, so four CPU misses cannot be issued simultaneously. |
| AXI dirty write, error, reset and OoO response | `test_apb_counters_writeback_and_reset_semantics` checks integrated AW, eight ordered W beats, matching B and backing-memory data; `test_axi_bresp_error_fails_stop_on_dirty_victim_writeback` and `test_reset_cancels_integrated_axi_writeback_before_b` cover BRESP fail-stop and reset cancellation; `test_axi4_four_outstanding_bursts_id_ordering_and_backpressure` checks four write IDs and out-of-order B at the adapter | **Closed at system/adapter boundaries.** Integrated writebacks are serialized by SharedLineEngine; B reordering is adapter-level, not integrated-top behavior. |
| APB event counters and reset | Integrated exact event deltas, dirty-writeback accounting, error status and reset-to-zero; `make coherence_bus_blocks` also checks the modulo-2^32 boundary of all six counters. | **Closed at the integrated event/reset and CSR block wrap scopes.** No claim of accumulating 2^32 integrated events. |
| Same-address dual-core ordering | `test_same_address_dual_core_store_serialization` observes both Directory accepts, advances the independent data model in that order, and checks final readback against the last accepted writer | **Closed for the two-lane paired-store case.** No claim is made about an external CPU memory model beyond the interface contract. |
| Replacement and Snoop races | `test_l1_replacement_putm_races_remote_snoop`; `test_live_l2_victim_back_invalidates_resident_l1`; `test_dirty_l2_victim_snoops_live_modified_owner`; cross-line owner-Snoop/refill overlap. | **Closed for these directed cases.** Exhaustive core × victim MESI state × timing combinations remain outside this sign-off. The dirty-owner case checks the live L1 Owner and its writeback; the stale L2 data-array dirty bit is not used as the oracle. |
| Reset × implemented stalls | Six `test_reset_during_*` cases in `tests/full_system/test_full_system_signoff.py` cross reset with AR, R gap, AW, W, CPU response and MMIO request stalls. Each checks reset epoch, stale response cancellation, and recovery where applicable; each also samples its own Required Cross Bin only after its checker passes. | **Closed for these six interface points and represented in the Cross Coverage report.** This is not reset × every protocol stall; RREADY/BREADY backpressure is unsupported at the integrated top, and the remaining Directory/Snoop/Grant combinations need additional tests if required. |

## Closure boundary

- The sign-off scenario run closes 38/38 implemented Required functional bins
  and 16/16 implemented Required cross bins. Planned/unreachable full-system
  features remain uncounted; in particular `FS.MSHR.OCCUPANCY_4` remains a
  Block-level result, not a system-level bin.
- `make COHERENCE_JOBS=2 coherence_verify` passed locally, including Blocks,
  Formal, subsystem regression, Python/AXI regressions, stress, mutation and
  Benchmark v4. `make coherence_full_system_stress` passed its 60 seeded
  environments. `make coherence_full_system_coverage` passed 42 environments
  with one conditional saved-trace replay skipped; closure was 38/38 Required
  functional bins and 16/16 Required crosses. These are separate commands and
  scopes; `coherence_verify` alone does not run the full-system coverage target.
- Verilator reported testbench empty-pin and RTL unused-signal warnings during
  the run. They were not treated as functional failures and have not been
  represented as warning-free lint.
- PPA, STA, real SRAM macro mapping, silicon/physical integration, and
  application-level CPU benchmarks are outside this verification result.
- No final system sign-off or release freeze is claimed while the gaps above
  remain.

## Remote status

The results above are local results for the DV delta. A GitHub Actions result
for a commit containing these changes has not yet been verified; local
Regression PASS is not remote CI PASS.
