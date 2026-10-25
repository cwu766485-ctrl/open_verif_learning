"""Small deterministic 8-beat line memory agent for coherence smoke tests."""

from collections import deque

from toffee import ClockCycles


class LineMemoryAxiAgent:
    def __init__(self, dut, response_delay: int = 2):
        self.dut = dut
        self.response_delay = response_delay
        self.read_requests = []

    @staticmethod
    def word(addr: int, beat: int) -> int:
        line = addr & ~0x3F
        return (0xA5A5000000000000 ^ (line << 8) ^ beat) & ((1 << 64) - 1)

    async def run(self):
        d = self.dut
        d.mem_rd_req_ready.value = 1
        d.mem_rd_data_valid.value = 0
        d.mem_rd_data_error.value = 0
        d.mem_wr_req_ready.value = 1
        d.mem_wr_data_ready.value = 1
        d.mem_wr_rsp_valid.value = 0
        d.mem_wr_rsp_error.value = 0

        queued = deque()
        active = None
        beat = 0
        delay = 0
        while True:
            if active is None and queued:
                active = queued.popleft()
                beat = 0
                delay = self.response_delay

            d.mem_rd_data_valid.value = int(active is not None and delay == 0)
            if active is not None:
                addr, txn_id = active
                d.mem_rd_data_txn_id.value = txn_id
                d.mem_rd_data_beat_idx.value = beat
                d.mem_rd_data.value = self.word(addr, beat)
                d.mem_rd_data_last.value = int(beat == 7)
            else:
                d.mem_rd_data_last.value = 0

            await ClockCycles(d, 1)

            if int(d.mem_rd_req_valid.value) and int(d.mem_rd_req_ready.value):
                addr = int(d.mem_rd_req_addr.value)
                txn_id = int(d.mem_rd_req_txn_id.value)
                self.read_requests.append((addr, txn_id))
                queued.append((addr, txn_id))

            if active is not None:
                if delay:
                    delay -= 1
                elif int(d.mem_rd_data_ready.value):
                    if beat == 7:
                        active = None
                    else:
                        beat += 1
