# Python/Toffee Coherence Functional Coverage

- Status: **PASS**
- Mapped bins: **37/37**
- L1 evictions: 16
- Live inclusive L2 evictions: 5
- MESI/op/core/source/snoop/transfer crosses: 12/12

| Feature | Testpoint | Checker | Hits | Status |
| --- | --- | --- | ---: | --- |
| `cold_read` | Independent cold GetS data check | CoherenceScoreboard response/data model | 95 | hit |
| `cold_write` | Cold GetM stores to the dual-core set-pressure sequence | CoherenceScoreboard byte-accurate data and MESI invariants | 78 | hit |
| `remote_read_from_E` | Core1 reads Core0 E line | Independent MESI state transition and returned data | 13 | hit |
| `remote_read_from_M` | Remote read observes latest M-owner data | Independent MESI state transition and returned data | 349 | hit |
| `shared_upgrade` | Core0 byte-masked S-to-M store | Byte-merge data comparison and MESI transition | 334 | hit |
| `l1_eviction` | Five same-index lines exceed one L1 set capacity | Independent 4-way L1 replacement model | 16 | hit |
| `l1_replacement_put_match` | Predicted L1 victim line/state matches the accepted Put opcode and address | Independent round-robin replacement scoreboard compared with Directory Put handshakes | 1 | hit |
| `l2_refill_hit` | Re-read L1-evicted line retained in shared L2 | DUT L2 event and no backing-memory read | 395 | hit |
| `l2_refill_miss` | Cold line refill absent from shared L2 | DUT L2 event and backing-memory read | 140 | hit |
| `l2_live_eviction` | Ninth same-set line evicts a line still owned by the other L1 | Directory/L1 reference state plus snoop, owner data, and L2 victim model | 5 | hit |
| `l2_live_victim_dirty_owner` | Dirty M owner is back-invalidated, written back, and reloaded with the same data | Independent Directory/MESI model, accepted Snoop, eight-beat memory writeback, and reload data | 3 | hit |
| `l2_live_victim_shared` | Shared L2 victim with two live S copies is invalidated at both L1s | Independent Directory/L1 model compared with both accepted snoops and any required memory writeback data | 1 | hit |
| `parallel_cold_miss_pair` | Both CPU lanes present independent cold misses together | Single packed DualCoreCpuDriver handshakes and matches each response | 1 | hit |
| `byte_mask_write` | Masked store followed by remote read | Architectural byte-lane merge comparison | 1 | hit |
| `byte_mask_m_hit` | Second byte-masked store hits a Modified line | Independent byte-merge model and local/remote data checks | 1 | hit |
| `dirty_writeback` | Dirty inclusive L2 victim writes all eight beats | Writable memory contents, beat count, and later victim reload | 2 | hit |
| `write_response` | CPU transaction completes after memory write response | ID-matched write response handshake count | 2 | hit |
| `reset_during_refill` | Reset cancels a memory-accepted refill without a stale CPU response; the same line works after recovery | CPU response monitor, reset-aware line memory and post-reset data scoreboard | 1 | hit |
| `cpu_response_backpressure` | CPU response payload remains stable while ready is held low | Packed-lane driver checks address, operation and data through the stall | 4 | hit |
| `memory_read_request_backpressure` | Cold refill request holds through deterministic memory-ready stalls | Accepted line-request queue and ready/valid stall counter | 3 | hit |
| `memory_write_request_backpressure` | Dirty victim write request holds through deterministic memory-ready stalls | Accepted write-request queue and ready/valid stall counter | 3 | hit |
| `memory_write_data_backpressure` | All eight dirty-victim beats survive deterministic write-data stalls | Beat-index checker, writable memory model and ready/valid stall counter | 3 | hit |
| `memory_read_response_gaps` | Read refill beats complete with deterministic response-valid gaps | ID/beat-aware memory queue and returned architectural data | 19 | hit |
| `directory_lookup_race_regression` | Different-address owner transfer and cold grant contend for the L2 lookup | Blocked-lookup monitor plus independent data, snoop-beat, and Directory scoreboard checks | 1 | hit |
| `directory_lookup_conflict_transfer` | A waiting request is held while an active owner-transfer lookup uses the shared port | Accepted transfer address remains distinct from blocked incoming request | 1 | hit |
| `directory_lookup_conflict_grant` | A waiting request is held while an active grant lookup uses the shared port | Accepted grant address remains distinct from blocked incoming request | 1 | hit |
| `snoop_ack_l2_retry` | A same-set PutM removes the snapshotted M owner before SnoopRead response; Directory retries from the retained L2 line | Accepted ACK/Snoop transaction ID, PutM-to-PutAck and GetS-to-DATA_E ID matching, post-ACK L2 hit, no owner beats or DRAM read, dirty data, and independent MESI/Directory commit | 1 | hit |
| `same_line_dual_lane` | Both CPU lanes read then write disjoint bytes of one line concurrently | Independent byte-accurate scoreboard and final readback | 1 | hit |
| `litmus_message_passing` | Core0 completes DATA then READY stores; Core1 observes READY and the latest DATA on distinct lines | Independent byte-accurate MESI/data scoreboard and accepted Directory metadata monitor | 1 | hit |
| `false_sharing_same_line` | Two cores repeatedly write different words in one 64-byte line | Independent data scoreboard, snoop/request monitor, and final word readback | 1 | hit |
| `false_sharing_separate_lines` | Matched two-core write workload on distinct 64-byte lines | Independent data scoreboard and final word readback | 1 | hit |
| `false_sharing_data_checked` | A/B cases preserve both final word values | Independent architectural data scoreboard | 1 | hit |
| `litmus_generation_counter_100` | 100 distinct DATA/READY/ACK generations complete without skip, duplicate consumption, or stale data | Independent scoreboard, generation sequence checker, and Directory monitor | 1 | hit |
| `litmus_generation_backpressure` | Generation handshake remains correct with memory request/response gaps and CPU response stalls | Ready/valid driver checks, memory agent stall counters, and scoreboard | 1 | hit |
| `randomized_seeded_regression` | Four reproducible mixed read/write seeds pass the independent model | Seeded Python sequence, byte-accurate MESI/data scoreboard and protocol error output | 4 | hit |
| `random_dual_lane_pairs` | Seeded regression issues independent requests on both packed CPU lanes | Single dual-core driver and per-core response matching | 24 | hit |
| `dirty_owner_snoop_during_l2_fill` | Both core directions transfer an M-owner line while an unrelated L2 refill is active | Eight-beat owner-data scoreboard, independent Directory model, and shared L2 write-port collision monitor | 2 | hit |

