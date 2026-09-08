"""
    Just Drive The Dut
    Author: yzcc
"""
import logging

from base_test import *
from toffee_test import case

@case
async def test_smoke(start_func):
    env: NtCacheEnv = await start_func()

    first_read = await env.in_agent.block_read(0x1)
    assert first_read["bits_cmd"] == CMD_READLST
    assert first_read["bits_rdata"] == 0

    write_rsp = await env.in_agent.block_write(0x1, 0x1, 0x1)
    assert write_rsp["bits_cmd"] == CMD_WRITERSP

    await env.in_agent.non_block_read(0x1)
    await env.in_agent.non_block_read(0x2)

    first = await env.in_agent.recv()
    second = await env.in_agent.recv()
    assert first["bits_cmd"] == CMD_READLST
    assert second["bits_cmd"] == CMD_READLST
