"""Inject representative verification faults and record the catching checker."""

import json
from pathlib import Path

from dv.checkers.cache_protocol_checker import CacheProtocolChecker
from dv.checkers.ready_valid_checker import ReadyValidChecker
from dv.checkers.transaction_lifecycle_checker import TransactionLifecycleChecker
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_READ, CMD_READLST, CMD_WRITE, CMD_WRITEBST, CMD_WRITELST,
)
from dv.models.reference import CacheReferenceModel
from dv.scoreboard.cache_scoreboard import CacheScoreboard
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard
from dv.monitors.snoop_data_monitor import SnoopDataMonitor


def _request(addr, cmd=CMD_READ):
    return SimpleBusRequest(addr=addr, size=3, cmd=cmd, wmask=0xFF)


def _expect_caught(name, checker, expected_text, inject):
    try:
        inject()
    except AssertionError as exc:
        message = str(exc)
        if expected_text not in message:
            raise AssertionError(
                f"{checker} caught {name}, but diagnostic did not contain "
                f"{expected_text!r}: {message}"
            ) from exc
        return {
            "fault": name,
            "checker": checker,
            "caught": True,
            "diagnostic": message,
        }
    raise AssertionError(f"{checker} failed to catch injected {name}")


def _inject_false_hit():
    scoreboard = CacheScoreboard()
    scoreboard._check_cache_outcome({
        "request": _request(0x1000),
        "cache_miss": False,
        "memory_requests": [],
    })


def _inject_corrupt_writeback_beat():
    reference = CacheReferenceModel()
    scoreboard = CacheScoreboard(reference)
    addresses = [0x3000 + way * 0x2000 for way in range(5)]
    for way, addr in enumerate(addresses[:4]):
        line = addr & ~0x3F
        for beat in range(8):
            reference.data[line + beat * 8] = (way << 32) | beat
        reference.cache_tags.observe_access(_request(addr, CMD_WRITE), was_miss=True)

    request = _request(addresses[4])
    prediction = reference.cache_tags.predict_access(request, was_miss=True)
    victim = min(prediction.dirty_victims)
    requests = [
        {
            "addr": victim,
            "cmd": CMD_WRITELST if beat == 7 else CMD_WRITEBST,
            "wmask": 0xFF,
            "wdata": reference.data[victim + beat * 8],
        }
        for beat in range(8)
    ]
    requests[3]["wdata"] ^= 1
    scoreboard._check_dirty_writeback(
        {"request": request, "memory_requests": requests}, prediction
    )


def _inject_dropped_stalled_response():
    checker = ReadyValidChecker("fault-injection")
    checker.observe("rsp", valid=1, ready=0, payload=(CMD_READLST, 0xA5))
    checker.observe("rsp", valid=0, ready=0, payload=(CMD_READLST, 0xA5))


def _inject_duplicate_response():
    checker = CacheProtocolChecker("cpu")
    checker.write(_request(0x5000))
    response = SimpleBusResponse(cmd=CMD_READLST, rdata=0)
    checker.write(response)
    checker.write(response)


def _inject_mesi_double_owner():
    model = CoherenceScoreboard()
    line = 0x8000
    model.states[line] = ["M", "S"]
    model.directory[line] = model.directory_view(line)
    model._assert_line_invariants(line)


def _inject_wrong_grant_id():
    checker = TransactionLifecycleChecker("grant")
    checker.accept(3, 0x9000, "GetM")
    checker.complete(4, 0x9000, "GetM")


def _inject_corrupt_owner_data():
    monitor = object.__new__(SnoopDataMonitor)
    line = 0xA000
    monitor.beat_errors = []
    monitor.transfers = [{
        "core": 0, "line": line,
        "words": tuple(range(7)) + (0xBAD,),
    }]
    monitor.partial = {}
    monitor.assert_line_data(line, tuple(range(8)))


def _inject_wrong_directory_sharer():
    model = CoherenceScoreboard()
    line = 0xB000
    model.states[line] = ["S", "I"]
    model.directory[line] = model.directory_view(line)
    monitor = object.__new__(SnoopDataMonitor)
    monitor.directory_commits = [{
        "line": line, "state": 1, "owner": 0, "sharers": 0b10,
    }]
    monitor.assert_directory_matches(model, line)


def _inject_duplicate_grant():
    checker = TransactionLifecycleChecker("grant")
    checker.accept(7, 0xC000, "GetM")
    checker.complete(7, 0xC000, "GetM")
    checker.complete(7, 0xC000, "GetM")


def run_all(output_path="reports/checker_fault_injection.json"):
    records = [
        _expect_caught(
            "false hit for a tag absent from the Refm",
            "CacheScoreboard tag/hit-miss checker",
            "predicted miss",
            _inject_false_hit,
        ),
        _expect_caught(
            "corrupted data on writeback beat 3",
            "CacheScoreboard writeback data checker",
            "writeback beat 3",
            _inject_corrupt_writeback_beat,
        ),
        _expect_caught(
            "response valid dropped before a stalled handshake",
            "ReadyValidChecker response stability checker",
            "changed while stalled",
            _inject_dropped_stalled_response,
        ),
        _expect_caught(
            "duplicate CPU response after request retirement",
            "CacheProtocolChecker response sequencing checker",
            "unexpected response",
            _inject_duplicate_response,
        ),
        _expect_caught(
            "unnecessary invalidate leaves two exclusive MESI copies",
            "CoherenceScoreboard MESI invariant checker",
            "M coexists with another copy",
            _inject_mesi_double_owner,
        ),
        _expect_caught(
            "Grant response uses a different transaction ID",
            "TransactionLifecycleChecker ID/address/opcode matcher",
            "unknown or retired ID",
            _inject_wrong_grant_id,
        ),
        _expect_caught(
            "corrupted owner-data beat",
            "SnoopDataMonitor owner-data scoreboard",
            "expected",
            _inject_corrupt_owner_data,
        ),
        _expect_caught(
            "Directory retains the wrong sharer bit",
            "SnoopDataMonitor Directory/reference-state checker",
            "directory metadata mismatch",
            _inject_wrong_directory_sharer,
        ),
        _expect_caught(
            "duplicate Grant after transaction retirement",
            "TransactionLifecycleChecker exactly-once lifecycle checker",
            "unknown or retired ID",
            _inject_duplicate_grant,
        ),
    ]
    report = {"status": "PASS", "caught": len(records), "injections": records}
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main():
    report = run_all()
    print(f"Checker fault injections caught: {report['caught']}/{len(report['injections'])}")
    for record in report["injections"]:
        print(f"  PASS {record['fault']} -> {record['checker']}")


if __name__ == "__main__":
    main()
