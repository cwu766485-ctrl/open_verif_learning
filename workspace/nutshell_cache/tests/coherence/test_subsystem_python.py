"""First Python/Toffee end-to-end MESI smoke test for the dual-L1 subsystem."""

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, case, fixture

from dv.agents.coherent_cpu_agent import CoherentCpuAgent
from dv.agents.line_memory_axi_agent import LineMemoryAxiAgent
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard

try:
    from coherent_python import DUTCoherentCachePythonWrapper
except ImportError:
    DUTCoherentCachePythonWrapper = None


@fixture
async def coherent_env(toffee_request: ToffeeRequest):
    if DUTCoherentCachePythonWrapper is None:
        pytest.skip("run make coherence_python_build before the subsystem Python test")
    dut = toffee_request.create_dut(DUTCoherentCachePythonWrapper, "clock")
    memory = LineMemoryAxiAgent(dut)

    async def start():
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
        async with Executor(exit="none") as executor:
            executor(memory.run(), sche_group="line_memory")
        return dut, memory

    return start


@case
async def test_dual_core_owner_transfer_and_data_visibility(coherent_env):
    dut, memory = await coherent_env()
    core0, core1 = CoherentCpuAgent(dut, 0), CoherentCpuAgent(dut, 1)
    addr = 0x4010
    initial = memory.word(addr, (addr >> 3) & 7)
    scoreboard = CoherenceScoreboard()
    scoreboard.seed_word(addr, initial)

    response = await core0.access(addr)
    scoreboard.observe(0, addr, response_data=response)
    assert len(memory.read_requests) == 1

    # A second core reads the line while core0 owns it. The directory should
    # obtain the current line from the owner instead of issuing another DRAM read.
    response = await core1.access(addr)
    scoreboard.observe(1, addr, response_data=response)
    assert len(memory.read_requests) == 1

    updated = 0xD00DFEED12345678
    write_response = await core1.access(addr, write=True, data=updated)
    scoreboard.observe(1, addr, write=True, write_data=updated,
                       response_data=write_response)
    response = await core0.access(addr)
    scoreboard.observe(0, addr, response_data=response)
    scoreboard.assert_covered("cold_read", "remote_read_from_E",
                              "shared_upgrade", "remote_read_from_M")
    assert len(memory.read_requests) == 1
    assert int(dut.protocol_error.value) == 0
