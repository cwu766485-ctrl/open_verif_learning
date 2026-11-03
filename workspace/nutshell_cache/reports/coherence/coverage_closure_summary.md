# RTL Coverage Closure Matrix Summary

Generated from each independent raw Verilator dataset listed in `coverage_closure_raw_runs.md`. The matrix includes one record per zero-count Product RTL LCOV line, branch, FSM state, and FSM arc for each run, with a run identity. Repeated source points in different runs are separate observations.

Zero count means unobserved in that raw dataset. It is not an unreachable-code waiver. Separate Python/Toffee, block, AXI, and subsystem builds are not arithmetically merged.

| Raw dataset | Metric | Unhit points |
| --- | --- | ---: |
| AXI cache subsystem E2E (five fixed seeds) | FSM arc | 44 |
| AXI cache subsystem E2E (five fixed seeds) | FSM state | 24 |
| AXI cache subsystem E2E (five fixed seeds) | LCOV RTL line | 166 |
| AXI cache subsystem E2E (five fixed seeds) | Verilator branch | 114 |
| Bus blocks | LCOV RTL line | 1 |
| Bus blocks | Verilator branch | 6 |
| DirectoryController block | FSM arc | 7 |
| DirectoryController block | FSM state | 1 |
| DirectoryController block | LCOV RTL line | 71 |
| DirectoryController block | Verilator branch | 12 |
| DirectoryMshrBank block | FSM arc | 25 |
| DirectoryMshrBank block | FSM state | 9 |
| DirectoryMshrBank block | LCOV RTL line | 125 |
| DirectoryMshrBank block | Verilator branch | 28 |
| Full coherent subsystem regression | FSM arc | 41 |
| Full coherent subsystem regression | FSM state | 24 |
| Full coherent subsystem regression | LCOV RTL line | 148 |
| Full coherent subsystem regression | Verilator branch | 86 |
| MesiL1Controller block | FSM arc | 4 |
| MesiL1Controller block | LCOV RTL line | 28 |
| MesiL1Controller block | Verilator branch | 6 |
| SharedL2DirectoryArray block | LCOV RTL line | 4 |
| SharedL2DirectoryArray block | Verilator branch | 9 |
| SharedLineEngine block | LCOV RTL line | 98 |
| SharedLineEngine block | Verilator branch | 42 |

Risk totals below describe only the primary subsystem run; rows across different runs are not pooled.

| Primary dataset risk label | Points |
| --- | ---: |
| High | 210 |
| Medium | 89 |
| Low | 0 |

**Open high-risk points:** 210 (none are waived by this report).

Primary-run review accounting: 85 points fall in hand-authored source-range reviews; 214 are mapped to source/path but not individually reviewed. All remain open until their prescribed test/proof evidence is verified.

Waiver inventory: zero approved or automatic waivers. The header-only `coverage_closure_waivers.csv` is retained as the explicit waiver record.

The detailed CSV records the raw dataset identity, RTL source line, block, feature/spec relationship, why that dataset missed it, reachability/error-protection assessment, existing evidence, other-run observation, recommended directed test or formal action, and risk.

A source-range assessment is not closure. Default/FSM branches are never called unreachable from source keywords alone; no point is waived by this report.
