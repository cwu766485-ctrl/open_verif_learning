from toffee_test import case
from base_test import *
import random


@case
async def test_mmio_isolated_from_cache_memory(start_func):
    """MMIO bypass：访问 0x30000000 区域，确认请求经 MMIO 端口响应，不访问 cache 下游主存。"""
    env: NtCacheEnv = await start_func()
    env.mmio_agent.request_ready_delay = 3
    addr = 0x30000000
    mem_before = len(env.mem_ram.requests)
    mmio_before = len(env.mmio_ram.requests)

    write_rsp = await env.in_agent.block_write(addr, 0xCAFE, 0xFF)
    read_rsp = await env.in_agent.block_read(addr)

    assert write_rsp["bits_cmd"] == CMD_WRITERSP
    assert read_rsp["bits_cmd"] == CMD_READLST
    assert read_rsp["bits_rdata"] == 0xCAFE
    assert len(env.mmio_ram.requests) > mmio_before
    assert len(env.mem_ram.requests) == mem_before
    assert env.mmio_agent.protocol_checker.stall_cycles_by_channel.get("req", 0) >= 3
