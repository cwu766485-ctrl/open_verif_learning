import pytest

from dv.coverage.full_system_evidence_gate import _test_name, _verify_evidence


def test_test_name_normalizes_pytest_nodeid_and_source_path():
    assert _test_name("tests/full_system/test_axi.py::test_read[7]") == "test_read"


def test_required_bin_evidence_requires_matching_passed_test_and_monitor():
    plan = [{
        "id": "FS.TEST.BIN",
        "checker": "independent data checker",
        "testcases": ["test_checked_transaction"],
        "required_monitor_event": "cpu.request_accept",
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "pass": True, "hit_count": 1,
        "evidence": [{
            "test_id": "tests/full_system/test_example.py::test_checked_transaction[1]",
            "count": 1, "test_status": "passed",
            "monitor": {"event_counts": {"cpu.request_accept": 1}},
        }],
    }]
    runs = {
        "tests/full_system/test_example.py::test_checked_transaction[1]": {
            "test_status": "passed"
        }
    }
    _verify_evidence(plan, evidence, runs, kind="bin")


@pytest.mark.parametrize("change", ["missing_checker", "wrong_test", "missing_monitor"])
def test_required_bin_evidence_rejects_incomplete_traceability(change):
    plan = [{
        "id": "FS.TEST.BIN", "checker": "independent checker",
        "testcases": ["test_checked_transaction"],
        "required_monitor_event": "cpu.request_accept",
    }]
    contribution = {
        "test_id": "test_checked_transaction", "count": 1,
        "test_status": "passed", "monitor": {"event_counts": {"cpu.request_accept": 1}},
    }
    if change == "missing_checker":
        plan[0]["checker"] = ""
    elif change == "wrong_test":
        plan[0]["testcases"] = ["test_other"]
    else:
        contribution["monitor"] = {"event_counts": {}}
    evidence = [{"id": "FS.TEST.BIN", "pass": True, "hit_count": 1,
                 "evidence": [contribution]}]
    runs = {"test_checked_transaction": {"test_status": "passed"}}
    with pytest.raises(ValueError):
        _verify_evidence(plan, evidence, runs, kind="bin")
