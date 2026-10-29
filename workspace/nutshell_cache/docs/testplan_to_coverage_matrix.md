# MESI v1.0 Verification Delivery Matrix

This document connects each planned verification item to an executable test,
the checker responsible for detecting a fault, and the artifact retained for
review. The long constrained-random sweep is intentionally separate from the
normal CI gate.

## Test plan to implementation

| Priority | Requirement | Test / entry point | Independent checker / evidence |
| --- | --- | --- | --- |
| P0 | Directory lookup race and Grant/Snoop admission regressions | `tests/coherence/test_subsystem_python.py`: `test_python_seeded_randomized_coherence` (fixed replay `0x5eed`), `test_directory_lookup_grant_conflict_offset_sweep`, and `test_clean_snoop_overlaps_l2_fill_stream` | Independent byte-accurate MESI model; accepted Snoop/data/Directory commit monitors; both core directions run for clean invalidation during refill |
| P0 | Dirty owner Snoop concurrent with L2 refill | `test_dirty_owner_snoop_and_refill_share_l2_write_port_safely` | Eight-beat owner-data comparison, reference Directory comparison, no simultaneous refill/owner write-port acceptance; runs with either core as owner |
| P0 | Dense same-L2-set victim race | `make coherence_dense_set_stress` (also in `make coherence_verify`) | 20 seeds × 200 operations with nine same-set lines, dual-lane traffic and memory backpressure; independent MESI/data/Directory checkers; ownership requests serialize per L2 set and same-set Put is allowed to retire L1 victims |
| P1 | Snoop ACK recovery through authoritative L2 | `test_python_snoop_ack_retries_from_authoritative_l2` | A deterministic offset sweep creates a legal PutM/SnoopRead overlap; monitor matches ACK target and transaction ID, then checks one L2 hit refill, no DRAM/owner-data path, correct dirty word, exactly-once Grant, and independent MESI/Directory commit |
| P1 | Stale Upgrade after peer invalidation | `test_python_stale_upgrade_recovers_after_peer_invalidation` | Both L1s begin in S; Core1 wins Upgrade and invalidates Core0 while Core0's Upgrade is queued; Core0 then recovers as data-bearing GetM. Check accepted request/grant order, all eight owner-data beats, final data/Directory state, and no protocol error |
| P0 | MESI checker sensitivity and RTL mutation | `make coherence_python_verify`; `make coherence_rtl_mutation` | Python fault injection checks checker rejection; RTL mutation compiles actual `MesiL1Controller.sv` mutants and requires the module testbench to fail on the named protocol expectation |
| P1 | Coverage gap review | `make coherence_regression`; `python3 -m dv.coverage.coherence_gap_review` | `docs/coherence_coverage_gap_review.md` lists all 288 unhit merged-LCOV lines, separates 244 product RTL from 44 testbench lines, and records source-level risk and directed-closure candidates |
| D01 | Coherence vs memory-ordering litmus | `test_python_message_passing_litmus` and `test_python_generation_counter_litmus` | Producer waits for each LSU Store response; consumer checks READY/DATA/ACK on separate lines against an independent scoreboard. This validates coherence visibility under the test driver's ordering contract, not ISA acquire/release, RVWMO, or fence semantics |
| D02 | False-sharing A/B | `test_python_false_sharing_ab` | Same fixed write count, response latency and backpressure; compares separate words in one 64-byte line against separate lines. Reports RTL cycles/op, mean/P95 CPU response latency, L1/L2 hit/miss rates, memory line traffic and simulated read/write/total bandwidth, snoop, GetM/Upgrade counts and final data in `reports/coherence/false_sharing_ab.json` |
| D04 | Testplan/checker/coverage closure | `dv/coverage/python_coherence_map.json`, `make coherence_python_test`, `make coherence_python_verify` | Litmus and A/B testpoints map to independent checker events and cross bins; generated JSON/Markdown closure reports hit/miss status. Required tests are part of the Python/Toffee gate |
| P1 | Extended constrained random | `make coherence_stress` (also included in `make coherence_verify`) | 20 deterministic seeds × 200 mixed transactions; ten addresses conflict in one L1 set while spreading across four L2 sets, plus 16 spread addresses. Replay seed `0x5eed` first forces a dirty M-owner victim and a two-sharer S victim, then random traffic runs with response gaps/backpressure and independent data/Directory checks. Config, coverage counters, and JUnit results are saved under `reports/coherence/stress/` |
| P1 | Independent L1 replacement / Put check | `test_python_l1_replacement_victim_matches_put` | A separate round-robin reference predicts the two victims from six same-set fills and compares each line, core, and PutS/PutE/PutM opcode with the accepted Directory request |
| P1 | L2 live victim coverage by coherence state | `test_python_parallel_misses_l2_hit_and_dirty_writeback` and stress replay `0x5eed` | Dirty M victim must return all eight beats, complete its memory write response, and reload unchanged; a two-sharer S victim must be snooped by both cores, and any conservative owner-data writeback must preserve all eight words |
| P1 | AXI error, reset, ID reuse, ordering and 4 KiB boundary | `make coherence_axi_python_test` | Five-channel memory agent checks R/B ID routing, propagated RRESP/BRESP errors, cancellation of active read/write IDs on reset, ID reuse after retirement/reset, 4 KiB-safe 64-byte bursts, and payload stability under backpressure |
| P1 | Integrated AXI R/B response backpressure | `make coherence_axi_backpressure` | Full cache-to-AXI top holds RREADY and BREADY low for five cycles after a response arrives; checks VALID/ID/data/RESP/LAST stability and successful drain in R-only, B-only, and simultaneous R+B modes |
| P2 | Functional cross closure and bounded progress | `make coherence_python_verify` and `make coherence_formal` | Python feature/cross maps require all listed bins; module harnesses check arbitration, Directory/MSHR, L1 controller safety, plus bounded cold-GetS Grant/commit progress under an always-ready fair environment |

