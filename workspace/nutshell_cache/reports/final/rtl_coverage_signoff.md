# RTL Coverage Closure — Audit and Sign-off Status

**Status: OPEN — not signed off.** This report preserves the raw coverage denominator and does not assign waivers. The latest available raw runs show unhit RTL coverage points and unresolved point-to-checker review. No claim of 100% reviewed/eligible code coverage is made.

Generated: 2026-11-11 01:19 +08.

## Scope and source manifest

Product RTL scope: `18` sources from `rtl/Coherence.files.f`. The primary subsystem Verilator source manifest contains `18` RTL sources; exact manifest match: **PASS**.

Manifest files without executable runtime points in a particular build are listed as N/A in `docs/coverage_audit_phase1.md`; they are not treated as zero coverage. The AXI top and independent Block tops are separate raw scopes.

## Raw coverage by independent dataset

Each row is one top/build and its documented run set. These denominators are not summed across rows. Line/branch/toggle/FSM are separate metrics.

| Dataset | Line hit/total | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full coherent subsystem regression | 864/992 | 473/556 | 21931/27474 | 30/54 | 13/48 |
| AXI cache subsystem E2E (five fixed seeds) | 901/1068 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| DirectoryController block | 178/182 | 37/42 | 260/612 | 10/10 | 3/9 |
| DirectoryMshrBank block | 167/286 | 100/128 | 1249/2904 | 31/40 | 11/36 |
| SharedLineEngine block | 101/104 | 44/52 | 304/648 | N/A | N/A |
| MesiL1Controller block | 124/132 | 43/46 | 741/1804 | 7/7 | 3/6 |
| SharedL2DirectoryArray block | 75/79 | 65/74 | 197/1778 | N/A | N/A |
| Bus blocks | 67/68 | 70/76 | 1100/2450 | N/A | N/A |

## Gap inventory

The detailed `coverage_closure_matrix.csv` contains **869 dataset-scoped zero-count records**. A point hit by another separately listed dataset is recorded as provenance, not credited to this dataset or denominator.

| Primary subsystem gap type | Unhit points |
| --- | ---: |
| LCOV RTL line | 128 |
| Verilator branch | 83 |
| FSM state | 24 |
| FSM arc | 35 |

The matrix records source path, source line, Block, branch/state/arc identity, feature/spec relationship, reachability review, protocol guard, risk, testcase/checker/formal references, other-dataset evidence, recommended disposition, and remaining action. Source inspection labels are not proofs. No automatic removal or waiver is performed.
All 869 zero-count dataset-scoped records currently have status **OPEN**. Allowed statuses are BLOCKED, COVERED, OPEN, PROVEN_UNREACHABLE, REVIEWED_WAIVER; promotion requires explicitly reviewed evidence and is never inferred from a hit in another raw dataset.

## Functional coverage and checker status

Python/Toffee coherence closure: functional 49/49 required bins (49 total records); cross 19/19 required bins (19 total records).
Full-system checked closure artifact: functional 53/53; cross 35/35; source SHA `b383383abea773decff022c149b7e767fb2df827`.
These are separate coverage plans and are not added together. Full-system counts require testcase, monitor-event, cycle-overlap, and checker evidence under the evidence contract. Coverage Bin IDs were not edited. Functional bins are not substituted for RTL source coverage.

## Reviewed / eligible coverage

**Reviewed/eligible percentages are not yet computable.** The raw points still need point-level review against the independent checker and the intended coverage obligation. The CSV preserves all zero-count points without marking them waived, unreachable, or redundant. Eligible Coverage must only be computed after that review; therefore there is no supported 100% closure claim yet.

## Tool and scope limits

- Verilator LCOV line records and native branch/toggle/FSM points have distinct instrumentation and denominators.
- Independent subsystem, AXI, and Block runs are not arithmetically merged. Repeated workload seeds are merged only where the raw inventory identifies the same elaboration and test definition.
- Python/Toffee functional coverage is not merged into Verilator RTL coverage: it uses a different simulator/wrapper and does not emit compatible source points.
- A zero FSM denominator means that the selected Verilator build did not extract an FSM point; it is not evidence that the design has no FSM.
- Toggle coverage is reported raw and reviewed separately; no 100% toggle requirement is asserted.
- Formal evidence is component/bounded where indicated by the existing tests. It is not treated as an unbounded whole-system proof.

## Regression evidence and remaining status

Current source fingerprint: 8/8 required regression targets have PASS exit status and verified log hashes. Regression status: PASS. Functional Verification Candidate evidence is separate from Reviewed RTL Code Coverage and Full Code Coverage Sign-off; code coverage remains OPEN.
This is local evidence only; it does not establish a remote GitHub Actions result. The full regression result does not close raw RTL coverage gaps by itself.

Required local gates are listed with source SHA and log references in `verification_run_manifest.json`. `coherence_full_system_verify` invokes `coherence_verify` as a nested prerequisite; the run manifest records that relationship so the nested execution is not mistaken for a separate simulator configuration.

**Sign-off: OPEN.** Raw uncovered legal paths, protocol fault paths, and per-instance FSM obligations remain for directed testing, fault injection, formal evidence, or reviewed disposition. No unresolved coverage gap is represented as closed. This sign-off excludes PPA, STA, real SRAM macro implementation, and chip-level physical implementation.
