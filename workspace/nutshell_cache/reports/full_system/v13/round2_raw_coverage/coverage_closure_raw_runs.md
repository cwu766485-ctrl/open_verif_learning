# Final Code Coverage Closure: Raw Run Inventory

Each row below is an independent Verilator elaboration/test definition. Values are never summed across the rows. The five-seed AXI top is merged only across those five runs because they share the same build, instrumentation, top and testcase definition.

Coverage ratios are raw observations, not signoff closure by themselves. Functional coverage and Python/Toffee observations are not merged into RTL LCOV or native point counts.

## Full coherent subsystem regression

Main subsystem smoke, multisnoop and five seeded regressions, all from one common subsystem elaboration and coverage definition. The standalone Directory MSHR regression is a separate dataset and is not included here.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 893/1024 | 131 |
| branch | 552/684 | 132 |
| toggle | 25866/33746 | 7880 |
| fsm_state | 42/80 | 38 |
| fsm_arc | 17/70 | 53 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 32/34 | 445/738 | N/A | N/A |
| `rtl/cluster/DualL1MesiCluster.sv` | 77/83 | 147/182 | 7966/10456 | N/A | N/A |
| `rtl/coherence/SharedLineEngine.sv` | 73/104 | 36/52 | 509/648 | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 125/182 | 30/42 | 521/612 | 18/40 | 9/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 94/104 | 73/86 | 929/2292 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | N/A | 350/414 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 4/4 | 222/260 | N/A | N/A |
| `rtl/interconnect/CpuMmioRouter.sv` | 31/34 | 18/20 | 1608/1872 | N/A | N/A |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 4/4 | 1274/1374 | N/A | N/A |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 53/62 | 1449/2054 | N/A | N/A |
| `rtl/l1/MesiL1Controller.sv` | N/A | N/A | 1208/1326 | N/A | N/A |
| `rtl/l1/MesiL1MissContext.sv` | 71/83 | 23/48 | 1131/1800 | 14/28 | 4/24 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 230/272 | N/A | N/A |
| `rtl/l1/MesiL1SnoopEngine.sv` | 38/46 | 15/26 | 616/706 | 10/12 | 4/10 |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 67/74 | 1096/1324 | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 50/50 | 6312/7598 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/bus/apb/CachePerformanceCsr.sv`
- `rtl/bus/axi/LineMemoryAxi4Adapter.sv`
- `rtl/common/CoherenceProtocol.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`

## AXI cache subsystem E2E (five fixed seeds)

Five official AXI E2E seeds merged only within this identical top/build/test definition.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 930/1100 | 170 |
| branch | 588/760 | 172 |
| toggle | 18350/38604 | 20254 |
| fsm_state | 42/80 | 38 |
| fsm_arc | 6/70 | 64 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | 13/17 | 7/8 | 119/558 | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | 50/51 | 57/68 | 793/1892 | N/A | N/A |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 32/34 | 263/738 | N/A | N/A |
| `rtl/cluster/DualL1MesiCluster.sv` | 70/83 | 138/182 | 5378/10456 | N/A | N/A |
| `rtl/coherence/SharedLineEngine.sv` | 66/104 | 34/52 | 309/648 | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 113/182 | 27/42 | 282/612 | 18/40 | 2/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 91/104 | 70/86 | 516/2292 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | N/A | 155/414 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 4/4 | 104/260 | N/A | N/A |
| `rtl/interconnect/CpuMmioRouter.sv` | 29/34 | 9/20 | 867/1872 | N/A | N/A |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 4/4 | 998/1374 | N/A | N/A |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 52/62 | 807/2054 | N/A | N/A |
| `rtl/l1/MesiL1Controller.sv` | N/A | N/A | 821/1326 | N/A | N/A |
| `rtl/l1/MesiL1MissContext.sv` | 71/83 | 23/48 | 797/1800 | 14/28 | 2/24 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 63/272 | N/A | N/A |
| `rtl/l1/MesiL1SnoopEngine.sv` | 35/46 | 14/26 | 424/706 | 10/12 | 2/10 |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 67/74 | 591/1324 | N/A | N/A |
| `rtl/top/CoherentCacheAxiSubsystem.sv` | 8/8 | N/A | 1249/2408 | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 50/50 | 3814/7598 | N/A | N/A |

No Product RTL points emitted in this run:

- `rtl/common/CoherenceProtocol.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`

## DirectoryController block

Standalone DirectoryController directed TB.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 178/182 | 4 |
| branch | 37/42 | 5 |
| toggle | 260/612 | 352 |
| fsm_state | 10/10 | 0 |
| fsm_arc | 3/9 | 6 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/directory/DirectoryController.sv` | 178/182 | 37/42 | 260/612 | 10/10 | 3/9 |

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
- `rtl/l1/MesiL1MissContext.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l1/MesiL1SnoopEngine.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## DirectoryMshrBank block

Standalone four-context MSHR directed/stress TB, including transfer-start backpressure.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 167/286 | 119 |
| branch | 100/128 | 28 |
| toggle | 1249/2904 | 1655 |
| fsm_state | 31/40 | 9 |
| fsm_arc | 11/36 | 25 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/directory/DirectoryController.sv` | 63/182 | 19/42 | 312/612 | 31/40 | 11/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 104/104 | 81/86 | 937/2292 | N/A | N/A |

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
- `rtl/l1/MesiL1MissContext.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l1/MesiL1SnoopEngine.sv`
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
- `rtl/l1/MesiL1MissContext.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l1/MesiL1SnoopEngine.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## MesiL1Controller block

Standalone controller refill, snoop, reset and malformed-beat tests.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 127/135 | 8 |
| branch | 46/50 | 4 |
| toggle | 1257/3204 | 1947 |
| fsm_state | 13/13 | 0 |
| fsm_arc | 5/11 | 6 |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/l1/MesiL1Controller.sv` | N/A | N/A | 496/1326 | N/A | N/A |
| `rtl/l1/MesiL1MissContext.sv` | 80/83 | 23/24 | 405/900 | 7/7 | 3/6 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | N/A | 113/272 | N/A | N/A |
| `rtl/l1/MesiL1SnoopEngine.sv` | 41/46 | 23/26 | 243/706 | 6/6 | 2/5 |

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
- `rtl/l1/MesiL1MissResponseOrder.sv`
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
- `rtl/l1/MesiL1MissContext.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l1/MesiL1SnoopEngine.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## Bus blocks

Standalone AXI line adapter and APB CSR tests, including malformed response and outstanding-ID cases.

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| line | 67/68 | 1 |
| branch | 70/76 | 6 |
| toggle | 1100/2450 | 1350 |
| fsm_state | N/A | N/A |
| fsm_arc | N/A | N/A |

| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | 16/17 | 8/8 | 433/558 | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | 51/51 | 62/68 | 667/1892 | N/A | N/A |

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
- `rtl/l1/MesiL1MissContext.sv`
- `rtl/l1/MesiL1MissResponseOrder.sv`
- `rtl/l1/MesiL1SnoopArbiter.sv`
- `rtl/l1/MesiL1SnoopEngine.sv`
- `rtl/l2/SharedL2DirectoryArray.sv`
- `rtl/top/CoherentCacheAxiSubsystem.sv`
- `rtl/top/CoherentCacheSubsystem.sv`

## Interpretation limits

- Verilator line, branch, toggle and FSM metrics have separate denominators. FSM metrics include only state machines extracted by this Verilator build; a zero denominator means no extracted machine, not zero design FSM coverage.
- Toggle totals are affected by Verilator instrumentation filters, optimization and elaboration. They are point totals for emitted signals, not all declared RTL bits.
- Python/Toffee uses a different simulator wrapper and does not emit compatible Verilator coverage points. Its passing tests are cited as separate functional evidence; its coverage is not added to RTL reports.
- Source lines absent from an LCOV file have no executable line point in that elaboration. Package-only files can legitimately emit no runtime point; wrapper files may still emit points in the AXI top even when absent in the selected non-AXI subsystem run.
- Block and subsystem coverage are separately reported. They must not be arithmetically combined because parameterization, elaborated hierarchy and stimulus differ.
