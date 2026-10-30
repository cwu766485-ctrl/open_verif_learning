# CoherenceRequestArbiter Verification

- **DUT:** `CoherenceRequestArbiter`
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/interconnect/CoherenceRequestArbiterCore.sv`, `rtl/interconnect/CoherenceRequestArbiter.sv`
- **Testbench:** `tb/CoherenceRequestArbiter_tb.sv`
- **Filelist:** `filelist.f`; paths are resolved from `rtl/` by the named Make target.
- **Run:** `make coherence_request_arbiter`
- **Testplan:** [testplan.md](testplan.md)

Shared Agents, Reference Models, Scoreboard, Checkers and Coverage remain single-source under `dv/`; this block directory contains no copied verification components.
