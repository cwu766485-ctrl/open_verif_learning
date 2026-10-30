# CoherentCacheAxiSubsystem Verification

- **DUT:** `CoherentCacheAxiSubsystem`
- **RTL dependencies:** `rtl/Coherence.files.f`
- **Testbench:** `tb/CoherentCacheAxiSubsystem_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_axi_e2e`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
