# Final Code Coverage Closure: Raw Run Inventory

Each row below is an independent Verilator elaboration/test definition. Values are never summed across the rows. The five-seed AXI top is merged only across those five runs because they share the same build, instrumentation, top and testcase definition.

Coverage ratios are raw observations, not signoff closure by themselves. Functional coverage and Python/Toffee observations are not merged into RTL LCOV or native point counts.

## Full coherent subsystem regression

Main subsystem smoke, multisnoop, five seeded regressions and Directory MSHR regression; one common elaboration and coverage definition.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 858/1006 | 148 |
| branch | 450/536 | 86 |
| toggle | 19916/26978 | 7062 |
| fsm_state | 30/54 | 24 |
| fsm_arc | 7/48 | 41 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 32/34 | 429/738 | N/A | N/A |
| `rtl/cluster/DualL1MesiCluster.sv` | 59/62 | 54/62 | 5066/6300 | N/A | N/A |
| `rtl/coherence/SharedLineEngine.sv` | 73/104 | 36/52 | 468/648 | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 114/188 | 29/42 | 497/612 | 18/40 | 4/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 94/104 | 71/86 | 863/2292 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | N/A | 276/414 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 4/4 | 183/260 | N/A | N/A |
| `rtl/interconnect/CpuMmioRouter.sv` | 31/34 | 18/20 | 1517/1872 | N/A | N/A |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 4/4 | 1215/1374 | N/A | N/A |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 54/62 | 1314/2054 | N/A | N/A |
| `rtl/l1/MesiL1Controller.sv` | 103/126 | 31/46 | 1291/1532 | 12/14 | 3/12 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 195/272 | N/A | N/A |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 67/74 | 992/1324 | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 50/50 | 5610/7286 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`

## AXI cache subsystem E2E (five fixed seeds)

Five official AXI E2E seeds merged only within this identical top/build/test definition.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 916/1082 | 166 |
| branch | 498/612 | 114 |
| toggle | 15559/31836 | 16277 |
| fsm_state | 30/54 | 24 |
| fsm_arc | 4/48 | 44 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | 13/17 | 7/8 | 117/558 | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | 50/51 | 57/68 | 793/1892 | N/A | N/A |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 32/34 | 260/738 | N/A | N/A |
| `rtl/cluster/DualL1MesiCluster.sv` | 59/62 | 55/62 | 3792/6300 | N/A | N/A |
| `rtl/coherence/SharedLineEngine.sv` | 66/104 | 34/52 | 309/648 | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 113/188 | 27/42 | 282/612 | 18/40 | 2/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 91/104 | 70/86 | 516/2292 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | N/A | 155/414 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 4/4 | 104/260 | N/A | N/A |
| `rtl/interconnect/CpuMmioRouter.sv` | 29/34 | 9/20 | 871/1872 | N/A | N/A |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 4/4 | 998/1374 | N/A | N/A |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 53/62 | 799/2054 | N/A | N/A |
| `rtl/l1/MesiL1Controller.sv` | 103/126 | 29/46 | 921/1532 | 12/14 | 2/12 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 63/272 | N/A | N/A |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 67/74 | 591/1324 | N/A | N/A |
| `rtl/top/CoherentCacheAxiSubsystem.sv` | 8/8 | N/A | 1251/2408 | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 50/50 | 3737/7286 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/common/CoherenceProtocol.sv`

## DirectoryController block

Standalone DirectoryController directed TB.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 117/188 | 71 |
| branch | 30/42 | 12 |
| toggle | 236/612 | 376 |
| fsm_state | 9/10 | 1 |
| fsm_arc | 2/9 | 7 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/directory/DirectoryController.sv` | 117/188 | 30/42 | 236/612 | 9/10 | 2/9 |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/coherence/SharedLineEngine.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/directory/DirectoryMshrBank.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l1/MesiL1Controller.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## DirectoryMshrBank block

Standalone four-context MSHR directed/stress TB, including transfer-start backpressure.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 167/292 | 125 |
| branch | 100/128 | 28 |
| toggle | 1063/2904 | 1841 |
| fsm_state | 31/40 | 9 |
| fsm_arc | 11/36 | 25 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/directory/DirectoryController.sv` | 63/188 | 19/42 | 276/612 | 31/40 | 11/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 104/104 | 81/86 | 787/2292 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/coherence/SharedLineEngine.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l1/MesiL1Controller.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## SharedLineEngine block

