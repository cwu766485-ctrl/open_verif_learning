"""Writable, ID-aware 64-byte backing memory for the custom line interface.

The DUT boundary here is a line-oriented adapter protocol, not AXI's five
channels. The model preserves line contents across refills/writebacks and can
delay independent read and write responses for benchmark sweeps.
"""

from collections import deque

from toffee import ClockCycles


class LineMemoryAxiAgent:
    BEATS_PER_LINE = 8
    WORD_MASK = (1 << 64) - 1

    def __init__(self, dut, response_delay: int = 2):
        if response_delay < 0:
            raise ValueError("response_delay must be non-negative")
        self.dut = dut
        self.response_delay = response_delay
        self.read_requests = []
        self.write_requests = []
        self.write_responses = []
        self.read_beats = 0
        self.write_beats = 0
        self.lines = {}
        self.cycle = 0

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
        rr = 0

        while True:
            self.cycle += 1

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

            ready_reads = [i for i, item in enumerate(reads)
                           if item[0] <= self.cycle]
            selected_read = None
            if ready_reads:
                selected_idx = ready_reads[rr % len(ready_reads)]
                selected_read = reads[selected_idx]
                rr = (rr + 1) % max(1, len(ready_reads))
                _, line_addr, txn_id, beat = selected_read
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

            if selected_read is not None and int(d.mem_rd_data_ready.value):
                self.read_beats += 1
                idx = reads.index(selected_read)
                due, addr, txn_id, beat = reads[idx]
                if beat == self.BEATS_PER_LINE - 1:
                    del reads[idx]
                else:
                    reads[idx] = (due, addr, txn_id, beat + 1)

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
