# Python/Toffee Full-System Verification Results

Date: 2026-11-03 (Asia/Singapore)
Verification base: local branch `codex/full-system-graybox-closure` at `fa7a9ef` before this DV-only delta; final source SHA is recorded by Git after commit.

## Delivered scope

The integrated verification slice targets `CoherentCacheAxiSubsystem` through
the verification-only packed wrapper. It uses coordinated dual-lane CPU,
AXI4 backing-memory, MMIO, and APB agents, passive internal observation,
independent data/coherence checks, checked functional coverage, seeded random
traffic, and JSONL trace/replay. This remains Python/Toffee with UVM-style
responsibilities, not SystemVerilog UVM. No product RTL behavior or interface
was changed.

The current sign-off delta adds eight directed full-system scenarios for
same-line and same-address dual-core stores, dirty L1 PutM versus remote
Snoop, inclusive L2 victim back-invalidation, owner Snoop overlapping an
independent refill, APB event/writeback/reset semantics, BRESP fail-stop, and
reset during an accepted dirty writeback. The independent reference checks
architectural data and observed protocol lifecycle before functional coverage
is credited. No product RTL functionality or interface changed.

This DV upgrade adds a seeded four-agent mixed scenario: both CPU lanes issue
a cacheable miss and mapped MMIO request together, APB samples the Miss counter
after AXI AR and before the final refill beat, and the MMIO response is held
until after refill completion. Four fixed seeds each run six operations with
varied CPU lane, cache/MMIO read/write, byte masks and CPU response holds. AXI
ARREADY stalls and source-side RVALID gaps are injected. The cache reference,
MMIO model, APB count checker, AXI protocol/data checker and observed metadata
commits must all agree before the new coverage bins are credited.

The AXI protocol agent now reports its already-checked channel handshakes to
the full-system event monitor. This removes a same-edge Toffee scheduling race
that occasionally caused the passive pin sampler to miss an accepted AXI
handshake. RTL-internal metadata, MSHR, Directory, L2, Snoop and stall/valid-gap
observations remain passive and are not used as expected-state inputs.

The resource-aware extension compares same-set and distinct-set M-owner Snoop
traffic against an active independent-line refill. It checks accepted CPU
requests, Directory/Snoop acceptance relative to refill retirement, all eight
owner-data beats, the M-to-S metadata commit, and both CPU return values. The
existing `same_set_conflict` observation is an unqualified internal signal and
is intentionally not used as coverage evidence.

## Results on implementation SHA

