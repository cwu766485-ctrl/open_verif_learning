# DirectoryController Testplan

## DUT and RTL dependencies

- DUT: `DirectoryController`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/directory/DirectoryController.sv`.
- Existing bench: `tb/DirectoryController_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

Request/grant; Directory lookup/update; Snoop request/response/data; L2 refill/read/write; memory request/response.

## Features and testpoints

GetS/GetM/Upgrade; owner/sharer snoop; dirty owner data; Put lifecycle; L2 hit/miss; response backpressure; reset/error.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Request/L2 transfer | GetS/GetM then line transfer and grant | helpers check address/opcode/ID, payload stability and completion | integrated only: `mesi.gets_cold_refill`, `mesi.getm_upgrade_s` |
| Snoop response/ID | snoop with stall, wrong then matching transaction ID | helpers verify target/opcode stability and ID matching | integrated only: `mesi.gets_share_m_owner`, `mesi.getm_remote_owner` |
| Metadata/grant commit | commit final Directory state and grant | helpers compare addr/state/sharer/owner and matching ID | integrated only: `mesi.getm_upgrade_s`, `mesi.getm_remote_owner` |
| Reset pending transfer | reset while transfer request blocked | fatal checks stale transaction outputs clear | no direct bin |
| Missing-owner recovery | owner-missing response with competing context payload | fatal checks recovery uses correct context/address and no protocol error | no direct bin |
| Malformed recovery | owner-missing response on GetS | fatal checks fallback transfer header and no protocol error | no direct bin |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
