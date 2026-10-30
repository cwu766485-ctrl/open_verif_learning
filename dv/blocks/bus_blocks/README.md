# LineMemoryAxi4Adapter + CachePerformanceCsr Verification

- **DUT:** `LineMemoryAxi4Adapter + CachePerformanceCsr`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/bus/axi/LineMemoryAxi4Adapter.sv`, `rtl/bus/apb/CachePerformanceCsr.sv`
- **Testbench:** `tb/CacheBusBlocks_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_bus_blocks`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
The top-level testbench is a short entry point. Its `tb/include/*.svh` fragments separate signal declarations, models/agents, checkers, and scenario groups. They are included by the block filelist and are not standalone tests.
