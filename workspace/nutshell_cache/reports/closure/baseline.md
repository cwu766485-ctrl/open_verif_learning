# DV Closure Phase 2 Baseline

## Source and repository state

- Repository: `cwu766485-ctrl/open_verif_learning`
- Requested base branch: `cache_coherence`
- Local work branch: `dv-closure-phase2`
- Tested source baseline: `9b281f3bd1d6b5dbdf9bb257313dd61a21d87252`
- `origin/cache_coherence` pointed to the same commit at audit start.
- The working tree was clean at audit start. Phase 1 changes are kept on the
  dedicated work branch.
- No change to the product RTL or its interfaces is in scope.

## Existing system-level verification baseline

- Existing integrated-top closure artifact: 53/53 Required Functional bins and
  29/29 Required Cross bins.
- Existing full-system testcase artifact: 57 run records, pytest exit status 0.
- These checked-coverage artifacts predate this phase: they did not record a
  source SHA or tool versions. Their counts are preserved as historical
  baseline only; they are not treated as reproducible evidence for this source
  SHA until the Phase 6 regression regenerates them.
- The full-system random campaigns use a blocking L1 request contract; four
  refill MSHRs do not mean four concurrent CPU misses. AXI RREADY/BREADY are
  fixed receiving behavior at the integrated top, APB PREADY wait states are
  not injectable, MMIO has no independent error response, and LSU responses
  do not promise arbitrary out-of-order completion.

## RTL coverage baseline

The prior main-subsystem dataset reported:

| Metric | Hit / total | Rate |
| --- | ---: | ---: |
| Line | 843 / 998 | 84.5% |
| Branch | 461 / 556 | 82.9% |
| Toggle | 19,980 / 27,474 | 72.7% |
| FSM states | 30 / 54 | 55.6% |
| FSM arcs | 7 / 48 | 14.6% |

These numbers are one elaborated top/dataset. They are not added to Block or
AXI-top reports. Prior source-point matrices contain dataset-scoped zero-count
records; these are observations, not 1,026 independent RTL defects. No
automatic waiver is accepted by this phase.

## CI evidence at audit start

The task attachment identifies the baseline GitHub Actions run as PASS. A live
commit-status query for `9b281f3` returned no status records, so this audit
cannot independently associate a green workflow run with the exact baseline
SHA. Remote CI for new commits must be checked after the branch is pushed.

## Local tool versions observed

- Python 3.12.3
- pytest 9.1.1
- Verilator 5.053 development build (`v5.052-521-g6388139f7`)
- Picker 0.9.0-HEAD-c100874-2026-08-06
- SymbiYosys 0.70

The Phase 6 run records the exact executable and Python package version strings
in the generated evidence artifacts.