## Cross coverage

| Cross | Observed transaction | Hits | Status |
| --- | --- | ---: | --- |
| `cross.cold_read_from_memory` | Invalid L1 cold GetS from memory after an L2 miss, with no snoop and an eight-beat line transfer | 71 | hit |
| `cross.remote_m_owner_read` | Core0 GetS while Core1 owns M, sourced from the remote owner with an eight-beat transfer | 110 | hit |
| `cross.remote_m_owner_read_core1` | Core1 GetS while Core0 owns M, including an overlapping independent Directory context | 239 | hit |
| `cross.shared_upgrade_snoop` | Core1 S-to-M upgrade snoops Core0 without a line-data transfer | 107 | hit |
| `cross.modified_hit_masked_store` | Core0 byte-masked M-hit store updates only selected byte lanes | 11 | hit |
| `cross.l2_hit_after_l1_eviction` | L1-evicted line refills from shared L2 without a snoop | 1 | hit |
| `cross.lookup_conflict_during_transfer` | Another line request is blocked during an owner-transfer lookup while randomized memory ready stalls are active | 1 | hit |
| `cross.lookup_conflict_during_grant` | Another line request is blocked during a grant lookup while randomized memory ready stalls are active | 1 | hit |
| `cross.dirty_owner_waits_for_fill_port` | Dirty owner writeback waits until the refill releases the shared L2 array port | 2 | hit |
| `cross.message_passing` | Ordered producer DATA/READY stores are observed by the consumer on separate lines | 1 | hit |
| `cross.false_sharing` | Same-line different-word stores create ownership traffic absent from matched separate-line stores | 1 | hit |
| `cross.generation_counter` | 100 monotonic generations cross producer/consumer with legal backpressure | 1 | hit |
