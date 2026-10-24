import pytest

from dv.checkers.dut_properties import CacheDutProperties
from dv.checkers.ready_valid_checker import ReadyValidChecker
from dv.common.transaction import SimpleBusRequest
from dv.common.utils.cmd_code import CMD_READ
from dv.models.reference import SetAssociativeTagModel


def _observe(props, **overrides):
    values = dict(
        reset=0,
        req_valid=0,
        req_ready=0,
        rsp_valid=0,
        rsp_ready=0,
        victim_mask_valid=0,
        victim_mask=0,
    )
    values.update(overrides)
    props.observe_cycle(**values)


def test_request_response_lifecycle_and_simultaneous_completion():
    props = CacheDutProperties()
    _observe(props, req_valid=1, req_ready=1)
    assert props.outstanding_cpu_requests == 1
    _observe(props, rsp_valid=1, rsp_ready=1)
    assert props.outstanding_cpu_requests == 0
    assert props.accepted_cpu_requests == props.completed_cpu_responses == 1


def test_unsolicited_or_duplicate_response_is_rejected():
    props = CacheDutProperties()
    with pytest.raises(AssertionError, match="without an outstanding request"):
        _observe(props, rsp_valid=1, rsp_ready=1)


def test_reset_cancels_old_request_but_no_response_may_escape_afterward():
    props = CacheDutProperties()
    _observe(props, req_valid=1, req_ready=1)
    _observe(props, reset=1)
    assert props.aborted_by_reset == 1
    assert props.outstanding_cpu_requests == 0
    with pytest.raises(AssertionError, match="without an outstanding request"):
        _observe(props, rsp_valid=1, rsp_ready=1)


def test_replacement_debug_mask_must_be_one_hot():
    props = CacheDutProperties()
    _observe(props, victim_mask_valid=1, victim_mask=0b0100)
    with pytest.raises(AssertionError, match="must be one-hot"):
        _observe(props, victim_mask_valid=1, victim_mask=0b0110)


def test_cache_access_observation_updates_exact_tag_way_state():
    tag_model = SetAssociativeTagModel()
    props = CacheDutProperties(tag_model=tag_model)
    request = SimpleBusRequest(addr=0x1A000, size=3, cmd=CMD_READ)

    # Empty set: RTL's invalid-first policy chooses the highest invalid way.
    props.observe_cache_access(
        valid=True,
        addr=request.addr,
        cmd=request.cmd,
        was_miss=True,
        waymask=0b1000,
        lfsr_waymask=0b0010,
    )
    resident = next(iter(tag_model.candidate_states(0x1A000 >> 6 & 0x7F)))
    assert [(line.tag, line.way) for line in resident] == [(0x1A000 >> 13, 3)]

    # A repeated access must hit that exact way and retire the matching saved
    # pre-update prediction, not infer the result from memory traffic.
    props.observe_cache_access(
        valid=True,
        addr=request.addr,
        cmd=request.cmd,
        was_miss=False,
        waymask=0b1000,
        lfsr_waymask=0b0010,
    )
    first = tag_model.consume_access_prediction(request)
    second = tag_model.consume_access_prediction(request)
    assert (first.outcome, first.selected_way) == ("miss", 3)
    assert (second.outcome, second.selected_way) == ("hit", 3)
    assert tag_model.exact_way_updates == 2


def test_ready_valid_checker_requires_stable_payload_while_stalled():
    checker = ReadyValidChecker("test")
    checker.observe("req", valid=1, ready=0, payload=(0x1000, 0))
    checker.observe("req", valid=1, ready=0, payload=(0x1000, 0))
    with pytest.raises(AssertionError, match="changed while stalled"):
        checker.observe("req", valid=1, ready=0, payload=(0x2000, 0))
