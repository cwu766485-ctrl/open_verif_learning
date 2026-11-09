# RTL Code Coverage Sign-off Status

**Decision: OPEN. This is not a completed RTL code-coverage closure or release sign-off.**

## Evidence identity

- RTL/DV source SHA tested: `8e268bda19f14ff6d587ca38d2813f69b868da97` (the source snapshot before this report-only evidence commit).
- Source fingerprint: `552e2c15801193839282bda632b0ce250d49af255d15cc7e5f462be36300f006`.
- Product RTL manifest: `18` files; 8 independent Verilator datasets.
- Verilator: `Verilator 5.053 devel rev v5.052-521-g6388139f7 (mod)`; coverage tool: `Verilator 5.053 devel rev v5.052-521-g6388139f7 (mod)`.
- Raw data: [`rtl_coverage_raw/README.md`](rtl_coverage_raw/README.md), dataset manifest [`rtl_coverage_dataset_manifest.json`](rtl_coverage_dataset_manifest.json), full point inventory [`rtl_release_point_matrix.csv.gz`](rtl_release_point_matrix.csv.gz).

## Main Subsystem raw coverage

These are observations from `CoherentCacheSubsystem_tb`, not reviewed eligible coverage.

| Metric | Raw hit/total | Miss | Raw rate |
| --- | ---: | ---: | ---: |
| line | 850/992 | 142 | 85.69% |
| branch | 468/556 | 88 | 84.17% |
| toggle | 19996/27474 | 7478 | 72.78% |
| fsm_state | 30/54 | 24 | 55.56% |
| fsm_arc | 7/48 | 41 | 14.58% |

## Baseline comparison

The earlier audit reported Main Subsystem line coverage as `850/998`; the current source snapshot reports `850/992`. The six-point denominator difference is localized to `DirectoryController.sv`: commit `422ab9d` removed six executable statements that incorrectly refilled/granted Modified after reporting an invalid `DIR_I + Upgrade` protocol error. The replacement fail-stop behavior has a dedicated block checker and passed the current regression. The number of hit lines remains 850; this is a source behavior correction, not test-driven coverage closure. Branch, toggle and FSM counts are unchanged from the earlier Main Subsystem raw report.

| RTL source | Earlier line hit/total | Current line hit/total |
| --- | ---: | ---: |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 37/37 |
| `rtl/cluster/DualL1MesiCluster.sv` | 51/54 | 51/54 |
| `rtl/coherence/SharedLineEngine.sv` | 73/104 | 73/104 |
| `rtl/directory/DirectoryController.sv` | 114/188 | 114/182 |
| `rtl/directory/DirectoryMshrBank.sv` | 94/104 | 94/104 |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | 5/5 |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 22/22 |
| `rtl/interconnect/CpuMmioRouter.sv` | 31/34 | 31/34 |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 50/50 |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 67/67 |
| `rtl/l1/MesiL1Controller.sv` | 103/126 | 103/126 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | 6/6 |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 75/79 |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 122/122 |

## Independent raw datasets

Each elaborated top retains its own denominator. Do not add these rows together.

### `axi_subsystem` — CoherentCacheAxiSubsystem_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 901/1068 | 167 |
| branch | 509/632 | 123 |
| toggle | 15623/32332 | 16709 |
| fsm_state | 30/54 | 24 |
| fsm_arc | 4/48 | 44 |
### `bus_blocks` — CacheBusBlocks_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 67/68 | 1 |
| branch | 70/76 | 6 |
| toggle | 1100/2450 | 1350 |
### `directory_controller` — DirectoryController_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 122/182 | 60 |
| branch | 30/42 | 12 |
| toggle | 250/612 | 362 |
| fsm_state | 10/10 | 0 |
| fsm_arc | 3/9 | 6 |
### `directory_mshr_bank` — DirectoryMshrBank_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 167/286 | 119 |
| branch | 100/128 | 28 |
| toggle | 1063/2904 | 1841 |
| fsm_state | 31/40 | 9 |
| fsm_arc | 11/36 | 25 |
### `main_subsystem` — CoherentCacheSubsystem_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 850/992 | 142 |
| branch | 468/556 | 88 |
| toggle | 19996/27474 | 7478 |
| fsm_state | 30/54 | 24 |
| fsm_arc | 7/48 | 41 |
### `mesi_l1_controller` — MesiL1Controller_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 107/132 | 25 |
| branch | 41/46 | 5 |
| toggle | 688/1804 | 1116 |
| fsm_state | 7/7 | 0 |
| fsm_arc | 3/6 | 3 |
### `shared_l2_directory_array` — SharedL2DirectoryArray_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 75/79 | 4 |
| branch | 65/74 | 9 |
| toggle | 197/1778 | 1581 |
### `shared_line_engine` — SharedLineEngine_tb

