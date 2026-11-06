# Verification Sign-off Status

**Status: OPEN — local regression passed, full verification closure not achieved.**

## Candidate snapshot

- Tested RTL/DV source SHA: `14542f52bef5a42560cc615a5db104e3122dbd33` on local branch `dv-closure-phase2`.
- Remote base: `cache_coherence` at `9b281f3bd1d6b5dbdf9bb257313dd61a21d87252`.
- GitHub Actions run [41962170929](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/41962170929) passed on the remote base SHA. It is **not** a run for the local candidate.
- Candidate remote CI: pending publication and Actions execution.
- Product RTL behavior/interfaces: unchanged in this DV closure work.

## Regression and coverage evidence

- Six requested gates passed locally: `coherence_verify`, `coherence_full_system_verify`, `coherence_hit_under_miss`, `coherence_full_system_cross_closure`, `coherence_full_system_stress`, and `coherence_coverage_audit`.
- Full-system evidence gate: source SHA matches; 57 testcase records, 53/53 required functional bins, 29/29 required crosses.
- Separate Python coherence closure: 49/49 functional bins, 19/19 crosses.
- Four-agent stress: 260/260 environments passed; no failing seed was produced.
- Checker fault sensitivity: 9/9 injected checker faults detected. Configured RTL mutation campaign: 4/4 mutations detected.
- Independent primary RTL raw coverage: 843/998 lines, 461/556 branches, 19980/27474 toggles, 30/54 FSM states, 7/48 FSM arcs.
- RTL closure matrix: 1,026 dataset-scoped zero-count records remain OPEN; 0 approved waivers; reviewed/eligible coverage not computed.
- Integrated cross-agent scenario matrix: CR01 and CR07 have checked overlap evidence; CR02–CR06 and CR08–CR10 remain OPEN.
- Trace minimization is a tested primitive, not yet automatically invoked by a simulator failure callback. No failing seed was available to minimize.

Detailed phase results, per-command outcomes, scenario disposition, and scope limits are recorded in [`docs/dv/closure_phase2_execution_2026-11-06.md`](../../docs/dv/closure_phase2_execution_2026-11-06.md). Raw point status is in [`coverage_closure_matrix.csv`](coverage_closure_matrix.csv) and [`rtl_coverage_signoff.md`](rtl_coverage_signoff.md).

## Sign-off boundary

The regression PASS does not close raw RTL coverage, unsupported cross-agent scenarios, or all lifecycle interleavings. No waiver was inferred, no Required Bin ID or denominator was changed, and Python functional coverage is not combined with Verilator source coverage. Integrated four-CPU-miss traffic, RREADY/BREADY receiver stalls, APB wait states, arbitrary CPU response reordering, and MMIO error responses are outside current interface support.

This status excludes PPA, STA, real SRAM macro implementation, and chip-level physical implementation. Do not treat this candidate as a release sign-off until remaining OPEN items are dispositioned and candidate CI passes on the final SHA.
