# DirectoryController Verification

- **DUT:** `DirectoryController`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/directory/DirectoryController.sv`
- **Testbench:** `tb/DirectoryController_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_directory`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
