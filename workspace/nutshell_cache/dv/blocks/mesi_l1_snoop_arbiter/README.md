# MesiL1SnoopArbiter Verification

- **DUT:** `MesiL1SnoopArbiter`
- **RTL dependencies:** `rtl/l1/MesiL1SnoopArbiter.sv`
- **Testbench:** `tb/MesiL1SnoopArbiter_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_snoop_arbiter`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
