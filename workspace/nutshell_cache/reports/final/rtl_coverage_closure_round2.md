# RTL Code Coverage Closure Round 2

**Decision: OPEN.** This round produced real Raw Coverage gains and closed the report/source mismatch, but the Release Gate still has 29,420 zero-count points with no point-level disposition. No waiver was added.

## Source and dataset identity

- Repository: `cwu766485-ctrl/open_verif_learning`; branch: `codex/v1.1-final-dv-evidence`.
- Fetched remote base: `789cc9c8891db0336f088647ad5e02de2a88a3ac`. The local tested source commit was `4c83f12d1a5302a5146c4816608ed330fd71458f`, two existing commits ahead of that remote base when this round began.
- Raw coverage source fingerprint: `764db6959c66632e8f882699d2bda2973e69268f910e968bb4a28c6fa9eeb5f5`. Product RTL fingerprint: `15798323c27cd473bf3d70a70b66b7cb39620c5abd2682a39e22512ac6794d6a`.
- Manifest: [`rtl_coverage_dataset_manifest.json`](../coherence/rtl_coverage_dataset_manifest.json), eight distinct elaborated tops, Verilator 5.053; all 18 product RTL manifest sources reconciled.
- Product RTL files were not changed. The Main Top test sequence already present at the tested source commit adds a legal dual-cold-miss transfer-offer stall scenario.

The prior and current full point inventories have identical 74,831 stable Point IDs and identical per-point RTL source hashes. Comparison found **46 zero-to-hit transitions and zero hit-to-zero transitions**. Per-dataset denominator and point identity are unchanged. The exact gained IDs, source locations, before/after counts, source hashes, and raw dataset hashes are in [`coverage_round2_raw_hit_delta.csv`](coverage_round2_raw_hit_delta.csv).

## Independent Raw Coverage by elaborated top

Counts are `hit/total`; datasets are not combined. A dash means the instrumentation emitted no points for that metric.

| Dataset / elaborated top | Line before → after | Branch before → after | Toggle before → after | FSM state before → after | FSM arc before → after |
|---|---:|---:|---:|---:|---:|
| Main subsystem / `CoherentCacheSubsystem_tb` | 864/992 → **868/992** | 473/556 → **475/556** | 21931/27474 → **21971/27474** | 30/54 → 30/54 | 13/48 → 13/48 |
| AXI subsystem / `CoherentCacheAxiSubsystem_tb` | 901/1068 → 901/1068 | 509/632 → 509/632 | 15623/32332 → 15623/32332 | 30/54 → 30/54 | 4/48 → 4/48 |
| Directory controller block | 178/182 → 178/182 | 37/42 → 37/42 | 260/612 → 260/612 | 10/10 → 10/10 | 3/9 → 3/9 |
| Directory MSHR bank block | 167/286 → 167/286 | 100/128 → 100/128 | 1249/2904 → 1249/2904 | 31/40 → 31/40 | 11/36 → 11/36 |
| Shared line engine block | 101/104 → 101/104 | 44/52 → 44/52 | 304/648 → 304/648 | — | — |
| MESI L1 controller block | 124/132 → 124/132 | 43/46 → 43/46 | 741/1804 → 741/1804 | 7/7 → 7/7 | 3/6 → 3/6 |
| Shared L2 directory array block | 75/79 → 75/79 | 65/74 → 65/74 | 197/1778 → 197/1778 | — | — |
| Bus blocks | 67/68 → 67/68 | 70/76 → 70/76 | 1100/2450 → 1100/2450 | — | — |

Main Top gained 4 line points, 2 branch points, and 40 toggle direction/bit points. Its FSM point counts are unchanged. No metric denominator changed.

## Point-level closure evidence

The additional legal stimulus is [`mshr_xfer_offer_lock.svh`](../../dv/blocks/coherent_cache_subsystem/tb/include/mshr_xfer_offer_lock.svh), included in the Main Subsystem instrumented test sequence. It starts two legal cold reads to different L2 sets, stalls the first memory request to hold the shared engine, then checks the second Directory transfer offer. The test checks the valid handshake, transaction/context/address/source payload stability during backpressure, exactly one matching acceptance, both correctly routed CPU responses, and the architectural state/data model. It does not force internal DUT state. The successful coverage audit log records processing this include and finishes with 18/18 RTL source reconciliation and the Main Top raw summary.

