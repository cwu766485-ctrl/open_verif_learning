"""Fail closed when full-system coverage artifacts lose traceability."""

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from dv.coverage.testcase_selector import testcase_selector


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports/full_system"
PLAN = ROOT / "dv/coverage/full_system_coverage_plan.json"
SOURCE_PATHS = (
    "workspace/nutshell_cache/rtl",
    "workspace/nutshell_cache/dv",
    "workspace/nutshell_cache/tests",
    "workspace/nutshell_cache/Makefile",
    "workspace/nutshell_cache/scripts",
    "workspace/nutshell_cache/pytest.ini",
    "workspace/nutshell_cache/rtl/Coherence.files.f",
    "workspace/nutshell_cache/rtl/Cache.files.f",
    "workspace/nutshell_cache/dv/coverage/full_system_coverage_plan.json",
    ".github/workflows",
)


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _test_name(value):
    """Legacy selector for v2 plan entries that predate module-qualified IDs."""
    value = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    value = value.split("::")[-1]
    return value.split("[", 1)[0]


def _strict_contract(item):
    """Whether an entry opts into event-ID and checker-attribution evidence."""
    contract = item.get("evidence_contract")
    _require(contract in (None, "checked_cross_v1"),
             f"coverage point {item.get('id')} has unknown evidence contract {contract!r}")
    if contract == "checked_cross_v1":
        _require(item.get("checker_testcases") and item.get("required_monitor_events"),
                 f"coverage point {item.get('id')} has an incomplete checked evidence contract")
    return contract == "checked_cross_v1"


def _required_monitor_events(item):
    events = item.get("required_monitor_events")
    _require(isinstance(events, list) and bool(events),
             f"coverage point {item.get('id')} has no explicit Monitor event IDs")
    _require(all(isinstance(event, str) and
                 re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", event)
                 for event in events),
             f"coverage point {item.get('id')} has malformed Monitor event IDs")
    return set(events)


def _check_monitor_conditions(item, evidence):
    conditions = item.get("required_monitor_conditions", [])
    for condition in conditions:
        field = condition["field"]
        op = condition["op"]
        expected = condition["value"]
        observed = [row.get("monitor", {}).get(field) for row in evidence]
        observed = [value for value in observed if value is not None]
        _require(bool(observed),
                 f"coverage point {item['id']} lacks Monitor field {field}")
        if op == "any_ge":
            passed = any(float(value) >= float(expected) for value in observed)
        elif op == "all_eq":
            passed = all(value == expected for value in observed)
        elif op == "any_eq":
            passed = any(value == expected for value in observed)
        else:
            raise ValueError(f"unsupported Monitor condition operator {op!r}")
        _require(passed, f"coverage point {item['id']} Monitor condition failed: "
                 f"{field} {op} {expected}")


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


