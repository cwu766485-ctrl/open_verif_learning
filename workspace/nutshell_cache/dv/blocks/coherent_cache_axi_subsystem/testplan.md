# CoherentCacheAxiSubsystem Testplan

## DUT and RTL dependencies

- DUT: `CoherentCacheAxiSubsystem`.
- RTL dependencies: `rtl/Coherence.files.f`.
- Existing bench: `tb/CoherentCacheAxiSubsystem_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

Coherent cache core; AXI4 memory adapter; 8-beat line memory model; AXI request/response channels.

## Features and testpoints

Cache refill/writeback end-to-end data; burst and ID routing; outstanding requests; R/B response ordering; channel backpressure.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Read/refill data integrity | CPU read through AXI-backed RAM model | SV reference-memory scoreboard checks address/data and backing memory | no coherence-map bin; AXI_TOP_BENCH |
| Dirty writeback | CPU dirty data through AXI AW/W/B | memory model checks AW/W sequence, B response and persisted bytes | no coherence-map bin; AXI_TOP_BENCH |
| Outstanding/interleaved reads | dual-core workload drives multiple memory slots | fatal checks outstanding depth, IDs, beat counts and CPU data | no coherence-map bin; AXI_TOP_BENCH |
| Five-channel backpressure | force AR/AW/W/R/B stalls | fatal checks stalls injected and stream payload stability | no coherence-map bin; AXI_TOP_BENCH |
| APB counters | read counters/status after cache traffic | fatal checks misses/snoops/writebacks and error status | no coherence-map bin; APB end-to-end checks |
| Seeded workload accounting | run fixed-seed mixed accesses | reference memory scoreboard and AXI_TOP_BENCH JSON record | no coherence-map bin; AXI_TOP_BENCH |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
