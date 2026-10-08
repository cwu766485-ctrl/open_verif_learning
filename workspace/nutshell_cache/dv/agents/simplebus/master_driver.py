"""SimpleBus master driver: transport only, with a response queue."""
import queue
from toffee import Agent, driver_method
from dv.protocol.simplebus.bundle import SimpleBusBundle
from dv.common.utils.cmd_code import *
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.checkers.ready_valid_checker import ReadyValidChecker

class MasterDriver(Agent):
    def __init__(self, bundle: SimpleBusBundle, monitor=None):
        super().__init__(bundle.step)
        self.bundle = bundle; self.monitor = monitor
        self.protocol_checker = ReadyValidChecker("simplebus-master")
        self.response_ready_delay = 0
        self.req_que, self.rsp_que = queue.Queue(), queue.Queue()

    async def send_req(self, addr, size, cmd, wmask=0, wdata=0):
        txn = SimpleBusRequest(addr, size, cmd, wmask, wdata)
        self.bundle.req.assign({"valid": 1, "addr": addr, "size": size,
                                "cmd": cmd, "wmask": wmask, "wdata": wdata})
        for _ in range(10000):
            await self.bundle.step()
            payload = tuple(int(getattr(self.bundle.req, pin).value)
                            for pin in ("addr", "size", "cmd", "wmask", "wdata"))
            self.protocol_checker.observe(
                "req", self.bundle.req.valid.value, self.bundle.req.ready.value, payload
            )
            if int(self.bundle.req.ready.value):
                break
        else:
            self.bundle.req.valid.value = 0
            raise TimeoutError("timeout waiting for request handshake")
        self.bundle.req.valid.value = 0
        if self.monitor: self.monitor.publish(txn)

    async def get_resp(self, response_ready_delay=None):
        self.bundle.rsp.ready.value = 0
        delay = self.response_ready_delay if response_ready_delay is None else response_ready_delay
        for _ in range(delay):
            await self.bundle.step()
            payload = tuple(int(getattr(self.bundle.rsp, pin).value) for pin in ("cmd", "rdata"))
            self.protocol_checker.observe(
                "rsp", self.bundle.rsp.valid.value, self.bundle.rsp.ready.value, payload
            )
        self.bundle.rsp.ready.value = 1
        # Keep ready asserted through a clock edge.  Observing valid and
        # immediately deasserting ready would not constitute a handshake.
        for _ in range(10000):
            await self.bundle.step()
            payload = tuple(int(getattr(self.bundle.rsp, pin).value) for pin in ("cmd", "rdata"))
            self.protocol_checker.observe(
                "rsp", self.bundle.rsp.valid.value, self.bundle.rsp.ready.value, payload
            )
            if int(self.bundle.rsp.valid.value):
                raw = self.bundle.rsp.as_dict()
                # Keep the established CPU-driver dictionary shape; user is
                # optional on this integration and the cache returns zero.
                raw.pop("bits_user", None)
                break
        else:
            raise TimeoutError("timeout waiting for CPU response valid")
        self.bundle.rsp.ready.value = 0
        if self.monitor: self.monitor.publish(SimpleBusResponse(raw["cmd"], raw["rdata"]))
        return raw

    async def req_handler(self):
        while True:
            if self.req_que.empty(): await self.bundle.step()
            else:
                req = self.req_que.get()
                await self.send_req(req.addr, req.size, req.cmd, req.mask, req.data)

    async def rsp_handler(self):
        while True:
            raw = await self.get_resp()
            self.rsp_que.put(SimpleBusResponse(raw["cmd"], raw["rdata"]))

    @driver_method()
    async def non_block_read(self, addr):
        self.req_que.put_nowait(SimpleBusRequest(addr, 7, CMD_READ))

    @driver_method()
    async def non_block_write(self, addr, data, mask):
        self.req_que.put_nowait(SimpleBusRequest(addr, 7, CMD_WRITE, mask, data))

    @driver_method()
    async def non_block_request(self, addr, size, cmd, wmask=0, wdata=0):
        """Queue a generic SimpleBus request for burst and directed tests."""
        self.req_que.put_nowait(SimpleBusRequest(addr, size, cmd, wmask, wdata))

    @driver_method()
    async def recv(self):
        for _ in range(10000):
            if not self.rsp_que.empty():
                return self.rsp_que.get().as_dict()
            await self.bundle.step()
        raise TimeoutError("timeout waiting for CPU response queue")

    async def block_read(self, addr):
        await self.non_block_read(addr); return await self.recv()

    async def block_write(self, addr, data, mask):
        await self.non_block_write(addr, data, mask); return await self.recv()

    async def probe(self, addr, size=7):
        await self.send_req(addr, size, CMD_PROBE)
        self.bundle.rsp.ready.value = 0
        for _ in range(self.response_ready_delay):
            await self.bundle.step()
            payload = tuple(int(getattr(self.bundle.rsp, pin).value) for pin in ("cmd", "rdata"))
            self.protocol_checker.observe(
                "rsp", self.bundle.rsp.valid.value, self.bundle.rsp.ready.value, payload
            )
        self.bundle.rsp.ready.value = 1
        first = await self._get_probe_beat(); release = []
        if self.monitor:
            self.monitor.publish(SimpleBusResponse(first["cmd"], first["rdata"]))
        if first["cmd"] == CMD_PROBEHIT:
            while True:
                beat = await self._get_probe_beat(); release.append(beat)
                if self.monitor:
                    self.monitor.publish(SimpleBusResponse(beat["cmd"], beat["rdata"]))
                if beat["cmd"] == CMD_READLST: break
        self.bundle.rsp.ready.value = 0
        return first, release

    async def _get_probe_beat(self):
        for _ in range(10000):
            await self.bundle.step()
            payload = tuple(int(getattr(self.bundle.rsp, pin).value) for pin in ("cmd", "rdata"))
            self.protocol_checker.observe(
                "rsp", self.bundle.rsp.valid.value, self.bundle.rsp.ready.value, payload
            )
            if int(self.bundle.rsp.valid.value):
                return self.bundle.rsp.as_dict()
        raise TimeoutError("timeout waiting for coherence response valid")

SimpleBusMasterAgent = MasterDriver
