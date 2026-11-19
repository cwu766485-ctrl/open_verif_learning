# MesiL1MissContext Testplan

## DUT and RTL dependencies

- DUTs: `rtl/l1/MesiL1MissContext.sv`, instantiated twice with
  `EXTERNAL_TXN_ID=1`, and `rtl/l1/MesiL1MissResponseOrder.sv` as the shared
  untagged LSU response retirement queue.
- Dependencies: `rtl/common/CoherenceProtocol.sv`.
- The production `MesiL1Controller` wrapper continues to use its legacy local
  transaction counter; this block test exercises the prepared external-ID
  mode directly.

## Interface groups

- CPU request and response handshakes.
- Directory request and grant handshakes.
- Tagged grant-data and L1 refill streams.
- L1 metadata commit and Directory grant commit.
- Reset and CPU response backpressure.

## Features, testpoints, checkers, and coverage mapping

| Feature | Testpoint | Testcase | Independent checker | Coverage observation |
|---|---|---|---|---|
| External transaction tag | Two contexts issue different lines with IDs 3 and 9 | `MesiL1MissContext_tb` | Directory address/ID checks | Both request IDs observed simultaneously |
| Grant ID routing | Younger ID 9 grant precedes ID 3 | `MesiL1MissContext_tb` | Only matching context may assert `grant_ready` | Both owner and non-owner grant-ready outcomes |
| Refill association | Eight beats for ID 9 then ID 3 | `MesiL1MissContext_tb` | Per-beat ID/index/data/last checker | Both contexts complete out-of-order refill |
| Commit/completion association | Distinct line metadata and context completion | `MesiL1MissContext_tb` | Address/state/ID matching | Both metadata and completion IDs observed |
| Same-core response ordering | Complete ID 9 before ID 3 | `MesiL1MissContext_tb` | Shared FIFO must withhold ID 9, then return 3 followed by 9 with captured data | Reverse completion plus ordered response check |
| Response backpressure | Hold the oldest response while both entries are complete | `MesiL1MissContext_tb` | Stable valid/tag/address/data check | Held response and ordered retirement |

## Known gaps

- The test composes two miss-context instances with the response-order queue,
  but it does not instantiate a production Cluster bank. Completion data is
  supplied by the test fixture; actual L1 Array data selection and storage are
  not integrated into this path.
- No two-entry L1 MSHR allocation, same-line conflict policy, replacement,
  Snoop collision, shared-array arbitration, or reset cancellation of multiple
  live integrated misses is tested here.
- The AXI subsystem test `tests/full_system/test_nonblocking_l1_mshr.py`
  separately verifies four accepted/retained L1 tracking entries before the
  first CPU response. It does not prove four Directory-issued requests: the
  second entry per core remains queued behind the single production controller.
- True same-core Miss-under-Miss, integrated response-queue use, two live
  Directory IDs per L1, and actual dual-context refill/array association remain
  OPEN for the next RTL increment.
