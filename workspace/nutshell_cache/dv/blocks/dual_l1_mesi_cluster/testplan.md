# DualL1MesiCluster Testplan

## DUT and RTL dependencies

- DUT: `DualL1MesiCluster`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1SnoopArbiter.sv`, `rtl/l1/MesiL1SnoopEngine.sv`, `rtl/l1/MesiL1MissContext.sv`, `rtl/l1/MesiL1Controller.sv`, `rtl/l1/MesiL1Array.sv`, `rtl/interconnect/CoherenceRequestArbiterCore.sv`, `rtl/interconnect/CoherenceRequestArbiter.sv`, `rtl/cluster/DualL1MesiCluster.sv`.
- Existing bench: `tb/DualL1MesiCluster_tb.sv`; its debug diagnostic now reads the Cluster's public `monitor_cpu_state` tap instead of reaching into the L1 Controller's private state register.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

Two CPU lanes; Directory request/grant/commit; Snoop channels; victim Put/data; per-core response and protocol-error monitor.

## Features and testpoints

Dual-L1 integration; replacement request flow; grant/refill; snoop response/data; arbitration and per-core routing.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Dual cold misses | both cores issue independent misses, refill separately | fatal checks routing/source/address/ID/data/response | integrated only: `cpu_pair.different_lines` |
| Refill metadata commit | finish two 8-beat refills and monitor commits | fatal checks per-core commit/address/state | integrated only: `mesi.gets_cold_refill` |
| Post-refill hits | repeat each read | fatal checks hit, data, response and MESI state | integrated only: `mesi.gets_cold_refill` |
| Protocol error | inspect monitor after both refills | fatal requires no protocol error | no direct bin |

## Two-entry L1 miss tracking regression

The system regression `tests/full_system/test_nonblocking_l1_mshr.py` checks
the current two-slot acceptance tracker through the AXI subsystem. Its
independent `L1MshrLifecycleChecker` checks request address/data association,
per-core miss response order, refill beat-to-ID routing, and transaction
allocation/retirement. `test_four_l1_misses_occupy_two_entries_per_core`
requires four accepted L1 entries (two per core) to remain valid before the
first CPU response, reverses the first two AXI read IDs, and separately samples
Directory contexts, refill MSHRs, and AXI outstanding reads/writes.

The same test module also checks same-line relookup, full-bank backpressure,
response backpressure, reset cancellation, and a queued Store relookup after a
remote Snoop. These are integration tests; they do not count as a standalone
Cluster block test or prove two same-core Directory requests in flight.

The second valid entry is queued behind the core's single
`MesiL1Controller`. Consequently four accepted/retained L1 requests are
supported, while at most one miss per core is issued downstream at a time.
True same-core Miss-under-Miss, two live Directory IDs per L1, simultaneous
same-core refill association, and the corresponding shared-array arbitration
remain OPEN. No Functional/Cross bin is closed by the MSHR monitor alone.

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
