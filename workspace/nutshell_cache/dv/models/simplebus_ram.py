from dv.common.utils.cmd_code import *
from dv.common.utils.common import replicate_bits

class SimpleBusRam:
    """Backing memory/MMIO model; only depends on the generic slave driver API."""
    def __init__(self, agent):
        self.data = {}; self.agent = agent
        self.requests = []; self.read_requests = []; self.write_requests = []

    async def rsp_write_burst(self, req):
        addr = req["addr"]
        while True:
            data, mask = req["wdata"], replicate_bits(req["wmask"], 8, 8)
            self.data[addr] = (self.data.get(addr, 0) & ~mask) | (data & mask)
            await self.agent.write_resp()
            if req["cmd"] == CMD_WRITELST: break
            req = await self.agent.get_req(); addr += 8

    async def rsp_once(self):
        req = await self.agent.get_req(); self.requests.append(dict(req))
        if req["cmd"] in (CMD_READBST, CMD_READ):
            self.read_requests.append(dict(req)); first = req["addr"] & 0xffffffc0
            index = (req["addr"] - first) >> 3; data = []
            for _ in range(1 << req["size"]):
                data.append(self.data.get(first + index * 8, 0)); index = (index + 1) % (1 << req["size"])
            await self.agent.read_resp(req["size"], data)
        elif req["cmd"] == CMD_WRITEBST:
            self.write_requests.append(dict(req)); await self.rsp_write_burst(req)
        elif req["cmd"] == CMD_WRITE:
            self.write_requests.append(dict(req)); addr = req["addr"] & ~7
            mask = replicate_bits(req["wmask"], 8, 8)
            self.data[addr] = (self.data.get(addr, 0) & ~mask) | (req["wdata"] & mask)
            await self.agent.write_resp()

    async def work(self):
        while True: await self.rsp_once()
