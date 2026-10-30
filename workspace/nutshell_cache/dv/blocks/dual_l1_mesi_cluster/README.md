# DualL1MesiCluster Verification

- **DUT:** `DualL1MesiCluster`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/l1/MesiL1SnoopArbiter.sv`, `rtl/l1/MesiL1Controller.sv`, `rtl/l1/MesiL1Array.sv`, `rtl/interconnect/CoherenceRequestArbiterCore.sv`, `rtl/interconnect/CoherenceRequestArbiter.sv`, `rtl/cluster/DualL1MesiCluster.sv`
- **Testbench:** `tb/DualL1MesiCluster_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_cluster`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
