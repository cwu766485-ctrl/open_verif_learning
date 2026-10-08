"""Inject representative verification faults and record the catching checker."""

import json
from pathlib import Path

from dv.checkers.cache_protocol_checker import CacheProtocolChecker
from dv.checkers.ready_valid_checker import ReadyValidChecker
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_READ, CMD_READLST, CMD_WRITE, CMD_WRITEBST, CMD_WRITELST,
)
from dv.models.reference import CacheReferenceModel
from dv.scoreboard.cache_scoreboard import CacheScoreboard


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
