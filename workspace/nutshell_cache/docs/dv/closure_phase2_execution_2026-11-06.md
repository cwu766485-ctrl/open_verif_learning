# NutShell Cache DV Closure Phase 2 — Execution Record

Date: 2026-11-06 (Asia/Singapore)
Repository: `cwu766485-ctrl/open_verif_learning`
Project: `workspace/nutshell_cache/`
Working branch: `dv-closure-phase2` (based on `cache_coherence`)
Remote baseline: `9b281f3bd1d6b5dbdf9bb257313dd61a21d87252`
Tested RTL/DV source SHA: `14542f52bef5a42560cc615a5db104e3122dbd33`

## Decision

**Verification closure status: OPEN.** All six requested local regression gates passed on the tested source SHA, and the full-system required functional/cross evidence is internally consistent. This does not close the raw RTL coverage audit or all ten planned Cross-Agent scenario families. No 2-entry L1 MSHR was implemented. No product RTL files or interfaces were changed in this phase; the source delta is verification infrastructure, test/checker support, and evidence generation.

## Phase 1 — Baseline audit and evidence consistency

The latest remote `cache_coherence` head was `9b281f3`. Its GitHub Actions run [41962170929](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/41962170929) completed successfully on that SHA. The local candidate contains six commits beyond that remote baseline and therefore its results must be treated separately from the remote run.

An evidence collision was found: full-system stress output could overwrite the canonical sign-off JSON/trace. Commit `14542f5` gives stress its own raw JSON and trace destinations and makes the stress summary consume its stress-scoped artifact. The consistency gate passed:

```text
SHA=14542f52bef5a42560cc615a5db104e3122dbd33 runs=57 bins=53 crosses=29
```

The full-system JSON artifacts and closure Markdown identify the same tested source SHA. The integrated sign-off slice remains 53/53 required bins and 29/29 required crosses. The separate Python coherence closure is 49/49 functional bins and 19/19 crosses. These scopes and their Bin IDs were retained; Python functional coverage is not merged into RTL source coverage.

**Gate 1: local evidence consistency PASS. Candidate GitHub CI: pending publication of this branch; the remote baseline run is not evidence for the candidate SHA.**

## Phase 2 — RTL coverage-gap audit

Coverage was regenerated for the current RTL using independent elaborated tops. Denominators are not combined across tops.

| Dataset | Line | Branch | Toggle | FSM state | FSM arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full coherent subsystem | 843/998 | 461/556 | 19980/27474 | 30/54 | 7/48 |
| AXI subsystem E2E, five fixed seeds | 901/1074 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| DirectoryController block | 117/188 | 30/42 | 236/612 | 9/10 | 2/9 |
| DirectoryMshrBank block | 167/292 | 100/128 | 1063/2904 | 31/40 | 11/36 |
| SharedLineEngine block | 101/104 | 44/52 | 304/648 | N/A | N/A |
| MesiL1Controller block | 104/132 | 40/46 | 629/1804 | 7/7 | 2/6 |
| SharedL2DirectoryArray block | 75/79 | 65/74 | 197/1778 | N/A | N/A |
| Bus blocks | 67/68 | 70/76 | 1100/2450 | N/A | N/A |

The primary subsystem run has 155 unhit executable lines, 95 branches, 24 FSM states, and 41 FSM arcs. The source-linked closure matrix contains 1,026 dataset-scoped zero-count records across the audited datasets. These are coverage-point records, not 1,026 distinct RTL defects or a required number of new tests. All 1,026 remain **OPEN**; there are zero approved waivers and reviewed/eligible coverage has not been computed.

The detailed source/line/point inventory is in [`reports/final/coverage_closure_matrix.csv`](../../reports/final/coverage_closure_matrix.csv), with scope and raw denominator notes in [`reports/final/rtl_coverage_signoff.md`](../../reports/final/rtl_coverage_signoff.md). A hit in another elaborated top is recorded as provenance, not credited to this dataset. Raw line, branch, toggle, and FSM metrics use different instrumentation and are not added together.

**Gate 2: audit generated; closure not achieved. Legal and defensive zero-count points remain OPEN pending point-by-point test, fault-injection, formal, or reviewed disposition.**

