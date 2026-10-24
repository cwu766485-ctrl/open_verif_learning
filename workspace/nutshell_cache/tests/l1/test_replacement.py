from toffee_test import case
from base_test import *
import random


@case
async def test_dirty_eviction_writes_back(start_func):
    """Dirty eviction：用 5 条映射到同一 set 的 cache line 填满 4-way cache 并触发替换，检查 dirty victim 的 8-beat 写回数据。"""
    env: NtCacheEnv = await start_func()
    base = 0x1000
    addresses = [base + way * 0x2000 for way in range(5)]
    line_data = {}

    # Fill each of four conflicting lines with eight distinct dirty beats.
    # This makes the writeback check data-exact rather than merely checking
    # that some write request happened.
    for way, addr in enumerate(addresses[:4]):
        expected_line = []
        for beat in range(8):
            data = 0xD000000000000000 | (way << 8) | beat
            expected_line.append(data)
            response = await env.in_agent.block_write(addr + beat * 8, data, 0xFF)
            assert response["bits_cmd"] == CMD_WRITERSP
        line_data[addr & ~0x3F] = expected_line

    # Check that the four fills occupy all ways before forcing a replacement.
    # A hit here must not be rescued by stale backing-memory contents.
    reads_after_fill = len(env.mem_ram.read_requests)
    for way, addr in enumerate(addresses[:4]):
        response = await env.in_agent.block_read(addr)
        assert response["bits_rdata"] == line_data[addr & ~0x3F][0]
    assert len(env.mem_ram.read_requests) == reads_after_fill, (
        "a four-line conflict set must retain all four lines before eviction"
    )

    writes_before = len(env.mem_ram.write_requests)
    response = await env.in_agent.block_read(addresses[4])

    assert response["bits_cmd"] == CMD_READLST
    assert len(env.mem_ram.write_requests) > writes_before
    assert any(
        req["cmd"] in (CMD_WRITEBST, CMD_WRITELST)
        for req in env.mem_ram.write_requests[writes_before:]
    ), "a dirty victim must generate a backing-memory writeback"
    writeback = next(
        req for req in env.mem_ram.write_requests[writes_before:]
        if req["cmd"] == CMD_WRITEBST
    )
    evicted_line = writeback["addr"] & ~0x3F
    assert evicted_line in line_data, f"unexpected dirty victim line 0x{evicted_line:08x}"
    assert [env.mem_ram.data.get(evicted_line + beat * 8, 0) for beat in range(8)] == line_data[evicted_line]
