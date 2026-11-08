"""Emit the final, dataset-scoped RTL coverage gap inventory.

Coverage from separate tops/builds is never added. The detailed matrix contains
one row for each zero-count point in each applicable raw dataset. A raw hit in
another run is recorded as evidence to review, not as an automatic closure.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from dv.coverage import coherence_gap_review as audit
from dv.coverage import coverage_closure_matrix as gaps
from dv.coverage import coverage_raw_runs as raw


ROOT = audit.ROOT
OUT = ROOT / "reports/final"
MATRIX = OUT / "coverage_closure_matrix.csv"
WAIVERS = OUT / "coverage_waivers.json"
RTL_REPORT = OUT / "rtl_coverage_signoff.md"
VERIFY_REPORT = OUT / "verification_signoff.md"
RUN_STATUS = ROOT / "reports/closure/coherence_verify_final.status"
RUN_MANIFEST = OUT / "verification_run_manifest.json"

EXTRA_FIELDS = [
    "disposition", "closure_status", "resolution_evidence", "remaining_action",
]
VALID_CLOSURE_STATUSES = {
    "OPEN", "COVERED", "PROVEN_UNREACHABLE", "REVIEWED_WAIVER", "BLOCKED",
}


def disposition(action: str) -> str:
    text = action.lower()
    has_test = any(token in text for token in ("directed", "test", "checker"))
    has_fault = any(token in text for token in ("fault injection", "inject"))
    has_formal = "formal" in text or "prove" in text or "proof" in text
    if has_fault and has_formal:
        return "FAULT_INJECTION_OR_FORMAL"
    if has_fault and has_test:
        return "TEST_AND_FAULT_INJECTION"
    if has_fault:
        return "FAULT_INJECTION"
    if has_formal:
        return "FORMAL_OR_INVESTIGATE"
    if has_test:
        return "TEST"
    return "INVESTIGATE"


def current_raw_metrics() -> dict[str, dict[str, tuple[int, int]]]:
    results: dict[str, dict[str, tuple[int, int]]] = {}
    for name, (dat, info, _scope) in raw.DATASETS.items():
        if not dat.is_file() or not info.is_file():
            continue
        line_info = raw.read_line_info(info)
        points = raw.read_points(dat)
        totals, _ = raw.metric_counts(line_info, points)
        results[name] = {
            kind: tuple(totals[kind])
            for kind in raw.POINT_TYPES
        }
    return results


def functional_counts() -> tuple[str, str]:
    path = ROOT / "reports/coherence/python_coverage_closure.json"
    if not path.is_file():
        return "not available", "not available"
    data = json.loads(path.read_text(encoding="utf-8"))
    def count(section: str) -> str:
        bins = data.get(section, {}).get("bins", [])
        hit = sum(item.get("status") == "hit" for item in bins)
        required = sum(item.get("required", True) for item in bins)
        return f"{hit}/{required} required bins ({len(bins)} total records)"
    return count("functional_coverage"), count("cross_coverage")


def full_system_counts() -> tuple[str, str, str]:
    """Read the checked full-system artifact without mixing it with Python bins."""
    path = ROOT / "reports/full_system/full_system_coverage_closure.json"
    if not path.is_file():
        return "not available", "not available", "source SHA unavailable"
    data = json.loads(path.read_text(encoding="utf-8"))
    functional = f"{data.get('required_bins_passed', 0)}/{data.get('required_bins_total', 0)}"
    cross = f"{data.get('required_cross_bins_passed', 0)}/{data.get('required_cross_bins_total', 0)}"
    return functional, cross, data.get("git_sha", "source SHA unavailable")


def full_regression_status() -> tuple[str, str]:
    """Read an explicit exit-status record written by the make invocation."""
    if not RUN_STATUS.is_file():
        return "not recorded", "No final-candidate full-regression status file is present."
    fields = {}
    for line in RUN_STATUS.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    result = fields.get("result", "UNKNOWN")
    sha = fields.get("source_sha", "unknown source SHA")
    timestamp = fields.get("timestamp", "time not recorded")
    log = fields.get("log", "log path not recorded")
    summary = f"Local {fields.get('command', 'coherence_verify')} result: {result} at source SHA `{sha}` ({timestamp}); log: `{log}`."
    return result, summary


def regression_gate_rows() -> list[dict[str, str]]:
    if not RUN_MANIFEST.is_file():
        return []
    try:
        data = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("required_gates", [])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw_rows = gaps.build_rows()
    rows = []
    fields = list(gaps.FIELDS) + EXTRA_FIELDS
    for source_row in raw_rows:
        row = dict(source_row)
        row["disposition"] = disposition(row["recommended_action"])
        # A zero-count raw point is an open obligation in this dataset. A hit
        # in another elaborated top is retained as provenance, never promoted
        # to COVERED here. Other statuses require explicit reviewed evidence.
        row["closure_status"] = "OPEN"
        row["resolution_evidence"] = row["separate_raw_dataset_evidence"]
        row["remaining_action"] = row["recommended_action"]
        if row["closure_status"] not in VALID_CLOSURE_STATUSES:
            raise AssertionError(f"invalid closure status for {row['point_id']}: {row['closure_status']}")
        rows.append(row)

    with MATRIX.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    WAIVERS.write_text(json.dumps({
        "schema_version": 1,
        "status": "No waivers approved or generated by this audit.",
        "policy": "Any future waiver requires a specific point ID, justification, risk owner, and independent review approval.",
        "waivers": [],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metrics = current_raw_metrics()
    func, cross = functional_counts()
    full_func, full_cross, full_system_sha = full_system_counts()
    per_dataset = Counter(row["raw_dataset"] for row in rows)
    primary = "Full coherent subsystem regression"
    primary_misses = Counter(
        row["metric"] for row in rows if row["raw_dataset"] == primary
    )
    manifest = audit.read_manifest()
    compiled_path = ROOT / "reports/coherence/obj_dir/VCoherentCacheSubsystem_tb__verFiles.dat"
    compiled_sources = audit.compiled_rtl_sources() if compiled_path.is_file() else set()
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    report = [
        "# RTL Coverage Closure — Audit and Sign-off Status", "",
        "**Status: OPEN — not signed off.** This report preserves the raw coverage denominator and does not assign waivers. The latest available raw runs show unhit RTL coverage points and unresolved point-to-checker review. No claim of 100% reviewed/eligible code coverage is made.", "",
        f"Generated: {now}.", "",
        "## Scope and source manifest", "",
        f"Product RTL scope: `{len(manifest)}` sources from `rtl/Coherence.files.f`. The primary subsystem Verilator source manifest contains `{len(compiled_sources)}` RTL sources; exact manifest match: **{'PASS' if compiled_sources == manifest else 'NOT VERIFIED / MISMATCH'}**.", "",
        "Manifest files without executable runtime points in a particular build are listed as N/A in `docs/coverage_audit_phase1.md`; they are not treated as zero coverage. The AXI top and independent Block tops are separate raw scopes.", "",
        "## Raw coverage by independent dataset", "",
        "Each row is one top/build and its documented run set. These denominators are not summed across rows. Line/branch/toggle/FSM are separate metrics.", "",
        "| Dataset | Line hit/total | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |", "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in raw.DATASETS:
        if name not in metrics:
            report.append(f"| {name} | not run/data absent | not run/data absent | not run/data absent | not run/data absent | not run/data absent |")
            continue
        vals = metrics[name]
        fmt = lambda key: f"{vals[key][0]}/{vals[key][1]}" if vals[key][1] else "N/A"
        report.append(f"| {name} | {fmt('line')} | {fmt('branch')} | {fmt('toggle')} | {fmt('fsm_state')} | {fmt('fsm_arc')} |")

    run_result, run_summary = full_regression_status()
    gate_rows = regression_gate_rows()
    report += [
        "", "## Gap inventory", "",
        f"The detailed `coverage_closure_matrix.csv` contains **{len(rows)} dataset-scoped zero-count records**. A point hit by another separately listed dataset is recorded as provenance, not credited to this dataset or denominator.", "",
        "| Primary subsystem gap type | Unhit points |", "| --- | ---: |",
    ]
    for metric in ("LCOV RTL line", "Verilator branch", "FSM state", "FSM arc"):
        report.append(f"| {metric} | {primary_misses[metric]} |")
    report += [
        "", "The matrix records source path, source line, Block, branch/state/arc identity, feature/spec relationship, reachability review, protocol guard, risk, testcase/checker/formal references, other-dataset evidence, recommended disposition, and remaining action. Source inspection labels are not proofs. No automatic removal or waiver is performed.",
        f"All {len(rows)} zero-count dataset-scoped records currently have status **OPEN**. Allowed statuses are {', '.join(sorted(VALID_CLOSURE_STATUSES))}; promotion requires explicitly reviewed evidence and is never inferred from a hit in another raw dataset.", "",
        "## Functional coverage and checker status", "",
        f"Python/Toffee coherence closure: functional {func}; cross {cross}.",
        f"Full-system checked closure artifact: functional {full_func}; cross {full_cross}; source SHA `{full_system_sha}`.",
        "These are separate coverage plans and are not added together. Full-system counts require testcase, monitor-event, cycle-overlap, and checker evidence under the evidence contract. Coverage Bin IDs were not edited. Functional bins are not substituted for RTL source coverage.", "",
        "## Reviewed / eligible coverage", "",
        "**Reviewed/eligible percentages are not yet computable.** The raw points still need point-level review against the independent checker and the intended coverage obligation. The CSV preserves all zero-count points without marking them waived, unreachable, or redundant. Eligible Coverage must only be computed after that review; therefore there is no supported 100% closure claim yet.", "",
        "## Tool and scope limits", "",
        "- Verilator LCOV line records and native branch/toggle/FSM points have distinct instrumentation and denominators.",
        "- Independent subsystem, AXI, and Block runs are not arithmetically merged. Repeated workload seeds are merged only where the raw inventory identifies the same elaboration and test definition.",
        "- Python/Toffee functional coverage is not merged into Verilator RTL coverage: it uses a different simulator/wrapper and does not emit compatible source points.",
        "- A zero FSM denominator means that the selected Verilator build did not extract an FSM point; it is not evidence that the design has no FSM.",
        "- Toggle coverage is reported raw and reviewed separately; no 100% toggle requirement is asserted.",
        "- Formal evidence is component/bounded where indicated by the existing tests. It is not treated as an unbounded whole-system proof.", "",
        "## Regression evidence and remaining status", "",
        run_summary,
        "This is local evidence only; it does not establish a remote GitHub Actions result. The full regression result does not close raw RTL coverage gaps by itself.", "",
        "Required local gates are listed with source SHA and log references in `verification_run_manifest.json`. `coherence_full_system_verify` invokes `coherence_verify` as a nested prerequisite; the run manifest records that relationship so the nested execution is not mistaken for a separate simulator configuration.", "",
        "**Sign-off: OPEN.** Raw uncovered legal paths, protocol fault paths, and per-instance FSM obligations remain for directed testing, fault injection, formal evidence, or reviewed disposition. No unresolved coverage gap is represented as closed. This sign-off excludes PPA, STA, real SRAM macro implementation, and chip-level physical implementation.", "",
    ]
    RTL_REPORT.write_text("\n".join(report), encoding="utf-8")

    verification = [
        "# Verification Sign-off Status", "",
        "**Status: OPEN — not a release sign-off.** This file is the current coverage-closure status view; consult the per-run raw reports and CI for test results.", "",
        f"Python/Toffee coherence closure: functional {func}; cross {cross}.",
        f"Full-system checked closure artifact: functional {full_func}; cross {full_cross}; source SHA `{full_system_sha}`.",
        f"Dataset-scoped zero-count RTL points: {len(rows)}.",
        "Approved coverage waivers: 0.",
        "Reviewed/eligible RTL coverage: not computed; point-by-checker review is incomplete.",
        f"Final full regression status: {run_result}.",
        run_summary,
        "Required gate summary: " + (", ".join(f"`{row.get('target', 'unknown')}` {row.get('status', 'UNKNOWN')}" for row in gate_rows) if gate_rows else "not recorded in the machine-readable run manifest."),
        "Candidate remote CI must be checked against the published PR head; see the final verification report for the SHA-scoped GitHub Actions link. This local report generator does not query GitHub.",
        "PPA, STA, real SRAM macro implementation, and chip-level physical implementation are excluded.", "",
    ]
    VERIFY_REPORT.write_text("\n".join(verification), encoding="utf-8")

    print(f"Wrote {MATRIX.relative_to(ROOT)}: {len(rows)} unhit dataset-scoped points")
    print(f"Primary subsystem open points: {dict(primary_misses)}")
    print(f"Waivers: 0; sign-off: OPEN")


if __name__ == "__main__":
    main()
