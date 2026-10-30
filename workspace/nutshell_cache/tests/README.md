# Tests

Python/Toffee pytest cases for the original single-L1 cache remain under
`tests/l1/` with their existing imports and entry points. They are the Legacy
L1 verification suite and are not MESI L1 block tests. Existing SystemVerilog
block and subsystem benches now live with their actual DUT ownership under
[`dv/blocks/`](../dv/blocks/README.md), each with `tb/`, an independent
`filelist.f`, a README and a testplan. Shared Python agents, models, checkers,
scoreboard and coverage stay single-source under `dv/`. Existing Make targets
remain the build/run entry points.
