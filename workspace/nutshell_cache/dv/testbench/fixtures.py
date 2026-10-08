"""Pytest/Toffee fixture factory for the UVM-like CacheTestbench."""
from toffee_test import ToffeeRequest, fixture
from Cache import DUTCache
from dv.testbench.cache_testbench import CacheTestbench
from dv.models.simplebus_ram import SimpleBusRam
from toffee import *

@fixture
async def cache_testbench(toffee_request: ToffeeRequest):
    """Create a CacheTestbench; reset and agent startup remain centralized."""
    dut = toffee_request.create_dut(DUTCache, "clock")
    tb = CacheTestbench(dut)
    dut.reset.AsImmWrite(); dut.reset.value = 1; dut.reset.AsRiseWrite()
    start_clock(dut); await ClockCycles(dut, 100)
    dut.reset.value = 0; dut.io_flush.value = 0
    tb.env.mem_ram = SimpleBusRam(tb.env.mem_agent.driver)
    tb.env.mmio_ram = SimpleBusRam(tb.env.mmio_agent.driver)
    async with Executor(exit="none") as exec:
        exec(tb.env.cpu.driver.req_handler(), sche_group="req_handler")
        exec(tb.env.cpu.driver.rsp_handler(), sche_group="rsp_handler")
        exec(tb.env.mem_ram.work(), sche_group="mem")
        exec(tb.env.mmio_ram.work(), sche_group="mmio")
    return tb
