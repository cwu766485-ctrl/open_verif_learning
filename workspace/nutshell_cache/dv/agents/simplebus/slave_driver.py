"""SimpleBus slave driver: response generation and request collection."""
from toffee import Agent, AllValid, driver_method
from dv.protocol.simplebus.bundle import SimpleBusBundle
from dv.common.utils.cmd_code import *
from dv.checkers.ready_valid_checker import ReadyValidChecker

class SlaveDriver(Agent):
    def __init__(self, bundle: SimpleBusBundle, monitor=None):
        super().__init__(bundle.step); self.bundle = bundle; self.monitor = monitor
        self.protocol_checker = ReadyValidChecker("simplebus-slave")
        self.request_ready_delay = 0; self.response_valid_delay = 0
        self.response_beat_delay = 0; self.response_stall_after = None
        self.response_stall_cycles = 0

    async def _delay(self, cycles):
        for _ in range(cycles): await self.bundle.step()

    def _observe(self, channel):
        bus = getattr(self.bundle, channel)
        fields = ("addr", "size", "cmd", "wmask", "wdata") if channel == "req" else ("cmd", "rdata")
        payload = tuple(int(getattr(bus, pin).value) for pin in fields)
        self.protocol_checker.observe(channel, bus.valid.value, bus.ready.value, payload)

    @driver_method()
    async def read_resp(self, size, rdata):
        assert len(rdata) == 1 << size
        for i, data in enumerate(rdata):
            # Ready/valid: hold valid and payload until ready completes the handshake.
            self.bundle.rsp.valid.value = 0
            await self._delay(self.response_valid_delay)
            self.bundle.rsp.cmd.value = CMD_READLST if i == ((1 << size)-1) else CMD_READ
            self.bundle.rsp.rdata.value = data; self.bundle.rsp.valid.value = 1

            for _ in range(10000):
                await self.bundle.step()
                self._observe("rsp")
                if int(self.bundle.rsp.ready.value):
                    break
            else:
                raise TimeoutError(f"memory response beat {i} was not accepted (rsp.ready stayed low)")
            self.bundle.rsp.valid.value = 0
            await self._delay(self.response_beat_delay)
            if self.response_stall_after is not None and i == self.response_stall_after:
                await self._delay(self.response_stall_cycles)

    @driver_method()
    async def write_resp(self):
        await self._delay(self.response_valid_delay)
        self.bundle.rsp.cmd.value = CMD_WRITERSP
        self.bundle.rsp.valid.value = 1
        for _ in range(10000):
            await self.bundle.step()
            self._observe("rsp")
            if int(self.bundle.rsp.ready.value):
                break
        else:
            raise TimeoutError("memory write response was not accepted (rsp.ready stayed low)")
        self.bundle.rsp.valid.value = 0

    @driver_method()
    async def get_req(self):
        self.bundle.req.ready.value = 0
        for _ in range(self.request_ready_delay):
            await self.bundle.step()
            self._observe("req")
        self.bundle.req.ready.value = 1
        # Complete the request handshake on a clock edge before lowering ready.
        for _ in range(10000):
            await self.bundle.step()
            self._observe("req")
            if int(self.bundle.req.valid.value):
                req = self.bundle.req.as_dict()
                break
        else:
            raise TimeoutError("timeout waiting for request valid")
        self.bundle.req.ready.value = 0
        if self.monitor: self.monitor.publish(req)
        return req

SimpleBusSlaveAgent = SlaveDriver
