# SharedL2DirectoryArray Testplan

## DUT and RTL dependencies

- DUT: `SharedL2DirectoryArray`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/l2/SharedL2DirectoryArray.sv`.
- Existing bench: `tb/SharedL2DirectoryArray_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

L2 line lookup/read/write; Directory state, sharers and owner metadata; replacement/victim interface.

## Features and testpoints

Tag hit/miss; data and directory metadata; replacement; valid and invalid victim; write and read port arbitration.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Tag/data lookup and refill | write line/directory metadata then lookup and read | fatal checks hit, metadata and all eight beats | integrated only: `mesi.gets_cold_refill` |
| Read stream/backpressure | stall line reader after first beat | fatal checks payload stability and ordered data | no direct bin |
| Live victim/control | fill set, inspect victim, mark clean and invalidate | fatal checks victim state/address and slot reallocation | integrated only: `l2.live_u_victim`, `l2.shared_multisnoop` |
| Malformed line write | send malformed write beat sequence | fatal requires protocol_error latch | no direct bin |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
