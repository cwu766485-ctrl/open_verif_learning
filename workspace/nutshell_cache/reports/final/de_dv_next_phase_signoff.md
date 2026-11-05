# DE/DV Next-Phase Verification Candidate

**Decision: regression candidate PASS; full RTL coverage sign-off OPEN.**

This report records the v1.1 Hit-under-Miss and four-agent DV results on the
`cache_coherence` baseline. It does not authorize a v2 RTL branch: the raw RTL
coverage audit still has unreviewed points. No 2-entry L1 MSHR or other product
RTL feature was added.

## Source and environment

- Repository: `cwu766485-ctrl/open_verif_learning`
- Project: `workspace/nutshell_cache`
- Base ref at start: local `origin/cache_coherence` at
  `f16b7f14d7478c9148f0e0632e1183f9d71df50f`
- Work ref: `verify/gap-closure`, forked directly from that base; it does not
  contain the unrelated divergent local `cache_coherence` history.
- Product RTL changed: **no**. Changes in this phase are DV, coverage
  instrumentation/reporting, Makefile integration, traceability, and the v2
  architecture proposal only.
- Tool versions: Verilator 5.053 devel, Python 3.12.3, pytest 9.1.1.
- Baseline Actions run known before the phase: `41677618348` (success). It is
  not evidence for this candidate SHA.

## Local regression gates

Executed from the project root after `source scripts/env.sh`:

