# Full-System DV Evidence Index

Implementation SHA: `0f32de71126163bb9b9b32ec1ce8c23d731a58b1`
Branch: `codex/full-system-graybox-closure`
Date: 2026-11-02 (Asia/Singapore)

## Regression logs

| Artifact | Meaning |
| --- | --- |
| `coherence_verify_0f32de7.log.gz` + `.status` | Full `make COHERENCE_JOBS=2 coherence_verify` rerun on this implementation SHA; status file records the command exit code. |
| `coherence_full_system_coverage_0f32de7.log.gz` | Integrated full-system pytest suite; 19 passed / 1 replay test skipped without a trace argument; 26/26 Required bins and 7/7 Required crosses. |
| `stress_20x500_0f32de7.log` | Extended random regression, 20 seeds × 500 operations; 20/20 seeds passed. |
| `replay_dual_cold_misses_0f32de7.log` | Explicit saved-trace replay on this implementation SHA; 1 passed. |

Inspect the compressed logs with `gzip -dc <artifact>.gz`.

## Machine-readable coverage

- `full_system_coverage.json`: per-test events, monitor records, coverage and
  seed data from the integrated run.
- `full_system_coverage_closure.json` / `.md`: Required-bin closure, scoped to
  entries marked implemented in the coverage plan.
- `functional_coverage.json` and `cross_coverage.json`: observed bin counts
  from that run.
- `replay_dual_cold_misses.jsonl`: selected replay trace exercising two
  overlapping cold misses and out-of-order AXI read responses.

The full generated random trace is ignored local output and is not committed.

## Reports and scope

- [`verification_summary.md`](verification_summary.md): commands, local
  results, scope and reproduction steps.
- [`unresolved_gaps.md`](unresolved_gaps.md): remaining integrated-system,
  RTL coverage and CI evidence gaps.
- [`../../docs/dv/full_system_verification_results.md`](../../docs/dv/full_system_verification_results.md)
  and [`../../docs/dv/full_system_scenario_testplan.md`](../../docs/dv/full_system_scenario_testplan.md):
  design-facing scenario status and limitations.
- `rtl_coverage_summary.md`: separately measured raw RTL coverage. Python
  functional coverage is not added to RTL code coverage.

These are local verification results, not a final system sign-off or remote CI
result. See the unresolved-gap report for open and partial scenarios.
