# Full-System Verification Traceability

This matrix records evidence from the integrated Python/Toffee environment and
keeps it separate from raw Verilator RTL coverage. A checked functional or
cross bin requires observed monitor events and an independent checker pass.

Evidence baseline: source SHA `92d6373cf1bb25e3efe8a82bba9c6dde162de5e9`,
local regression snapshot 2026-11-08. The report-only candidate commit and its
GitHub Actions status are recorded separately in
[`final_verification_report.md`](final_verification_report.md).

## CR01–CR12 checked scenario instances

| ID | Scenario | Checked evidence | Status and remaining scope |
| --- | --- | --- | --- |
| CR01 | Dirty owner transfer × independent refill × APB | Directed overlap at cycle 163, four correlated transactions, independent MESI/data/Directory/MSHR and APB count checks; also exercised by mixed-agent seeds. | **Verified instance**; randomized address/stall breadth remains open. |
| CR02 | Shared upgrade × MMIO pending | Seed 49154, checked overlap at cycles 90–92 and MMIO/cache response checks. | **Verified instance**; broader timing and address variation open. |
| CR03 | Dirty L1 victim × AXI writeback stall | Seeds 49155 and 49411; victim/PutM and AXI AW/W/B events checked under writeback stall. | **Verified instances**; longer stall and alternate core variants open. |
| CR04 | Dirty L2 victim × Snoop × APB | Seeds 49156 and 49412; dirty-owner data, victim reclaim, Snoop and APB events correlated. | **Verified instances**; additional victim ways and stall combinations open. |
| CR05 | Same-set Directory conflict × AXI stall | Seeds 49413 and 49415; same-set conflict, AR stall and refill lifecycle checked. | **Verified instances**; wider resource-pressure sweep open. |
| CR06 | Dual cold miss × out-of-order AXI R × APB | Seed 49158; two refill contexts overlap and first two AXI R responses complete in reverse order with ID/data routing checks. | **Verified instance**; repeated response permutations open. |
| CR07 | Hit-under-miss × remote Snoop | Directed overlap cycles 67–78, five correlated transactions; checker verifies independent pending miss and remote-owner Snoop/data transfer. | **Verified instance**; randomized addresses/stalls open. |
| CR08 | Reset × Directory/Snoop pending | Seeds 59248–59251 and stress seeds 59248–59267 exercise pending Directory/Snoop reset epoch and recovery. | **Verified instances**; all reset phases and interface combinations are not exhaustive. |
| CR09 | AXI error × fail-stop × reset | Seeds 59248–59251 and stress seeds 59248–59267 inject read error beats, check no false success, reset and retry. | **Verified instances**; write-channel and all error-beat positions are not exhaustive. |
| CR10 | Ownership ping-pong × MMIO/APB | Seeds 49168 and 49424; ownership transitions and MMIO/APB activity checked by the independent model. | **Verified instances**; broader ping-pong depth and timing open. |
| CR11 | Complementary Byte Mask × ownership × dirty L2 eviction | Seeds 49156/49412; Core0/Word0/Set0 and Core1/Word7/Set511; 0xAA/0x55 reference merge, observed GetM/Snoop/M-to-I, dirty victim owner beats, AXI writeback and complete 8-word refill readback. | **Verified instances**; exact directed edge configurations checked, not a Cartesian address sweep. Extends CR04 with an independent required Cross checker. |
| CR12 | AXI R beat interleaving × MSHR/L2/CPU lifecycle | Seed 49158; two distinct AXI IDs, sixteen beat records, per-ID Beat0–7/address signatures/RLAST and a sampled RID switch before first RLAST; lifecycle checker correlates allocate, AR/R, L2 fill, grants, responses and retirement. | **Verified instance**; no claim of all 8! response permutations. Extends CR06. |

Candidate Cross deduplication: `MASK_OWNER_EVICT` and `AXI_R_BEAT_INTERLEAVE` lacked their required independent checker contracts and were added by extending CR04/CR06. `PUTM_GETM_WSTALL` is not credited: CR03 checks PutM × AW stall and CR05 checks GetM × AR stall, but no trace demonstrates all three as a legal overlapping event; the current serialized line-write path makes a simultaneous AXI writeback overlap structurally unavailable while a conflicting GetM owns the line. `HUM_SNOOP_RESPSTALL` remains outside required coverage because CR07 proves hit-under-miss × Snoop while response backpressure is separately checked; no existing trace proves the three-way overlap, and the CPU lane response hold is not an independent cache transaction. `DIR_OFFERLOCK_CONFLICT` is covered by Directory block tests/formal stability checks, but no integrated independent cross checker was found; candidate is deferred because no demonstrated legal integrated conflict trace is present. `MMIO_SAME_ADDR_ARB` remains optional: the contract only promises dual-lane distinct-address arbitration and the CPU request interface serializes the packed lanes; it is not a required same-address concurrency behavior.

