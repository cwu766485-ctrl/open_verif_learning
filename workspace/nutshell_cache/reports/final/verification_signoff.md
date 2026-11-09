# Verification Sign-off Status

**Decision: OPEN — not a release sign-off.** The current full regression is green, but Raw RTL zero-count closure remains incomplete.

## Tested snapshot

- Tested source SHA: `0f18c4363a5e7ab7612417645d3bb20b655a3df5`
- Verification source fingerprint: `51545483279d0f053de85e8abbb2dd845f9df577cd1f3343c77aab4f6034f8bd`
- RTL manifest: 18 Product RTL sources
- Raw coverage: 8 independently elaborated Top datasets; no cross-Top aggregation

## Functional and Cross Coverage

- Full-system checked Functional: **53/53**.
- Full-system checked Cross: **35/35**.
- These are checked DV bins and do not substitute for Raw RTL Code Coverage.

## Raw RTL Coverage / Release Gate

- Raw points: **74,831**.
- Raw-hit points: **43,074**, machine-attested **43,074/43,074**.
- Zero-count points: **31,757**; current per-point decisions accepted: **0**; OPEN/unreviewed: **31,757**.
- Current approved waivers: **0**; stale ledger rows: **19**.
- Reviewed Eligible Coverage: **not computable**.
- RTL release gate: **OPEN**. Its 17 unit tests pass, but the final gate correctly exits nonzero while required zero-count points remain unreviewed.

Main Subsystem Raw Coverage: Line **850/992**, Branch **468/556**, Toggle **19,996/27,474**, FSM State **30/54**, FSM Arc **7/48**. Per-Top results and the source-mapped review are in `reports/final/rtl_coverage_closure_round.md` and `reports/final/rtl_coverage_signoff.md`.

## Regression

All eight required regression targets completed PASS (rc=0) on the tested source fingerprint; exact commands, log paths, completion times and SHA-256 digests are recorded in `reports/closure/rtl_release_regression_status.json`:

- `coherence_coverage_audit`: **PASS** (rc=0)
- `coherence_full_system_cross_closure`: **PASS** (rc=0)
- `coherence_full_system_evidence_gate`: **PASS** (rc=0)
- `coherence_full_system_replay_closure`: **PASS** (rc=0)
- `coherence_full_system_stress`: **PASS** (rc=0)
- `coherence_full_system_verify`: **PASS** (rc=0)
- `coherence_hit_under_miss`: **PASS** (rc=0)
- `coherence_verify`: **PASS** (rc=0)

Full-system: 70 passed, 1 skipped; Hit-under-Miss: 3/3; cross closure: 21 tests; stress: 280 seeded environments passed. The stress rerun has a concise exit/pass record but not full stdout preserved; see the run manifest for this limitation.

## Remote CI

The known PR head at the start of this round was `15ae24c5ba655e7b46f047f283118f86cdc6b0a4`; its PR-triggered GitHub Actions run #85 completed successfully. That result is not CI for tested local source SHA `0f18c4363a5e7ab7612417645d3bb20b655a3df5`. Remote status must be refreshed after publishing this candidate.

PPA, STA, physical SRAM macro implementation, and chip-level physical implementation are excluded. This document is not ASIC/tapeout sign-off.
