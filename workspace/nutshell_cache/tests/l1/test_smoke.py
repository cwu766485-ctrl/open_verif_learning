from toffee_test import case
from base_test import *
import random

@case
async def test_smoke(start_func):
    """基础冒烟测试：检查未初始化读返回默认值、单字节写入，以及连续非阻塞读的响应。"""
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
