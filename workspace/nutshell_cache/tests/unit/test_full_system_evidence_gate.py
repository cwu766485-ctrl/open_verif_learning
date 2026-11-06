import pytest

from dv.coverage.full_system_evidence_gate import _verify_evidence
from dv.coverage.testcase_selector import testcase_selector


def test_testcase_selector_preserves_module_and_removes_parameter():
    assert testcase_selector(
        "tests/full_system/test_axi.py::test_read[7]"
    ) == "tests/full_system/test_axi.py::test_read"


def test_required_bin_evidence_requires_matching_passed_test_and_monitor():
    plan = [{
        "id": "FS.TEST.BIN",
        "evidence_contract": "checked_cross_v1",
        "checker": "independent data checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "required_monitor_event": "cpu.request_accept",
        "required_monitor_events": ["cpu.request_accept"],
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "pass": True, "hit_count": 1,
        "checker": "independent data checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "required_monitor_events": ["cpu.request_accept"],
        "evidence": [{
            "test_id": "tests/full_system/test_example.py::test_checked_transaction[1]",
            "count": 1, "test_status": "passed",
            "sample_testcases": ["tests/full_system/test_example.py::test_checked_transaction[1]"],
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
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "checker": "independent checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "required_monitor_event": "cpu.request_accept",
        "required_monitor_events": ["cpu.request_accept"],
    }]
    contribution = {
        "test_id": "tests/full_system/test_example.py::test_checked_transaction", "count": 1,
        "test_status": "passed", "monitor": {"event_counts": {"cpu.request_accept": 1}},
        "sample_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
    }
    if change == "missing_checker":
        plan[0]["checker"] = ""
    elif change == "wrong_test":
        plan[0]["testcases"] = ["test_other"]
    else:
        contribution["monitor"] = {"event_counts": {}}
    evidence = [{"id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
                 "pass": True, "hit_count": 1,
                 "checker": "independent checker",
                 "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
                 "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
                 "required_monitor_events": ["cpu.request_accept"],
                 "evidence": [contribution]}]
    runs = {"tests/full_system/test_example.py::test_checked_transaction": {
        "test_status": "passed"
    }}
    with pytest.raises(ValueError):
        _verify_evidence(plan, evidence, runs, kind="bin")


def test_required_bin_evidence_rejects_missing_required_monitor_event():
    plan = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "checker": "independent checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "required_monitor_event": "cpu.request_accept and cpu.response_complete",
        "required_monitor_events": ["cpu.request_accept", "cpu.response_complete"],
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "pass": True, "hit_count": 1,
        "checker": "independent checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "required_monitor_events": ["cpu.request_accept", "cpu.response_complete"],
        "evidence": [{
            "test_id": "tests/full_system/test_example.py::test_checked_transaction", "count": 1,
            "test_status": "passed",
            "sample_testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
            "monitor": {"event_counts": {"cpu.request_accept": 1}},
        }],
    }]
    with pytest.raises(ValueError, match="missing required Monitor events"):
        _verify_evidence(plan, evidence,
                         {"tests/full_system/test_example.py::test_checked_transaction": {
                             "test_status": "passed"
                         }},
                         kind="bin")


def test_required_bin_evidence_rejects_misassigned_checker_testcase():
    plan = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "checker": "independent checker",
        "testcases": ["tests/full_system/test_example.py::test_checked_transaction"],
        "checker_testcases": ["tests/full_system/test_wrong.py::test_wrong_checker"],
        "required_monitor_event": "cpu.request_accept",
        "required_monitor_events": ["cpu.request_accept"],
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "pass": True, "hit_count": 1,
        "checker": "independent checker",
        "testcases": plan[0]["testcases"],
        "checker_testcases": plan[0]["checker_testcases"],
        "required_monitor_events": ["cpu.request_accept"],
        "evidence": [{
            "test_id": "tests/full_system/test_example.py::test_checked_transaction",
            "count": 1, "test_status": "passed",
            "sample_testcases": [
                "tests/full_system/test_example.py::test_checked_transaction"
            ],
            "monitor": {"event_counts": {"cpu.request_accept": 1}},
        }],
    }]
    with pytest.raises(ValueError, match="invalid checker-to-testcase mapping"):
        _verify_evidence(plan, evidence, {
            "tests/full_system/test_example.py::test_checked_transaction": {
                "test_status": "passed"
            }
        }, kind="bin")


def test_required_bin_evidence_rejects_sample_from_unmapped_test_module():
    selector = "tests/full_system/test_example.py::test_checked_transaction"
    other = "tests/full_system/test_other.py::test_checked_transaction"
    plan = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "checker": "independent checker",
        "testcases": [selector], "checker_testcases": [selector],
        "required_monitor_event": "CPU request and response",
        "required_monitor_events": ["cpu.request_accept"],
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "pass": True, "hit_count": 1,
        "checker": "independent checker", "testcases": [selector],
        "checker_testcases": [selector],
        "required_monitor_events": ["cpu.request_accept"],
        "evidence": [{
            "test_id": other, "count": 1, "test_status": "passed",
            "sample_testcases": [other],
            "monitor": {"event_counts": {"cpu.request_accept": 1}},
        }],
    }]
    with pytest.raises(ValueError, match="outside its checker testcase mapping"):
        _verify_evidence(plan, evidence, {
            other: {"test_status": "passed"}
        }, kind="bin")


def test_required_bin_evidence_rejects_missing_sample_attribution():
    selector = "tests/full_system/test_example.py::test_checked_transaction"
    plan = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "checker": "independent checker",
        "testcases": [selector], "checker_testcases": [selector],
        "required_monitor_event": "CPU request accepted",
        "required_monitor_events": ["cpu.request_accept"],
    }]
    evidence = [{
        "id": "FS.TEST.BIN", "evidence_contract": "checked_cross_v1",
        "pass": True, "hit_count": 1,
        "checker": "independent checker", "testcases": [selector],
        "checker_testcases": [selector],
        "required_monitor_events": ["cpu.request_accept"],
        "evidence": [{
            "test_id": selector, "count": 1, "test_status": "passed",
            "sample_testcases": [],
            "monitor": {"event_counts": {"cpu.request_accept": 1}},
        }],
    }]
    with pytest.raises(ValueError, match="exact runtime sample attribution"):
        _verify_evidence(plan, evidence, {
            selector: {"test_status": "passed"}
        }, kind="bin")
