# Full-System Gray-Box Observability Matrix

All probes below are read-only wrapper connections to existing
`CoherentCacheSubsystem` monitor/metadata outputs. The Python monitor never
assigns these signals and never uses them to calculate expected architectural
data.

| Observation | Wrapper source | Event/checker use | Boundary |
| --- | --- | --- | --- |
| CPU request/response handshakes | Top-level packed CPU interface | CPU lane identity, address, operation, data, ID and transaction lifecycle | Public pins are authoritative for acceptance/completion |
| L1 metadata commits | `cache_core.metadata_commit_*` | Compare observed new MESI state to independent model state | Old state comes from reference history, not DUT output |
| Snoop request and response | `cache_core.monitor_snoop_*` | Core, address, opcode, transaction ID, accepted response | Only accepted request/response edges are recorded |
| Directory commits | `cache_core.monitor_dir_commit_*` | Compare Directory I/S/U state, sharer mask, owner against model | A commit is actual observation; expected is derived independently |
| Directory request/grant | `cache_core.monitor_dir_req_accept_*`, `monitor_dir_grant_accept_*` | Address/opcode/source/destination/transaction correlation | Context IDs are not reconstructed from log adjacency |
| Owner data | `cache_core.monitor_owner_data_*` | Address, source core, beat, data, last | Transfer data is checked by monitor; full AXI/memory data closure remains ongoing |
| L2 lookup/write/fill | `monitor_l2_lookup_*`, `monitor_l2_line_wr_*`, `monitor_l2_fill_active` | Hit/miss and accepted line-write beat counters | Does not imply all data-array contents are observable |
| Engine, victim, MSHR | `monitor_engine_*`, `monitor_victim_*`, `monitor_mem_mshr_valid`, `monitor_directory_active_contexts` | Debug/progress and occupancy statistics | Occupancy alone is not proof of allocation/routing/retirement correctness |
| AXI five channels | Top-level AXI pins | Burst, ID, beat, stall and response lifecycle | AXI slave drives only slave-side READY and R/B responses |
| MMIO / APB | Top-level external ports | MMIO model and CSR access/error checks | APB product interface has no write-data signal because CSRs are read-only |

The existing top-level product module is unchanged. The additional Python
wrapper is a verification artifact and should remain separate from synthesis
source manifests.
