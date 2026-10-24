"""Cycle-level ready/valid timing checks at the DCache SimpleBus boundary."""

from toffee_test import case
from base_test import *


@case
async def test_memory_request_and_cpu_response_stall_timing(start_func):
    """Hold a memory request and CPU response through real RTL backpressure."""
    env = await start_func(start_cpu_response_handler=False)
    addr = 0x6A00

    # Stall the DCache's downstream request before memory accepts it.
    env.mem_agent.request_ready_delay = 6
    env.mem_agent.response_valid_delay = 2

    # The legacy pipeline couples request acceptance to response READY. Let
    # the miss enter the pipeline, then close the response sink before refill
    # completes so the test exercises a real held response.
    env.cpu.bundle.rsp.ready.value = 1
    reads_before = len(env.mem_ram.read_requests)
    await env.cpu.send_req(addr, 7, CMD_READ)
    for _ in range(1000):
        if len(env.mem_ram.read_requests) > reads_before:
            break
        await env.cpu.bundle.step()
    assert len(env.mem_ram.read_requests) > reads_before, "miss did not reach backing memory"
    env.cpu.bundle.rsp.ready.value = 0

    for _ in range(1000):
        await env.cpu.bundle.step()
        if int(env.cpu.bundle.rsp.valid.value):
            break
    else:
        raise AssertionError("DCache did not produce a CPU response")

    held_payload = (
        int(env.cpu.bundle.rsp.cmd.value),
        int(env.cpu.bundle.rsp.rdata.value),
    )
    env.cpu.protocol_checker.observe(
        "rsp", valid=1, ready=0, payload=held_payload
    )

    # Check several sampled clock edges while valid is blocked by ready=0.
    for _ in range(4):
        await env.cpu.bundle.step()
        valid = int(env.cpu.bundle.rsp.valid.value)
        payload = (
            int(env.cpu.bundle.rsp.cmd.value),
            int(env.cpu.bundle.rsp.rdata.value),
        )
        assert valid == 1, "response valid dropped during backpressure"
        assert payload == held_payload, "response payload changed during backpressure"
        env.cpu.protocol_checker.observe("rsp", valid, ready=0, payload=payload)

    response = await env.cpu.get_resp(response_ready_delay=0)
    assert response["cmd"] == CMD_READLST
    assert response["rdata"] == 0
    assert env.cpu.protocol_checker.stall_cycles_by_channel.get("rsp", 0) >= 4
    assert env.mem_agent.protocol_checker.stall_cycles_by_channel.get("req", 0) >= 4
