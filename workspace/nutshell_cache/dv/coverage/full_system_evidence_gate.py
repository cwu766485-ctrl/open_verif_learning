"""Fail closed when full-system coverage artifacts lose traceability."""

import json
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports/full_system"
PLAN = ROOT / "dv/coverage/full_system_coverage_plan.json"
SOURCE_PATHS = ("rtl", "dv", "tests", "Makefile", ".github/workflows")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _test_name(value):
    value = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    value = value.split("::")[-1]
    return value.split("[", 1)[0]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _aggregate(raw):
    bins, crosses = Counter(), Counter()
    run_by_id = {}
    for run in raw.get("runs", []):
        test_id = run.get("test_id")
        _require(test_id, "raw coverage contains a run without test_id")
        _require(test_id not in run_by_id, f"duplicate testcase record: {test_id}")
        run_by_id[test_id] = run
        _require(run.get("test_status") == "passed",
                 f"testcase did not pass: {test_id}")
        bins.update(run.get("coverage", {}).get("bins", {}))
        crosses.update(run.get("coverage", {}).get("cross_bins", {}))
    return bins, crosses, run_by_id


def _verify_evidence(items, evidence_items, run_by_id, *, kind):
    evidence_by_id = {item["id"]: item for item in evidence_items}
    for item in items:
        point_id = item["id"]
        _require(item.get("checker"), f"{kind} {point_id} has no checker mapping")
        _require(item.get("testcases"), f"{kind} {point_id} has no testcase mapping")
        _require(item.get("required_monitor_event"),
                 f"{kind} {point_id} has no monitor mapping")
        evidence = evidence_by_id.get(point_id)
        _require(evidence is not None, f"{kind} {point_id} has no evidence record")
        _require(evidence.get("pass") and evidence.get("hit_count", 0) > 0,
                 f"{kind} {point_id} has no checked hit")
        allowed_tests = {_test_name(test) for test in item["testcases"]}
        observed_tests = set()
        for contribution in evidence.get("evidence", []):
            test_id = contribution.get("test_id")
            run = run_by_id.get(test_id)
            _require(run is not None,
                     f"{kind} {point_id} references unknown testcase {test_id}")
            _require(contribution.get("test_status") == "passed" and
                     run.get("test_status") == "passed",
                     f"{kind} {point_id} references a non-passing testcase")
            _require(contribution.get("count", 0) > 0,
                     f"{kind} {point_id} references a zero-count testcase")
            monitor = contribution.get("monitor", {})
            counts = monitor.get("event_counts", {})
            _require(isinstance(counts, dict) and counts,
                     f"{kind} {point_id} contribution lacks monitor evidence")
            observed_tests.add(_test_name(test_id))
        _require(bool(allowed_tests & observed_tests),
                 f"{kind} {point_id} testcase mapping does not match observed contributors")


def audit(root=ROOT):
    root = Path(root)
    reports = root / "reports/full_system"
    plan = _read(root / "dv/coverage/full_system_coverage_plan.json")
    raw = _read(reports / "full_system_coverage.json")
    closure = _read(reports / "full_system_coverage_closure.json")
    functional = _read(reports / "functional_coverage.json")
    cross = _read(reports / "cross_coverage.json")

    source_sha = raw.get("git_sha")
    _require(source_sha and len(source_sha) == 40,
             "raw coverage must identify the complete tested source SHA")
    _require(raw.get("pytest_exit_status") == 0,
             "full-system pytest exit status is not passing")
    for name, artifact in (("closure", closure), ("functional", functional),
                           ("cross", cross)):
        _require(artifact.get("git_sha") == source_sha,
                 f"{name} source SHA differs from raw coverage")
        _require(artifact.get("tool_versions") == raw.get("tool_versions"),
                 f"{name} tool versions differ from raw coverage")

    repo = root.parents[1]
    changed = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", source_sha, "--",
         *SOURCE_PATHS], check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    _require(not changed,
             "tested source differs from current checkout: " + ", ".join(changed[:12]))

    bins, crosses, run_by_id = _aggregate(raw)
    _require(functional.get("bins") == dict(sorted(bins.items())),
             "functional_coverage.json disagrees with passing raw testcase records")
    _require(cross.get("cross_bins") == dict(sorted(crosses.items())),
             "cross_coverage.json disagrees with passing raw testcase records")
    required_bins = [item for item in plan["bins"]
                     if item.get("required") and item.get("status") == "implemented"]
    required_crosses = [item for item in plan["crosses"]
                        if item.get("required") and item.get("status") == "implemented"]
    _require(len(required_bins) == closure.get("required_bins_total"),
             "required functional-bin denominator changed or is stale")
    _require(len(required_crosses) == closure.get("required_cross_bins_total"),
             "required cross-bin denominator changed or is stale")
    _require(closure.get("required_bins") ==
             {item["id"]: bins[item["id"]] for item in required_bins},
             "closure functional counts differ from raw testcase records")
    _require(closure.get("required_cross_bins") ==
             {item["id"]: crosses[item["id"]] for item in required_crosses},
             "closure cross counts differ from raw testcase records")
    _verify_evidence(required_bins, closure.get("bin_evidence", []),
                     run_by_id, kind="bin")
    _verify_evidence(required_crosses, closure.get("cross_evidence", []),
                     run_by_id, kind="cross")

    markdown = (reports / "full_system_coverage_closure.md").read_text(
        encoding="utf-8")
    _require(f"- Tested source SHA: `{source_sha}`" in markdown,
             "Markdown report has stale source SHA")
    _require(f"- Required bins: {closure['required_bins_passed']}/"
             f"{closure['required_bins_total']}" in markdown,
             "Markdown functional closure differs from JSON")
    _require(f"- Required cross bins: {closure['required_cross_bins_passed']}/"
             f"{closure['required_cross_bins_total']}" in markdown,
             "Markdown cross closure differs from JSON")

    trace = reports / "full_system_trace.jsonl"
    _require(trace.is_file(), "full-system trace is missing")
    trace_runs = [json.loads(line) for line in trace.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    trace_runs = [record for record in trace_runs
                  if record.get("record_type") == "run"]
    _require(bool(trace_runs), "full-system trace contains no run headers")
    for record in trace_runs:
        _require(record.get("git_sha") == source_sha,
                 "trace run source SHA differs from coverage source SHA")
        _require(record.get("tool_versions") == raw.get("tool_versions"),
                 "trace run tool versions differ from raw coverage")

    return {"source_sha": source_sha, "runs": len(run_by_id),
            "required_bins": len(required_bins),
            "required_cross_bins": len(required_crosses)}


def main():
    result = audit()
    print("Full-system evidence gate PASS: "
          f"SHA={result['source_sha']} runs={result['runs']} "
          f"bins={result['required_bins']} crosses={result['required_cross_bins']}")


if __name__ == "__main__":
    main()
