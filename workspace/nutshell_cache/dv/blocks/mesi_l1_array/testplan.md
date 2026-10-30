# MesiL1Array Testplan

## DUT and RTL dependencies

- DUT: `MesiL1Array`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1Array.sv`.
- Existing bench: `tb/MesiL1Array_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

CPU tag/data lookup, metadata writes, refill, byte-masked store and line streaming.

## Features and testpoints

lookup hit/miss; replacement way/state; refill beat order and last; metadata arbitration; full-line read; backpressure.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Lookup/refill | refill, tag lookup, state/data compare | fatal checks on ready/hit/address/state/data | integrated only: `mesi.gets_cold_refill` |
| Masked store/snoop metadata | byte-masked store then snoop metadata write | fatal compare merged word and metadata | no direct bin |
| Line stream/backpressure | 8-beat line read with consumer stall | fatal checks stable payload and exact beats | no direct bin |
| Replacement victim | fill ways and inspect victim metadata | fatal compare victim way/address/state | integrated only: `l1.putm`, `l1.pute`, `l1.puts` |
| Malformed refill | inject malformed beat marker | fatal requires protocol_error | no direct bin |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