def _verify_overlap_evidence(point_id, contribution, trace_events, test_id,
                             required_events):
    proofs = contribution.get("checked_cross_evidence", [])
    _require(bool(proofs), f"cross {point_id} lacks cycle-overlap checker evidence")
    for proof in proofs:
        _require(proof.get("checker_pass") is True and proof.get("checker"),
                 f"cross {point_id} has no passing named overlap checker")
        overlap = proof.get("overlap", {})
        roles = overlap.get("roles", {})
        _require(len(roles) >= 2 and overlap.get("start_cycle") is not None and
                 overlap.get("end_cycle") is not None,
                 f"cross {point_id} has malformed overlap interval")
        start = max(int(role["start_cycle"]) for role in roles.values())
        end = min(int(role["end_cycle"]) for role in roles.values())
        _require(start <= end and int(overlap["start_cycle"]) == start and
                 int(overlap["end_cycle"]) == end,
                 f"cross {point_id} roles do not share a checked cycle window")
        transactions = proof.get("transactions", [])
        transitions = proof.get("state_transitions", [])
        _require(transactions and transitions,
                 f"cross {point_id} lacks transaction/state outcome evidence")
        refs = proof.get("event_refs", [])
        _require(bool(refs), f"cross {point_id} has no monitor event references")
        refs_by_id = {ref.get("ref_id"): ref for ref in refs
                      if isinstance(ref, dict) and ref.get("ref_id")}
        _require(len(refs_by_id) == len(refs),
                 f"cross {point_id} has missing or duplicate event reference IDs")
        observed_event_ids = set()
        for ref in refs:
            _require({"ref_id", "role", "source", "event_type", "cycle"} <= set(ref),
                     f"cross {point_id} has an underspecified Monitor event reference")
            observed_event_ids.add(f"{ref['source']}.{ref['event_type']}")
            reference = {key: value for key, value in ref.items()
                         if key not in ("role", "ref_id")}
            found = any(event.get("test_id") == test_id and
                        all(event.get(key) == value for key, value in reference.items())
                        for event in trace_events)
            _require(found,
                     f"cross {point_id} references Monitor event absent from saved trace: {ref}")
        _require(required_events <= observed_event_ids,
                 f"cross {point_id} overlap proof omits required event references: "
                 f"{sorted(required_events - observed_event_ids)}")

        # The interval endpoints must be actual saved handshakes, not just
        # caller-provided cycle numbers. This also makes the computed overlap
        # independently reproducible from the trace.
        for role_name, role in roles.items():
            start_ref = refs_by_id.get(role.get("start_event_ref"))
            end_ref = refs_by_id.get(role.get("end_event_ref"))
            _require(start_ref is not None and end_ref is not None,
                     f"cross {point_id} role {role_name} has no event-bound endpoints")
            _require(start_ref.get("role") == role_name and
                     end_ref.get("role") == role_name and
                     int(role["start_cycle"]) == int(start_ref["cycle"]) and
                     int(role["end_cycle"]) == int(end_ref["cycle"]),
                     f"cross {point_id} role {role_name} endpoints disagree with trace refs")
            _require(int(role["start_cycle"]) <= int(role["end_cycle"]),
                     f"cross {point_id} role {role_name} has a reversed interval")

        for transaction in transactions:
            ref_ids = transaction.get("event_ref_ids", [])
            _require(ref_ids and all(ref_id in refs_by_id for ref_id in ref_ids),
                     f"cross {point_id} transaction has dangling event references")
            if transaction.get("txn_id") is not None:
                _require(any(refs_by_id[ref_id].get("txn_id") == transaction["txn_id"]
                             for ref_id in ref_ids),
                         f"cross {point_id} transaction ID is not tied to its Monitor events")
            if transaction.get("address") is not None:
                _require(any(refs_by_id[ref_id].get("address") == transaction["address"]
                             for ref_id in ref_ids),
                         f"cross {point_id} transaction address is not tied to its Monitor events")

        for transition in transitions:
            event_ref = refs_by_id.get(transition.get("event_ref_id"))
            _require(event_ref is not None,
                     f"cross {point_id} state transition has no Monitor event reference")
            for field in ("old_state", "new_state", "state", "owner", "sharers"):
                if field in transition:
                    _require(event_ref.get(field) == transition[field],
                             f"cross {point_id} state transition disagrees with Monitor event")


def _verify_evidence(items, evidence_items, run_by_id, *, kind, trace_events=()):
    evidence_by_id = {item["id"]: item for item in evidence_items}
    _require(len(evidence_by_id) == len(evidence_items),
             f"{kind} evidence contains duplicate point IDs")
    _require(set(evidence_by_id) == {item["id"] for item in items},
             f"{kind} evidence point set differs from the required plan")
    for item in items:
        point_id = item["id"]
        _require(item.get("checker"), f"{kind} {point_id} has no checker mapping")
        _require(item.get("testcases"), f"{kind} {point_id} has no testcase mapping")
        _require(item.get("required_monitor_event"),
                 f"{kind} {point_id} has no monitor mapping")
        strict = _strict_contract(item)
        required_events = _required_monitor_events(item) if strict else set()
        evidence = evidence_by_id.get(point_id)
        _require(evidence is not None, f"{kind} {point_id} has no evidence record")
        _require(evidence.get("checker") == item.get("checker"),
                 f"{kind} {point_id} checker mapping is stale or mismatched")
        _require(evidence.get("testcases") == item.get("testcases"),
                 f"{kind} {point_id} testcase mapping is stale or mismatched")
        _require(evidence.get("evidence_contract") == item.get("evidence_contract"),
                 f"{kind} {point_id} evidence contract is stale or mismatched")
        if strict:
            _require(evidence.get("checker_testcases") == item.get("checker_testcases"),
                     f"{kind} {point_id} checker testcase mapping is stale or mismatched")
            _require(evidence.get("required_monitor_events", []) ==
                     item.get("required_monitor_events", []),
                     f"{kind} {point_id} monitor mapping is stale or mismatched")
            _require(evidence.get("requires_cycle_overlap", False) ==
                     item.get("requires_cycle_overlap", False),
                     f"{kind} {point_id} overlap requirement is stale or mismatched")
        _require(evidence.get("pass") and evidence.get("hit_count", 0) > 0,
                 f"{kind} {point_id} has no checked hit")
        if strict:
            allowed_tests = {testcase_selector(test) for test in item["testcases"]}
            checker_tests = {testcase_selector(test)
                             for test in item.get("checker_testcases", [])}
            _require(all("::" in selector for selector in allowed_tests | checker_tests),
                     f"{kind} {point_id} strict testcase IDs must be module-qualified")
            _require(checker_tests and checker_tests <= allowed_tests,
                     f"{kind} {point_id} has invalid checker-to-testcase mapping")
        else:
            allowed_tests = {_test_name(test) for test in item["testcases"]}
            checker_tests = set()
        observed_tests = set()
        observed_hits = 0
        monitor_contributions = []
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
            selector = testcase_selector(test_id) if strict else _test_name(test_id)
            if strict:
                _require(selector in checker_tests,
                         f"{kind} {point_id} contribution is outside its checker testcase mapping: "
                         f"{test_id}")
            else:
                _require(selector in allowed_tests,
                         f"{kind} {point_id} testcase mapping does not match contributor: "
                         f"{test_id}")
            observed_hits += contribution["count"]
            sample_testcases = {
                testcase_selector(value)
                for value in contribution.get("sample_testcases", [])
            }
            if strict:
                _require(selector in sample_testcases,
                         f"{kind} {point_id} lacks exact runtime sample attribution for {test_id}")
            monitor = contribution.get("monitor", {})
            counts = monitor.get("event_counts", {})
            _require(isinstance(counts, dict) and counts,
                     f"{kind} {point_id} contribution lacks monitor evidence")
            contribution_events = {
                event for event, count in counts.items()
                if isinstance(count, int) and count > 0
            }
            if strict:
                _require(required_events <= contribution_events,
                         f"{kind} {point_id} testcase {test_id} is missing required "
                         f"Monitor events: {sorted(required_events - contribution_events)}")
            monitor_contributions.append(contribution)
            if strict and kind == "cross" and item.get("requires_cycle_overlap"):
                _verify_overlap_evidence(point_id, contribution, trace_events, test_id,
                                         required_events)
            observed_tests.add(selector)
        if strict:
            _require(checker_tests <= observed_tests,
                     f"{kind} {point_id} checker testcase mapping has no checked sample: "
                     f"{sorted(checker_tests - observed_tests)}")
        else:
            _require(bool(allowed_tests & observed_tests),
                     f"{kind} {point_id} testcase mapping does not match observed contributors")
        _require(observed_hits == evidence.get("hit_count"),
                 f"{kind} {point_id} hit count disagrees with testcase evidence")
        _check_monitor_conditions(item, monitor_contributions)


