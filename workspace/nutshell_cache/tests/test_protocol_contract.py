"""CPU-port contract checks that do not require a simulator."""

import pytest

from dv.checkers.cache_protocol_checker import CacheProtocolChecker
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import CMD_READBST, CMD_READ, CMD_READLST


def test_l1_dcache_cpu_checker_rejects_read_burst_command():
    checker = CacheProtocolChecker("cpu")
    request = SimpleBusRequest(addr=0x1000, size=3, cmd=CMD_READBST)

    with pytest.raises(AssertionError, match="unsupported CPU request command"):
        checker.write(request)


def test_response_checker_catches_lost_and_duplicate_replies():
    checker = CacheProtocolChecker("cpu")
    checker.write(SimpleBusRequest(addr=0x1000, size=3, cmd=CMD_READ))
    with pytest.raises(AssertionError, match="unpaired request"):
        checker.assert_clean()

    checker.write(SimpleBusResponse(cmd=CMD_READLST, rdata=0))
    checker.assert_clean()
    with pytest.raises(AssertionError, match="unexpected response"):
        checker.write(SimpleBusResponse(cmd=CMD_READLST, rdata=0))


def test_protocol_reset_cancels_pending_request_and_rejects_stale_reply():
    checker = CacheProtocolChecker("cpu")
    checker.write(SimpleBusRequest(addr=0x1000, size=3, cmd=CMD_READ))
    checker.on_reset()
    checker.assert_clean()
    with pytest.raises(AssertionError, match="unexpected response"):
        checker.write(SimpleBusResponse(cmd=CMD_READLST, rdata=0))
