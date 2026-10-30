# CoherenceRequestArbiter Testplan

## DUT and RTL dependencies

- DUT: `CoherenceRequestArbiter`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/interconnect/CoherenceRequestArbiterCore.sv`, `rtl/interconnect/CoherenceRequestArbiter.sv`.
- Existing bench: `tb/CoherenceRequestArbiter_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

Two request input lanes and one Directory output with source, opcode, line address and transaction ID.

## Features and testpoints

Round-robin fairness; one-hot ready; output stability while stalled; lane/payload routing; reset.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Idle/reset | inspect outputs after reset | fatal checks idle and reset preference | no direct bin |
| Source selection/lock | competing requests under downstream stall | fatal checks selected lane and stable payload | no direct bin |
| Round robin | handshake alternating competing requests | fatal checks lane alternation | integrated only: `cpu_pair.same_line`, `cpu_pair.different_lines` |
| Ready qualification | inspect ready on selected/unselected lanes | fatal checks ready asserted only for selected source | no direct bin |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
