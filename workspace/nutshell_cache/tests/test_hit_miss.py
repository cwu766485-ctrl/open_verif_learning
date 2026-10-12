from toffee_test import case
from base_test import *
import random


@case
async def test_cross_cache_line_access(start_func):
    """跨 cache line 访问：在 0x83F8 与 0x8400 写入不同数据并读回，检查相邻 64B cache line 的地址译码与数据隔离。"""
    env: NtCacheEnv = await start_func()
    first_addr = 0x83F8
    second_addr = 0x8400
    first_data = 0x1111222233334444
    second_data = 0xAAAABBBBCCCCDDDD

    await env.in_agent.block_write(first_addr, first_data, 0xFF)
    await env.in_agent.block_write(second_addr, second_data, 0xFF)

    assert (await env.in_agent.block_read(first_addr))["bits_rdata"] == first_data
    assert (await env.in_agent.block_read(second_addr))["bits_rdata"] == second_data



@case
async def test_read_miss_then_hit(start_func):
    """读 miss 后 hit：首次读取应触发下游 refill；再次读取同一地址应返回相同数据且不再产生下游读请求。"""
    env: NtCacheEnv = await start_func()
    addr = 0x1000

    first = await env.in_agent.block_read(addr)
    reads_after_miss = len(env.mem_ram.read_requests)
    second = await env.in_agent.block_read(addr)

    assert first["bits_cmd"] == CMD_READLST
    assert second["bits_cmd"] == CMD_READLST
    assert second["bits_rdata"] == first["bits_rdata"]
    assert reads_after_miss > 0, "the cold read must access backing memory"
    assert len(env.mem_ram.read_requests) == reads_after_miss, (
        "a repeated read of the same line should be a cache hit"
    )


@case
async def test_back_to_back_hit_write_then_read_forwarding(start_func):
    """Check same-line data forwarding with queued requests and a stalled sink."""
    env: NtCacheEnv = await start_func()
    addr = 0x3A00
    old_data = 0x0123456789ABCDEF
    new_data = 0xFEDCBA9876543210

    await env.in_agent.block_write(addr, old_data, 0xFF)
    reads_before = len(env.mem_ram.read_requests)
    env.cpu.response_ready_delay = 12
    await env.cpu.non_block_write(addr, new_data, 0xFF)
    await env.cpu.non_block_read(addr)

    write_response = await env.cpu.recv()
    read_response = await env.cpu.recv()
    assert write_response["bits_cmd"] == CMD_WRITERSP
    assert write_response["bits_rdata"] == old_data
    assert read_response["bits_cmd"] == CMD_READLST
    assert read_response["bits_rdata"] == new_data
    assert len(env.mem_ram.read_requests) == reads_before, (
        "queued same-line hit traffic must not issue another refill"
    )
    assert env.testbench.properties.forward_data_cycles > 0, (
        "back-to-back same-word hit traffic must exercise the data forwarding path"
    )


@case
async def test_queued_conflict_misses_preserve_tag_state(start_func):
    """Queue two cold stores to one set and verify both refilled tags/data."""
    env: NtCacheEnv = await start_func()
    addresses = (0x4400, 0x6400)
    values = (0x1111AAAABBBB2222, 0x3333CCCCDDDD4444)

    await env.cpu.non_block_write(addresses[0], values[0], 0xFF)
    await env.cpu.non_block_write(addresses[1], values[1], 0xFF)
    responses = (await env.cpu.recv(), await env.cpu.recv())
    assert [rsp["bits_cmd"] for rsp in responses] == [CMD_WRITERSP, CMD_WRITERSP]
    assert [rsp["bits_rdata"] for rsp in responses] == [0, 0]

    reads_after_refill = len(env.mem_ram.read_requests)
    for addr, expected in zip(addresses, values):
        response = await env.cpu.block_read(addr)
        assert response["bits_rdata"] == expected
    assert len(env.mem_ram.read_requests) == reads_after_refill, (
        "the queued conflicting fills must retain both lines in the 4-way set"
    )



@case
async def test_sequential_words_preserve_order(start_func):
    """顺序 word 访问：在同一 64B line 的 8 个 64-bit word 写入不同数据并读回，检查 word 选择和数据顺序。"""
    env: NtCacheEnv = await start_func()
    base = 0x2800
    expected = {}

    for index in range(8):
        addr = base + index * 8
        data = 0xA500000000000000 | index
        expected[addr] = data
        response = await env.in_agent.block_write(addr, data, 0xFF)
        assert response["bits_cmd"] == CMD_WRITERSP

    for addr, data in expected.items():
        response = await env.in_agent.block_read(addr)
        assert response["bits_cmd"] == CMD_READLST
        assert response["bits_rdata"] == data
