# MesiL1MissResponseOrder Testplan

## DUT and dependencies

- DUT: `rtl/l1/MesiL1MissResponseOrder.sv`.
- Dependency: `rtl/common/CoherenceProtocol.sv` for the default transaction ID width.

## Interface groups

- MSHR reservation (`reserve_valid/ready/tag`).
- Tagged completion (`complete_valid/ready/tag/address/write/data`).
- Untagged ordered CPU miss response (`resp_valid/ready/tag/address/write/data`).
- Reset and occupancy monitor.

## Testpoints and checker mapping

| Feature | Testpoint | Checker | Status |
|---|---|---|---|
| Reverse completion | Reserve tag 3 then 9; complete 9 before 3 | Head-of-order response must remain hidden until tag 3 completes | PASS |
| FIFO retirement | Both complete, CPU response accepts twice | Returned tags and payloads must be 3 then 9 | PASS |
| Response stall | Hold `resp_ready=0` | Valid/tag/address/write remain stable | PASS |
| Completion data retention | Complete B before A using distinct data payloads | FIFO response carries each tag's captured data even when completion order differs | PASS |
| Full capacity | Reserve two entries | Occupancy reaches two and `reserve_ready` deasserts | PASS |
| Tag reuse | Retire, then reserve and complete tag 3 again | No stale address/write payload leaks from prior allocation | PASS |

This unit test does not establish MSHR allocation correctness, array data
lookup, Directory issue, refill routing, snoop/replacement arbitration, or
system-level two-miss/four-miss behavior. There are no new product functional
coverage bin IDs in this block; its checks are direct assertions in the SV TB.
