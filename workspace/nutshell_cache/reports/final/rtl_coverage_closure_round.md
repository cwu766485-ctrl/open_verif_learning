# RTL Coverage Closure — Final Round Status

**Decision: OPEN.** This report records the final closure round’s reproducible baseline, release-gate behavior, and unresolved raw coverage. It does not claim full RTL code coverage closure.

## Source and evidence identity

- Tested source commit: `0f18c4363a5e7ab7612417645d3bb20b655a3df5`
- Verification source fingerprint: `51545483279d0f053de85e8abbb2dd845f9df577cd1f3343c77aab4f6034f8bd`
- RTL manifest: 18 Product RTL files.
- Coverage: 8 independent Elaborated Top datasets; metrics and denominators are never combined across Tops.
- Raw point inventory: 74,831 total points; 43,074 have Count > 0; 31,757 have Count = 0.
- Point inventory: `reports/final/rtl_release_point_matrix.csv.gz` (one stable ID per dataset/metric/source/identity).
- Full machine gate output: `reports/final/rtl_release_gate.json.gz` (compressed exact gate JSON; SHA-256 `3aa6fe0ef1be5060e7587cc95727aefe2973901b64a685a4950ae0d66e6d4ab1`). Regression logs referenced by the manifests are retained under `reports/closure/release_runs/`.

## Raw Coverage by dataset

Each cell is `raw hit / total (change in hit count from the frozen pre-round dataset)`. The recorded before/after raw counts are unchanged. The baseline manifest fingerprint was `552e2c15801193839282bda632b0ce250d49af255d15cc7e5f462be36300f006`; current RTL/DV source fingerprint is `51545483279d0f053de85e8abbb2dd845f9df577cd1f3343c77aab4f6034f8bd`. Raw numbers are comparable because each row refers to the same named Top/metric and its dataset fingerprint; percentages from different Tops are not pooled.

| Dataset / Elaborated Top | Line | Branch | Toggle | FSM State | FSM Arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| axi_subsystem | 901/1068 (Δhit +0) | 509/632 (Δhit +0) | 15623/32332 (Δhit +0) | 30/54 (Δhit +0) | 4/48 (Δhit +0) |
| bus_blocks | 67/68 (Δhit +0) | 70/76 (Δhit +0) | 1100/2450 (Δhit +0) | N/A | N/A |
| directory_controller | 122/182 (Δhit +0) | 30/42 (Δhit +0) | 250/612 (Δhit +0) | 10/10 (Δhit +0) | 3/9 (Δhit +0) |
| directory_mshr_bank | 167/286 (Δhit +0) | 100/128 (Δhit +0) | 1063/2904 (Δhit +0) | 31/40 (Δhit +0) | 11/36 (Δhit +0) |
| main_subsystem | 850/992 (Δhit +0) | 468/556 (Δhit +0) | 19996/27474 (Δhit +0) | 30/54 (Δhit +0) | 7/48 (Δhit +0) |
| mesi_l1_controller | 107/132 (Δhit +0) | 41/46 (Δhit +0) | 688/1804 (Δhit +0) | 7/7 (Δhit +0) | 3/6 (Δhit +0) |
| shared_l2_directory_array | 75/79 (Δhit +0) | 65/74 (Δhit +0) | 197/1778 (Δhit +0) | N/A | N/A |
| shared_line_engine | 101/104 (Δhit +0) | 44/52 (Δhit +0) | 304/648 (Δhit +0) | N/A | N/A |

### Main Subsystem zero-count inventory by RTL source

Counts below are only the `main_subsystem` dataset. They count raw point identities per metric, not unique lines; a source line may own multiple branch/FSM/toggle points.

| Product RTL block | Line | Branch | FSM State | FSM Arc | Toggle |
| --- | ---: | ---: | ---: | ---: | ---: |
| DirectoryController | 68 | 13 | 22 | 32 | 115 |
| SharedLineEngine | 31 | 16 | 0 | 0 | 180 |
| MesiL1Controller | 23 | 15 | 2 | 9 | 241 |
| DirectoryMshrBank | 10 | 15 | 0 | 0 | 1445 |
| DualL1MesiCluster | 3 | 10 | 0 | 0 | 1634 |
| SharedL2DirectoryArray | 4 | 7 | 0 | 0 | 332 |

Main Subsystem aggregate remains: Line **850/992**, Branch **468/556**, Toggle **19,996/27,474**, FSM State **30/54**, FSM Arc **7/48**. Its 142 missed source lines are concentrated in DirectoryController (68), SharedLineEngine (31), MesiL1Controller (23), DirectoryMshrBank (10), SharedL2DirectoryArray (4), DualL1MesiCluster (3), and CpuMmioRouter (3).

## Release gate and zero-count disposition

- Raw-hit attestations: **43,074/43,074**. The gate verified stable Point ID/metric, source hashes, Top and dataset fingerprint, raw file hashes, regression gate status, and test/checker source contracts.
- This is execution evidence only. It does not replace protocol correctness evidence. Critical MESI features remain subject to the separate Monitor/Checker evidence gate.
- Zero-count points: **31,757; accepted current dispositions: 0; OPEN/unreviewed: 31,757**.
- Historical decision rows: **19**, all stale against current source/dataset identities; none receive credit.
- Accepted waivers: **0**. Formal/reachability evidence accepted for this zero-count inventory: **0**.
- Reviewed Eligible Coverage: **not computable** because required zero-count review is incomplete.
- `make COHERENCE_JOBS=2 coherence_release_gate`: its unit suite passes **17/17**; the final release gate returns nonzero/OPEN because zero-count points remain unresolved. This is the intended fail-closed result.

