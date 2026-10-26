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
| P0 | MESI scoreboard/checker mutation sensitivity | `PYTHONPATH=.:./dv python3 -m dv.fault_injection.run` (also part of `make coherence_python_verify`) | Injects false hit, corrupt writeback and owner data, dropped stalled payload, duplicate response/Grant, unnecessary invalidate, mismatched Grant ID, and wrong Directory sharer; each must raise from its named checker |
| P1 | Extended constrained random | `make coherence_stress` (also included in `make coherence_verify`) | 20 deterministic seeds × 200 mixed transactions; ten addresses conflict in one L1 set while spreading across four L2 sets, plus 16 spread addresses. Replay seed `0x5eed` first forces a dirty M-owner victim and a two-sharer S victim, then random traffic runs with response gaps/backpressure and independent data/Directory checks. Config, coverage counters, and JUnit results are saved under `reports/coherence/stress/` |
| P1 | Independent L1 replacement / Put check | `test_python_l1_replacement_victim_matches_put` | A separate round-robin reference predicts the two victims from six same-set fills and compares each line, core, and PutS/PutE/PutM opcode with the accepted Directory request |
| P1 | L2 live victim coverage by coherence state | `test_python_parallel_misses_l2_hit_and_dirty_writeback` and stress replay `0x5eed` | Dirty M victim must return all eight beats, complete its memory write response, and reload unchanged; a two-sharer S victim must be snooped by both cores, and any conservative owner-data writeback must preserve all eight words |
| P1 | AXI error, reset, ID reuse, ordering and 4 KiB boundary | `make coherence_axi_python_test` | Five-channel memory agent checks R/B ID routing, propagated RRESP/BRESP errors, cancellation of active read/write IDs on reset, ID reuse after retirement/reset, 4 KiB-safe 64-byte bursts, and payload stability under backpressure |
| P2 | Functional cross closure and formal baseline | `make coherence_python_verify` and `make coherence_formal` | Python feature/cross maps require all listed bins; existing module formal harnesses check arbitration, Directory/MSHR, and L1 controller properties at their configured bounded depths |

## Mutation sensitivity cases

| Injected fault | Expected detection |
| --- | --- |
| Unnecessary invalidation leaves an M and another valid copy | MESI single-writer invariant |
| Grant changes the transaction ID | Transaction lifecycle ID/address/opcode matcher |
| An owner-data beat is corrupted | Eight-beat owner-data scoreboard |
| Directory retains the wrong sharer bit | Directory/reference-state comparison |
| Grant is delivered twice | Exactly-once transaction lifecycle checker |
| A response payload changes while ready is low | Ready/valid stability checker |

The mutation runner succeeds only when every injected fault is rejected. These
are checker-sensitivity tests; they do not claim that each fault was compiled
into and injected into the RTL netlist.

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

## Commands

```bash
make coherence_python_verify
make coherence_axi_python_test
make coherence_stress
make coherence_formal
```

`coherence_verify` runs the component, formal, RTL, Python/Toffee, AXI and
4,000-operation stress gates together. `make coherence_stress` runs the same
long random sweep by itself for replay and local debugging.

**Open stress limit:** a separate experiment placed nine random read/write
lines in one L2 set while dual-lane requests and backpressure were active. It
produced Directory-state mismatches or response timeouts/protocol errors in
14/20 seeds. The accepted sweep keeps L1 replacement pressure across four L2
sets and uses a deterministic sequential nine-line prologue for dirty-owner
and two-sharer live victims; the denser same-set concurrent case remains to be
debugged before claiming full closure of that stress corner.
