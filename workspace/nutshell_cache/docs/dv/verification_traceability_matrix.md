# Full-System Verification Traceability

This matrix distinguishes integrated-top evidence from block-only evidence.
A feature/cross bin is credited only after the listed independent checker has
passed; Verilator RTL source coverage is reported separately and is never
added to Python functional coverage.

| Requirement | Testpoint / sequence | Observation | Independent checker | Coverage / status |
| --- | --- | --- | --- | --- |
| Cold cacheable read and AXI refill | `FS-D01`, `test_dual_core_coherence_uses_axi_backing_memory` | CPU handshake, AXI AR/R ID and beats, L1/Directory metadata commits | Backing memory contents, AXI protocol checker, MESI/data scoreboard | `FS.AXI.READ_BURST`, `FS.MESI.I_TO_E`; Closed |
| MESI legal state transitions | `SC01–SC05`, state-aware preludes | Directory GetM, L1 metadata commits and CPU lifecycle | Independent MESI/data scoreboard | Required MESI bins; Closed for planned legal transitions |
| Remote owner read/write transfer | `FS-D02/D03` | Snoop, owner data, Directory/L1 commits | Scoreboard checks latest word data and owner/sharer state | MESI transition bins; Closed for tested paths |
| Same-address paired store serialization | `SC06`, `test_same_address_dual_core_store_serialization` | Directory acceptance order | Both responses and final value match acceptance-ordered model | `FS.CONCURRENCY.SAME_ADDRESS_DUAL_WRITE`; Closed |
| Paired same-set cold misses preserve request order | `test_paired_cold_miss_same_set_uses_directory_accept_order` | CPU accept, Directory accept, AXI ID/refill, response | Request-order reference plus ID/address/data matching | `FS.CROSS.PAIRED_MISS_ORDERING`; Closed |
| Repeated paired replacement in one L2 set | `test_repeated_paired_misses_replace_one_l2_set` | Four victim selections across two paired rounds | Predicted victim, invalidation, data and final readback | `FS.CROSS.PAIRED_SAME_SET_REPLACEMENTS`; Closed |
| Full refill MSHR lifecycle and response association | Same paired miss testpoints and `SC08` | MSHR allocate/retire, AXI ID/beats, CPU response | Independent per-line data and transaction lifecycle check | `FS.CROSS.MSHR_LIFECYCLE_END_TO_END`; Closed for one/two active system requests |
| Two distinct cold misses overlap and return out of order | `SC08`, `test_dual_cold_misses_overlap_and_route_axi_responses` | Two AXI IDs, peak two refill MSHRs, reverse R completion | Per-ID data routing and CPU response data | `FS.MSHR.OCCUPANCY_2`, `FS.AXI.READ_OUT_OF_ORDER`; Closed; CPU lanes remain blocking |
| Four Directory contexts | Directory MSHR block regression | Four independent Directory contexts and arbitration | Block lifecycle/formal harness | Block scope only; does not claim four simultaneous CPU misses |
| L2 live victim invalidation / dirty owner preservation | `SC07/SC10` | Victim, Snoop, metadata invalidation, owner beats, AXI writeback | Independent directory/data model and memory readback | `FS.L2.LIVE_VICTIM_SNOOP`, serialized writeback bins; Closed for directed variants |
| Hit-under-miss on the full AXI top | `tests/full_system/test_hit_under_miss_axi.py` | Pending miss AXI ID/address plus resident hit response address/data/ID | Independent CPU data model, AXI ID correlation, response stability | `FS.HIT_UNDER_MISS.*`, `FS.CROSS.HIT_UNDER_MISS_*`; Closed for resident-hit bypass cases |
| Hit-under-miss with remote Snoop progress | `test_axi_top_snoop_completes_during_other_line_pending_miss` | Pending unrelated refill and owner Snoop accepted/completed | Owner's latest data, MESI commits, CPU response checks | H-u-M Snoop cross; Closed for tested cross-line case |
| Dirty-owner transfer + AXI refill + APB counter | `test_dirty_owner_transfer_during_refill_with_apb_snoop_count` | M→S owner transfer, eight owner-data beats, unrelated AXI AR/R, APB Snoop-count read and cycle order | Independent MESI/data/Directory model, AXI burst/ID checker, APB count equals one accepted Snoop | `FS.XAGENT.OWNER_TRANSFER_REFILL_APB`; `FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET`; directed case Closed |
| Hit-under-miss reset cancellation | `test_axi_top_reset_cancels_pending_hit_under_miss_request` | Reset epoch, canceled AXI context, no stale response, retry | AXI agent cancellation and reference data | H-u-M reset bin; Closed |
| Reset during AR stall, R gap, CPU response stall, MMIO request stall | `test_seeded_reset_during_randomized_stall` | Each seeded phase is explicitly observed before reset; reset epoch and retry | AXI/MMIO handshakes, stale response exclusion, independent returned data | `FS.STRESS.RESET_*`; targeted and stress evidence recorded in campaign output |
| AXI R error beat injection and recovery | `test_seeded_axi_read_error_beat_and_recovery` | Chosen beat address/RESP, fail-stop, reset and retry | Error correlated to selected beat; no success response; retry matches memory model | `FS.STRESS.AXI_R_ERROR_BEAT_INJECTION`; targeted and stress evidence recorded |
| Four-agent sustained traffic | `test_seeded_full_system_coherence`, `test_seeded_cpu_mmio_apb_axi_overlap` | CPU, Directory, Snoop, refill, MMIO, APB and AXI events | Independent MESI/data/MMIO/APB models plus AXI protocol checker | Random and four-agent bins; counts in stress CSV/summary |
| AXI write errors and channel ordering | Integrated signoff and standalone AXI adapter tests | AW/W/B IDs, response and stalls | AXI burst/ID checker, fail-stop and memory readback | Integrated supported paths plus adapter's four-ID reordering; integrated writes are serialized |
| CPU response ordering contract | Full-system CPU wrapper | No request tag input; response returns internally allocated transaction ID, address and operation | Driver lifecycle checker plus H-u-M address/data/ID correlation | No general arbitrary OoO contract is specified. A resident hit may complete before an earlier unrelated miss in the tested H-u-M bypass case; other completion orders remain unspecified |
| APB CSR counter/reset semantics | `SC17` | APB access, event deltas and reset | Expected counter deltas for checked transactions | CSR directed bins; wrap/saturation remains Open unless run evidence says otherwise |
| Raw RTL line/branch/toggle/FSM | `make coherence_coverage_audit` separate subsystem and block tops | Each elaborated top's own Verilator dataset | Source manifest and point-level coverage matrix | Raw results remain separate; reviewed/eligible closure has open items |

