import pytest
import subprocess
from pathlib import Path

from dv.coverage.full_system_evidence_gate import (
    _verify_evidence,
    _verify_source_snapshot,
)
from dv.coverage.testcase_selector import testcase_selector
from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)


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


def _checked_cross_fixture():
    selector = "tests/full_system/test_cross.py::test_overlap"
    events = [
        {"source": "cpu", "event_type": "request_accept", "cycle": 10,
         "core": 0, "address": 0x100},
        {"source": "cpu", "event_type": "response_complete", "cycle": 30,
         "core": 0, "address": 0x100, "txn_id": 4},
        {"source": "directory", "event_type": "request_accept", "cycle": 11,
         "address": 0x100, "txn_id": 4},
        {"source": "axi", "event_type": "read_address", "cycle": 12,
         "address": 0x100, "txn_id": 7},
        {"source": "axi", "event_type": "read_beat", "cycle": 20,
         "address": 0x138, "txn_id": 7, "beat": 7, "last": 1},
        {"source": "snoop", "event_type": "accept", "cycle": 14,
         "core": 0, "address": 0x200, "txn_id": 2},
        {"source": "snoop", "event_type": "response", "cycle": 18,
         "core": 0, "txn_id": 2},
        {"source": "coherence", "event_type": "owner_data_beat", "cycle": 16,
         "core": 0, "address": 0x200, "beat": 7, "last": 1},
        {"source": "l1", "event_type": "metadata_commit", "cycle": 17,
         "core": 0, "address": 0x200, "old_state": 3, "new_state": 1},
        {"source": "directory", "event_type": "metadata_commit", "cycle": 19,
         "address": 0x200, "state": 1, "sharers": 3},
    ]
    names = [
        "cpu.request_accept", "cpu.response_complete",
        "directory.request_accept", "axi.read_address", "axi.read_beat",
        "snoop.accept", "snoop.response", "coherence.owner_data_beat",
        "l1.metadata_commit", "directory.metadata_commit",
    ]
    def role_for(event):
        if event["source"] == "axi":
            return "refill"
        if event["source"] == "snoop":
            return "snoop"
        if event["source"] in ("coherence", "l1") or (
                event["source"] == "directory" and
                event["event_type"] == "metadata_commit"):
            return "snoop"
        return "pending_miss"

    refs = [event_reference(f"ref{i}", role_for(event), event)
            for i, event in enumerate(events)]
    ref_by_event = {(event["source"], event["event_type"], event["cycle"]): ref
                    for event, ref in zip(events, refs)}
    proof = checked_overlap_proof(
        checker="independent scoreboard and protocol checker",
        checker_pass=True,
        role_endpoints={
            "pending_miss": (
                ref_by_event[("cpu", "request_accept", 10)]["ref_id"],
                ref_by_event[("cpu", "response_complete", 30)]["ref_id"],
            ),
            "refill": (
                ref_by_event[("axi", "read_address", 12)]["ref_id"],
                ref_by_event[("axi", "read_beat", 20)]["ref_id"],
            ),
            "snoop": (
                ref_by_event[("snoop", "accept", 14)]["ref_id"],
                ref_by_event[("snoop", "response", 18)]["ref_id"],
            ),
        },
        event_refs=refs,
        transactions=[
            {"protocol": "CPU", "txn_id": 4, "address": 0x100,
             "event_ref_ids": ["ref0", "ref1"]},
            {"protocol": "AXI4-R", "txn_id": 7, "address": 0x100,
             "event_ref_ids": ["ref3", "ref4"]},
            {"protocol": "Snoop", "txn_id": 2, "address": 0x200,
             "event_ref_ids": ["ref5", "ref6"]},
        ],
        state_transitions=[
            {"event_ref_id": "ref8", "old_state": 3, "new_state": 1},
            {"event_ref_id": "ref9", "state": 1, "sharers": 3},
        ],
    )
    point = {
        "id": "FS.CROSS.STRICT",
        "evidence_contract": "checked_cross_v1",
        "checker": "independent scoreboard and protocol checker",
        "testcases": [selector], "checker_testcases": [selector],
        "required_monitor_event": "CPU/Directory/Snoop/AXI events",
        "required_monitor_events": names,
        "requires_cycle_overlap": True,
    }
    contribution = {
        "test_id": selector, "count": 1, "test_status": "passed",
        "sample_testcases": [selector],
        "monitor": {"event_counts": {
            ".".join(name.split(".")): 1 for name in names
        }},
        "checked_cross_evidence": [proof],
    }
    closure_record = {
        "id": point["id"], "evidence_contract": point["evidence_contract"],
        "checker": point["checker"], "testcases": [selector],
        "checker_testcases": [selector],
        "required_monitor_events": names, "requires_cycle_overlap": True,
        "pass": True, "hit_count": 1, "evidence": [contribution],
    }
    trace = [{**event, "test_id": selector} for event in events]
    return point, closure_record, {selector: {"test_status": "passed"}}, trace


def test_checked_cross_requires_real_trace_bound_overlap_and_transactions():
    point, record, runs, trace = _checked_cross_fixture()
    _verify_evidence([point], [record], runs, kind="cross", trace_events=trace)


@pytest.mark.parametrize("mutation, message", [
    ("missing_event", "omits required event references"),
    ("wrong_cycle", "roles do not share a checked cycle window"),
    ("wrong_testcase", "outside its checker testcase mapping"),
    ("checker_failed", "no passing named overlap checker"),
])
def test_checked_cross_negative_evidence_is_rejected(mutation, message):
    point, record, runs, trace = _checked_cross_fixture()
    contribution = record["evidence"][0]
    proof = contribution["checked_cross_evidence"][0]
    if mutation == "missing_event":
        proof["event_refs"] = [
            ref for ref in proof["event_refs"]
            if not (ref["source"] == "axi" and ref["event_type"] == "read_beat")
        ]
    elif mutation == "wrong_cycle":
        proof["overlap"]["start_cycle"] += 1
    elif mutation == "wrong_testcase":
        contribution["test_id"] = "tests/full_system/test_wrong.py::test_overlap"
        contribution["sample_testcases"] = [contribution["test_id"]]
        runs[contribution["test_id"]] = {"test_status": "passed"}
    else:
        proof["checker_pass"] = False

    with pytest.raises(ValueError, match=message):
        _verify_evidence([point], [record], runs, kind="cross", trace_events=trace)


def test_source_snapshot_ignores_review_ledger_but_rejects_rtl_changes(tmp_path):
    repo = tmp_path / "repo"
    ledger = repo / "workspace/nutshell_cache/dv/coverage/rtl_release_decisions.json"
    rtl = repo / "workspace/nutshell_cache/rtl/Block.sv"
    ledger.parent.mkdir(parents=True)
    rtl.parent.mkdir(parents=True)
    ledger.write_text("{}\n", encoding="utf-8")
    rtl.write_text("module Block; endmodule\n", encoding="utf-8")

    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "coverage-gate-test@example.invalid")
    git("config", "user.name", "Coverage Gate Test")
    git("add", ".")
    git("commit", "-qm", "source snapshot")
    source_sha = git("rev-parse", "HEAD").stdout.strip()

    ledger.write_text('{"reviewed": true}\n', encoding="utf-8")
    _verify_source_snapshot(
        repo, source_sha,
        source_paths=("workspace/nutshell_cache/dv", "workspace/nutshell_cache/rtl"),
    )

    rtl.write_text("module Block; wire changed; endmodule\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tested source differs"):
        _verify_source_snapshot(
            repo, source_sha,
            source_paths=("workspace/nutshell_cache/dv", "workspace/nutshell_cache/rtl"),
        )
