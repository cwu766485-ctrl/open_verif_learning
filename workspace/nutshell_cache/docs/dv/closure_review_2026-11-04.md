# System-Level Verification Closure Review — 2026-11-04

## What was closed in this update

Added `test_dirty_owner_transfer_during_refill_with_apb_snoop_count` as a
directed full-system cross-interface scenario. It starts with Core0 holding a
modified line, then overlaps a Core1 read of that line with an unrelated AXI
refill and an APB read of the Snoop counter.

The test checks, before sampling coverage:

- all eight beats of the dirty owner's latest line data;
- both CPU return values against the independent coherence/data model;
- owner `M→S`, requester `I→S`, and final Directory sharer state;
- AXI burst completion and cycle ordering around Snoop and APB;
- APB Snoop count equals the one accepted Snoop, with no protocol/fatal error.

New required IDs are `FS.XAGENT.OWNER_TRANSFER_REFILL_APB` and
`FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET`. Both were hit by the passing
test and are present in the integrated closure artifact. Existing IDs and
Checker rules were left intact.

## Regression evidence

| Command | Result |
| --- | --- |
| `make COHERENCE_JOBS=2 coherence_full_system_cross_closure` | 1 passed |
| `make COHERENCE_JOBS=2 coherence_full_system_verify` | 57 passed, 1 skipped; Required Functional 53/53; Required Cross 29/29 |
| `make COHERENCE_JOBS=2 coherence_coverage_audit` | 7 independent elaborated tops passed |

The full-system coverage artifact reports pytest exit status 0 and no missing
required bins or crosses. `coherence_full_system_verify` also runs the existing
block, AXI, Formal, Python coherence, stress, mutation, and Benchmark v4 gates.
The standard coherence and dense-L2 stress regressions each passed their
configured 20-seed set. The integrated suite includes four configured
mixed-agent seeds. RTL mutation detection caught 4/4 injected mutations.

## Raw RTL coverage remains open

The refreshed source audit is in
[`coverage_audit_phase1.md`](../coverage_audit_phase1.md). It reconciles the
18-file RTL manifest with the compiled source manifest and reports the
following raw Product RTL coverage for its `CoherentCacheSubsystem` elaborated
top:

| Metric | Hit / total | Raw result |
| --- | ---: | ---: |
| Line | 843 / 998 | 84.5% |
| Branch | 461 / 556 | 82.9% |
| Toggle | 19,980 / 27,474 | 72.7% |
| FSM state | 30 / 54 | 55.6% |
| FSM arc | 7 / 48 | 14.6% |

There are 155 uncovered Product RTL executable lines in this run. The audit
links every line to its source and labels it for review; those labels are not
waivers or proofs of unreachability. No RTL code or coverage denominator was
changed in this update. The separate block-coverage runs are retained as
independent datasets and must not be added to the subsystem percentages.

## Remaining work and decision

- **Broader mixed-agent cross coverage:** the new three-way Owner/AXI/APB case
  is closed. This does not prove every Resource Conflict, Dirty Victim, Reset,
  and backpressure combination. Existing random campaigns cover selected
  combinations; gaps still need explicit scenario-to-bin mapping and checkers.
- **Coverage-guided random:** the current campaigns close their declared
  required bins, but the scheduler does not yet turn every uncovered plan bin
  into a legal prelude plus timing perturbation. Do not infer universal
  scenario closure from 53/53 and 29/29 for the implemented plan slice.
- **Replay/minimization:** saved seeds and transaction configurations replay
  scenarios, but do not guarantee cycle-identical interleaving across tool or
  environment changes. A generic failure-trace minimizer is not implemented.
- **Raw RTL closure:** the 155 missed lines, uncovered native points, and
  FSM arcs still need point-by-point reachability, directed/fault-injection,
  formal, or reviewed waiver evidence. Functional coverage does not discharge
  these source-coverage obligations.

Conclusion: this update closes one previously missing, independently checked
cross-interface scenario and preserves the passing integrated coverage
closure. It does not claim complete Raw RTL Coverage sign-off.