## Phase 3 — Cross-Agent scenario and random evidence

The four-agent campaign completed 260 seeded environments: 100 CPU random, 100 mixed CPU/MMIO/APB/AXI, 20 resource-aware Snoop/refill, 20 randomized reset, and 20 AXI read-error recovery. All passed, with no failing seed and no failure replay to minimize. The mixed campaign recorded real Snoop accepts (100 total) and the checked owner-transfer/refill/APB cross; it no longer reports zero Snoop activity. The campaign details and per-seed reproducibility commands are in [`reports/full_system/stress_campaign_summary.md`](../../reports/full_system/stress_campaign_summary.md) and [`reports/full_system/stress_seed_summary.csv`](../../reports/full_system/stress_seed_summary.csv).

Scenario status is intentionally stricter than “the component features were each tested somewhere.” A scenario is called verified only where its required overlap was observed and independently checked in that scenario.

| ID | Required overlap | Status | Evidence / remaining gap |
| --- | --- | --- | --- |
| CR01 | M Owner Transfer × AXI Refill × APB | **Verified** | Directed checked scenario and 100 mixed/random CR01 observations; data, owner transfer, refill, APB event, and overlap are checked. |
| CR02 | Shared Upgrade × MMIO Pending | **Open** | Shared upgrade and MMIO/cache overlap exist separately; no same-window independent checker for this pair. |
| CR03 | Dirty L1 Victim × AXI Writeback Stall | **Open** | Dirty victim and source-side writeback stalls are tested, but their required overlap is not established by one scenario checker. |
| CR04 | Dirty L2 Victim × Snoop × APB | **Open** | Victim, Snoop, and APB behaviors have component/directed evidence; the three-way overlap is not checked. |
| CR05 | Same-Set Directory Conflict × AXI Stall | **Open** | Same-set conflict and AXI stall coverage exist separately; context and overlap checker are missing. |
| CR06 | Two Cold Misses × Out-of-Order R × APB | **Open** | Two-ID/reordered refill and APB overlap are covered in separate tests; the triple overlap is not checked. |
| CR07 | Hit-under-Miss × Remote Snoop | **Verified** | AXI-top directed test observes a different-line owner Snoop completing while a refill is pending; returned data and coherence state are checked. |
| CR08 | Reset × Directory/Snoop/Grant Pending | **Open** | Reset crosses several supported stalls and active transactions; the requested pending-protocol phases are not all constructed and checked. |
| CR09 | AXI SLVERR/BRESP × Fail-Stop × Reset | **Open** | Read/write errors, fail-stop, reset, and recovery have evidence, but not a complete error-kind × reset lifecycle cross. |
| CR10 | Ownership Ping-Pong × MMIO/APB | **Open** | Ownership and mixed-agent traffic are exercised; no checker proves the requested ping-pong/MMIO/APB interleaving. |

The current coverage-guided scheduler adds checked CR01 preludes and retains MESI transition / dual cold-miss targets. It does not yet translate every Directory, MSHR, L2, AXI, MMIO, APB, reset, and error gap into a scenario prelude plus timing perturbation. Therefore the 260-seed pass count is stress evidence, not proof that every cross-agent family is closed.

**Gate 3: partially met. CR01 and CR07 have checked integrated evidence; CR02–CR06 and CR08–CR10 remain OPEN.**

## Phase 4 — Monitor, lifecycle checker, and sensitivity

The MSHR lifecycle checker correlates observed allocation/retirement with AXI transaction ID/address, ordered R beats, L2 fill writes, grant, and CPU response in the targeted scenarios. Existing full-system monitor/reference checking covers selected data, MESI/Directory commits, same-address acceptance order, AXI beat/ID association, and APB event deltas. Checker fault-injection sensitivity caught 9/9 injected checker faults; RTL mutation campaign caught 4/4 configured mutations. The 4-context Directory MSHR block regression and its bounded formal checks pass.

This evidence is not a proof that every context/victim/snoop lifecycle cross is covered. In particular, same-set contention, all victim MESI states, reset epoch cancellation, and each grant/snoop backpressure combination are not exhaustively paired at the integrated top.

