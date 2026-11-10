# Risk-Based RTL Closure

**Decision: OPEN.** Required zero points remain; no waiver or independent approval is inferred.

Tested source SHA: `3526950e59ff042973ccb822414d6a7361c682da`
Source fingerprint: `5e6fbd81eee6091df1a5d9028df0af5b5a516c6612f2f3e920398746c92ca846`

| Dataset | Metric | Before | After | Delta hits |
| --- | --- | ---: | ---: | ---: |
| main_subsystem | line | 850/992 | 850/992 | +0 |
| main_subsystem | branch | 468/556 | 468/556 | +0 |
| main_subsystem | toggle | 19996/27474 | 21887/27474 | +1891 |
| main_subsystem | fsm_state | 30/54 | 30/54 | +0 |
| main_subsystem | fsm_arc | 7/48 | 13/48 | +6 |
| axi_subsystem | line | 901/1068 | 901/1068 | +0 |
| axi_subsystem | branch | 509/632 | 509/632 | +0 |
| axi_subsystem | toggle | 15623/32332 | 15623/32332 | +0 |
| axi_subsystem | fsm_state | 30/54 | 30/54 | +0 |
| axi_subsystem | fsm_arc | 4/48 | 4/48 | +0 |
| directory_controller | line | 122/182 | 149/182 | +27 |
| directory_controller | branch | 30/42 | 33/42 | +3 |
| directory_controller | toggle | 250/612 | 255/612 | +5 |
| directory_controller | fsm_state | 10/10 | 10/10 | +0 |
| directory_controller | fsm_arc | 3/9 | 3/9 | +0 |
| directory_mshr_bank | line | 167/286 | 167/286 | +0 |
| directory_mshr_bank | branch | 100/128 | 100/128 | +0 |
| directory_mshr_bank | toggle | 1063/2904 | 1189/2904 | +126 |
| directory_mshr_bank | fsm_state | 31/40 | 31/40 | +0 |
| directory_mshr_bank | fsm_arc | 11/36 | 11/36 | +0 |
| shared_line_engine | line | 101/104 | 101/104 | +0 |
| shared_line_engine | branch | 44/52 | 44/52 | +0 |
| shared_line_engine | toggle | 304/648 | 304/648 | +0 |
| shared_line_engine | fsm_state | 0/0 | 0/0 | +0 |
| shared_line_engine | fsm_arc | 0/0 | 0/0 | +0 |
| mesi_l1_controller | line | 107/132 | 107/132 | +0 |
| mesi_l1_controller | branch | 41/46 | 41/46 | +0 |
| mesi_l1_controller | toggle | 688/1804 | 688/1804 | +0 |
| mesi_l1_controller | fsm_state | 7/7 | 7/7 | +0 |
| mesi_l1_controller | fsm_arc | 3/6 | 3/6 | +0 |
| shared_l2_directory_array | line | 75/79 | 75/79 | +0 |
| shared_l2_directory_array | branch | 65/74 | 65/74 | +0 |
| shared_l2_directory_array | toggle | 197/1778 | 197/1778 | +0 |
| shared_l2_directory_array | fsm_state | 0/0 | 0/0 | +0 |
| shared_l2_directory_array | fsm_arc | 0/0 | 0/0 | +0 |
| bus_blocks | line | 67/68 | 67/68 | +0 |
| bus_blocks | branch | 70/76 | 70/76 | +0 |
| bus_blocks | toggle | 1100/2450 | 1100/2450 | +0 |
| bus_blocks | fsm_state | 0/0 | 0/0 | +0 |
| bus_blocks | fsm_arc | 0/0 | 0/0 | +0 |

All zero points retain individual IDs in `risk_closure/zero_point_review.csv.gz`.
Toggle axes retain native signal/array/bit/direction and instance. Unclassified bits remain OPEN; none are called constant or noncritical without proof.
Reviewed Eligible Coverage is not available until independent review completes. The raw denominator and coverage plan are unchanged.

## Review and residual risks


Required non-toggle zero points: 976 before, 940 after (36 real hits). Toggle zero points: 30,781 before, 28,759 after (2,022 real hits). These cross-dataset point counts measure review workload only, never a combined coverage percentage.

| Toggle review queue | Remaining points |
| --- | ---: |
| ADDRESS_RANGE_REVIEW: determine routing/alignment/tag constraints per bit | 20738 |
| BYTE_MASK_REVIEW: exercise individual byte lanes and combinations | 176 |
| DATA_PATTERN_REVIEW: ones/zeros/walking patterns with checked readback | 3717 |
| ID_CONTEXT_REVIEW: allocation, wrap and resource contention | 739 |
| STATE_ENCODING_REVIEW: reset, protocol error and reachability evidence | 100 |
| UNREVIEWED_SIGNAL_BIT: constant/range/protocol/data causes require individual evidence | 3289 |

No category is an approved constant, unreachable conclusion or waiver. Classification preserves each native point ID and elaborated dataset.

Important OPEN risks: same-top grant-read retry under L2 read-port contention; Directory contexts 2/3 protocol scenarios; remaining legal owner/sharer/Put and recovery branch conditions; per-bit ID/address/state and data coverage; reset arcs not observed in each elaborated instance; external faults not covered by the nine added Directory cases. The encoding proof does not discharge these risks.

