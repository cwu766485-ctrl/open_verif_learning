# MesiL1Array Verification

- **DUT:** `MesiL1Array`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1Array.sv`
- **Testbench:** `tb/MesiL1Array_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_l1_array`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
