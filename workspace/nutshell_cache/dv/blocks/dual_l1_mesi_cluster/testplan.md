# DualL1MesiCluster Testplan

## DUT and RTL dependencies

- DUT: `DualL1MesiCluster`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1SnoopArbiter.sv`, `rtl/l1/MesiL1Controller.sv`, `rtl/l1/MesiL1Array.sv`, `rtl/interconnect/CoherenceRequestArbiterCore.sv`, `rtl/interconnect/CoherenceRequestArbiter.sv`, `rtl/cluster/DualL1MesiCluster.sv`.
- Existing bench: `tb/DualL1MesiCluster_tb.sv`; the SV test body is unchanged by this move.
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

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
