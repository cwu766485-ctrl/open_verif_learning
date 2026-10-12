from toffee_test import case
from base_test import *
import random


@case
async def test_write_read_and_byte_mask(start_func):
    """Byte-mask 写入：先全字节写入，再只更新 byte lane 0，确认未选中的字节保持不变。"""
    env: NtCacheEnv = await start_func()
    addr = 0x1800
    original = 0x1122334455667788
    updated = 0x11223344556677AA

    write_rsp = await env.in_agent.block_write(addr, original, 0xFF)
    assert write_rsp["bits_cmd"] == CMD_WRITERSP
    assert await env.in_agent.block_read(addr) == {
        "valid": True,
        "bits_rdata": original,
        "bits_cmd": CMD_READLST,
    }

    masked_rsp = await env.in_agent.block_write(addr, 0xAA, 0x01)
    assert masked_rsp["bits_cmd"] == CMD_WRITERSP
    read_rsp = await env.in_agent.block_read(addr)
    assert read_rsp["bits_rdata"] == updated
