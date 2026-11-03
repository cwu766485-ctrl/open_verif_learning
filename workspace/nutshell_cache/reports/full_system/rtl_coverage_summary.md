# Raw RTL Coverage Summary

Audit source: [`docs/coverage_audit_phase1.md`](../../docs/coverage_audit_phase1.md)
Audit snapshot: 2026-11-01 14:55 +08
RTL behavior/interface changes in the full-system DV work: none

## Accounting and scope

`rtl/Coherence.files.f` contains 18 Product RTL source files. The normalized
Verilator source manifest contains the same 18 files (exact match). The
selected subsystem LCOV run contains executable line points for 14 manifest
files; the other four are explicitly N/A for line coverage in this selected
top/run, not zero-percent covered. LCOV also contains testbench and Generated/
Other records. Each line category reconciles hit + missed = total.

| LCOV category | Hit | Total | Missed |
| --- | ---: | ---: | ---: |
| Product RTL | 858 | 1006 | 148 |
| Testbench | 738 | 748 | 10 |
| Generated/Other | 0 | 0 | 0 |
| All LCOV source records | 1596 | 1754 | 158 |

Native Verilator point coverage is separate from LCOV source lines:

| Product RTL point type | Hit | Total | Missed |
| --- | ---: | ---: | ---: |
| Branch | 450 | 536 | 86 |
| Toggle | 19916 | 26978 | 7062 |
| FSM state | 30 | 54 | 24 |
| FSM arc | 7 | 48 | 41 |

Testbench native coverage is branch 235/266 and toggle 4060/6628. No testbench
FSM points or Generated/Other native points were emitted. Do not sum these
figures with independent Block, AXI, Python functional, or different-top runs.

## Per-module raw Product RTL line coverage

| RTL source | Hit / total | Missed |
| --- | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | N/A | N/A |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37 / 37 | 0 |
| `rtl/cluster/DualL1MesiCluster.sv` | 59 / 62 | 3 |
| `rtl/coherence/SharedLineEngine.sv` | 73 / 104 | 31 |
| `rtl/common/CoherenceProtocol.sv` | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 114 / 188 | 74 |
| `rtl/directory/DirectoryMshrBank.sv` | 94 / 104 | 10 |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5 / 5 | 0 |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22 / 22 | 0 |
| `rtl/interconnect/CpuMmioRouter.sv` | 31 / 34 | 3 |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50 / 50 | 0 |
| `rtl/l1/MesiL1Array.sv` | 67 / 67 | 0 |
| `rtl/l1/MesiL1Controller.sv` | 103 / 126 | 23 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6 / 6 | 0 |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75 / 79 | 4 |
| `rtl/top/CoherentCacheAxiSubsystem.sv` | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122 / 122 | 0 |

The four sources with no executable LCOV line points in this selected run are
`CachePerformanceCsr.sv`, `LineMemoryAxi4Adapter.sv`, `CoherenceProtocol.sv`,
and `CoherentCacheAxiSubsystem.sv`. Their independent APB, AXI-adapter,
package, and integrated-AXI scopes require separate evidence. This subsystem
LCOV result does not claim those scopes were covered.

## Review status and tool limitations

The detailed missed-source/line list and source-context categories are in the
[Phase 1 audit](../../docs/coverage_audit_phase1.md). It identifies 148 missed
Product RTL executable lines, including legal paths, recovery/retry paths,
protocol error handling, and FSM/default defense candidates. A default/FSM
label is only a review candidate, not proof of unreachability. No automatic
waiver or line exclusion is applied.

Verilator emitted line/branch/toggle points and native FSM state/arc points for
the selected design. FSM totals are raw state/arc observations, not a complete
specification-level state-transition proof. No unsupported metric is
fabricated. Python functional coverage is separate and was not merged with
RTL coverage.

Reviewed/eligible RTL coverage is not calculated here: point-by-point closure
and waiver review for all raw misses is incomplete. The 19/19 functional-bin
and 6/6 cross-bin closure figures belong to a different coverage model.