## Coverage scope and limitations

The full-system Python functional closure is generated from
`dv/coverage/full_system_coverage_plan.json`. Do not combine it with the
separate 49-bin Python coherence closure, block test results, bounded formal
proofs, or raw Verilator line/branch/toggle/FSM percentages. Each uses a
different testbench, point definition, or elaborated design scope.

The present CPU wrapper has two packed blocking lanes and no request tag input.
It can exercise simultaneous paired requests and a resident L1 hit while a
different miss is pending, but it does not define arbitrary multi-request CPU
completion reordering. Four Directory contexts and four refill MSHRs are not
evidence that four CPU misses can be issued concurrently.

The stress campaign records one row per seed in
`reports/full_system/stress_seed_summary.csv`, including configured workload,
observed handshakes, checked-bin deltas, and replay command. There is no failing
seed in a passing campaign; trace minimization is not claimed as implemented.

The directed owner-transfer/refill/APB scenario is run by
`make coherence_full_system_cross_closure`; it complements the larger random
campaigns, which do not guarantee this exact three-way overlap.

## Reproduction

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_full_system_verify
make COHERENCE_JOBS=2 coherence_hit_under_miss
make COHERENCE_JOBS=2 coherence_full_system_stress
make COHERENCE_JOBS=2 coherence_coverage_audit
```

See `reports/final/de_dv_next_phase_signoff.md` for the current run SHA,
results, and remaining sign-off boundaries.
