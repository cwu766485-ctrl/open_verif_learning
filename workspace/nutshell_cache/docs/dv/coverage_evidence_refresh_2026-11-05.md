# Full-System Coverage Evidence Refresh — 2026-11-05

## Run

Command:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_full_system_coverage
```

Result: **57 passed, 1 skipped** (the saved-trace replay test is skipped when
no replay trace is supplied). Pytest exit status is 0. The raw report contains
57 completed test environments.

## Synchronized artifacts

All four files below were regenerated from the same test run:

- `reports/full_system/full_system_coverage.json` — raw per-test run evidence.
- `reports/full_system/full_system_coverage_closure.json` — **53/53 Required**
  and **29/29 Required Cross**; no missing required entries.
- `reports/full_system/functional_coverage.json` — observed functional-bin
  counts.
- `reports/full_system/cross_coverage.json` — observed cross-bin counts.

The raw report contains
`tests/full_system/test_owner_transfer_apb_cross.py::test_dirty_owner_transfer_during_refill_with_apb_snoop_count`
with status `passed`. The closure maps both new required IDs to this testcase:

- `FS.XAGENT.OWNER_TRANSFER_REFILL_APB` — hit count 1.
- `FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET` — hit count 1.

The testcase checks dirty-owner data across all eight beats, the independent
MESI/data and Directory predictions, AXI burst/ID behavior, APB Snoop counter,
and cycle ordering before sampling either bin. The closure evidence records the
scenario's Monitor events and Checker contract. Existing Bin IDs and Checker
rules are unchanged.

This refresh changes generated verification evidence and its summary only; it
does not change RTL behavior or testcase stimulus/checking behavior. Raw RTL
line/branch/toggle/FSM coverage remains a separate open audit and is not claimed
closed by these functional coverage results.
