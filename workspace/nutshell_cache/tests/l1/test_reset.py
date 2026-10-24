from toffee_test import case
from base_test import *
import random


@case
async def test_reset_drains_pipeline(start_func):
    """复位空闲状态：确认复位后 pipeline 为空，且没有产生 memory/MMIO 访问。"""
    env: NtCacheEnv = await start_func()
    assert int(env.dut.io_empty.value) == 1
    assert not env.mem_ram.requests
    assert not env.mmio_ram.requests


@case
async def test_reset_aborts_inflight_refill_and_recovers(start_func):
    """Reset while an accepted miss waits for memory; no stale CPU reply may escape."""
    env: NtCacheEnv = await start_func()
    addr = 0x26000
    env.mem_agent.response_valid_delay = 60
    reads_before = len(env.mem_ram.read_requests)
    await ClockCycles(env.dut, 150)

    await env.in_agent.non_block_read(addr)
    for _ in range(1000):
        if len(env.mem_ram.read_requests) > reads_before:
            break
        await env.cpu.bundle.step()
    assert len(env.mem_ram.read_requests) > reads_before, "miss was not accepted by memory"

    # The transaction is outstanding at the memory boundary. A reset flushes
    # the cache-side request/response state; the memory agent still completes
    # its already accepted burst, which must not become a phantom CPU response.
    await env.testbench.reset(recovery_cycles=0)
    for _ in range(150):
        await env.cpu.bundle.step()
        assert int(env.dut.io_in_resp_valid.value) == 0, "stale response escaped after reset"
    assert int(env.dut.io_empty.value) == 1

    # A fresh transaction after reset proves that the pipeline and backing
    # responder both recovered, rather than merely hiding the abandoned read.
    await env.in_agent.non_block_read(addr)
    response = await env.in_agent.recv()
    assert response["bits_cmd"] == CMD_READLST
    assert response["bits_rdata"] == 0
    assert env.testbench.scoreboard.compared == 1