## Mutation sensitivity cases

| Injected fault | Expected detection |
| --- | --- |
| Unnecessary invalidation leaves an M and another valid copy | MESI single-writer invariant |
| Grant changes the transaction ID | Transaction lifecycle ID/address/opcode matcher |
| An owner-data beat is corrupted | Eight-beat owner-data scoreboard |
| Directory retains the wrong sharer bit | Directory/reference-state comparison |
| Grant is delivered twice | Exactly-once transaction lifecycle checker |
| A response payload changes while ready is low | Ready/valid stability checker |

The Python fault-injection runner mutates checker-visible observations and
proves the checker is sensitive to those faults. Separately,
`coherence_rtl_mutation` changes two real L1 controller RTL expressions,
rebuilds the DUT with the module testbench, and requires the named checker
failure. This is a small mutation set, not exhaustive RTL mutation coverage.

## Debug cases to retain

1. **Directory lookup race.** A new miss could allocate a Directory context
   while the shared L2 lookup port still selected the previous transfer/grant
   address. The fix gates both upstream `valid` and `ready` until the lookup is
   available. The fixed `0x5eed` replay checks the active and incoming line
   addresses, returned data, snoop beats, and committed Directory state.
2. **Grant valid/ready mismatch.** The Directory backpressured a Grant but the
   L1 still saw `valid`, consumed it, and waited for data that the top-level
   engine never launched. Valid and ready now share the same admission
   condition; an offset sweep checks both responses and the reference state.
3. **Snoop valid/ready mismatch during refill.** Snoop valid reached the L1
   while Directory ready was low during an L2 fill, so the L1 consumed a
   request the Directory did not own. Snoop admission is now consistent across
   both sides. Clean invalidations may overlap a refill; dirty owner data must
   wait for the shared array write port.
4. **Refill writer deadlock against owner-data SnoopRead.** A pending SnoopRead
   could take priority in the shared L2 line-write mux while its request was
   still backpressured. That suppressed the active refill writer's `valid`,
   while the SnoopRead itself waited for the refill to release the port. The
   active refill now owns the port through beat 7, and an assertion checks its
   address/beat/valid continuity. The L1 cluster also holds snoops during a
   replacement stream, preventing the snoop array read from blocking an
   eviction already in progress. The fixed 20-seed stress reproduces both
   interleavings.
