# SharedLineEngine Testplan

## DUT and RTL dependencies

- DUT: `rtl/coherence/SharedLineEngine.sv`.
- RTL dependency: `rtl/common/CoherenceProtocol.sv`.
- Independent signal-level bench: `dv/blocks/shared_line_engine/tb/SharedLineEngine_tb.sv`.
- The bench uses the production DUT and real input/output handshakes. It does not edit internal state. It checks internal state only as an observation to make transaction progress and fail-stop outcomes explicit.

## Interface groups

- Directory transfer start/completion and grant-data requests.
- L2 lookup, victim metadata, line read/write stream, directory clear, mark-clean and invalidate.
- Two-core snoop request, response and dirty-owner data stream.
- Backing-memory read request/response and write request/data/response.
- Active-low protocol/data status and synchronous reset recovery.

## Features, testpoints, and checking

| Feature | Testpoint / testcase | Independent checker | Coverage obligation |
| --- | --- | --- | --- |
| Grant read accepted after L2 backpressure | `test_grant_read_backpressure` | Checks latched aligned address, transaction ID and destination; state hold; data stream final-beat retirement | Grant wait and delayed hit behavior |
| Grant and L2 hit accepted in the same cycle | `test_grant_immediate_l2_hit` | Checks immediate stream entry, non-final beat hold, and final-beat retirement | Immediate grant/read handshake arm |
| Grant followed by L2 miss | `test_grant_immediate_l2_miss_fault`, `test_grant_read_miss_fault` | Checks `ENGINE_ERROR` and sticky protocol error for immediate and delayed lookup paths | Both grant lookup miss guards |
| L2 refill hit and cold miss | `test_refill_hit_and_cold_miss` | Checks aligned address, transfer completion on hit, and memory request on cold miss | Refill hit/no-victim arms |
| PutM line write | `test_putm_stream` | Holds L2 write ready low, then checks all eight accepted beat indexes, final marker and one completion | PutM stream and ready backpressure |
| Malformed PutM | `test_putm_malformed_beat` | Supplies an out-of-order first beat and checks fail-stop | PutM beat-order protection |
| Clean invalid victim | `test_clean_invalid_victim` | Checks direct invalidate path and refill release | Invalid, clean victim fast path |
| Clean shared victim with two sharers | `test_clean_shared_victim_reclaim` | Checks core 0 then core 1 selection, snoop-send hold under backpressure, INV_ACK progression, Directory-clear hold, invalidate and refill release | Multi-target snoop and clean reclaim |
| Dirty unique owner victim | `test_dirty_owner_victim_writeback` | Checks owner core 1, eight data beats and transaction ID, Directory clear, L2 victim read, memory write request, eight write beats, B response, mark-clean, invalidate and refill release | Dirty owner collection and writeback lifecycle |
| Memory read channel faults | `test_memory_protocol_faults` | Checks malformed R protocol and matched R error are distinguished and fail-stop | Read protocol/data error handling |
| Memory write channel faults | `test_memory_protocol_faults`, `test_dirty_writeback_faults` | Checks stray B, skipped beat, mismatched B ID and matching B error; verifies protocol-vs-data error classification | Write response ownership, ordering and error guards |
| Victim and transfer faults | `test_memory_protocol_faults`, `test_dirty_writeback_faults` | Checks invalid victim metadata, unsupported transfer opcode, owner response ID/no-data, owner beat index/last/ID faults | Victim metadata, opcode and owner stream guards |
| Reset after sticky fault | Fault tasks call `reset_dut` between cases | Checks state returns to IDLE and both sticky status bits clear | Error-state reset; not active-transaction reset |

No Functional Coverage Bin IDs were added or changed by this block test.

## Current raw result

Latest independent Verilator dataset is reported in `reports/coherence/coverage_closure_raw_runs.md`. It is a standalone parameterized Engine top and is **not merged** with subsystem, AXI or other Block runs. Current result: line 101/104, branch 44/52, toggle 304/648; this top did not emit FSM state/arc points.

The three missed executable LCOV lines are the `default` state-encoding guard in `SharedLineEngine.sv:366-368`. The native branch misses are listed individually in `reports/final/coverage_closure_matrix.csv`. They remain open; this testplan does not label them unreachable or waived.

## Remaining verification gaps

- Illegal FSM encoding is not driven through a supported public interface, and this bench has no formal proof that the encoding cannot occur. Keep the default fail-stop logic; classify the point as open pending proof or a safe dedicated fault-injection mechanism.
- Remaining native branch outcomes need point-by-point review. They include dirty invalid victim handling, owner-core selection for core 0, L2 victim-read miss, and wait/ready arms that this directed set does not exercise. Do not infer each point's exact meaning from line number alone; use the coverage point identity and RTL condition.
- Dirty-owner write request/data, mark-clean and invalidate backpressure are not comprehensively stalled in this bench. Active reset in every Engine state is also untested.
- Refill ID/beat mismatch belongs to the external refill-MSHR/adapter boundary (`mem_mshr_r_match`/`mem_r_protocol_bad`); this block does not independently reconstruct the full AXI response protocol.
- Interface-driven fault cases validate Engine fail-stop behavior, but do not establish that such malformed combinations can arise in the integrated subsystem.
- Required subsystem-wide closure remains governed by the full subsystem dataset and `reports/final/coverage_closure_matrix.csv`; Block hits are independent evidence only and do not erase subsystem raw misses.

## Execution

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_shared_line_engine
make COHERENCE_JOBS=2 coherence_coverage_audit
```
