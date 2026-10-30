# MesiL1SnoopArbiter Testplan

## DUT and RTL dependencies

- DUT: `MesiL1SnoopArbiter`.
- RTL dependencies: `rtl/l1/MesiL1SnoopArbiter.sv`.
- Existing bench: `tb/MesiL1SnoopArbiter_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

CPU request readiness and Snoop readiness with CPU/Snoop active-line status.

## Features and testpoints

Same-line collision priority; active CPU lock; independent-line progress; idle and valid combinations.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Idle truth table | enumerate idle valid/active inputs | check_ready task compares both ready outputs | no direct bin |
| Same-line collision | CPU and snoop target the same active line | check_ready task checks priority | integrated only: `mesi.snoop_waits_store_commit` |
| Different-line progress | CPU and snoop use different lines | check_ready task checks independent readiness | integrated only: `cpu_pair.snoop_progress` |
| Busy/valid combinations | enumerate active/valid combinations | check_ready task compares expected truth table | no direct bin |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
