"""SimpleBus command/response sequencing checks for CPU and coherence ports."""

from collections import deque

from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_PROBE, CMD_PROBEHIT, CMD_PROBEMISS, CMD_READ, CMD_READLST,
    CMD_WRITE, CMD_WRITERSP,
)


class CacheProtocolChecker:
    def __init__(self, channel="cpu"):
        self.channel = channel
        self.errors = []
        self.pending = deque()
        self.probe_pending = False
        self.probe_release_beats = 0
        self.checked_responses = 0

    def write(self, transaction):
        self.write_channel(self.channel, transaction)

    def write_channel(self, channel, transaction):
        if channel != self.channel:
            return
        if isinstance(transaction, SimpleBusRequest):
            self._request(transaction)
        elif isinstance(transaction, SimpleBusResponse):
            self._response(transaction)

    def _request(self, request):
        if self.channel == "coherence":
            if request.cmd != CMD_PROBE:
                self._fail(f"unsupported coherence request command 0x{request.cmd:x}")
            if self.probe_pending or self.probe_release_beats:
                self._fail("new probe issued before the previous probe response completed")
            self.probe_pending = True
            return
        if request.cmd == CMD_READ:
            expected = (CMD_READLST,)
        elif request.cmd == CMD_WRITE:
            expected = (CMD_WRITERSP,)
        else:
            self._fail(f"unsupported CPU request command 0x{request.cmd:x}")
            return
        self.pending.append({"request": request, "expected": expected, "index": 0})

    def _response(self, response):
        if self.channel == "coherence":
            self._coherence_response(response)
            return
        if not self.pending:
            self._fail(f"unexpected response command 0x{response.cmd:x}")
        item = self.pending[0]
        request = item["request"]
        expected = item["expected"][item["index"]]
        self.checked_responses += 1
        if response.cmd != expected:
            self._fail(
                f"addr=0x{request.addr:08x} cmd=0x{request.cmd:x}: expected response "
                f"0x{expected:x}, got 0x{response.cmd:x}"
            )
        item["index"] += 1
        if item["index"] == len(item["expected"]):
            self.pending.popleft()

    def _coherence_response(self, response):
        if self.probe_pending:
            self.probe_pending = False
            if response.cmd == CMD_PROBEHIT:
                self.probe_release_beats = 8
            elif response.cmd != CMD_PROBEMISS:
                self._fail(f"probe must start with PROBEHIT/PROBEMISS, got 0x{response.cmd:x}")
            self.checked_responses += 1
            return
        if self.probe_release_beats:
            index = 8 - self.probe_release_beats
            expected = CMD_READLST if index == 7 else CMD_READ
            if response.cmd != expected:
                self._fail(
                    f"probe release beat {index}: expected command 0x{expected:x}, got 0x{response.cmd:x}"
                )
            self.probe_release_beats -= 1
            self.checked_responses += 1
            return
        self._fail(f"unsolicited coherence response command 0x{response.cmd:x}")

    def on_reset(self):
        self.pending.clear()
        self.probe_pending = False
        self.probe_release_beats = 0

    def _fail(self, message):
        self.errors.append(message)
        raise AssertionError(f"{self.channel} protocol: {message}")

    def assert_clean(self):
        assert not self.errors, f"{self.channel} protocol errors: {self.errors!r}"
        assert not self.pending, f"{self.channel} has {len(self.pending)} unpaired request(s)"
        assert not self.probe_pending and not self.probe_release_beats, (
            f"{self.channel} has an incomplete coherence probe response"
        )
