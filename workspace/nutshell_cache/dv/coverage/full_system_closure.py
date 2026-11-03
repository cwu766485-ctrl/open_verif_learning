"""Close only the implemented required bins in the integrated-top plan."""

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "dv/coverage/full_system_coverage_plan.json"
RAW = ROOT / "reports/full_system/full_system_coverage.json"
OUT = ROOT / "reports/full_system"


def close():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if raw.get("pytest_exit_status") != 0:
        raise SystemExit("full-system pytest run did not pass")
    bins, crosses = Counter(), Counter()
    bin_runs, cross_runs = {}, {}
    for run in raw.get("runs", []):
        bins.update(run.get("coverage", {}).get("bins", {}))
        crosses.update(run.get("coverage", {}).get("cross_bins", {}))
        for bin_id, count in run.get("coverage", {}).get("bins", {}).items():
            if count:
                bin_runs.setdefault(bin_id, []).append({
                    "test_id": run.get("test_id"),
                    "seed": run.get("seed"),
                    "count": count,
                })
        for cross_id, count in run.get("coverage", {}).get("cross_bins", {}).items():
            if count:
                cross_runs.setdefault(cross_id, []).append({
                    "test_id": run.get("test_id"),
                    "seed": run.get("seed"),
                    "count": count,
                })

    required_bins = [item for item in plan["bins"]
                     if item.get("required") and item.get("status") == "implemented"]
    required_crosses = [item for item in plan["crosses"]
                        if item.get("required") and item.get("status") == "implemented"]
    if not required_bins or not required_crosses:
        raise SystemExit("coverage plan has no implemented required bins/crosses")
    missing_bins = [item["id"] for item in required_bins if bins[item["id"]] == 0]
    missing_crosses = [item["id"] for item in required_crosses
                       if crosses[item["id"]] == 0]
    closure = {
        "schema_version": 1,
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
            "classification": item.get("classification", "unclassified"),
            "feature": item.get("feature"),
            "legal_preconditions": item.get("legal_preconditions"),
            "stimulus_strategy": item.get("stimulus_strategy"),
            "required_monitor_event": item.get("required_monitor_event"),
            "checker": item.get("checker"),
            "hit_count": bins[item["id"]],
            "pass": bins[item["id"]] > 0,
            "evidence": bin_runs.get(item["id"], []),
        } for item in required_bins],
        "cross_evidence": [{
            "id": item["id"],
            "classification": item.get("classification", "unclassified"),
            "legal_preconditions": item.get("legal_preconditions"),
            "stimulus_strategy": item.get("stimulus_strategy"),
            "checker": item.get("checker"),
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
        json.dumps({"bins": dict(sorted(bins.items()))}, indent=2) + "\n",
        encoding="utf-8"
    )
    (OUT / "cross_coverage.json").write_text(
        json.dumps({"cross_bins": dict(sorted(crosses.items()))}, indent=2) + "\n",
        encoding="utf-8"
    )
    lines = ["# Full-System Functional Coverage Closure", "",
             f"- DUT: `{plan['dut']}`",
             f"- Scope: {closure['scope']}",
             f"- Required bins: {closure['required_bins_passed']}/"
             f"{closure['required_bins_total']}",
             f"- Required cross bins: {closure['required_cross_bins_passed']}/"
             f"{closure['required_cross_bins_total']}", "",
             "This report covers only entries marked implemented in the plan. "
             "Planned full-system features remain open and are not counted as hits.", ""]
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
