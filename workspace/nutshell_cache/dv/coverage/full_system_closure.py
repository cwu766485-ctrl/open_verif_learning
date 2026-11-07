"""Close only the implemented required bins in the integrated-top plan."""

import json
from collections import Counter
from pathlib import Path

from dv.coverage.full_system_evidence_gate import _strict_contract, _test_name
from dv.coverage.testcase_selector import testcase_selector


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "dv/coverage/full_system_coverage_plan.json"
RAW = ROOT / "reports/full_system/full_system_coverage.json"
OUT = ROOT / "reports/full_system"


def close():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if raw.get("pytest_exit_status") != 0:
        raise SystemExit("full-system pytest run did not pass")
    raw_bins, raw_crosses = Counter(), Counter()
    bins, crosses = Counter(), Counter()
    bin_runs, cross_runs = {}, {}
    for run in raw.get("runs", []):
        # Coverage is credited only from a testcase that completed successfully.
        # A failed test may have sampled before discovering a checker failure.
        if run.get("test_status") != "passed":
            continue
        raw_bins.update(run.get("coverage", {}).get("bins", {}))
        raw_crosses.update(run.get("coverage", {}).get("cross_bins", {}))
        for bin_id, count in run.get("coverage", {}).get("bins", {}).items():
            if count:
                bin_runs.setdefault(bin_id, []).append({
                    "test_id": run.get("test_id"),
                    "seed": run.get("seed"),
                    "count": count,
                    "test_status": run.get("test_status"),
                    "sample_testcases": run.get("coverage", {}).get(
                        "sample_testcases", {}).get("bins", {}).get(bin_id, []),
                    "monitor": run.get("monitor", {}),
                })
        for cross_id, count in run.get("coverage", {}).get("cross_bins", {}).items():
            if count:
                cross_runs.setdefault(cross_id, []).append({
                    "test_id": run.get("test_id"),
                    "seed": run.get("seed"),
                    "count": count,
                    "test_status": run.get("test_status"),
                    "sample_testcases": run.get("coverage", {}).get(
                        "sample_testcases", {}).get("cross_bins", {}).get(cross_id, []),
                    "checked_cross_evidence": run.get("coverage", {}).get(
                        "checked_cross_evidence", {}).get(cross_id, []),
                    "monitor": run.get("monitor", {}),
                })

    required_bins = [item for item in plan["bins"]
                     if item.get("required") and item.get("status") == "implemented"]
    required_crosses = [item for item in plan["crosses"]
                        if item.get("required") and item.get("status") == "implemented"]
    if not required_bins or not required_crosses:
        raise SystemExit("coverage plan has no implemented required bins/crosses")
    for item in required_bins + required_crosses:
        strict = _strict_contract(item)
        if strict:
            selectors = {testcase_selector(value) for value in item.get("testcases", [])}
            checker_selectors = {
                testcase_selector(value) for value in item.get("checker_testcases", [])
            }
            if (not selectors or not checker_selectors or
                    not checker_selectors <= selectors or
                    not all("::" in value for value in selectors | checker_selectors)):
                raise SystemExit(f"invalid strict checker testcase mapping for {item['id']}")
        else:
            selectors = {_test_name(value) for value in item.get("testcases", [])}
            checker_selectors = selectors
            if not selectors:
                raise SystemExit(f"missing testcase mapping for {item['id']}")
        table = bin_runs if item in required_bins else cross_runs
        credited = [row for row in table.get(item["id"], [])
                    if (testcase_selector(row.get("test_id", "")) if strict else
                        _test_name(row.get("test_id", ""))) in checker_selectors]
        if item in required_bins:
            bins[item["id"]] = sum(row["count"] for row in credited)
            bin_runs[item["id"]] = credited
        else:
            crosses[item["id"]] = sum(row["count"] for row in credited)
            cross_runs[item["id"]] = credited
    missing_bins = [item["id"] for item in required_bins if bins[item["id"]] == 0]
    missing_crosses = [item["id"] for item in required_crosses
                       if crosses[item["id"]] == 0]
    revision = raw.get("git_sha")
    if not revision or len(revision) != 40:
        raise SystemExit("full-system raw coverage has no complete source SHA")
    closure = {
        "schema_version": 2,
        "git_sha": revision,
        "tool_versions": raw.get("tool_versions", {}),
        "scope": "implemented Required bins in the integrated-top sign-off slice",
        "dut": plan["dut"],
        "testcase_exit_status": raw["pytest_exit_status"],
        "required_bins": {item["id"]: bins[item["id"]]
                          for item in required_bins},
        "required_cross_bins": {item["id"]: crosses[item["id"]]
                                for item in required_crosses},
        "required_bins_passed": len(required_bins) - len(missing_bins),
        "required_bins_total": len(required_bins),
        "required_cross_bins_passed": len(required_crosses) - len(missing_crosses),
        "required_cross_bins_total": len(required_crosses),
        "missing_bins": missing_bins,
        "missing_cross_bins": missing_crosses,
        "bin_evidence": [{
            "id": item["id"],
            "evidence_contract": item.get("evidence_contract"),
            "classification": item.get("classification", "unclassified"),
            "feature": item.get("feature"),
            "legal_preconditions": item.get("legal_preconditions"),
            "stimulus_strategy": item.get("stimulus_strategy"),
            "required_monitor_event": item.get("required_monitor_event"),
            "required_monitor_events": item.get("required_monitor_events", []),
            "testcases": item.get("testcases", []),
            "checker_testcases": item.get("checker_testcases", []),
            "checker": item.get("checker"),
            "hit_count": bins[item["id"]],
            "pass": bins[item["id"]] > 0,
            "evidence": bin_runs.get(item["id"], []),
        } for item in required_bins],
        "cross_evidence": [{
            "id": item["id"],
            "evidence_contract": item.get("evidence_contract"),
            "classification": item.get("classification", "unclassified"),
            "legal_preconditions": item.get("legal_preconditions"),
            "stimulus_strategy": item.get("stimulus_strategy"),
            "required_monitor_event": item.get("required_monitor_event"),
            "required_monitor_events": item.get("required_monitor_events", []),
            "testcases": item.get("testcases", []),
            "checker_testcases": item.get("checker_testcases", []),
            "checker": item.get("checker"),
            "requires_cycle_overlap": item.get("requires_cycle_overlap", False),
            "hit_count": crosses[item["id"]],
            "pass": crosses[item["id"]] > 0,
            "evidence": cross_runs.get(item["id"], []),
        } for item in required_crosses],
        "planned_features_not_claimed": [item["id"] for item in plan["bins"]
                                          if item.get("status") != "implemented"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "full_system_coverage_closure.json").write_text(
        json.dumps(closure, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "functional_coverage.json").write_text(
        json.dumps({"schema_version": 2, "git_sha": revision,
                    "tool_versions": raw.get("tool_versions", {}),
                    "bins": dict(sorted(raw_bins.items()))}, indent=2) + "\n",
        encoding="utf-8"
    )
    (OUT / "cross_coverage.json").write_text(
        json.dumps({"schema_version": 2, "git_sha": revision,
                    "tool_versions": raw.get("tool_versions", {}),
                    "cross_bins": dict(sorted(raw_crosses.items()))}, indent=2) + "\n",
        encoding="utf-8"
    )
    lines = ["# Full-System Functional Coverage Closure", "",
             f"- Tested source SHA: `{revision}`",
             f"- DUT: `{plan['dut']}`",
             f"- Scope: {closure['scope']}",
             f"- Required bins: {closure['required_bins_passed']}/"
             f"{closure['required_bins_total']}",
             f"- Required cross bins: {closure['required_cross_bins_passed']}/"
             f"{closure['required_cross_bins_total']}", "",
             "This report covers only entries marked implemented in the plan. "
             "Planned full-system features remain open and are not counted as hits.", "",
             "## Tool Versions", ""]
    lines.extend(f"- {name}: `{version}`"
                 for name, version in sorted(raw.get("tool_versions", {}).items()))
    lines.append("")
    if missing_bins or missing_crosses:
        lines.extend(["## Missing Required Coverage", ""])
        lines.extend(f"- `{item}`" for item in missing_bins + missing_crosses)
    (OUT / "full_system_coverage_closure.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"Required bins: {closure['required_bins_passed']}/"
          f"{closure['required_bins_total']}")
    print(f"Required crosses: {closure['required_cross_bins_passed']}/"
          f"{closure['required_cross_bins_total']}")
    return not missing_bins and not missing_crosses


if __name__ == "__main__" and not close():
    raise SystemExit(1)
