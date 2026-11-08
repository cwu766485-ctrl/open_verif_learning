# Unresolved Full-System and RTL Verification Gaps

Status snapshot: 2026-11-08 (Asia/Singapore). Functional regression and raw
coverage were generated from source SHA
`92d6373cf1bb25e3efe8a82bba9c6dde162de5e9`. Decision: **OPEN**; this evidence
does not constitute complete RTL sign-off.

## Cross-agent coverage

CR01–CR10 each have at least one evidence-backed checked instance in the
full-system checked coverage artifact. The scenario table and remaining
variation are in
[`docs/dv/verification_traceability_matrix.md`](../../docs/dv/verification_traceability_matrix.md).
Those checked instances do not exhaust core direction, address/set, stall,
response order, error beat and reset-phase combinations. The untested breadth
remains open; no scenario family is removed from the plan.

The full-system closure artifact records 53/53 Required Functional bins and
35/35 Required Cross bins, with testcase, monitor, overlap and checker evidence.
These are Python/Toffee checks and do not replace RTL source coverage.

## Raw RTL coverage gaps

The primary `CoherentCacheSubsystem_tb` Verilator dataset is:

| Metric | Hit / total | Unhit |
| --- | ---: | ---: |
| Executable line | 850 / 998 | 148 |
| Branch | 468 / 556 | 88 |
| Toggle | 19,996 / 27,474 | 7,478 |
| Extracted FSM state | 30 / 54 | 24 |
| Extracted FSM arc | 7 / 48 | 41 |

The detailed matrix contains 1,012 dataset-scoped zero-count records across
the primary subsystem, AXI subsystem and independent Block elaborations. All
remain **OPEN**, and no waiver is approved. A hit in another elaborated top is
kept as separate evidence and does not close the zero count in this dataset.

The subsystem SV testbench now includes a Hit-under-Miss scenario. Its raw run
hits the corresponding `DualL1MesiCluster.sv` source lines 419–422 and 425–427.
The AXI wrapper tests separately check transaction-ID wrap, remote Snoop and
reset. Individual zero-count branch, line, state or arc points remain open;
the previous statement that the coverage top had no Hit-under-Miss stimulus is
obsolete and has been corrected in the generated matrix.

Coverage denominators are specific to each top and metric. The 18-source RTL
manifest is reported separately from files with no executable points in a
particular elaboration. Python/Toffee coverage is not merged with Verilator
LCOV or native branch/FSM data. See
[`coverage_provenance.md`](../coherence/coverage_provenance.md) and
[`coverage_closure_matrix.csv`](../final/coverage_closure_matrix.csv).

## Regression and replay scope

- `coherence_verify`, full-system verification, Hit-under-Miss, cross closure,
  280-environment stress, seven-top coverage audit, evidence gate and replay
  closure passed locally at source SHA `92d6373...`; exact commands and counts
  are in [`docs/dv/final_verification_report.md`](../../docs/dv/final_verification_report.md)
  and [`verification_run_manifest.json`](../final/verification_run_manifest.json).
- Full-system pytest: 70 passed, one skipped. The skip is a saved-trace replay
  test with no saved DUT failure trace; a separate controlled checker-failure
  replay test passed.
- Seed 61857 injected a checker expected-data mismatch, reproduced the same
  failure signature, and reduced the operation list from five to two while
  preserving the legal M-owner prelude. This is operation-level replay and
  minimization, not cycle-by-cycle interleaving minimization.
- Formal proofs are component-level/bounded as listed in the final report; no
  unbounded whole-system proof is claimed. Mutation and checker fault
  sensitivity results are preserved as their own evidence.

## Remaining sign-off limitations

1. The 1,012 raw zero-count records need point-by-point evidence review and
   disposition. Legal recovery paths, error/defensive paths, and FSM arcs must
   not be waived from source text alone.
2. CR01–CR10 have checked representative instances, but not exhaustive
   constrained variation over all listed dimensions.
3. The CPU wrapper does not specify arbitrary multi-request response ordering;
   only the tested resident-hit bypass relative to a different pending miss is
   claimed.
4. 2-entry L1 MSHR, PPA, STA, physical SRAM macros and chip-level physical
   implementation are outside this v1.1 closure scope.
5. The latest available GitHub Actions result was for the earlier PR head
   `69d30aee6999c5a85c906ae6547b6f3872a0f474`. The report-only candidate must
   be pushed and its own CI checked before it can be called a release
   candidate. No merge or release tag is claimed here.