| Metric | Raw hit/total | Miss |
| --- | ---: | ---: |
| line | 101/104 | 3 |
| branch | 44/52 | 8 |
| toggle | 304/648 | 344 |

The full source manifest reconciles 18/18 product RTL files. Absence of executable coverage points in a given top is reported per dataset; it is not evidence that another top exercised the same point.

## Point review and closure status

- Stable point inventory: **74,831** points across the eight datasets.
- Raw-hit points without an accepted current-source/current-dataset disposition: **43,074**.
- Zero-count points without a reviewed disposition: **31,757**.
- Historical ledger records: 19; all are bound to older source/dataset fingerprints and are stale for this raw run.
- Current valid point dispositions: **0**. Approved waivers: **0**.
- Reviewed Eligible Coverage: **not computable** until current evidence is reviewed point by point.
- Detailed zero-count source/line review matrix: [`coverage_closure_matrix.csv`](coverage_closure_matrix.csv). The machine gate matrix contains every raw line/branch/toggle/FSM point.

Selected audit conclusions are recorded in [`../../docs/coherence_coverage_gap_review.md`](../../docs/coherence_coverage_gap_review.md): invalid `DIR_I + Upgrade` is a protocol error and fail-stops; malformed beat/last cases are negative-protocol paths; `CpuMmioRouter` illegal FSM default remains defensive and unproven unreachable; `SharedLineEngine` Grant Read requires a precise valid L2-hit precondition. These classifications are not blanket waivers and do not close the remaining points.

## Release Gate

`make COHERENCE_JOBS=2 coherence_release_gate` ran its **15 gate unit tests successfully**, then returned the expected non-zero result because point review is incomplete. Final decision: **OPEN**. The gate output is in [`rtl_release_gate.json.gz`](rtl_release_gate.json.gz), [`rtl_release_point_matrix.csv.gz`](rtl_release_point_matrix.csv.gz), and [`../closure/rtl_release_gate.log.gz`](../closure/rtl_release_gate.log.gz). No coverage denominator was excluded by an approved waiver.

## Regression evidence

All eight required local regression gates passed at source SHA `8e268bda19f14ff6d587ca38d2813f69b868da97` and fingerprint `552e2c15801193839282bda632b0ce250d49af255d15cc7e5f462be36300f006`. The full-system run reported 70 passed and 1 skipped; checked Full-System Functional/Cross closure is 53/53 and 35/35. Python coherence closure is 49/49 Functional and 19/19 Cross. The stress target passed 280 seeded environments. See [`verification_run_manifest.json`](verification_run_manifest.json) and the compressed logs under [`../closure/release_runs/`](../closure/release_runs/).

The local tested source SHA differs from the historical PR CI SHA `d194d3f4552aa6d8f6e6c251f1995fc0f5bbff42`. No new remote CI result is claimed until the evidence commit is pushed and its Actions run is checked.

## Scope and remaining risk

The raw counts still include unreviewed legal paths, recovery paths, defensive/error branches and tool/instrumentation-sensitive points. No point is marked unreachable or waived without accepted evidence. Required Line/Branch/FSM closure is therefore unresolved. Toggle results are raw only and have not been bulk-waived. Formal/fault-injection evidence from existing regressions is recorded, but is not automatically credited to another elaborated-top raw point.

PPA, STA, physical SRAM macro mapping and chip-level implementation are excluded. **Final decision: OPEN; do not describe this as full code-coverage closure.**
