"""Shared Picker/Toffee subsystem fixture."""

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, fixture

from dv.agents.line_memory_axi_agent import LineMemoryAxiAgent
from dv.env.coherence_env import CoherenceEnv
from dv.monitors.cache_perf_monitor import CachePerfMonitor
from dv.monitors.snoop_data_monitor import SnoopDataMonitor
from .support import PYTHON_COVERAGE

try:
    from coherent_python import DUTCoherentCachePythonWrapper
except ImportError:
    DUTCoherentCachePythonWrapper = None


@fixture
async def coherent_env(toffee_request: ToffeeRequest):
    if DUTCoherentCachePythonWrapper is None:
        pytest.skip("run make coherence_python_build before the subsystem Python test")

    async def start(response_delay=2, *, backpressure_periods=None,
                    response_gap_periods=None):
        dut = toffee_request.create_dut(DUTCoherentCachePythonWrapper, "clock")
        memory = LineMemoryAxiAgent(
            dut, response_delay=response_delay,
            backpressure_periods=backpressure_periods,
            response_gap_periods=response_gap_periods,
        )
        perf = CachePerfMonitor(dut)
        snoop_data = SnoopDataMonitor(dut)
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        dut.cpu_req_valid.value = 0
        dut.cpu_resp_ready.value = 0
        dut.mem_rd_req_ready.value = 0
        dut.mem_rd_data_valid.value = 0
        dut.mem_wr_req_ready.value = 0
        dut.mem_wr_data_ready.value = 0
        dut.mem_wr_rsp_valid.value = 0
        start_clock(dut)
        await ClockCycles(dut, 4)
        dut.reset.value = 0
        env = CoherenceEnv(dut, memory, perf, snoop_data, PYTHON_COVERAGE)
        async with Executor(exit="none") as executor:
            executor(memory.run(), sche_group="line_memory")
            executor(perf.run(), sche_group="perf_monitor")
            executor(snoop_data.run(), sche_group="snoop_data_monitor")
        memory.snoop_data = snoop_data
        return env

    return start