A Block Top’s nonzero count is never transferred to a Subsystem Top. For example, the standalone `SharedLineEngine` regression exercises L2 grant-read and eight-beat stream scenarios, but that evidence does not change the Main Subsystem Raw Coverage count. The subsystem’s Grant Read / L2-hit path must be driven by the subsystem test and observed in that exact dataset before it can be marked Raw Covered there.

## Feature-focused closure review

The current tests provide separate Block evidence for several behaviors, but no new stimulus was added in this round and no main-top raw counts changed:

- **DirectoryController:** the standalone block test covers GetS/GetM/Upgrade, PutS/PutE/PutM, snoop response, recovery and invalid Upgrade fail-stop. Main Subsystem still has 68 missed line points, 13 missed branch points, and 32 missed FSM arcs mapped to this RTL. Those points are not all shown to be legal paths or protocol errors yet; they remain OPEN pending source-condition review and exact-top evidence.
- **SharedLineEngine:** the standalone block test includes grant-read backpressure, L2 hit streaming and malformed grant/read handling. Main Subsystem still has 31 missed line points and 16 missed branch points. Standalone Block results are supporting context only, not main-top closure.
- **MesiL1Controller:** Block tests cover snoop/refill and protocol-error cases. Main Subsystem retains 23 missed line points, 15 missed branch points, and 9 missed FSM arcs; exact points need condition-level classification and targeted evidence.
- **DirectoryMshrBank:** Block tests cover context allocation/routing, reset cancellation, same-line Put serialization, snoop independence and refill-start backpressure. The existing include `xfer_start_backpressure.svh` proves payload stability for that one offer channel in its Block Top. Main Subsystem still has 10 missed line points and 15 branch points for this RTL. Directory-write and grant-offer locks need their own observed/checked evidence in the relevant dataset before closure.

The source-mapped legacy matrix `reports/final/coverage_closure_matrix.csv` contains 976 Main-Subsystem LCOV line/branch/FSM entries. It is not the complete 74,831-point cross-dataset inventory. Its automated suggestions are not independent review decisions. No point has been converted to a waiver or marked unreachable based only on source keywords.

## Required regression evidence

All eight full regression targets below completed with return code 0 on source fingerprint `51545483279d0f053de85e8abbb2dd845f9df577cd1f3343c77aab4f6034f8bd`; machine records and log hashes are in `reports/closure/rtl_release_regression_status.json`:

| Target | Result |
| --- | --- |
| `coherence_coverage_audit` | PASS (rc=0) |
| `coherence_full_system_cross_closure` | PASS (rc=0) |
| `coherence_full_system_evidence_gate` | PASS (rc=0) |
| `coherence_full_system_replay_closure` | PASS (rc=0) |
| `coherence_full_system_stress` | PASS (rc=0) |
| `coherence_full_system_verify` | PASS (rc=0) |
| `coherence_hit_under_miss` | PASS (rc=0) |
| `coherence_verify` | PASS (rc=0) |

Additional recorded outcomes:

- Full-system regression: 70 passed, 1 skipped; checked Functional **53/53**, Cross **35/35**.
- Hit-under-Miss: 3/3.
- Cross closure targeted regression: 21 tests.
- Full-system stress: 280 seeded tests passed, 2,684.90 s, return code 0. The current evidence file is a concise completion record; full stdout for this rerun was not persisted, so per-test stdout provenance is weaker than for the captured `.log` gates.
- RTL coverage audit: 18/18 Product RTL Manifest sources reconciled; raw Top datasets remain separate.
- Evidence gate: PASS; source SHA/fingerprint and Monitor/Checker evidence consistent.
- Replay closure: PASS for the controlled checker-failure replay/minimization test.

The release-gate unit tests pass 17/17, but the release decision is **OPEN**. No full RTL Coverage sign-off is claimed.

## GitHub / PR status

At the start of this round, PR #1 was open and unmerged at remote head `15ae24c5ba655e7b46f047f283118f86cdc6b0a4`. The Actions run associated with that head completed successfully (PR run #85, conclusion `success`); this is evidence for that old head only. The local regressions recorded above ran on source commit `0f18c4363a5e7ab7612417645d3bb20b655a3df5` and the stated source fingerprint. The PR update and its Actions result must be checked against the exact newly published head; this report does not infer remote CI status from the old run.

## Next required work

1. Review each zero point against its actual RTL condition and feature contract; prioritize the legal/recovery paths in DirectoryController, SharedLineEngine, MesiL1Controller and DirectoryMshrBank.
2. Add minimal directed tests to the exact Elaborated Top where raw closure is required. Keep independent Checker assertions and record per-point test/evidence links.
3. For block-boundary protocol faults, add fault-injection evidence. For genuinely unreachable states, produce reproducible reachability evidence with interface-realistic assumptions and obtain independent review.
4. Review FSM State/Arc and Toggle misses by state, arc, signal bit and instance. Do not bulk-exclude them.
5. Re-run coverage and full regressions after new stimuli; refresh source and dataset hashes; only then issue a candidate Gate decision.

PPA, STA, physical SRAM macro mapping, chip-level physical implementation, and ASIC/tapeout sign-off are outside this closure round.
