"""Synthetic monitor-data mutations for MSHR lifecycle checker sensitivity."""

from copy import deepcopy

import pytest

from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker


LINE = 0x0240_1000
WORD = 0xA55A_1234_9876_FEDC
CORE = 1


def valid_events():
    events = [
        {"source": "mshr", "event_type": "allocate", "cycle": 1,
         "slot": 0, "address": LINE, "reset_epoch": 0},
        {"source": "directory", "event_type": "request_accept", "cycle": 2,
         "address": LINE, "source_id": CORE, "txn_id": 3, "reset_epoch": 0},
        {"source": "axi", "event_type": "read_address", "cycle": 3,
         "txn_id": 0, "address": LINE, "reset_epoch": 0},
    ]
    for beat in range(8):
        events.append({
            "source": "axi", "event_type": "read_beat", "cycle": 4 + beat,
            "txn_id": 0, "address": LINE + beat * 8, "beat": beat,
            "data": WORD if beat == 0 else beat,
            "last": beat == 7, "response": 0,
            "reset_epoch": 0,
        })
        events.append({
            "source": "l2", "event_type": "line_write_beat", "cycle": 5 + beat,
            "address": LINE + beat * 8, "beat": beat,
            "owner_snoop_data": 0,
            "reset_epoch": 0,
        })
    events.extend([
        {"source": "directory", "event_type": "grant_accept", "cycle": 14,
         "address": LINE, "destination": CORE, "txn_id": 3, "reset_epoch": 0},
        {"source": "cpu", "event_type": "response_complete", "cycle": 15,
         "address": LINE, "data": WORD, "core": CORE, "txn_id": 2,
         "reset_epoch": 0},
        {"source": "mshr", "event_type": "retire", "cycle": 16,
         "slot": 0, "address": LINE, "reset_epoch": 0},
    ])
    return events


def check(events):
    return MshrLifecycleChecker.check(
        events, expected_lines={LINE}, expected_words={LINE: WORD},
        expected_cores={LINE: CORE},
    )


def test_valid_lifecycle_monitor_stream_passes():
    result = check(valid_events())
    assert result["mshr_allocations"] == 1
    assert result["mshr_retirements"] == 1
    assert result["axi_read_beats"] == result["l2_refill_beats"] == 8


@pytest.mark.parametrize("mutation", [
    "missing_r_beat",
    "bad_r_address",
    "bad_r_last",
    "r_error_response",
    "missing_l2_fill_beat",
    "duplicate_l2_fill_beat",
    "missing_directory_request",
    "duplicate_directory_request",
    "missing_grant",
    "grant_before_fill",
    "response_before_grant",
    "wrong_response_data",
    "wrong_response_core",
    "missing_mshr_retire",
    "wrong_axi_id",
    "wrong_r_epoch",
    "wrong_grant_epoch",
    "ar_before_allocation",
    "duplicate_allocation",
    "wrong_l2_fill_address",
    "wrong_grant_txn_id",
    "wrong_directory_requester",
    "wrong_grant_destination",
])
def test_checker_rejects_corrupted_lifecycle_evidence(mutation):
    events = deepcopy(valid_events())
    if mutation == "missing_r_beat":
        events = [event for event in events if not (
            event["source"] == "axi" and event["event_type"] == "read_beat" and
            event["beat"] == 4
        )]
    elif mutation == "bad_r_address":
        next(event for event in events if event["source"] == "axi" and
             event["event_type"] == "read_beat" and event["beat"] == 3)[
                 "address"] += 8
    elif mutation == "bad_r_last":
        next(event for event in events if event["source"] == "axi" and
             event["event_type"] == "read_beat" and event["beat"] == 7)[
                 "last"] = False
    elif mutation == "r_error_response":
        next(event for event in events if event["source"] == "axi" and
             event["event_type"] == "read_beat" and event["beat"] == 2)[
                 "response"] = 2
    elif mutation == "missing_l2_fill_beat":
        events = [event for event in events if not (
            event["source"] == "l2" and event["event_type"] == "line_write_beat" and
            event["beat"] == 5
        )]
    elif mutation == "duplicate_l2_fill_beat":
        duplicate = deepcopy(next(event for event in events if
                                  event["source"] == "l2" and
                                  event["event_type"] == "line_write_beat" and
                                  event["beat"] == 5))
        events.append(duplicate)
    elif mutation == "missing_directory_request":
        events = [event for event in events if not (
            event["source"] == "directory" and event["event_type"] == "request_accept"
        )]
    elif mutation == "duplicate_directory_request":
        duplicate = deepcopy(next(event for event in events if
                                  event["source"] == "directory" and
                                  event["event_type"] == "request_accept"))
        events.append(duplicate)
    elif mutation == "missing_grant":
        events = [event for event in events if not (
            event["source"] == "directory" and event["event_type"] == "grant_accept"
        )]
    elif mutation == "grant_before_fill":
        next(event for event in events if event["source"] == "directory" and
             event["event_type"] == "grant_accept")["cycle"] = 8
    elif mutation == "response_before_grant":
        next(event for event in events if event["source"] == "cpu" and
             event["event_type"] == "response_complete")["cycle"] = 10
    elif mutation == "wrong_response_data":
        next(event for event in events if event["source"] == "cpu" and
             event["event_type"] == "response_complete")["data"] ^= 1
    elif mutation == "wrong_response_core":
        next(event for event in events if event["source"] == "cpu" and
             event["event_type"] == "response_complete")["core"] = 0
    elif mutation == "missing_mshr_retire":
        events = [event for event in events if not (
            event["source"] == "mshr" and event["event_type"] == "retire"
        )]
    elif mutation == "wrong_axi_id":
        next(event for event in events if event["source"] == "axi" and
             event["event_type"] == "read_address")["txn_id"] = 1
    elif mutation == "wrong_r_epoch":
        next(event for event in events if event["source"] == "axi" and
             event["event_type"] == "read_beat" and event["beat"] == 3)[
                 "reset_epoch"] = 1
    elif mutation == "wrong_grant_epoch":
        next(event for event in events if event["source"] == "directory" and
             event["event_type"] == "grant_accept")["reset_epoch"] = 1
    elif mutation == "ar_before_allocation":
        next(event for event in events if event["source"] == "mshr" and
             event["event_type"] == "allocate")["cycle"] = 8
    elif mutation == "duplicate_allocation":
        duplicate = deepcopy(next(event for event in events if
                                  event["source"] == "mshr" and
                                  event["event_type"] == "allocate"))
        duplicate["cycle"] = 2
        events.append(duplicate)
    elif mutation == "wrong_l2_fill_address":
        next(event for event in events if event["source"] == "l2" and
             event["event_type"] == "line_write_beat" and event["beat"] == 4)[
                 "address"] += 64
    elif mutation == "wrong_grant_txn_id":
        next(event for event in events if event["source"] == "directory" and
             event["event_type"] == "grant_accept")["txn_id"] += 1
    elif mutation == "wrong_directory_requester":
        next(event for event in events if event["source"] == "directory" and
             event["event_type"] == "request_accept")["source_id"] = 0
    elif mutation == "wrong_grant_destination":
        next(event for event in events if event["source"] == "directory" and
             event["event_type"] == "grant_accept")["destination"] = 0
    else:  # pragma: no cover - guards additions to the parameter list
        raise AssertionError(f"unhandled mutation {mutation}")

    with pytest.raises(AssertionError):
        check(events)
