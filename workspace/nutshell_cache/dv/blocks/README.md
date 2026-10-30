# Block-Centric Verification

This directory groups each existing independent SystemVerilog bench with the DUT block it verifies. Each block has `tb/`, an independent `filelist.f`, a `README.md` and `testplan.md`. The filelist paths are resolved from `rtl/` by the existing Make target.

| DUT / existing bench | Directory | Make target |
|---|---|---|
| MesiL1Array | `mesi_l1_array/` | `make coherence_l1_array` |
| MesiL1Controller | `mesi_l1_controller/` | `make coherence_l1_controller` |
| MesiL1SnoopArbiter | `mesi_l1_snoop_arbiter/` | `make coherence_snoop_arbiter` |
| DirectoryController | `directory_controller/` | `make coherence_directory` |
| DirectoryMshrBank | `directory_mshr_bank/` | `make coherence_directory_mshr_bank` |
| SharedL2DirectoryArray | `shared_l2_directory_array/` | `make coherence_l2_array` |
| CoherenceRequestArbiter | `coherence_request_arbiter/` | `make coherence_request_arbiter` |
| LineMemoryAxi4Adapter + CachePerformanceCsr | `bus_blocks/` | `make coherence_bus_blocks` |
| DualL1MesiCluster | `dual_l1_mesi_cluster/` | `make coherence_cluster` |
| CoherentCacheSubsystem | `coherent_cache_subsystem/` | `make coherence_build` |
| CoherentCacheAxiSubsystem | `coherent_cache_axi_subsystem/` | `make coherence_axi_e2e` |

Legacy single-L1 Python/Toffee tests remain under `tests/l1/` with their existing imports and Make/pytest entry points; they are not part of the new MESI block directories. No standalone bench is created for modules that did not already have one; their plan marks integration-only evidence.
