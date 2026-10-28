# Coherence RTL Coverage Gap Review

Generated from `reports/coherence/coverage.info` on 2026-10-28 01:32 +08.

## Summary

- Merged line records: 3153/3441 hit; 288 missed.
- Product RTL: 1579/1823 hit; 244 missed lines.
- SystemVerilog testbench: 44 missed lines (kept separate from RTL).

## Per-file unhit line ranges

Line numbers refer to the source paths in the merged LCOV report.

| Source | Hit / total | Missed | Unhit lines |
| --- | ---: | ---: | --- |
| `../tests/subsystem/rtl/CoherentCacheSubsystem_tb.sv` | 1534/1578 | 44 | 581, 694–696, 976–977, 1123, 1324–1325, 1330–1332, 1334–1336, 1359, 1363–1364, 1403–1406, 1436, 1440–1441, 1504, 1509–1510, 1514–1515, 1549, 1897, 1925, 1945–1947, 1956, 1988, 1996, 2118, 2438, 2482, 2527, 2564 |
| `cluster/DualL1MesiCluster.sv` | 126/134 | 8 | 407–409, 412–413, 443–445 |
| `directory/DirectoryController.sv` | 218/323 | 105 | 198–201, 238–241, 277–286, 299–302, 313–315, 331–334, 353, 356–364, 366–369, 378–380, 388–389, 392–401, 413–418, 431–434, 438–441, 467, 470, 475–480, 482–493, 495–498, 501–504, 529, 531–534 |
| `directory/DirectoryMshrBank.sv` | 171/188 | 17 | 147–148, 157, 159, 161, 179, 288, 342–344, 365–368, 375–377 |
| `l1/MesiL1Array.sv` | 146/159 | 13 | 260–262, 269–270, 290–291, 300–301, 309–310, 326, 341 |
| `l1/MesiL1Controller.sv` | 188/225 | 37 | 254–256, 287–289, 309, 317–318, 345, 347–349, 365–368, 377–379, 394–395, 409, 415–420, 429, 436, 439–440, 454, 456–458 |
| `l2/SharedL2DirectoryArray.sv` | 187/197 | 10 | 274–275, 288–289, 305, 313–314, 326–327, 340 |
| `top/CoherentCacheSubsystem.sv` | 543/597 | 54 | 675, 1191, 1219–1221, 1337–1339, 1345–1347, 1386–1388, 1395–1397, 1407–1409, 1411–1412, 1422–1424, 1436–1439, 1450–1452, 1480, 1482–1484, 1502–1504, 1524, 1535–1538, 1552–1558, 1570–1572 |

## Risk classification and closure candidates

The 244 missed product-RTL lines were inspected at their source locations and
grouped by behavior. “Unhit” means the merged subsystem LCOV run did not execute
the line; it does not mean the behavior is unreachable in the module benches or
formal harnesses, whose coverage databases are separate.

| RTL block | Unhit lines | Source-level behavior | Review / next directed evidence |
| --- | ---: | --- | --- |
| `DirectoryController` | 105 | Most lines reject illegal I/S/U metadata, invalid Put ownership/opcode, and wrong Snoop response type. Remaining unhit legal recovery includes GetM when the requester is still recorded as U owner and stale Upgrade recovery. The no-data Snoop ACK to authoritative L2 refill now has integrated Python/Toffee evidence, although that separate simulator run is not part of this LCOV snapshot. | Keep malformed-state paths as negative protocol checks. Track owner-self GetM and stale Upgrade as follow-up legal-recovery tests; retain the ACK-to-L2 case as a regression and do not infer its LCOV hit from Python evidence. |
| `DirectoryMshrBank` | 17 | Same-line Put serialization and the stalled-Snoop Put bypass; locks that hold the selected Directory-write, Snoop, transfer-start, and Grant context while downstream ready is low. | Existing MSHR module directed/formal tests cover four contexts, duplicate suppression, Put bypass, and reset. The subsystem line report does not cover all arbitration lock/reselection paths; add integrated ready-low tests that change competing contexts while each offer is stalled. |
| `MesiL1Controller` | 37 | Illegal Grant/data beat and invalid opcode checks; snoop tag-miss/no-data recovery; malformed owner-data beat handling and default/error states. | `test_python_snoop_ack_retries_from_authoritative_l2` now exercises the legal same-set PutM/SnoopRead overlap and checks no-data ACK, retained Directory authority, and L2 retry with independent data/state checks. This is separate Python/Toffee evidence; the integrated SV LCOV snapshot remains unchanged. Keep malformed beat cases as checker/mutation candidates. |
| `MesiL1Array` | 13 | Refill address/way/beat/last mismatch, metadata write to a missing line, invalid store permission, and line-read miss without an authorized miss indication. | These are primarily input-contract guards. Add focused negative beat-order/last checks only where the interface permits malformed traffic; legal grant/refill sequencing is already exercised by the functional regression. |
| `SharedL2DirectoryArray` | 10 | Illegal directory metadata, eviction of a live/dirty entry, malformed line-write start/address/beat/last, or write to a full set without a victim. | Preserve as protocol guards. The highest-value directed negative case is an attempted invalidate of a live or dirty way; valid dirty writeback sequencing is already covered by owner-victim tests. |
| `DualL1MesiCluster` | 8 | Illegal replacement response/default state and replay after a same-set Put/Snoop admission conflict. | Add a replacement replay test with the snoop target and Put source on each core in turn; existing subsystem dense-set tests cover the broader race but not every replacement FSM branch. |
| `CoherentCacheSubsystem` | 54 | MMIO arbitration/error state and memory-adapter/engine protocol guards for response ID, stream beat/last, owner-data, and engine-state mismatches. A few normal branches are related to rare refill/victim resource transitions. | Current Python adapter tests cover AXI errors/ID reuse and the integrated top covers valid R/B stalls. Add top-level malformed R/B ID/RESP and stream-framing injection if those error pins are part of the release contract; do not infer top-level error coverage from adapter-only tests. |

The 44 testbench misses are mostly deliberately untriggered fatal guards and
helper/setup branches. They are not counted as product-RTL coverage. Some are
valuable for checker sensitivity; the nine Python checker fault injections and
two real L1 RTL mutations provide separate evidence, but do not claim those
testbench source lines were covered.

## Review conclusion

The unhit RTL is concentrated in defensive protocol-error handling, illegal metadata/opcode rejection, reset/error FSM defaults, and rare recovery/arbiter-lock paths. Directory owner-self GetM, stale Upgrade, and selected MSHR/replacement arbitration paths remain follow-up risks. The Snoop ACK-to-L2 retry is now a required Python/Toffee regression with independent data, transaction, MESI, and Directory checks; it remains unhit in the separate integrated SV LCOV snapshot, which is not inferred from Python evidence. These coverage gaps are not evidence of a functional failure by themselves, and the remaining legal recovery paths are not waived. Existing bounded formal and independent Python/Toffee tests provide separate evidence for transaction stability, MSHR admission, reset cancellation, data integrity, and coherence state.

The testbench misses are assertion/error guards and setup branches; they are reported separately. This review does not waive any functional requirement and does not claim 100% statement/branch coverage. PPA, SRAM mapping, and STA are outside this review.
