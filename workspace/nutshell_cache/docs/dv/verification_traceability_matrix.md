# Full-System Verification Traceability

| Spec / interface requirement | Feature | Testpoint | Sequence / driver | Monitor | Checker | Coverage / evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CPU requests complete on lane handshakes | CPU lane lifecycle | FS-D01–D03, FS-C01 | `DualCoreCpuDriver.access` / `access_pair` | CPU request/response pins | Per-lane lifecycle, payload match, response stability | `FS.CPU.*`; full-system pytest report |
| Cold cacheable read refills from backing memory | L1 miss + AXI refill | FS-D01 | CPU request + AXI memory agent | AR/R, L1/Directory commits | AXI burst/data checker and independent coherence scoreboard | `FS.AXI.READ_BURST`, `FS.MESI.I_TO_E` |
| Remote GetS downgrades an owner correctly | MESI sharing | FS-D02 | Core0 read, then Core1 read | Snoop, owner data, metadata commits | Independent data/MESI/Directory model | MESI bins and directed-test trace |
| Remote write preserves the latest value | MESI ownership transfer | FS-D03 | Cross-core writes and reads | Snoop and metadata commits | CPU response comparison and model state checks | `FS.MESI.S_TO_M`, `FS.MESI.M_TO_S` |
| All ten legal MESI state transitions complete through the integrated top | MESI transition closure: I→E/S/M, E→M/S/I, S→M/I, M→S/I | SC01–SC05 | `run_legal_mesi_transition_scenario` from directed and coverage-guided sequences | Directory GetM request, L1 metadata commits, CPU lifecycle | Independent data/coherence scoreboard compares each stable expected state with observed metadata commits before coverage credit | Ten `FS.MESI.*` bins; `test_cold_store_silent_upgrade_and_remote_getm`; full-system coverage report |
| Distinct cold misses overlap and route by ID | Refill concurrency | FS-C01, FS-A01 | `DualCoreCpuDriver.access_pair` | AXI ID/beat events and MSHR occupancy | Per-ID data routing, completion ordering, CPU reference data | `FS.MSHR.OCCUPANCY_2`, `FS.AXI.READ_OUT_OF_ORDER` |
| MMIO masked writes update only selected bytes | MMIO bypass | FS-M01 | CPU MMIO request | MMIO request/response events | Independent MMIO model and readback | `FS.MMIO.BYTE_MASK` |
| Two cores arbitrate MMIO accesses | MMIO dual-lane arbitration | FS-M02 | Paired CPU MMIO operations | MMIO handshakes | Distinct-address writes and readback | `FS.MMIO.CORE_ARBITRATION` |
| MMIO and cache traffic progress concurrently | MMIO/cache isolation | FS-M03 | CPU0 MMIO + CPU1 cold miss | MMIO and AXI events | Separate MMIO and cache reference checks | `FS.MMIO.CACHE_CONCURRENT`, `FS.CROSS.MMIO_WITH_CACHE_TRAFFIC` |
| APB protected writes and invalid offsets report errors | APB CSR protection | FS-P01 | APB reads/writes | APB completion and PSLVERR | Access result checks | `FS.APB.READONLY_ERROR` |
| APB remains responsive during AXI refill | Independent APB progress | FS-P02 | APB read while CPU miss is active | APB and AXI handshakes | APB completion while refill is outstanding | `FS.APB.READ_DURING_AXI`, `FS.CROSS.APB_WITH_AXI_TRAFFIC` |
| CPU0 MMIO, CPU1 cache miss, AXI refill and APB counter read overlap | Five-interface lifecycle overlap | SC21 | Concurrent CPU lanes, delayed MMIO response and APB read inserted during refill | CPU/MMIO/APB/AXI handshake events plus L1/Directory observations | Independent CPU/MMIO data, APB counter, AXI ID/beat and cycle-order checks | `FS.XAGENT.MMIO_READ_CACHE_MISS_APB_COUNTER`, `FS.CROSS.MMIO_READ_CACHE_MISS_APB` |
| Seeded CPU cache miss + MMIO request + APB read during AXI refill | Four-agent mixed timing stress | SC23; `test_seeded_cpu_mmio_apb_axi_overlap` | Four fixed seeds × six rounds; cache lane and access type/mask vary; paired MMIO request; APB reads Miss count while refill is outstanding; AXI ARREADY stalls and RVALID gaps | CPU/L1/Directory/Snoop/L2/MSHR/AXI observations; AXI accepted handshakes are recorded by the protocol-checking memory agent to avoid same-edge scheduler races; internal RTL observations remain passive | Independent MESI/data, MMIO register, APB counter, and AXI burst checkers; checks `MMIO accept < AR < APB < RLAST < MMIO response` before credit | `FS.STRESS.MIXED_CPU_MMIO_APB_AXI`, `FS.CROSS.MIXED_CPU_MMIO_APB_AXI`, APB/AXI overlap bins |
| Reset cancels active AXI/MMIO work | Reset lifecycle | FS-R01/R02 | Delayed AXI read and delayed MMIO response | Reset and transaction-context monitor | Cancellation count, no stale response, AXI ID reuse and successful retry | `FS.AXI.RESET_CANCEL`, `FS.MMIO.RESET_CANCEL`, `FS.CROSS.RESET_WITH_OUTSTANDING` |
| AXI read error cannot complete as success | Error handling | FS-E01 | Inject RRESP error | R channel and fail-stop probes | Sticky fail-stop and no successful CPU response | `FS.AXI.ERROR_RESPONSE` |
| Seeded random CPU traffic remains coherent | Random regression | FS-RAND | `FullSystemRandomSequence` | CPU, snoop, metadata, AXI/MMIO events | Independent model and protocol checks | JSON coverage/trace; default 10 seeds × 100 operations |
| Seeded same-set and distinct-set owner Snoop/refill contention | Resource-aware random regression | SC24 | `test_seeded_same_and_distinct_l2_set_snoop_refill` | CPU accept, Directory request, Snoop accept/response, L2 refill, owner data beats and metadata commits | Independent CPU data/reference checks; exact eight-beat owner transfer; checks same-set request enters Directory after refill retirement and distinct-set Snoop completes before refill end | `FS.RESOURCE.SNOOP_REFILL_SAME_L2_SET`, `FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET` and corresponding cross bins |
| Saved CPU transaction groups replay deterministically | Replay | FS-REPLAY | `replay_cpu_transactions` | Fresh DUT observations | Compare each replay response with source trace | Replay pytest result; cycle timing is re-evaluated |

