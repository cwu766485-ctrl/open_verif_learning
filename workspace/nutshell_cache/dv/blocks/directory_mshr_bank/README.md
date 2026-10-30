# DirectoryMshrBank Verification

- **DUT:** `DirectoryMshrBank`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/directory/DirectoryController.sv`, `rtl/directory/DirectoryMshrBank.sv`
- **Testbench:** `tb/DirectoryMshrBank_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_directory_mshr_bank`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
