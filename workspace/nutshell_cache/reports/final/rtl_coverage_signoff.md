# RTL Code Coverage Release Gate

**Decision: OPEN**

- Repository HEAD: `3a4c720ef11ba9f6be126c97f725a78d276f8a82`
- Verification source fingerprint: `d25006778cded048cf4f9a4e638c3725a606460537df96d7a36f239a6cce4e01`
- Raw points inventoried: 74831; zero-count points requiring review: 29466
- Raw-hit execution attestations: 45365/45365; unattested hits: 0
- Zero-point decisions recorded: 0 (COVERED=0, PROVEN_UNREACHABLE=0, REVIEWED_WAIVER=0, OPEN=0, BLOCKED=0); zero OPEN/BLOCKED: 29466
- Archived stale historical decisions: 19; unreviewed zero-count rows: 29466
- Reviewed waivers accepted: 0

Coverage remains separated by elaborated top and metric; these tables are not summed across datasets.
RAW_COVERED means only that a nonzero point was observed in the exact hashed dataset under the recorded Top/source/tool/test/checker contract and required regression. It does not establish functional correctness; key protocol behavior requires the independent Functional-System Evidence Gate. Candidate counts exclude only independently reviewed unreachable/waiver points.

| Dataset | Metric | Raw hit/total | Candidate hit/total after approved exclusions | Candidate misses |
| --- | --- | ---: | ---: | ---: |
| axi_subsystem | branch | 509/632 | 509/632 | 123 |
| axi_subsystem | fsm_arc | 4/48 | 4/48 | 44 |
| axi_subsystem | fsm_state | 30/54 | 30/54 | 24 |
| axi_subsystem | line | 901/1068 | 901/1068 | 167 |
| axi_subsystem | toggle | 15623/32332 | 15623/32332 | 16709 |
| bus_blocks | branch | 70/76 | 70/76 | 6 |
| bus_blocks | line | 67/68 | 67/68 | 1 |
| bus_blocks | toggle | 1100/2450 | 1100/2450 | 1350 |
| directory_controller | branch | 37/42 | 37/42 | 5 |
| directory_controller | fsm_arc | 3/9 | 3/9 | 6 |
| directory_controller | fsm_state | 10/10 | 10/10 | 0 |
| directory_controller | line | 178/182 | 178/182 | 4 |
| directory_controller | toggle | 260/612 | 260/612 | 352 |
| directory_mshr_bank | branch | 100/128 | 100/128 | 28 |
| directory_mshr_bank | fsm_arc | 11/36 | 11/36 | 25 |
| directory_mshr_bank | fsm_state | 31/40 | 31/40 | 9 |
| directory_mshr_bank | line | 167/286 | 167/286 | 119 |
| directory_mshr_bank | toggle | 1249/2904 | 1249/2904 | 1655 |
| main_subsystem | branch | 473/556 | 473/556 | 83 |
| main_subsystem | fsm_arc | 13/48 | 13/48 | 35 |
| main_subsystem | fsm_state | 30/54 | 30/54 | 24 |
| main_subsystem | line | 864/992 | 864/992 | 128 |
| main_subsystem | toggle | 21931/27474 | 21931/27474 | 5543 |
| mesi_l1_controller | branch | 43/46 | 43/46 | 3 |
| mesi_l1_controller | fsm_arc | 3/6 | 3/6 | 3 |
| mesi_l1_controller | fsm_state | 7/7 | 7/7 | 0 |
| mesi_l1_controller | line | 124/132 | 124/132 | 8 |
| mesi_l1_controller | toggle | 741/1804 | 741/1804 | 1063 |
| shared_l2_directory_array | branch | 65/74 | 65/74 | 9 |
| shared_l2_directory_array | line | 75/79 | 75/79 | 4 |
| shared_l2_directory_array | toggle | 197/1778 | 197/1778 | 1581 |
| shared_line_engine | branch | 44/52 | 44/52 | 8 |
| shared_line_engine | line | 101/104 | 101/104 | 3 |
| shared_line_engine | toggle | 304/648 | 304/648 | 344 |

## Open gate findings by dataset and metric

- axi_subsystem / branch: 123 unresolved finding(s)
- axi_subsystem / fsm_arc: 44 unresolved finding(s)
- axi_subsystem / fsm_state: 24 unresolved finding(s)
- axi_subsystem / line: 167 unresolved finding(s)
- axi_subsystem / toggle: 16709 unresolved finding(s)
- bus_blocks / branch: 6 unresolved finding(s)
- bus_blocks / line: 1 unresolved finding(s)
- bus_blocks / toggle: 1350 unresolved finding(s)
- directory_controller / branch: 5 unresolved finding(s)
- directory_controller / fsm_arc: 6 unresolved finding(s)
- directory_controller / line: 4 unresolved finding(s)
- directory_controller / toggle: 352 unresolved finding(s)
- directory_mshr_bank / branch: 28 unresolved finding(s)
- directory_mshr_bank / fsm_arc: 25 unresolved finding(s)
- directory_mshr_bank / fsm_state: 9 unresolved finding(s)
- directory_mshr_bank / line: 119 unresolved finding(s)
- directory_mshr_bank / toggle: 1655 unresolved finding(s)
- main_subsystem / branch: 83 unresolved finding(s)
- main_subsystem / fsm_arc: 35 unresolved finding(s)
- main_subsystem / fsm_state: 24 unresolved finding(s)
- main_subsystem / line: 128 unresolved finding(s)
- main_subsystem / toggle: 5543 unresolved finding(s)
- mesi_l1_controller / branch: 3 unresolved finding(s)
- mesi_l1_controller / fsm_arc: 3 unresolved finding(s)
- mesi_l1_controller / line: 8 unresolved finding(s)
- mesi_l1_controller / toggle: 1063 unresolved finding(s)
- shared_l2_directory_array / branch: 9 unresolved finding(s)
- shared_l2_directory_array / line: 4 unresolved finding(s)
- shared_l2_directory_array / toggle: 1581 unresolved finding(s)
- shared_line_engine / branch: 8 unresolved finding(s)
- shared_line_engine / line: 3 unresolved finding(s)
- shared_line_engine / toggle: 344 unresolved finding(s)
- 29466 total point-level/infrastructure finding(s); see the machine-readable gate JSON and point matrix for stable IDs and details.

A PASS requires current source and dataset fingerprints, hashed regression logs for all required gates, valid Test/Checker source contracts, and an individual accepted disposition for every zero-count point. A zero-count point cannot be marked COVERED; it must first be observed in this exact dataset. PROVEN_UNREACHABLE and REVIEWED_WAIVER require evidence and independent approval. Raw hits are never transferred across elaborated Tops, and no disposition changes Raw Coverage.
