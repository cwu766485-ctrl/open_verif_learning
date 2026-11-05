# Verification Sign-off Status

**Status: OPEN for final sign-off; local DE/DV regression candidate passes.**

On candidate `fd6ca87a2418ab9cae737b2b73dead6ca5dd5ef5`, the following local gates
passed after `source scripts/env.sh`:

- `make COHERENCE_JOBS=2 coherence_verify`
- `make COHERENCE_JOBS=2 coherence_full_system_verify`
- `make COHERENCE_JOBS=2 coherence_hit_under_miss`
- `make COHERENCE_JOBS=2 coherence_full_system_stress`
- `make COHERENCE_JOBS=2 coherence_coverage_audit`

Integrated feature coverage is 53/53 Required and 29/29 Required Cross. The
separate Python coherence plan remains 49/49 and 19/19. Four-agent stress
completed 260/260 seed environments with zero final protocol/fatal errors.
Details and testcase/checker evidence are in
[`de_dv_next_phase_signoff.md`](de_dv_next_phase_signoff.md).

Raw RTL coverage is not closed: the full subsystem dataset has 155 uncovered
lines, 95 branches, 24 FSM states and 41 arcs; point-by-point review is
incomplete. No waivers are approved. Therefore this is not a release or final
RTL/DV sign-off, and no RTL v2 branch is created.

The candidate's remote GitHub Actions status is not inferred from the historical
baseline. Check status for the exact pushed candidate commit. This sign-off
excludes PPA, STA, physical SRAM macros and chip-level implementation.
