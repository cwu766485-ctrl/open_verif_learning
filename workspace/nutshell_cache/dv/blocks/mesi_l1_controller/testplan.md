# MesiL1Controller Testplan

## DUT and RTL dependencies

- DUT: `MesiL1Controller`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1SnoopArbiter.sv`, `rtl/l1/MesiL1Controller.sv`.
- Existing bench: `tb/MesiL1Controller_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

CPU request/response; Directory request/grant/commit; refill; snoop request/response/data; CPU and snoop metadata updates.

## Features and testpoints

GetS/GetM/Upgrade selection; grant ID validation; refill streaming; E/M store; SnoopRead/Invalidate; same-line serialization; reset/error.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| E local store | store hit in E | fatal check E-to-M metadata and CPU response | integrated only: `mesi.e_to_m_silent` |
| GetS refill | GetS miss, matching grant and 8 refill beats | fatal check Directory request, grant, refill, commit and response | integrated only: `mesi.gets_cold_refill` |
| M owner SnoopRead | snoop M line, send line data and downgrade | fatal check 8 beats, S metadata and ACK header | integrated only: `mesi.gets_share_m_owner` |
| S store Upgrade | store hit in S with Directory/response stalls | fatal check Upgrade, wrong-ID rejection, payload stability and commit | integrated only: `mesi.getm_upgrade_s` |
| GetM miss/refill | GetM miss with grant/refill stalls | fatal check opcode, stale-ID rejection, beat stability and M commit | integrated only: `mesi.getm_remote_owner` |
| SnoopInvalidate | invalidate M and S entries | fatal check M data stream, invalid metadata and InvAck | integrated only: `mesi.getm_remote_owner`, `mesi.getm_upgrade_s` |
| Missing-line recovery | SnoopRead to absent line | fatal requires recoverable ACK | no direct bin |
| Reset/error | reset stalled refill; inject malformed refill | fatal checks reset clears state and bad refill fails without success | integrated only: `reset.refill` |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
