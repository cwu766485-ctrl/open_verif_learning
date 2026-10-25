"""Writable, ID-aware 64-byte backing memory for the custom line interface.

The DUT boundary here is a line-oriented adapter protocol, not AXI's five
channels. The model preserves line contents across refills/writebacks and can
delay independent read and write responses, apply deterministic backpressure,
and cancel outstanding line transactions on the shared reset contract.
"""

from collections import Counter, deque

from toffee import ClockCycles


class LineMemoryAxiAgent:
    BEATS_PER_LINE = 8
    WORD_MASK = (1 << 64) - 1

    def __init__(self, dut, response_delay: int = 2, *,
                 backpressure_periods=None, response_gap_periods=None):
        if response_delay < 0:
            raise ValueError("response_delay must be non-negative")
        self.dut = dut
        self.response_delay = response_delay
        self.backpressure_periods = dict(backpressure_periods or {})
        self.response_gap_periods = dict(response_gap_periods or {})
        for channel, period in self.backpressure_periods.items():
            if channel not in {"read_req", "write_req", "write_data"}:
                raise ValueError(f"unsupported backpressure channel: {channel}")
            if period < 2:
                raise ValueError(f"{channel} stall period must be at least 2")
        for channel, period in self.response_gap_periods.items():
            if channel != "read_data" or period < 2:
                raise ValueError(f"unsupported response gap: {channel}={period}")
        self.read_requests = []
        self.read_completions = []
        self.write_requests = []
        self.write_responses = []
        self.read_beats = 0
        self.write_beats = 0
        self.lines = {}
        self.cycle = 0
        self.stalls = Counter()
        self.response_gaps = Counter()
        self.reset_cancelled = Counter()
        self._armed_stalls = {}

    def _ready(self, channel, valid):
        if channel in self._armed_stalls:
            if not valid:
                return 0
            remaining = self._armed_stalls[channel]
            if remaining > 0:
                self._armed_stalls[channel] = remaining - 1
                return 0
            del self._armed_stalls[channel]
            return 1
        period = self.backpressure_periods.get(channel, 0)
        return int(not period or self.cycle % period != 0)

    def arm_stall(self, channel, cycles=1):
        """Hold ready low until the next transfer has seen ``cycles`` stalls."""
        if channel not in {"read_req", "write_req", "write_data"}:
            raise ValueError(f"unsupported backpressure channel: {channel}")
        if cycles < 1:
            raise ValueError("an armed stall must contain at least one cycle")
        self._armed_stalls[channel] = cycles

    @classmethod
    def word(cls, addr: int, beat: int) -> int:
        line = addr & ~0x3F
        return (0xA5A5000000000000 ^ (line << 8) ^ beat) & cls.WORD_MASK

    def _read_word(self, line_addr: int, beat: int) -> int:
        line = self.lines.get(line_addr)
        return line[beat] if line is not None else self.word(line_addr, beat)

    async def run(self):
        d = self.dut
        d.mem_rd_req_ready.value = 1
        d.mem_rd_data_valid.value = 0
        d.mem_rd_data_error.value = 0
        d.mem_wr_req_ready.value = 1
        d.mem_wr_data_ready.value = 1
        d.mem_wr_rsp_valid.value = 0
        d.mem_wr_rsp_error.value = 0

        # A due-cycle queue plus round-robin beat service permits responses
        # from distinct read IDs to overlap and complete out of request order.
        reads = deque()
        writes = {}
        write_responses = deque()
        active_rsp = None
        active_read = None
        rr = 0

        while True:
            self.cycle += 1

            if int(d.reset.value):
                # This custom subsystem contract cancels accepted line work
                # when reset is asserted. Backing contents survive reset.
                self.reset_cancelled["reads"] += len(reads)
                self.reset_cancelled["writes"] += len(writes)
                self.reset_cancelled["write_responses"] += len(write_responses)
                self.reset_cancelled["write_responses"] += int(active_rsp is not None)
                reads.clear()
                writes.clear()
                write_responses.clear()
                active_rsp = None
                active_read = None
                self._armed_stalls.clear()
                d.mem_rd_req_ready.value = 0
                d.mem_rd_data_valid.value = 0
                d.mem_rd_data_last.value = 0
                d.mem_wr_req_ready.value = 0
                d.mem_wr_data_ready.value = 0
                d.mem_wr_rsp_valid.value = 0
                await ClockCycles(d, 1)
                continue

            d.mem_rd_req_ready.value = self._ready(
                "read_req", bool(int(d.mem_rd_req_valid.value)))
            d.mem_wr_req_ready.value = self._ready(
                "write_req", bool(int(d.mem_wr_req_valid.value)))
            d.mem_wr_data_ready.value = self._ready(
                "write_data", bool(int(d.mem_wr_data_valid.value)))

            if active_rsp is None:
                for idx, item in enumerate(write_responses):
                    if item[0] <= self.cycle:
                        active_rsp = write_responses[idx]
                        del write_responses[idx]
                        break
            if active_rsp is None:
                d.mem_wr_rsp_valid.value = 0
            else:
                _, rsp_id = active_rsp
                d.mem_wr_rsp_valid.value = 1
                d.mem_wr_rsp_txn_id.value = rsp_id

            ready_reads = [item for item in reads if item[0] <= self.cycle]
            if active_read is None and ready_reads:
                active_read = ready_reads[rr % len(ready_reads)]
                rr = (rr + 1) % max(1, len(ready_reads))
            send_read = active_read is not None
            gap_period = self.response_gap_periods.get("read_data", 0)
            if send_read and gap_period and self.cycle % gap_period == 0:
                send_read = False
                self.response_gaps["read_data"] += 1
            if send_read:
                _, line_addr, txn_id, beat = active_read
                d.mem_rd_data_valid.value = 1
                d.mem_rd_data_txn_id.value = txn_id
                d.mem_rd_data_beat_idx.value = beat
                d.mem_rd_data.value = self._read_word(line_addr, beat)
                d.mem_rd_data_last.value = int(beat == self.BEATS_PER_LINE - 1)
            else:
                d.mem_rd_data_valid.value = 0
                d.mem_rd_data_last.value = 0

            await ClockCycles(d, 1)

            if int(d.mem_rd_req_valid.value) and int(d.mem_rd_req_ready.value):
                addr = int(d.mem_rd_req_addr.value) & ~0x3F
                txn_id = int(d.mem_rd_req_txn_id.value)
                self.read_requests.append((addr, txn_id, self.cycle))
                reads.append((self.cycle + self.response_delay, addr, txn_id, 0))

            if (send_read and int(d.mem_rd_data_valid.value) and
                    int(d.mem_rd_data_ready.value)):
                self.read_beats += 1
                idx = reads.index(active_read)
                due, addr, txn_id, beat = reads[idx]
                if beat == self.BEATS_PER_LINE - 1:
                    self.read_completions.append((addr, txn_id, self.cycle))
                    del reads[idx]
                else:
                    reads[idx] = (due, addr, txn_id, beat + 1)
                active_read = None

            if int(d.mem_rd_req_valid.value) and not int(d.mem_rd_req_ready.value):
                self.stalls["read_req"] += 1
            if int(d.mem_wr_req_valid.value) and not int(d.mem_wr_req_ready.value):
                self.stalls["write_req"] += 1
            if int(d.mem_wr_data_valid.value) and not int(d.mem_wr_data_ready.value):
                self.stalls["write_data"] += 1
            if (int(d.mem_rd_data_valid.value) and
                    not int(d.mem_rd_data_ready.value)):
                self.stalls["read_data"] += 1
            if int(d.mem_wr_rsp_valid.value) and not int(d.mem_wr_rsp_ready.value):
                self.stalls["write_rsp"] += 1

            if int(d.mem_wr_req_valid.value) and int(d.mem_wr_req_ready.value):
                addr = int(d.mem_wr_req_addr.value) & ~0x3F
                txn_id = int(d.mem_wr_req_txn_id.value)
                if txn_id in writes:
                    raise AssertionError(f"write ID {txn_id} reused before last beat")
                writes[txn_id] = {"addr": addr, "beats": [], "due": None}
                self.write_requests.append((addr, txn_id, self.cycle))

            if int(d.mem_wr_data_valid.value) and int(d.mem_wr_data_ready.value):
                txn_id = int(d.mem_wr_data_txn_id.value)
                if txn_id not in writes:
                    raise AssertionError(f"write data for unknown ID {txn_id}")
                txn = writes[txn_id]
                beat = int(d.mem_wr_data_beat_idx.value)
                if beat != len(txn["beats"]):
                    raise AssertionError(
                        f"write ID {txn_id} beat order {beat}, expected {len(txn['beats'])}"
                    )
                txn["beats"].append(int(d.mem_wr_data.value) & self.WORD_MASK)
                self.write_beats += 1
                if int(d.mem_wr_data_last.value):
                    if len(txn["beats"]) != self.BEATS_PER_LINE:
                        raise AssertionError(
                            f"write ID {txn_id} ended after {len(txn['beats'])} beats"
                        )
                    self.lines[txn["addr"]] = list(txn["beats"])
                    txn["due"] = self.cycle + self.response_delay
                    write_responses.append((txn["due"], txn_id))
                    del writes[txn_id]

            if active_rsp is not None and int(d.mem_wr_rsp_ready.value):
                self.write_responses.append((active_rsp[1], self.cycle))
                active_rsp = None