| Entry point | Result | Scope |
| --- | --- | --- |
| `python3 -m pytest -q tests/full_system/test_mixed_agent_random.py` with `.tooling` on `PYTHONPATH` | PASS, 4 passed | Four reproducible seeds × six checked mixed CPU/MMIO/APB/AXI operations; independent data models and cross-agent cycle ordering checked. |
| `python3 -m pytest -q tests/full_system/test_resource_aware_random.py` with `.tooling` on `PYTHONPATH` | PASS, 4 passed | Two same-set and two distinct-set seeded Snoop/refill cases; request ordering, eight owner beats and independent CPU data checked. |
| `make coherence_full_system_stress` | PASS, 60 passed | 20 seeds × 500 CPU operations, 20 mixed-agent seeds × 10 rounds, and 20 resource-aware set-contention seeds. |
| `make coherence_full_system_coverage` | PASS, 35 passed / 1 skipped | Integrated directed/seeded suite plus four-agent and same/distinct-set scenarios; Required bins 38/38, Required crosses 10/10. The skip is replay without a supplied trace path. |
| `make COHERENCE_JOBS=2 coherence_directory_mshr_bank` | PASS | Four Directory contexts active together; distinct refill IDs and out-of-order fills; duplicate suppression; held payload stability; three independent contexts progress around a snoop-blocked context; reset cancels all four. The target also checks its existing bounded formal harness under `coherence_verify`. |
| `make COHERENCE_JOBS=2 coherence_axi_python_test` | PASS, 3 passed | Four outstanding read and write IDs; out-of-order R and B completion; all five AXI channel stalls; response errors, reset cancellation, ID reuse, and 4 KiB boundary. This is adapter-level evidence. |
| `source scripts/env.sh && make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS, exit 0 | Full `coherence_verify` plus full-system suite; bounded Formal tasks; block/AXI regressions; Python coherence 36 passed / 1 deselected, 49/49 functional bins, 9/9 checker fault injections; AXI Python 3 passed; standard and dense stress 20 passed each; RTL mutation 4/4; Benchmark v4 24 workload rows; full-system 35 passed / 1 replay skipped, 38/38 Required bins and 10/10 Required crosses. |

The machine-readable coverage artifacts are in `reports/full_system/`; exact
command output is local to the regression run. The default suite skips saved
trace replay when no replay path is supplied.

## Coverage interpretation

The 38/38 Required-bin and 10/10 Required-cross result applies only to
implemented Required entries in `dv/coverage/full_system_coverage_plan.json`.
It is Python functional/cross coverage, not RTL line, branch, toggle, or FSM
coverage. Existing IDs were retained; new IDs are credited only after their
listed checker succeeds.

## Scenario sign-off and remaining boundaries

- Same-address dual-core stores are checked against the observed Directory
  acceptance order and read back against the last accepted writer. Dirty L1
  replacement versus peer Snoop, live inclusive L2 victim back-invalidation,
  dirty writeback, and legal cross-line Snoop/refill overlap pass directed
  integrated checkers.
- Four simultaneously active MSHRs are signed off at the independent
  `DirectoryMshrBank` block. The integrated CPU API has two blocking lanes, so
  the full system cannot issue four CPU misses concurrently; this is not
  represented as a system-level four-requester result.
- Integrated dirty writeback verifies AW, all eight ordered W beats, matching
  B, error fail-stop and reset cancellation. Four-ID out-of-order B responses
  are verified at the standalone AXI adapter. The current cache line engine
  serializes writebacks, so integrated B reordering is not reachable.
- APB Hit/Miss/Snoop/Completed deltas, dirty-writeback count, error status,
  and reset-to-zero for every CSR offset are checked. Counter wrap/saturation
  and an exhaustive APB/cache/AXI timing cross matrix remain untested.
- The subsystem ties RREADY and BREADY high; receiver-side R/B backpressure is
  adapter-level only. Complete reset-phase × channel-stall cross coverage is
  not claimed.
- The independent checker covers CPU-visible data, byte masks, selected MESI
  and Directory commits, and transaction lifecycles. It does not yet predict
  every MSHR allocation/retirement or every L2 victim/writeback path.
- The random scheduler is not adaptive across every Directory, Snoop, MSHR,
  L2, AXI, MMIO, and APB feature. Replay reevaluates cycle scheduling; a
  general failure minimizer and waveform exporter are not implemented.
- The regular mixed four-agent campaign is a bounded 4-seed × 6-operation
  timing sample; extended stress runs 20 seeds × 10 rounds. These campaigns
  are not a long-duration randomized cross of all interfaces. Reset is
  verified in dedicated tests rather than randomized in this scenario.
- Existing Formal is component/bounded evidence; no full-system unbounded
  proof is claimed.

The requested concurrency, replacement/Snoop, AXI, and APB scenarios have
directed evidence at the system or block boundary described above. This is
not an unbounded full-system proof or complete all-channel closure. PPA, STA,
SRAM macro implementation, and chip-level physical integration are outside
this result. Local PASS does not imply GitHub Actions PASS.

## Reproduction

From `workspace/nutshell_cache`:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
make coherence_full_system_coverage
PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -q \
  tests/full_system/test_mixed_agent_random.py
FULL_SYSTEM_RANDOM_SEED_COUNT=20 FULL_SYSTEM_RANDOM_OPERATIONS=500 \
FULL_SYSTEM_RANDOM_BASE_SEED=0x57E55 \
PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -q \
  tests/full_system/test_full_system_random.py
```

To run saved-trace replay:

```bash
FULL_SYSTEM_REPLAY_TRACE=reports/full_system/replay_dual_cold_misses.jsonl \
FULL_SYSTEM_REPLAY_TEST_ID='tests/full_system/test_full_system_coherence.py::test_dual_cold_misses_overlap_and_route_axi_responses' \
PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv \
  tests/full_system/test_full_system_replay.py
```