**Gate 4: partial. Targeted lifecycle and sensitivity checks pass; complete all-context/all-resource cross checking remains OPEN.**

## Phase 5 — Trace replay and minimization

Seed, generated operation/configuration, testcase, and replay command are stored per stress seed. Existing JSONL replay support remains available. An order-preserving delta-debugging primitive preserves marked legal preludes and has unit coverage, but it requires a caller-supplied replay predicate and is not automatically connected to simulator failure callbacks. All 260 environments passed, so this campaign produced no failing DUT trace to minimize. Replay is seed/configuration reproducibility, not a promise of cycle-identical scheduling across tool or source versions.

**Gate 5: partial. Reproduction metadata and replay support exist; automatic failure capture/minimization is not closed.**

## Phase 6 — Regression results

Environment was loaded with `source scripts/env.sh`. All required commands were run on source SHA `14542f52bef5a42560cc615a5db104e3122dbd33`:

| Command | Result |
| --- | --- |
| `make COHERENCE_JOBS=2 coherence_verify` | PASS; component, bounded formal, coherence/Python, AXI, stress, mutation, and benchmark targets passed. Python coherence: 38 passed, 1 deselected; 49/49 bins. Fault injection: 9/9; RTL mutation: 4/4. |
| `make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS; integrated run 57 passed, 1 optional replay skipped because no saved failure trace was supplied. This target also invokes the coherence verification dependency. |
| `make COHERENCE_JOBS=2 coherence_hit_under_miss` | PASS; 3 directed tests, including pending miss with remote Snoop, reset cancellation, and AXI-top ID wrap/stall. |
| `make COHERENCE_JOBS=2 coherence_full_system_cross_closure` | PASS; 1 directed checked owner-transfer/refill/APB cross testcase. |
| `make COHERENCE_JOBS=2 coherence_full_system_stress` | PASS; 260/260 seeded environments, 0 failing seeds. |
| `make COHERENCE_JOBS=2 coherence_coverage_audit` | PASS; primary, AXI, and independent Block raw datasets generated and audited. |

Additional checks passed: `coherence_full_system_evidence_gate` (57 testcase records, 53 required bins, 29 required crosses), `python3 -m dv.coverage.coverage_raw_runs`, `coverage_closure_matrix`, `rtl_coverage_closure`, and `python_closure` (49/49). Run logs are in `/tmp/nutshell_phase2_*_14542f5.log` on the execution host; the committed JSON/CSV/Markdown reports are the durable summary artifacts.

The remote Actions run currently confirmed is the base commit run on `9b281f3`, not this candidate. Candidate CI must be checked after the branch is published. Local PASS must not be described as remote CI PASS.

## Required evidence and remaining risk

- Latest full-system artifacts: [`full_system_coverage_closure.md`](../../reports/full_system/full_system_coverage_closure.md), [`full_system_coverage_closure.json`](../../reports/full_system/full_system_coverage_closure.json), `functional_coverage.json`, and `cross_coverage.json`; all carry source SHA `14542f5…`.
- Scenario/testpoint map: [`full_system_scenario_testplan.md`](full_system_scenario_testplan.md). Required Bin IDs remain unchanged.
- RTL raw point inventory and sign-off status: [`coverage_closure_matrix.csv`](../../reports/final/coverage_closure_matrix.csv) and [`rtl_coverage_signoff.md`](../../reports/final/rtl_coverage_signoff.md).
- No approved waiver was added. No gap was promoted based on source keywords or another top's hit.
- Unsupported integrated behaviors remain unsupported: four simultaneous CPU misses, integrated RREADY/BREADY backpressure, APB wait-state insertion, arbitrary CPU response reordering, and MMIO error response.
- No full-system unbounded formal proof, PPA, STA, real SRAM macro, or physical implementation is claimed.

**Final candidate decision: OPEN.** Local regressions pass and the evidence pipeline is more consistent, but unresolved raw RTL points and CR02–CR06/CR08–CR10 prevent a full DV sign-off. Do not freeze a release from this report alone.
