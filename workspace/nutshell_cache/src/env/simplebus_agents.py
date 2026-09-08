from toffee import *
from .bundle import *
from utils.cmd_code import *
from utils.common import *
import queue

class SimpleBusMasterAgent(Agent):
    def __init__(self, bundle: SimpleBusBundle):
        super().__init__(bundle.step)
        self.bundle:SimpleBusBundle = bundle

        # Test knob for holding the upstream response channel not-ready.
        self.response_ready_delay = 0

        self.req_que = queue.Queue()
        self.rsp_que = queue.Queue()

    async def send_req(self, addr, size, cmd, wmask=0, wdata=0):
        await AllValid(self.bundle.req.ready, delay=0)
        self.bundle.req.assign({
            "valid": 1,   "addr": addr,   "size": size,  "cmd": cmd,
            "wmask": wmask, "wdata": wdata
        })
        await self.bundle.step()
        self.bundle.req.valid.value = 0

    async def get_resp(self):
        for _ in range(self.response_ready_delay):
            await self.bundle.step()
        self.bundle.rsp.ready.value = 1
        await AllValid(self.bundle.rsp.valid)
        resp = self.bundle.rsp.as_dict()
        self.bundle.rsp.ready.value = 0
        return resp

    async def read(self, addr, size):
        await self.send_req(addr, size, CMD_READ)

    async def write(self, addr, size, wdata, wmask):
        await self.send_req(addr, size, CMD_WRITE, wmask, wdata)

    async def req_handler(self):
        while True:
            if self.req_que.empty():
                await self.bundle.step()
            else:
                req: ReqMsg = self.req_que.get()
                if req.cmd == CMD_READ:
                    await self.send_req(req.addr, req.size, CMD_READ)
                elif req.cmd == CMD_WRITE:
                    await self.send_req(req.addr, req.size, CMD_WRITE, req.mask, req.data)

    async def rsp_handler(self):
        while True:
            res = await self.get_resp()
            rsp = RespMsg(rdata=res["rdata"], cmd=res["cmd"])
            self.rsp_que.put(rsp)

    @driver_method()
    async def non_block_read(self, addr):
        self.req_que.put_nowait(ReqMsg(addr, CMD_READ))

    @driver_method()
    async def non_block_write(self, addr, data, mask):
        self.req_que.put_nowait(
            ReqMsg(addr, CMD_WRITE, mask=mask, data=data)
        )

    @driver_method()
    async def recv(self):
        while self.rsp_que.empty():
            await self.bundle.step()
        return self.rsp_que.get().as_dict()
    
    async def block_read(self, addr):
        await self.non_block_read(addr)
        res = await self.recv()
        return res
    
    async def block_write(self, addr, data, mask):
        await self.non_block_write(addr, data, mask)
        res = await self.recv()
        return res

    async def probe(self, addr, size=7):
        """Issue a coherence probe and drain a possible line release."""
        await self.send_req(addr, size, CMD_PROBE)
        self.bundle.rsp.ready.value = 1
        await AllValid(self.bundle.rsp.valid)
        first = self.bundle.rsp.as_dict()

        release = []
        if first["cmd"] == CMD_PROBEHIT:
            while True:
                await AllValid(self.bundle.rsp.valid)
                beat = self.bundle.rsp.as_dict()
                release.append(beat)
                if beat["cmd"] == CMD_READLST:
                    break

        self.bundle.rsp.ready.value = 0
        return first, release


class SimpleBusSlaveAgent(Agent):
    def __init__(self, bundle: SimpleBusBundle):
        super().__init__(bundle.step)
        self.bundle: SimpleBusBundle = bundle

        # Latency knobs for request backpressure and fragmented responses.
        self.request_ready_delay = 0
        self.response_valid_delay = 0
        self.response_beat_delay = 0
        # Optional one-shot gap in a burst response.  This models a memory
        # controller pausing between beats and then resuming the same burst.
        self.response_stall_after = None
        self.response_stall_cycles = 0

    async def _delay(self, cycles):
        for _ in range(cycles):
            await self.bundle.step()

    @driver_method()
    async def read_resp(self, size, rdata: list):
        assert len(rdata) == 1 << size
        for i in range(1 << size):
            self.bundle.rsp.valid.value = 0
            await self._delay(self.response_valid_delay)
            await AllValid(self.bundle.rsp.ready, delay=0)
            self.bundle.rsp.cmd.value = CMD_READLST if (i == ((1 << size) - 1)) else CMD_READ
            self.bundle.rsp.rdata.value = rdata[i]
            self.bundle.rsp.valid.value = 1
            await self.bundle.step()
            self.bundle.rsp.valid.value = 0
            await self._delay(self.response_beat_delay)
            if (
                self.response_stall_after is not None
                and i == self.response_stall_after
            ):
                await self._delay(self.response_stall_cycles)

    @driver_method()
    async def write_resp(self):
        await self._delay(self.response_valid_delay)
        await AllValid(self.bundle.rsp.ready, delay=0)
        self.bundle.rsp.assign({"valid": 1, "cmd": CMD_WRITERSP})
        await self.bundle.step()
        self.bundle.rsp.valid.value = 0

    @driver_method()
    async def get_req(self):
        await self._delay(self.request_ready_delay)
        self.bundle.req.ready.value = 1
        await AllValid(self.bundle.req.valid)
        req = self.bundle.req.as_dict()
        self.bundle.req.ready.value = 0
        return req
