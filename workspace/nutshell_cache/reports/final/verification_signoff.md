# Verification Sign-off Status

**Status: OPEN — not a release sign-off.** The functional regression passes, but source-coverage obligations have not been closed point by point. This report does not claim final RTL coverage closure.

## Frozen candidate and local regression

The tested RTL/DV candidate was `9797623ae2c63563f9419c743e4b91e03c0e0d9b` on `cache_coherence`. The full command `source scripts/env.sh && make COHERENCE_JOBS=2 coherence_verify` exited 0 on 2026-10-31 at 07:29:57 UTC. The complete log and machine-readable status are local, gitignored artifacts at `reports/closure/coherence_verify_final.log` and `reports/closure/coherence_verify_final.status`; the log SHA-256 is `07ec9f71edf84e8e0722eb045170092308205524a58bdf28d18dc939bd86af37`. The test summary below is committed; the raw log is not included in Git.

The passing run included:

- 7 bounded SymbiYosys proof/cover tasks: request arbiter, snoop arbiter, Directory, Directory MSHR bank safety/cover, Directory progress, and L1 controller.
- Python/Toffee coherence regression: 36 passed, 1 deselected; functional coverage 49/49; checker fault injections 9/9.
- AXI Python regression: 3 passed, including four outstanding bursts, ID/order/backpressure, error/reset, and 4 KiB boundary checks.
- Standard and dense-set randomized stress: 20 seeds passed in each suite.
- RTL mutation campaign: 4/4 injected mutations detected.
- Benchmark v4: 24 workload rows validated.
- Independent block and subsystem simulation targets included by `coherence_verify` passed.

The formal results are bounded/component results; they are not an unbounded proof of the full subsystem. This regression result is local evidence for the exact candidate SHA above.

## Coverage status

Functional closure: 49/49 required bins. Cross closure: 19/19 required bins. The full regression refreshed the Python coverage artifact and printed `Python coherence coverage: 49/49 bins hit`; the cross artifact reports 19/19. Bin IDs were not changed.

Raw RTL coverage is reported per independent elaboration and is not added across tops. For the full coherent subsystem dataset:

| Metric | Hit / total | Raw result |
| --- | ---: | ---: |
| RTL line | 858 / 1006 | 85.3% |
| Branch | 450 / 536 | 84.0% |
| Toggle | 19916 / 26978 | 73.8% |
| FSM state | 30 / 54 | 55.6% |
| FSM arc | 7 / 48 | 14.6% |

The closure matrix contains 994 **dataset-scoped zero-count observations** across the subsystem, AXI and independent block runs. In the primary subsystem dataset these comprise 148 line, 86 branch, 24 FSM state and 41 FSM arc misses (299 observations). Dataset-scoped observations are not the same as globally unique RTL points. All remain `OPEN_DATASET_MISS`; no waiver has been approved. Point-by-checker review is incomplete, so reviewed/eligible coverage is **not computed** and unresolved gaps are not zero.

There are zero approved waivers. `reports/final/coverage_waivers.json` contains no generated waivers. Raw denominators and the separate block datasets are preserved in `reports/final/rtl_coverage_signoff.md` and `reports/final/coverage_closure_matrix.csv`.

## Remaining sign-off blockers

- Review each required zero-count line/branch/FSM point against its spec, actual reachability, checker and evidence; the matrix currently has source/path mapping but does not constitute completion of that review.
- Close legal-path gaps with directed stimulus and independent checking; fault-injection or a defensible interface invariant is still needed for unhit protocol guards. The existing 9 checker injections and 4 RTL mutations do not cover every defensive RTL path.
- Resolve or explicitly justify the subsystem FSM state/arc gaps. Component bounded proofs do not discharge every FSM transition obligation.
- Reconcile remaining source-file coverage scope and keep line, branch, toggle, FSM, functional and cross metrics separate. Python/Toffee functional hits are not source-coverage hits.
- Remote GitHub Actions for the final local candidate have not been verified. No remote CI sign-off is claimed.

The run emits existing lint/tool warnings; this is not a warning-free lint sign-off. PPA, STA, real SRAM macro implementation, and chip-level physical implementation are excluded.

**Release decision: do not mark RTL coverage closure complete on this evidence.** The functional regression is green, but the coverage closure status remains OPEN until the listed point-level review and evidence are completed.