Formal evidence: `risk_closure/formal_evidence.json` and `risk_closure/directory_encoding_proof.log.gz`. Initial-reset-only single-clock encoding invariant proved by k-induction without interface assumptions. Independent reviewer/approver: none; accepted waivers and exclusions: zero.

PR: https://github.com/cwu766485-ctrl/open_verif_learning/pull/1. Remote baseline SHA 2c40bfe has successful CI runs 42642245560 and 42642231316; those runs do not validate this new source SHA. New-source CI remains pending until the branch is published.

## New stimulus and checker trace

| Required behavior | Test source | Independent expected result | Dataset |
| --- | --- | --- | --- |
| Directory invalid metadata/state/opcode and Put/Upgrade port faults | `dv/blocks/directory_controller/tb/include/test_sequence.svh` | Exact error code, no successful side effects, sustained fail-stop, reset followed by checked legal refill | directory_controller only |
| Full beat sequence ending with missing Last | `dv/blocks/mesi_l1_controller/tb/include/reset_and_protocol_error_cases.svh` | Legal beats 0..6 precede malformed beat7; error path checked for refill and snoop data | mesi_l1_controller only |
| High tag bits, masked peer writes and data patterns | `dv/blocks/coherent_cache_subsystem/tb/include/risk_closure_patterns.svh` | Software byte-merge expected value and peer readback through DUT | main_subsystem only |
| Reset from observed Directory states | `dv/blocks/coherent_cache_subsystem/tb/include/risk_reset_states.svh` | No stale response/request/fatal after reset and checked recovery read; state observation without force | main_subsystem only |
| MSHR write and grant arbitration under later higher-priority contender | `dv/blocks/directory_mshr_bank/tb/include/offer_competition.svh` | Full held payload stable and both contexts retire once | directory_mshr_bank only |

Raw coverage archives and hashes bind these runs to each elaborated Top. They establish execution; the independent expected-result comparisons establish the checked behavior within the listed scope. Unhit legal paths remain OPEN.

## Formal assumption analysis (not independent approval)

Existing `coherence_directory_harness.sv:99` and `coherence_directory_mshr_bank_harness.sv:140` constrain accepted requests to supported opcodes, valid directory encodings and coherent owner/sharer metadata. Consequently their PASS results cannot prove the malformed opcode/state/metadata handlers unreachable. Those cases are exercised separately by the added external-port faults. MSHR additionally assumes initial reset. L1 harness assumptions at lines167–181 require an upstream stalled data payload to remain valid/stable; they constrain handshake behavior and cannot discharge faults that violate this producer contract. Existing bounded safety/progress runs are not unbounded reachability proofs.

The new `coherence_directory_unconstrained.sby` uses `mode prove`, depth24, `smtbmc z3`; its harness has no `assume` statements. A reset counter initializes to zero and asserts reset for the first two clock edges; later reset and all protocol inputs are unconstrained. Only the valid encoding of `state_q` and `snoop_resume_q` is asserted. The invariant succeeded by k-induction; it neither proves coverage of every valid state/arc nor protocol liveness. No Coverage Point is excluded on this basis without an independently reviewed point mapping.

## Final regression and release decision

All eight required regression targets passed with COHERENCE_JOBS=2 against source `3526950e59ff042973ccb822414d6a7361c682da`. Functional 53/53, Cross 35/35; Full-System Stress 280/280. Full-System verify: 70 passed, 1 skipped. Gate unit tests: 19 passed.

| Command | Result | Exit |
| --- | --- | ---: |
| coherence_coverage_audit | PASS | 0 |
| coherence_full_system_cross_closure | PASS | 0 |
| coherence_full_system_evidence_gate | PASS | 0 |
| coherence_full_system_replay_closure | PASS | 0 |
| coherence_full_system_stress | PASS | 0 |
| coherence_full_system_verify | PASS | 0 |
| coherence_hit_under_miss | PASS | 0 |
| coherence_verify | PASS | 0 |
| coherence_release_gate | OPEN | 2 (make); gate executable 1 |

Raw points 74,831; hits 43,074 → **45,132**; machine-attested **45,132/45,132**, unattested hits 0. New hits: Line27, Branch3, FSM State0, FSM Arc6, Toggle2,022. Zero points 31,757 → **29,699** (Line494, Branch276, FSM State57, FSM Arc113, Toggle28,759). Stale ledger history:19; approved waivers:0. Manifest errors:0. No scope or denominator change. Reviewed Eligible Coverage: **not calculated**, independent review incomplete.

**Release Decision: OPEN; no Full Code Coverage PASS.** Remaining required obligations have no reviewed disposition. Raw hit counts across datasets describe workload only, never a pooled coverage percentage. Logs/status/hash: `reports/closure/rtl_release_regression_status.json`, `release_runs/*.log.gz`, `rtl_release_gate_status.json`; complete per-point matrix: `rtl_release_point_matrix.csv.gz`. New raw files and dataset hashes: `risk_closure/raw/`, `raw_archive.json`, `dataset_manifest.json`. Baseline raw archives remain unchanged.

Source commit: `3526950e59ff042973ccb822414d6a7361c682da`. Report commit is the Git commit containing this file; resolve with `git log -1 --format=%H -- reports/final/risk_based_closure_report.md`. Source snapshot validation permits report-only commits and verifies the real tested source commit.

PR #1 remains at baseline remote HEAD: publication blocked because `git push origin dv-closure-phase2` returned `could not read Username`. No new-source GitHub Actions run exists; baseline Actions are historical only. No merge or release tag performed.
