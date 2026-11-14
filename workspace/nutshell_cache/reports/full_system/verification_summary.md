# Full-System Verification Summary

Date: 2026-11-06 (Asia/Singapore)
Tested RTL/DV source SHA: `14542f52bef5a42560cc615a5db104e3122dbd33`
Working branch: `dv-closure-phase2`; base `cache_coherence` SHA: `9b281f3bd1d6b5dbdf9bb257313dd61a21d87252`

## Results

All six required local gates passed on the tested source SHA:

| Command | Result |
| --- | --- |
| `make COHERENCE_JOBS=2 coherence_verify` | PASS; component/Formal, Python coherence, AXI, stress, mutation, and benchmark dependencies completed. Python coherence 38 passed / 1 deselected; 49/49 bins; checker fault injection 9/9; RTL mutation 4/4. |
| `make COHERENCE_JOBS=2 coherence_full_system_verify` | PASS; 57 passed, 1 optional saved-trace replay skipped. |
| `make COHERENCE_JOBS=2 coherence_hit_under_miss` | PASS; 3 directed full-AXI-top tests. |
| `make COHERENCE_JOBS=2 coherence_full_system_cross_closure` | PASS; checked CR01 owner transfer/refill/APB testcase. |
| `make COHERENCE_JOBS=2 coherence_full_system_stress` | PASS; 260/260 seeded environments. |
| `make COHERENCE_JOBS=2 coherence_coverage_audit` | PASS; primary subsystem, AXI, and independent Block raw coverage generated. |

Evidence consistency gate: PASS, 57 testcase records, 53/53 integrated required functional bins, and 29/29 required crosses. Separate Python coherence coverage: 49/49 bins and 19/19 crosses. Four-agent stress recorded real Snoop activity and checked CR01 coverage. No failing stress seed occurred.

## Closure status

**OPEN — the regression passing does not mean verification closure.** Primary raw RTL coverage remains 843/998 lines, 461/556 branches, 19980/27474 toggles, 30/54 FSM states, and 7/48 FSM arcs. There are 1,026 dataset-scoped zero-count records in the point matrix; all remain OPEN, with no approved waivers and no reviewed/eligible percentage computed. CR01 and CR07 have checked integrated overlap evidence; CR02–CR06 and CR08–CR10 remain OPEN.

See [`docs/dv/closure_phase2_execution_2026-11-06.md`](../../docs/dv/closure_phase2_execution_2026-11-06.md) for phase-by-phase details, per-seed campaign results, exact scope limits, and the candidate sign-off decision. Raw RTL results are in [`reports/final/rtl_coverage_signoff.md`](../final/rtl_coverage_signoff.md); functional/cross artifacts are in this directory.

The remote Actions run [41962170929](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/41962170929) passed on base SHA `9b281f3`; it is not candidate CI. Candidate CI is pending publishing the branch. PPA, STA, physical SRAM macro implementation, and unbounded full-system formal proof are excluded.
