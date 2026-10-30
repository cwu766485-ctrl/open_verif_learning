# CoherentCacheSubsystem Testplan

## DUT and RTL dependencies

- **DUT:** `CoherentCacheSubsystem` (integrated two-L1 MESI, shared L2 and Directory subsystem).
- **RTL dependencies:** `rtl/Coherence.files.f` (all production RTL dependencies are owned by the canonical coherence filelist).
- **Existing bench:** `tb/CoherentCacheSubsystem_tb.sv`; its stimulus/checkers are unchanged by the move.
- **Shared verification:** the bench contains its existing SV shadow/reference state checks and protocol assertions. Python agents, independent models, scoreboards and coverage tools remain single-source under `dv/`.

## Interface Groups

Two CPU/LSU request-response lanes; L1-to-Directory request/grant/commit; snoop request/response/data; shared L2 lookup/refill/write; backing-memory request/refill/writeback; MMIO; reset/error; protocol and coverage monitors.

## Features, testpoints and checkers

The table is generated as a traceability view of the existing `dv/coverage/coherence_map.json`. It preserves the existing Feature, Testpoint, Checker and Bin ID fields; no bin is added or reclassified.

| Feature | Existing testpoint / testcase | Existing checker | Coverage Bin ID |
|---|---|---|---|
| MESI GetS | PASS: Core0 GetS refill from backing memory | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.gets_cold_refill` |
| MESI sharing/intervention | PASS: Core1 GetS shares the full latest line from the M owner | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.gets_share_m_owner` |
| MESI GetM / Upgrade | PASS: shared-to-exclusive upgrade invalidates peer; remote read sees M data | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.getm_upgrade_s` |
| MESI GetM / intervention | PASS: remote GetM invalidates an M owner and preserves its latest data | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.getm_remote_owner` |
| MESI GetM / intervention | PASS: remote GetM invalidates a clean E owner and receives all beats | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.getm_remote_clean_e` |
| MESI E-to-M | PASS: E-to-M local write is silent and preserves the full line | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.e_to_m_silent` |
| MESI progress | PASS: same-line SnoopRead waits for local E-to-M write commit | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.snoop_waits_store_commit` |
| MESI masked write | PASS: byte-masked write is visible after remote owner intervention | `subsystem_reference_scoreboard_and_protocol_invariants` | `mesi.masked_owner_write` |
| Concurrency / same line | PASS: same-line simultaneous GetS/GetM and byte-mask corner cases | `subsystem_reference_scoreboard_and_protocol_invariants` | `cpu_pair.same_line` |
| Concurrency / different lines | PASS: different-address concurrent misses route to the correct cores | `subsystem_reference_scoreboard_and_protocol_invariants` | `cpu_pair.different_lines` |
| Concurrency / Snoop progress | PASS: different-line SnoopInvalidate progresses during a local CPU response stall | `subsystem_reference_scoreboard_and_protocol_invariants` | `cpu_pair.snoop_progress` |
| L1 replacement | PASS: dirty M victim uses PutM, returns to L2, then refills by peer | `subsystem_reference_scoreboard_and_protocol_invariants` | `l1.putm` |
| L1 replacement | PASS: clean E victim is removed with PutE; dirty L2 data is preserved | `subsystem_reference_scoreboard_and_protocol_invariants` | `l1.pute` |
| L1 replacement | PASS: shared S victim is removed with PutS while the peer retains its copy | `subsystem_reference_scoreboard_and_protocol_invariants` | `l1.puts` |
| L2 live victim reclaim | PASS: L2 live victim back-invalidates an M owner and writes back its line | `subsystem_reference_scoreboard_and_protocol_invariants` | `l2.live_u_victim` |
| L2 live victim reclaim | PASS: dirty owner data survives L2 eviction through backing memory | `subsystem_reference_scoreboard_and_protocol_invariants` | `l2.dirty_owner_writeback` |
| L2 shared victim multi-snoop | PASS: DIR_S L2 victim invalidates both sharers and writes back dirty L2 data | `subsystem_reference_scoreboard_and_protocol_invariants` | `l2.shared_multisnoop` |
| MMIO isolation | PASS: MMIO read/write bypasses L1, L2, and backing memory | `subsystem_reference_scoreboard_and_protocol_invariants` | `mmio.bypass` |
| MMIO address decode | PASS: cacheable/MMIO address-domain boundary cases | `subsystem_reference_scoreboard_and_protocol_invariants` | `mmio.address_boundaries` |
| Backpressure | PASS: refill MSHR absorbs the memory line while the L2 fill port is stalled | `subsystem_reference_scoreboard_and_protocol_invariants` | `backpressure.mem_refill` |
| Backpressure | PASS: memory request/refill and CPU response survive independent stalls | `subsystem_reference_scoreboard_and_protocol_invariants` | `backpressure.independent_channels` |
| Backpressure | PASS: MMIO request and response payloads remain stable under backpressure | `subsystem_reference_scoreboard_and_protocol_invariants` | `backpressure.mmio` |
| Reset cancellation | PASS: reset cancels an active refill without a stale response | `subsystem_reference_scoreboard_and_protocol_invariants` | `reset.refill` |
| Reset cancellation | PASS: reset cancels a backpressured MMIO response | `subsystem_reference_scoreboard_and_protocol_invariants` | `reset.mmio` |
| Reset cancellation | PASS: reset cancels a stalled cache response without replay | `subsystem_reference_scoreboard_and_protocol_invariants` | `reset.cpu_rsp` |
| Reset cancellation | PASS: reset cancels an active owner SnoopData stream | `subsystem_reference_scoreboard_and_protocol_invariants` | `reset.snoop_data` |
| Reset cancellation | PASS: reset cancels a stalled dirty L2 writeback beat | `subsystem_reference_scoreboard_and_protocol_invariants` | `reset.l2_writeback` |
| Error handling | PASS: terminal memory read error suppresses success and blocks new requests | `subsystem_reference_scoreboard_and_protocol_invariants` | `error.mem_read` |
| Error handling | PASS: failed write response preserves the valid dirty L2 victim | `subsystem_reference_scoreboard_and_protocol_invariants` | `error.mem_write` |
| Seeded random data/state traffic | PASS: seeded 80-operation coherence/data scoreboard regression seed= | `subsystem_reference_scoreboard_and_protocol_invariants` | `random.seeded_data` |

## Coverage ownership and gaps

- The exact Bin IDs in the table remain owned by `dv/coverage/coherence_map.json`. Directory MSHR bank IDs are collected by its block bench and are mapped separately in `../directory_mshr_bank/testplan.md`.
- Existing directed COV_EVENTs are checked against the map by the existing closure scripts. Seeded/random coverage is limited to what the unchanged testbench actually samples; the directory refactor adds no closure claim.
- Remaining gaps are those reported by the existing coverage closure and gap review, including unhit RTL branches and scenarios not represented in the current map. See [`docs/coherence_coverage_gap_review.md`](../../../docs/coherence_coverage_gap_review.md).
