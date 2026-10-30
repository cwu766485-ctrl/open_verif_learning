# SharedL2DirectoryArray Verification

- **DUT:** `SharedL2DirectoryArray`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/l2/SharedL2DirectoryArray.sv`
- **Testbench:** `tb/SharedL2DirectoryArray_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_l2_array`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