def _verify_source_snapshot(repo, source_sha, *, source_paths=SOURCE_PATHS):
    """Require tested source to match checkout while allowing report-only commits."""
    repo = str(repo)
    commit_check = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", f"{source_sha}^{{commit}}"],
        capture_output=True, text=True,
    )
    _require(commit_check.returncode == 0,
             "raw coverage source SHA is not a commit in this repository")
    head = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    ancestry = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", source_sha, head],
        capture_output=True, text=True,
    )
    _require(ancestry.returncode == 0,
             f"coverage source SHA {source_sha} is not an ancestor of checkout HEAD {head}")
    changed = subprocess.run(
        ["git", "-C", repo, "diff", "--name-only", source_sha, "--",
         *source_paths], check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    _require(not changed,
             "tested source differs from current checkout: " + ", ".join(changed[:12]))
    untracked = subprocess.run(
        ["git", "-C", repo, "ls-files", "--others", "--exclude-standard"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    source_untracked = [path for path in untracked
                        if any(path == prefix or path.startswith(prefix + "/")
                               for prefix in source_paths)]
    _require(not source_untracked,
             "untracked source files are not represented by coverage SHA: " +
             ", ".join(source_untracked[:12]))
    return head


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
    _verify_source_snapshot(repo, source_sha)

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
    trace = reports / "full_system_trace.jsonl"
    _require(trace.is_file(), "full-system trace is missing")
    trace_records = [json.loads(line) for line in trace.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    trace_runs = [record for record in trace_records
                  if record.get("record_type") == "run"]
    trace_events = [record for record in trace_records
                    if record.get("record_type") == "event"]
    _require(bool(trace_runs), "full-system trace contains no run headers")
    _verify_evidence(required_bins, closure.get("bin_evidence", []),
                     run_by_id, kind="bin", trace_events=trace_events)
    _verify_evidence(required_crosses, closure.get("cross_evidence", []),
                     run_by_id, kind="cross", trace_events=trace_events)
    credited_bins = {item["id"]: next(row["hit_count"] for row in
                                      closure["bin_evidence"]
                                      if row["id"] == item["id"])
                     for item in required_bins}
    credited_crosses = {item["id"]: next(row["hit_count"] for row in
                                         closure["cross_evidence"]
                                         if row["id"] == item["id"])
                        for item in required_crosses}
    _require(closure.get("required_bins") == credited_bins,
             "closure functional counts differ from checked mapped evidence")
    _require(closure.get("required_cross_bins") == credited_crosses,
             "closure cross counts differ from checked mapped evidence")

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
