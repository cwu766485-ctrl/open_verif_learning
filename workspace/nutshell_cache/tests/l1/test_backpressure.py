from toffee_test import case
from base_test import *
import random


@case
async def test_memory_backpressure_and_slow_refill(start_func):
    """慢 refill 与 backpressure：延迟内存响应、在 burst 中制造停顿，并延迟 CPU 响应接收，检查事务完成和 ready/valid 行为。"""
    env: NtCacheEnv = await start_func(start_cpu_response_handler=False)
    env.mem_agent.response_valid_delay = 2
    env.mem_agent.response_beat_delay = 1
    env.mem_agent.response_stall_after = 3
    env.mem_agent.response_stall_cycles = 5

    # The current cache couples CPU request acceptance to downstream ready.
    # Let the miss reach the backing-memory boundary with ready high, then
    # withhold response-ready before the refill can complete.
    reads_before = len(env.mem_ram.read_requests)
    env.cpu.bundle.rsp.ready.value = 1
    await env.cpu.send_req(0x6000, 7, CMD_READ)
    for _ in range(1000):
        if len(env.mem_ram.read_requests) > reads_before:
            break
        await env.cpu.bundle.step()
    assert len(env.mem_ram.read_requests) > reads_before, "miss did not reach backing memory"
    # Withhold ready after the response has time to arrive; the DUT must keep
    # valid and payload stable until this explicit sink accepts the beat.
    response = await env.cpu.get_resp(response_ready_delay=5000)
    assert response["cmd"] == CMD_READLST
    assert response["rdata"] == 0
    assert env.mem_ram.read_requests
    assert env.cpu.protocol_checker.stall_cycles_by_channel.get("rsp", 0) >= 4