| New Raw point | RTL location | Before → after count |
|---|---|---:|
| `RCP-LINE-0A86ED285F9DE5E69C45` | `rtl/directory/DirectoryMshrBank.sv:362` | 0 → 6 |
| `RCP-LINE-4BEF62343B00B31A0F65` | `rtl/directory/DirectoryMshrBank.sv:363` | 0 → 6 |
| `RCP-LINE-ECB553D940B9D561C11F` | `rtl/directory/DirectoryMshrBank.sv:364` | 0 → 6 |
| `RCP-LINE-7F56A107C7E4D505BE09` | `rtl/directory/DirectoryMshrBank.sv:365` | 0 → 6 |
| `RCP-BRANCH-3F28E313D7B657696F34` | `rtl/directory/DirectoryMshrBank.sv:220` | 0 → 84 |
| `RCP-BRANCH-C9D511AA4362A68A21D4` | `rtl/directory/DirectoryController.sv:445` | 0 → 12 |

The 40 additional toggle points are listed individually in the delta CSV. They correspond to Main Top address/context and transfer-offer-lock bits toggling in the same legal dual-miss scenario. These raw hits attest execution; the independent test checks above provide behavioral checking.

## Regression and gate results

All eight required regressions passed individually on the same source fingerprint. The initial aggregate runner was interrupted after the long stress target; the remaining audit/evidence/replay targets were then invoked separately and their log hashes recorded. The interruption is not counted as a passing aggregate invocation.

| Gate | Result | Evidence log |
|---|---|---|
| `coherence_verify` | PASS, exit 0 | [`coherence_verify.log`](../closure/release_runs/coherence_verify.log) |
| `coherence_full_system_verify` | PASS, exit 0; 72 passed, 1 skipped; checked coverage 53/53 + 37/37 | [`coherence_full_system_verify.log`](../closure/release_runs/coherence_full_system_verify.log) |
| `coherence_hit_under_miss` | PASS, exit 0; 3 passed | [`coherence_hit_under_miss.log`](../closure/release_runs/coherence_hit_under_miss.log) |
| `coherence_full_system_cross_closure` | PASS, exit 0; 21/21 | [`coherence_full_system_cross_closure.log`](../closure/release_runs/coherence_full_system_cross_closure.log) |
| `coherence_full_system_stress` | PASS, exit 0; 280 passed | [`coherence_full_system_stress.log`](../closure/release_runs/coherence_full_system_stress.log) |
| `coherence_coverage_audit` | PASS, exit 0; 8 independent datasets | [`coherence_coverage_audit.log`](../closure/release_runs/coherence_coverage_audit.log) |
| `coherence_full_system_evidence_gate` | PASS, exit 0; source SHA `4c83f12...`, 71 runs, 53 functional bins, 37 crosses | [`coherence_full_system_evidence_gate.log`](../closure/release_runs/coherence_full_system_evidence_gate.log) |
| `coherence_full_system_replay_closure` | PASS, exit 0; controlled replay 1/1 | [`coherence_full_system_replay_closure.log`](../closure/release_runs/coherence_full_system_replay_closure.log) |

`coherence_release_gate` was also executed and returned **exit 2 / OPEN**. The gate inventories 74,831 points: 45,411 Raw Hits, all 45,411 attested; 29,420 zero-count points remain OPEN with no accepted point-level review. There are 0 approved waivers. This is the correct outcome until the remaining Required points are evidenced or reviewed.

## Corrected source classification and remaining gaps

The previous Main Top report had 128 unhit lines and 83 unhit branch points. Current Main Top has **124 missed lines and 81 missed branches**; exact gained points above were reclassified as actually exercised, not waived. The all-top coverage closure matrix is now 863 zero-count dataset-scoped records, down from 869. The reviewed line/branch matrix has six fewer Main Top zero points; it does not change another elaborated top’s counts.

The legal transfer-offer path is now observed in the Main Top. Remaining Main Top Raw misses are 124 lines, 81 branches, 5,503 toggle points, 24 FSM states, and 35 FSM arcs. These are not all proven legal gaps: each still requires point-level reachability/error-path review. Other-top Raw misses remain as shown above. No Formal proof or waiver was added in this round.

The baseline and current source metadata for all points match; the current raw and line-info hashes are recorded per point/dataset in the generated manifest and delta CSV. No lost hit or denominator change was observed. Product RTL remains frozen.

## Sign-off and remote state

- RTL code coverage Release Gate: **OPEN** (not sign-off).
- Functional-system evidence gate and required regression targets: **PASS** on local source `4c83f12d1a5302a5146c4816608ed330fd71458f`.
- GitHub CI/PR state must be checked on the final pushed evidence commit; local regression PASS is not a claim of remote CI PASS.
- No PR merge, release tag, waiver approval, or product RTL modification was made in this round.