## Explicitly separate evidence

The full-system coverage plan in `dv/coverage/full_system_coverage_plan.json`
includes the ten Required legal MESI transition bins plus directed sign-off
bins for same-address writes, L1 replacement/Snoop, live L2 victim
back-invalidation, APB counter/reset behavior, serialized integrated
writeback/error/reset, Snoop/refill overlap, and seeded CPU/MMIO/APB/AXI
overlap. The latest local integrated run closes 38/38 implemented Required
bins and 10/10 implemented Required
crosses. This is Python functional/cross coverage, not RTL
line/branch/toggle/FSM coverage. Existing Python coherence bins (49
functional / 19 cross), SV Block results, formal proofs and RTL coverage
retain their own plans and reports. They are not merged or added together.

`full_system_scenario_testplan.md` maps all planned SC01–SC24 families and
marks each Verified, Partial or Open. The coverage closure only applies to
implemented Required bins, not to every scenario dimension. Four MSHR
contexts are verified at the Directory MSHR block; the two blocking CPU lanes
cannot issue four concurrent misses. AXI write error/reset are checked at the
integrated top, while four-ID B reordering is adapter-level because the
integrated line engine serializes writebacks. APB basic counter and reset
semantics, same-address ordering, replacement/Snoop races and a legal
cross-line Snoop/refill overlap are now directed integrated tests. The 20×500
random run is CPU-centric and does not close sustained mixed MMIO/APB traffic.
