# Verification Sign-off Status

**Decision: OPEN — functional regressions pass, RTL code-coverage closure remains incomplete.**

## Tested source and tools

- Source SHA: `8e268bda19f14ff6d587ca38d2813f69b868da97`; verification fingerprint: `552e2c15801193839282bda632b0ce250d49af255d15cc7e5f462be36300f006`.
- Product RTL manifest: 18 files; raw coverage is split into eight independent elaborated-top datasets.
- Verilator: `Verilator 5.053 devel rev v5.052-521-g6388139f7 (mod)`; Python: `3.12.3`.

## Regression results

| Target | Result | Evidence |
| --- | --- | --- |
| `coherence_verify` | PASS (exit 0) | [`coherence_verify.log.gz`](../closure/release_runs/coherence_verify.log.gz) |
| `coherence_full_system_verify` | PASS (exit 0) | [`coherence_full_system_verify.log.gz`](../closure/release_runs/coherence_full_system_verify.log.gz) |
| `coherence_hit_under_miss` | PASS (exit 0) | [`coherence_hit_under_miss.log.gz`](../closure/release_runs/coherence_hit_under_miss.log.gz) |
| `coherence_full_system_cross_closure` | PASS (exit 0) | [`coherence_full_system_cross_closure.log.gz`](../closure/release_runs/coherence_full_system_cross_closure.log.gz) |
| `coherence_full_system_stress` | PASS (exit 0) | [`coherence_full_system_stress.log.gz`](../closure/release_runs/coherence_full_system_stress.log.gz) |
| `coherence_coverage_audit` | PASS (exit 0) | [`coherence_coverage_audit.log.gz`](../closure/release_runs/coherence_coverage_audit.log.gz) |
| `coherence_full_system_evidence_gate` | PASS (exit 0) | [`coherence_full_system_evidence_gate.log.gz`](../closure/release_runs/coherence_full_system_evidence_gate.log.gz) |
| `coherence_full_system_replay_closure` | PASS (exit 0) | [`coherence_full_system_replay_closure.log.gz`](../closure/release_runs/coherence_full_system_replay_closure.log.gz) |


- `coherence_full_system_verify`: 70 passed, 1 skipped; checked Functional 53/53, Cross 35/35.
- `coherence_full_system_stress`: 280 seeded environments passed.
- Python coherence checked coverage: 49/49 Functional, 19/19 Cross.
- `coherence_release_gate`: 15/15 gate unit tests passed; the release gate itself correctly returns OPEN/non-zero because raw point-by-point review is incomplete.

## Raw RTL coverage

Main Subsystem (`CoherentCacheSubsystem_tb`): Line 850/992, Branch 468/556, Toggle 19,996/27,474, FSM State 30/54, FSM Arc 7/48. These are raw counts, not Reviewed Eligible Coverage. Across all datasets there are 74,831 stable points; 43,074 raw-hit and 31,757 zero-count points lack accepted current-source/current-dataset review. The 19 historic decision-ledger entries are stale; no waiver or unreachable disposition is accepted. Reviewed Eligible Coverage is not computable.

The older raw line denominator was 998. The current 992 denominator follows the separately committed invalid `DIR_I + Upgrade` fail-stop RTL correction, which removed six erroneous recovery statements. Raw Main Subsystem hit-line count stayed at 850; the difference is explicitly not presented as closure.

## CI and release scope

The tested local SHA `8e268bda19f14ff6d587ca38d2813f69b868da97` differs from the historical PR head SHA `d194d3f4552aa6d8f6e6c251f1995fc0f5bbff42`. Remote CI for the new evidence commit must be checked after push; this report makes no claim that the historical CI applies to this candidate.

PPA, STA, physical SRAM macro implementation and chip-level physical sign-off are excluded. **Overall sign-off remains OPEN.**
