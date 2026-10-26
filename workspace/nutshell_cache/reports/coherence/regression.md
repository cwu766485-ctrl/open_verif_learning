# Dual-L1 MESI Regression Report

- **Status:** PASS
- **PASS markers:** 197
- **Functional coverage:** 34/34 (100.0%)
- **Code line coverage:** 3089/3331 (92.7%)
- **Documented waivers:** 0

Functional bins close only from structured `COV_EVENT` records emitted after the corresponding checker completes; PASS text is informational.

| Feature | Bin | Stimulus / checker | Expected transaction axes | Hits | Status |
|---|---|---|---|---:|---|
| MESI GetS | `mesi.gets_cold_refill` | Core0 GetS refill from backing memory / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=I, requester=0, opcode=GetS, snoop_target=none, new_state=E, data_source=memory, beats=8` | 6 | hit |
| MESI sharing/intervention | `mesi.gets_share_m_owner` | Core1 GetS shares the full latest line from the M owner / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=1, opcode=GetS, snoop_target=0, new_state=S, data_source=remote_owner, beats=8` | 6 | hit |
| MESI GetM / Upgrade | `mesi.getm_upgrade_s` | shared-to-exclusive upgrade invalidates peer; remote read sees M data / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=S, requester=0, opcode=GetM, snoop_target=1, new_state=M, data_source=L1_peer, beats=0` | 6 | hit |
| MESI GetM / intervention | `mesi.getm_remote_owner` | remote GetM invalidates an M owner and preserves its latest data / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=0, opcode=GetM, snoop_target=1, new_state=M, data_source=remote_owner, beats=8` | 6 | hit |
| MESI GetM / intervention | `mesi.getm_remote_clean_e` | remote GetM invalidates a clean E owner and receives all beats / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=E, requester=0, opcode=GetM, snoop_target=1, new_state=M, data_source=clean_L1_peer, beats=8` | 6 | hit |
| MESI E-to-M | `mesi.e_to_m_silent` | E-to-M local write is silent and preserves the full line / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=E, requester=0, opcode=Store, snoop_target=none, new_state=M, data_source=local_L1, beats=0` | 6 | hit |
| MESI progress | `mesi.snoop_waits_store_commit` | same-line SnoopRead waits for local E-to-M write commit / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=E, requester=1, opcode=GetS+StoreCommit, snoop_target=0, new_state=S, data_source=L1_owner, beats=8` | 6 | hit |
| MESI masked write | `mesi.masked_owner_write` | byte-masked write is visible after remote owner intervention / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=1, opcode=GetS_after_MaskedStore, snoop_target=0, new_state=S, data_source=remote_owner, beats=8` | 6 | hit |
| Concurrency / same line | `cpu_pair.same_line` | same-line simultaneous GetS/GetM and byte-mask corner cases / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=mixed, requester=both, opcode=GetS+GetM, snoop_target=both, new_state=M, data_source=mixed, beats=8` | 6 | hit |
| Concurrency / different lines | `cpu_pair.different_lines` | different-address concurrent misses route to the correct cores / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=I, requester=both, opcode=GetS, snoop_target=none, new_state=E, data_source=memory, beats=8` | 6 | hit |
| Concurrency / Snoop progress | `cpu_pair.snoop_progress` | different-line SnoopInvalidate progresses during a local CPU response stall / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=S, requester=1, opcode=GetM_Upgrade, snoop_target=0, new_state=M, data_source=local_L1, beats=0` | 6 | hit |
| L1 replacement | `l1.putm` | dirty M victim uses PutM, returns to L2, then refills by peer / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=0, opcode=PutM, snoop_target=none, new_state=I, data_source=L1_owner, beats=8` | 6 | hit |
| L1 replacement | `l1.pute` | clean E victim is removed with PutE; dirty L2 data is preserved / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=E, requester=0, opcode=PutE, snoop_target=none, new_state=I, data_source=L2, beats=0` | 6 | hit |
| L1 replacement | `l1.puts` | shared S victim is removed with PutS while the peer retains its copy / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=S, requester=0, opcode=PutS, snoop_target=none, new_state=I, data_source=L2, beats=0` | 6 | hit |
| L2 live victim reclaim | `l2.live_u_victim` | L2 live victim back-invalidates an M owner and writes back its line / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=1, opcode=L2_Evict, snoop_target=1, new_state=I, data_source=L1_owner, beats=8` | 6 | hit |
| L2 live victim reclaim | `l2.dirty_owner_writeback` | dirty owner data survives L2 eviction through backing memory / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=1, opcode=L2_Evict, snoop_target=1, new_state=I, data_source=backing_memory, beats=8` | 6 | hit |
| L2 shared victim multi-snoop | `l2.shared_multisnoop` | DIR_S L2 victim invalidates both sharers and writes back dirty L2 data / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=S, requester=both, opcode=L2_Evict, snoop_target=both, new_state=I, data_source=L2_dirty, beats=8` | 6 | hit |
| MMIO isolation | `mmio.bypass` | MMIO read/write bypasses L1, L2, and backing memory / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=na, requester=both, opcode=MMIO, snoop_target=none, new_state=na, data_source=MMIO, beats=0` | 6 | hit |
| MMIO address decode | `mmio.address_boundaries` | cacheable/MMIO address-domain boundary cases / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=na, requester=both, opcode=MMIO_boundary, snoop_target=none, new_state=na, data_source=MMIO, beats=0` | 6 | hit |
| Backpressure | `backpressure.mem_refill` | refill MSHR absorbs the memory line while the L2 fill port is stalled / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=I, requester=0, opcode=GetS, snoop_target=none, new_state=E, data_source=memory, beats=8` | 6 | hit |
| Backpressure | `backpressure.independent_channels` | memory request/refill and CPU response survive independent stalls / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=mixed, requester=both, opcode=GetS+GetM, snoop_target=none, new_state=mixed, data_source=memory, beats=8` | 6 | hit |
| Backpressure | `backpressure.mmio` | MMIO request and response payloads remain stable under backpressure / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=na, requester=0, opcode=MMIO, snoop_target=none, new_state=na, data_source=MMIO, beats=0` | 6 | hit |
| Reset cancellation | `reset.refill` | reset cancels an active refill without a stale response / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=I, requester=0, opcode=GetS+Reset, snoop_target=none, new_state=I, data_source=memory, beats=0` | 6 | hit |
| Reset cancellation | `reset.mmio` | reset cancels a backpressured MMIO response / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=na, requester=0, opcode=MMIO+Reset, snoop_target=none, new_state=na, data_source=MMIO, beats=0` | 6 | hit |
| Reset cancellation | `reset.cpu_rsp` | reset cancels a stalled cache response without replay / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=E, requester=0, opcode=GetS+Reset, snoop_target=none, new_state=I, data_source=L1, beats=0` | 6 | hit |
| Reset cancellation | `reset.snoop_data` | reset cancels an active owner SnoopData stream / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=0, opcode=SnoopData+Reset, snoop_target=1, new_state=I, data_source=L1_owner, beats=8` | 6 | hit |
| Reset cancellation | `reset.l2_writeback` | reset cancels a stalled dirty L2 writeback beat / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=1, opcode=L2_Writeback+Reset, snoop_target=1, new_state=I, data_source=backing_memory, beats=8` | 6 | hit |
| Error handling | `error.mem_read` | terminal memory read error suppresses success and blocks new requests / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=I, requester=0, opcode=GetS+MemError, snoop_target=none, new_state=I, data_source=memory_error, beats=1` | 6 | hit |
| Error handling | `error.mem_write` | failed write response preserves the valid dirty L2 victim / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=M, requester=0, opcode=L2_Writeback+MemError, snoop_target=none, new_state=M, data_source=backing_memory, beats=8` | 6 | hit |
| Directory MSHR concurrency | `mshr_bank.four_contexts` | four concurrent line misses, reversed refill completion / `directory_mshr_bank_transaction_checks` | `old_state=I, requester=multiple, opcode=GetS, snoop_target=none, new_state=DIR_U, data_source=L2_refill, beats=8, contexts=4` | 1 | hit |
| Directory MSHR concurrency | `mshr_bank.duplicate_suppression` | same-line duplicate plus fifth unique request / `directory_mshr_bank_transaction_checks` | `old_state=I, requester=multiple, opcode=GetS_duplicate, snoop_target=none, new_state=I, data_source=none, beats=0, contexts=4` | 1 | hit |
| Directory MSHR concurrency | `mshr_bank.snoop_independence` | hold one owner snoop while other contexts refill / `directory_mshr_bank_transaction_checks` | `old_state=DIR_U, requester=0, opcode=GetS_plus_GetS, snoop_target=owner1, new_state=mixed, data_source=owner_plus_memory, beats=8, contexts=4` | 1 | hit |
| Directory MSHR concurrency | `mshr_bank.reset_cancel` | four active requests followed by reset / `directory_mshr_bank_transaction_checks` | `old_state=mixed, requester=multiple, opcode=GetS_plus_Reset, snoop_target=none, new_state=I, data_source=none, beats=0, contexts=4` | 1 | hit |
| Seeded random data/state traffic | `random.seeded_data` | seeded 80-operation coherence/data scoreboard regression seed= / `subsystem_reference_scoreboard_and_protocol_invariants` | `old_state=mixed, requester=both, opcode=random, snoop_target=mixed, new_state=mixed, data_source=mixed, beats=8` | 6 | hit |

## Backpressure closure

| Channel | Stalled cycles | Status |
|---|---:|---|
| `cpu_resp` | 26 | hit |
| `mmio_req` | 4 | hit |
| `mmio_resp` | 5 | hit |
| `mem_rd_req` | 9 | hit |
| `l2_fill` | 2 | hit |
| `mem_wr_req` | 11 | hit |
| `mem_wr_data` | 756 | hit |
| `dir_req` | 42 | hit |

Logs:

- `reports/coherence/smoke.log`
- `reports/coherence/multisnoop.log`
- `reports/coherence/directory_mshr_bank.log`
- `reports/coherence/seed_00000001.log`
- `reports/coherence/seed_00001234.log`
- `reports/coherence/seed_5EEDC0DE.log`
- `reports/coherence/seed_DEADBEEF.log`
- `reports/coherence/seed_2468ACE0.log`


## Performance and storage baseline

- L1 hit: 2 average cycles (59 samples)
- L1 miss: 41 average cycles (150 samples; 39 cycle penalty vs. hit)
- Read hit: 2 average cycles (43 samples)
- Write hit (E/M): 3 average cycles (16 samples)
- S-to-M upgrade: 11 average cycles (10 samples)
- Cold L1 miss: 43 average cycles (140 samples)
- CPU request-ready stalled cycles: 0
- Remote snoop: 19 average cycles (41 samples)
- Configured data capacity: 320 KiB (two 32 KiB L1s plus 256 KiB shared L2)
- These are RTL simulation cycle counts and configured capacity. No target standard-cell library, SRAM compiler model, clock constraint, or physical-design flow is configured, so this report does not claim silicon area or static timing closure.
