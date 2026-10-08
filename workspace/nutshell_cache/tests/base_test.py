from toffee_test import ToffeeRequest, fixture
from Cache import DUTCache
from toffee import *
from dv.testbench.cache_testbench import CacheTestbench
from dv.models.simplebus_ram import SimpleBusRam
from dv.coverage import CacheCoverage
from dv.common.utils.cmd_code import *
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
import json
from pathlib import Path

@fixture
async def start_func(toffee_request: ToffeeRequest, request):
    setup_logging(ERROR)
    dut = toffee_request.create_dut(DUTCache, "clock")
    tb = CacheTestbench(dut); env = tb.env

    def finalize_testbench():
        try:
            tb.finalize()
        finally:
            payload = tb.coverage.as_dict()
            prior = getattr(request.config, "_nutshell_cache_coverage_payloads", [])
            prior.append(payload)
            request.config._nutshell_cache_coverage_payloads = prior
            merged = CacheCoverage.merge_payloads(prior)
            report = Path("reports/functional_coverage.json")
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(merged, indent=2, sort_keys=True))

    request.addfinalizer(finalize_testbench)

    async def start_environment(start_cpu_handlers=True, start_cpu_response_handler=True):
        """Start clocks and responders inside the Toffee test event loop."""
        tb.on_reset()
        dut.reset.AsImmWrite(); dut.reset.value = 1; dut.reset.AsRiseWrite()
        start_clock(dut)
        await ClockCycles(dut, 100)
        dut.reset.value = 0; dut.io_flush.value = 0
        env.mem_ram = SimpleBusRam(env.memory)
        env.mmio_ram = SimpleBusRam(env.mmio)
        async with Executor(exit="none") as exec:
            if start_cpu_handlers:
                exec(env.cpu.req_handler(), sche_group="req_handler")
            if start_cpu_handlers and start_cpu_response_handler:
                exec(env.cpu.rsp_handler(), sche_group="rsp_handler")
            exec(tb.properties.monitor(dut), sche_group="dut_properties")
            exec(env.mem_ram.work(), sche_group="mem")
            exec(env.mmio_ram.work(), sche_group="mmio")
        return env

    return start_environment