Standalone immediate/delayed grant read, refill, PutM, multi-sharer clean victim, dirty-owner writeback, backpressure and selected protocol fault cases.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 101/104 | 3 |
| branch | 44/52 | 8 |
| toggle | 304/648 | 344 |
| fsm_state | N/A | N/A |
| fsm_arc | N/A | N/A |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/coherence/SharedLineEngine.sv` | 101/104 | 44/52 | 304/648 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/directory/DirectoryController.sv`
- `rtl/directory/DirectoryMshrBank.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l1/MesiL1Controller.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## MesiL1Controller block

Standalone controller refill, snoop, reset and malformed-beat tests.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 104/132 | 28 |
| branch | 40/46 | 6 |
| toggle | 629/1804 | 1175 |
| fsm_state | 7/7 | 0 |
| fsm_arc | 2/6 | 4 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/l1/MesiL1Controller.sv` | 98/126 | 40/46 | 542/1532 | 7/7 | 2/6 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 87/272 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/coherence/SharedLineEngine.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/directory/DirectoryController.sv`
- `rtl/directory/DirectoryMshrBank.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## SharedL2DirectoryArray block

Standalone L2 array lookup, stream, victim and malformed-write tests.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 75/79 | 4 |
| branch | 65/74 | 9 |
| toggle | 197/1778 | 1581 |
| fsm_state | N/A | N/A |
| fsm_arc | N/A | N/A |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 65/74 | 197/1778 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/coherence/SharedLineEngine.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/directory/DirectoryController.sv`
- `rtl/directory/DirectoryMshrBank.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l1/MesiL1Controller.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## Bus blocks

Standalone AXI line adapter and APB CSR tests, including malformed response and outstanding-ID cases.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 67/68 | 1 |
| branch | 70/76 | 6 |
| toggle | 682/2450 | 1768 |
| fsm_state | N/A | N/A |
| fsm_arc | N/A | N/A |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | 16/17 | 8/8 | 51/558 | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | 51/51 | 62/68 | 631/1892 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/axi/MemoryRefillMshrBank.sv`
- `rtl/cluster/DualL1MesiCluster.sv`
- `rtl/coherence/SharedLineEngine.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/directory/DirectoryController.sv`
- `rtl/directory/DirectoryMshrBank.sv`
- `rtl/interconnect/CoherenceRequestArbiter.sv`
- `rtl/interconnect/CoherenceRequestArbiterCore.sv`
- `rtl/interconnect/CpuMmioRouter.sv`
- `rtl/interconnect/L2LineWriteArbiter.sv`
- `rtl/l1/MesiL1Array.sv`
- `rtl/l1/MesiL1Controller.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## Interpretation limits

- Verilator line, branch, toggle and FSM metrics have separate denominators. FSM metrics include only state machines extracted by this Verilator build; a zero denominator means no extracted machine, not zero design FSM coverage.
- Toggle totals are affected by Verilator instrumentation filters, optimization and elaboration. They are point totals for emitted signals, not all declared RTL bits.
- Python/Toffee uses a different simulator wrapper and does not emit compatible Verilator coverage points. Its passing tests are cited as separate functional evidence; its coverage is not added to RTL reports.
- Source lines absent from an LCOV file have no executable line point in that elaboration. Package-only files can legitimately emit no runtime point; wrapper files may still emit points in the AXI top even when absent in the selected non-AXI subsystem run.
- Block and subsystem coverage are separately reported. They must not be arithmetically combined because parameterization, elaborated hierarchy and stimulus differ.