These statuses close the named checked instances, not the Cartesian product of
all Core, address, response-order, stall, error and reset combinations.

## Feature and interface traceability

| Requirement | Testpoint / sequence | Observation | Independent checker | Coverage / status |
| --- | --- | --- | --- | --- |
| Cold cacheable read and AXI refill | `FS-D01`, `test_dual_core_coherence_uses_axi_backing_memory` | CPU handshake, AXI AR/R ID and beats, L1/Directory commits | Backing memory, AXI protocol and MESI/data scoreboards | Required MESI/AXI bins; verified |
| MESI transitions and remote-owner data | `SC01–SC05`, seeded state-aware sequences | GetM, Snoop, owner data and metadata commits | Independent MESI/data model and Directory consistency checker | Required planned transitions; verified for exercised paths |
| Same-address dual-store ordering | `SC06`, `test_same_address_dual_core_store_serialization` | Directory acceptance order and both responses | Acceptance-ordered memory model and final readback | `FS.CONCURRENCY.SAME_ADDRESS_DUAL_WRITE`; verified |
| Paired same-set cold misses | `test_paired_cold_miss_same_set_uses_directory_accept_order` | CPU/Directory accept, AXI IDs/refills and response order | Request-order/data checker | `FS.CROSS.PAIRED_MISS_ORDERING`; verified |
| Repeated paired replacement | `test_repeated_paired_misses_replace_one_l2_set` | Four victim choices over two rounds | Victim-way, invalidation, data and readback checker | `FS.CROSS.PAIRED_SAME_SET_REPLACEMENTS`; verified |
| Refill MSHR lifecycle / out-of-order AXI R | `SC08`, paired-miss tests | Allocation/retirement, AXI ID/beat correlation; peak two active system refills | Per-ID data and lifecycle checker | `FS.MSHR.OCCUPANCY_2`, `FS.AXI.READ_OUT_OF_ORDER`; verified; CPU lanes remain blocking |
| Four Directory contexts | `DirectoryMshrBank` block tests and formal harness | Four contexts, transfer-start backpressure, reset cancellation | Block lifecycle assertions/checker and bounded formal | Block scope only; not four concurrent CPU misses |
| L2 live victim / dirty owner writeback | `SC07/SC10`, dense-set tests | Victim snoop, directory clear, owner beats and memory writeback | Independent directory/data model and memory readback | L2 victim/writeback bins; verified for directed cases |
| Hit-under-miss on instrumented subsystem top | `hit_under_miss_coverage.svh` in `CoherentCacheSubsystem_tb` | Pending cold miss, resident hit response, distinct transaction IDs, 3-cycle response stall, then miss completion | Data/response checker checks both values and response stability | Main subsystem raw LCOV: related source lines 419–422 and 425–427 hit; remaining zero-count branch/points stay open |
| Hit-under-miss in AXI wrapper | `tests/full_system/test_hit_under_miss_axi.py` | ID wrap/stall, remote Snoop while another line is pending, reset cancellation | CPU/AXI ID and data correlation, reset epoch and response checker | H-u-M AXI functional tests; verified; separate raw dataset |
| Four-agent traffic and recovery | Seeded CPU/MMIO/APB/AXI, reset and AXI error tests | Accepted protocol events, overlap intervals, reset epochs and response IDs | Independent reference data/MESI/MMIO/APB models plus AXI checker | Full-system checked functional/cross plan; 53/53 and 35/35 |
| APB CSR counter semantics | `test_apb_counters_writeback_and_reset_semantics` | APB read/write, event deltas and reset | Expected event-counter deltas | Tested semantics verified; complete wrap/saturation space remains open |
| Raw RTL line/branch/toggle/FSM | `make coherence_coverage_audit` | Instrumented source points per elaborated top | Manifest and point-level matrix | Separate datasets; no cross-top sum or Python substitution |

## Contract and limitations

- The CPU wrapper has two packed request lanes and no externally supplied
  request tag. A resident hit can respond before a different pending miss, as
  tested by Hit-under-Miss; arbitrary completion reordering is not specified.
- Full-system coverage uses `dv/coverage/full_system_coverage_plan.json`.
  Coherence block Python bins, full-system bins, block SV results, formal
  properties, and raw Verilator points have different denominators and are not
  added together.
- The stress campaign contains 280 passing environments. Its generated CSV
  records per-seed configuration, observed events and checked-bin deltas.
- A controlled checker expected-data mismatch on seed 61857 was captured and
  replayed on RTL. The operation reducer preserved the legal owner-store
  prelude and reduced the trigger trace from five operations to two. It is
  operation-level reduction, not general cycle-by-cycle interleaving
  minimization.
- Raw RTL coverage remains OPEN: the primary subsystem dataset has 148 missed
  executable lines, 88 missed branches, 24 missed extracted FSM states and 41
  missed extracted FSM arcs. See the raw-run inventory and closure matrix.

## Reproduction

Run from `workspace/nutshell_cache` with the repository tool environment:

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