| Command | Result | Evidence / scope |
| --- | --- | --- |
| `make COHERENCE_JOBS=2 coherence_verify` | PASS | Existing block, formal, subsystem, Python/Toffee, AXI, stress, mutation and benchmark regression chain |
| `make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS | Includes the above plus integrated full-system regression; 57 passed and 1 replay test skipped because no replay trace was supplied |
| `make COHERENCE_JOBS=2 coherence_hit_under_miss` | PASS | Blocking-L1 H-u-M tests and three full AXI-top H-u-M tests |
| `make COHERENCE_JOBS=2 coherence_full_system_stress` | PASS | 260/260 seeded environments; detailed totals below |
| `make COHERENCE_JOBS=2 coherence_coverage_audit` | PASS | Independent subsystem, AXI and block coverage collection completed; raw gaps remain open |

The full-system feature closure artifact was refreshed on 2026-11-05 and reports
**53/53 Required bins** and **29/29 Required Cross bins**. The separate legacy Python coherence closure is
**49/49** and **19/19**. These are separate coverage plans; their counts are
not combined. The integrated closure JSON has exit status 0 and no missing
required entries.

The exact make command outcomes above are the local run evidence. Their full
console logs were not retained as per-command artifacts in this worktree; the
machine-readable feature closure and stress campaign CSV/summary are retained.
No claim about remote CI is inferred from these local results.

## Hit-under-Miss closure

`make coherence_hit_under_miss` now also runs
`tests/full_system/test_hit_under_miss_axi.py` against the AXI-integrated top.
Coverage is sampled only after its checker passes.

| Testpoint | Independent observations/checks | Checked coverage |
| --- | --- | --- |
| Pending miss + resident hit | Miss AR accepted; a different resident line responds while the refill is pending; returned data, response address and internal transaction ID correlate | `FS.HIT_UNDER_MISS.PENDING_MISS_HIT`; `FS.CROSS.HIT_UNDER_MISS_X_AXI_REFILL` |
| Response backpressure | Hit response payload remains stable while READY is low; miss completes and is separately matched by AXI ID/address/data | `FS.HIT_UNDER_MISS.RESPONSE_STALL` |
| Transaction-ID wrap | Repeated accepted hits advance through the 3-bit transaction-ID wrap while the original miss remains live; final miss response is matched to its request | `FS.HIT_UNDER_MISS.TXN_ID_WRAP` |
| Snoop progress | Remote GetS to a different M-owned line completes during an unrelated pending miss; owner data and observed Snoop/metadata events are checked | `FS.HIT_UNDER_MISS.SNOOP_PROGRESS`; `FS.CROSS.HIT_UNDER_MISS_X_SNOOP` |
| Reset cancellation | Accepted miss is canceled by reset; no stale response appears; retry returns independent model data | `FS.HIT_UNDER_MISS.RESET_CANCEL`; `FS.CROSS.HIT_UNDER_MISS_X_RESET` |

All five Feature bins and all three H-u-M Cross bins have checked evidence in
`reports/full_system/full_system_coverage_closure.json` and the observed counts
in `functional_coverage.json` / `cross_coverage.json`.

The CPU LSU request has no caller-supplied transaction tag. The cache returns
an internal transaction ID, address and operation, so the tested H-u-M bypass
can correlate a resident hit that completes before an earlier unrelated miss.
This establishes that specific completion reordering behavior. It does **not**
define arbitrary CPU out-of-order completion for all request combinations.
AXI has its own explicit IDs and is separately checked for reordered R
responses. The v2 proposal keeps the general CPU ordering rule open until the
LSU contract supplies tags or specifies an ordering guarantee.

## Paired misses, replacement and refill MSHR lifecycle

The integrated test set closes the previously reported paired-miss gaps:

- `test_dual_cold_misses_overlap_and_route_axi_responses` checks two active
  refill MSHRs, two allocations and retirements, reversed AXI R completion ID
  order, all 16 returned/refill beats, and each CPU line's independent data.
- `test_paired_cold_miss_same_set_uses_directory_accept_order` delays one
  request lane and checks the observed Directory acceptance order before
  applying the same-set replacement model.
- `test_repeated_paired_misses_replace_one_l2_set` runs two paired rounds and
  checks all four observed victims against independent replacement
  predictions.
- `test_paired_hit_and_miss_checks_dirty_l2_victim` checks the model-predicted
  dirty owner, invalidation, writeback and data preservation under paired
  hit/miss traffic.

Coverage IDs are `FS.CONCURRENCY.PAIRED_MISS_ORDERING`,
`FS.CONCURRENCY.PAIRED_SAME_SET_REPLACEMENTS`,
`FS.CONCURRENCY.PAIRED_L2_DIRTY_VICTIM`, `FS.MSHR.LIFECYCLE_END_TO_END` and
their corresponding `FS.CROSS.*` bins. These close only the tested two-request
integrated lifecycle. They do not claim four simultaneous CPU misses: the
system has four downstream Directory/refill contexts, while each CPU lane is
still blocking.

This closes the paired miss/miss ordering, repeated same-set replacement, and
full refill MSHR lifecycle scenarios previously listed as remaining gaps.
:codex-annotation{index="1"}

## Four-agent stress results

`reports/full_system/stress_seed_summary.csv` contains one reproducible row per
seed with configuration, checked-bin delta, monitor transaction counts,
protocol/error counters and a replay command. The compact campaign summary is
`reports/full_system/stress_campaign_summary.md`.

| Campaign | Result | Work / observations |
| --- | --- | --- |
| `FULL_SYSTEM_RANDOM` | 100/100 PASS | 100 × 500 configured CPU operations; dual-core MESI/coherence traffic; AXI read reordering; max refill MSHR occupancy 2 |
| `SEEDED_MIXED_CPU_MMIO_APB_AXI` | 100/100 PASS | 100 × 500 mixed rounds; CPU, MMIO, APB and AXI; APB reads during refill. This campaign observed zero Snoop accepts, so it is not evidence for Snoop overlap |
| `RESOURCE_AWARE_SNOOP_REFILL` | 20/20 PASS | 20 owner/Snoop cases; 10 same-L2-set and 10 distinct-L2-set Snoop/refill crosses |
| `RANDOMIZED_RESET_PHASE` | 20/20 PASS | Reset in AR stall, accepted-read R gap, held CPU response and MMIO request stall; five seeds per phase |
| `RANDOMIZED_AXI_READ_ERROR_RECOVERY` | 20/20 PASS | One selected SLVERR beat per seed; no successful CPU data response on fault; reset and independently checked retry |
| **Total** | **260/260 PASS** | 100,000 configured CPU/mixed operations or rounds, plus targeted resource/recovery campaigns; zero final protocol/fatal errors; 20 intentional AXI error injections; zero failing seeds/replays |

The counters are monitor observations and are not interchangeable with
configured operation counts. The 100 mixed rounds include 50,000 APB
completions and 50,000 MMIO request/response pairs. In that campaign AXI
read-address/R-beat counts were 50,000/400,000. Trace capture records failing
operation prefixes and failure context. A trace minimizer is not implemented;
there were no failed seeds to minimize.

## Raw RTL coverage and closure decision

`make coherence_coverage_audit` completed on the current RTL manifest and
reported independent elaborated scopes. Do not add or average their
denominators.

| Independent dataset | Line hit/total | Branch hit/total | Toggle hit/total | FSM states | FSM arcs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full coherent subsystem | 843/998 | 461/556 | 19980/27474 | 30/54 | 7/48 |
| AXI subsystem E2E (5 fixed seeds) | 901/1074 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| DirectoryController block | 117/188 | 30/42 | 236/612 | 9/10 | 2/9 |
| DirectoryMshrBank block | 167/292 | 100/128 | 1063/2904 | 31/40 | 11/36 |
| SharedLineEngine block | 101/104 | 44/52 | 304/648 | N/A | N/A |
| MesiL1Controller block | 104/132 | 40/46 | 629/1804 | 7/7 | 2/6 |
| SharedL2DirectoryArray block | 75/79 | 65/74 | 197/1778 | N/A | N/A |
| Bus blocks | 67/68 | 70/76 | 1100/2450 | N/A | N/A |

The primary subsystem dataset has 155 uncovered line points, 95 uncovered
branch points, 24 uncovered FSM states and 41 uncovered FSM arcs. The
dataset-scoped matrix lists 1,026 zero-count observations across separate
builds; it is not a count of unique design defects. In the primary dataset,
226 points carry a high-risk label and 230 mapped points have not received
individual point-level review. No waiver is approved and no unreachable or
redundant classification is inferred from source keywords.

The four manifest files without executable points in a given top are listed
as N/A in `coverage_closure_raw_runs.md`; the AXI and Block datasets separately
exercise some of those sources. Python/Toffee functional coverage is not
merged into Verilator source coverage because it is generated by a distinct
simulator/build and does not emit compatible source points.

**Closure decision: OPEN.** Functional/cross closure and the listed system
scenarios pass, but the raw RTL line/branch/FSM gaps and their individual
checker/proof review are not closed. This is a regression and coverage-audit
candidate, not a final Functional RTL + DV sign-off. No RTL v2 branch is
created in this phase.

## Artifacts and residual limits

- `docs/dv/verification_traceability_matrix.md`: testcase → observed event →
  checker → checked coverage mapping and response-order contract.
- `reports/full_system/full_system_coverage.json`: raw 57-run integrated-top
  evidence, including the owner-transfer/refill/APB testcase.
- `reports/full_system/full_system_coverage_closure.json`: 53/53 Required and
  29/29 Cross evidence from that raw run.
- `docs/dv/coverage_evidence_refresh_2026-11-05.md`: report consistency and
  testcase-to-monitor/checker evidence for the refresh.
- `reports/full_system/stress_seed_summary.csv` and
  `reports/full_system/stress_campaign_summary.md`: per-seed regression
  outcomes.
- `reports/coherence/coverage_closure_raw_runs.md`,
  `reports/coherence/coverage_closure_matrix.csv`, and
  `reports/final/coverage_closure_matrix.csv`: independent raw scopes and
  source/line gap inventory.
- `docs/l1_2entry_mshr_v2_proposal.md`: next-version architecture proposal;
  it does not change product RTL.

Not signed off here: complete point-by-point RTL coverage review, arbitrary
CPU response reordering, four simultaneous CPU misses, trace shrinking,
PPA/STA, physical SRAM macros, and chip-level physical implementation.
Remote GitHub Actions status must be read for the pushed candidate commit; the
historical baseline run is not a substitute.
