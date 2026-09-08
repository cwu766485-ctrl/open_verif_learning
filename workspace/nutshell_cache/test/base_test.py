from toffee_test import ToffeeRequest, fixture
from Cache import DUTCache
from env.ntcache_env import *
from env.simpleram import *

@fixture
async def start_func(toffee_request: ToffeeRequest):
    setup_logging(ERROR)
    dut = toffee_request.create_dut(DUTCache, "clock")
    env = NtCacheEnv(dut)
    env.dut = dut

    async def start_code():
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        start_clock(dut)

        await ClockCycles(dut, 100)
        dut.reset.value = 0
        dut.io_flush.value = 0

        env.mem_ram = SimpleBusRam(env.mem_agent)
        env.mmio_ram = SimpleBusRam(env.mmio_agent)
        async with Executor(exit="none") as exec:
            exec(env.in_agent.req_handler(), sche_group="req_handler")
            exec(env.in_agent.rsp_handler(), sche_group="rsp_handler")
            exec(env.mem_ram.work(), sche_group="mem")
            exec(env.mmio_ram.work(), sche_group="mmio")
        return env

    return start_code