5. **Replacement-model divergence under random traffic.** The checker had
   predicted L1 victim ways independently from the hardware. Concurrent snoop
   invalidations can change free-way selection, so that prediction sometimes
   reported a false Directory mismatch. The random reference model now learns
   L1 removal from accepted PutS/PutE/PutM protocol requests and still computes
   expected MESI ownership from CPU traffic and those protocol events; it does
   not sample the DUT's Directory state.
   A separate deterministic replacement test keeps the way predictor enabled
   and compares predicted L1 victims with accepted Put addresses/opcodes. The
   model also advances its L2 replacement pointer when an observed PutM returns
   a dirty line, matching the full-line write event that the RTL uses.
6. **Concurrent same-L2-set victim race.** Dense dual-core stress could make a
   live L2 victim overlap another Directory context in the same 512-set index.
   Victim invalidation removed the L1 owner while that context retained its old
   Directory snapshot; a later SnoopRead then received an invalidation ack
   instead of owner data. `DirectoryMshrBank` serializes same-set ownership
   requests while retaining four-context concurrency across distinct sets.
   Same-set Put bypasses that lock so an L1 replacement can complete and
   service an outstanding snoop. The MSHR bench checks ownership backpressure,
   Put bypass, and re-admission after grant commit; dense random replay stresses
   same-set dual-lane traffic.

## Application litmus scope (D01/D02)

`test_python_message_passing_litmus` and the 100-generation DATA/READY/ACK
test use three different cache lines. Each producer Store is completed through
the LSU driver before the next Store is issued. Their result demonstrates
coherence visibility under this explicit driver ordering. The testbench has no
real CPU pipeline, ISA fence, acquire/release instruction, or architectural
memory-model checker, so it must not be used to claim RVWMO or another CPU
memory-ordering guarantee.

The false-sharing A/B keeps the measured number of writes and configured
memory delays/backpressure equal. One case places each core's word in the same
64-byte line; the control places them in separate lines. Each workload is
preconditioned into S/S or per-core E ownership, respectively, and excludes
setup/final readback from the measured window. Reported latency and throughput
are Verilator simulation cycles, not physical clock frequency or silicon PPA.

## Commands

```bash
make coherence_python_verify
make coherence_axi_python_test
make coherence_stress
make coherence_dense_set_stress
make coherence_axi_backpressure
make coherence_rtl_mutation
make coherence_formal
PYTHONPATH=.:./dv python3 -m dv.coverage.coherence_gap_review
```

## Deferred integrated recovery closure

The remaining legal Directory, Snoop, MSHR backpressure, and replacement replay
paths are tracked as v1.1 follow-up items in
[`docs/releases/v1.1_verification_backlog.md`](releases/v1.1_verification_backlog.md).
They are not reported as covered by the current merged subsystem LCOV run.
Three representative RTL defect investigations and their passing regressions
are documented in [`docs/bug_case_studies.md`](bug_case_studies.md).

`coherence_verify` runs the component, formal, RTL, Python/Toffee, AXI, the
standard 4,000-operation stress sweep, and the dense same-set 4,000-operation
regression. Each stress target can also run independently for replay and local
debugging.

**Same-set stress:** nine read/write lines are placed in one L2 set while
dual-lane requests and memory backpressure are active. Directory allocation
serializes new ownership requests sharing that set, while Put requests bypass
the lock so L1 replacement can retire. Distinct sets can still use all four
contexts. This does not imply four-way same-set miss parallelism.

**Stale Upgrade recovery:** `test_python_stale_upgrade_recovers_after_peer_invalidation`
starts from an independently established S/S line, queues two competing
Upgrade requests, and checks that the second request is serviced as a
data-bearing GetM after the first core becomes the owner. The checker compares
the eight transferred owner beats, accepted request/Grant/Snoop ordering,
final data and Directory state, and protocol-error status. The mapped feature
is `stale_upgrade_recovery` in `dv/coverage/python_coherence_map.json`.
