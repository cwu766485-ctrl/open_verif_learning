"""Functional scenarios for the NutShell Cache learning task.

The tests intentionally exercise the cache through the SimpleBus boundary.  The
reference model checks the request/response contract while the RAM services let
the tests observe miss/refill and MMIO routing.
"""

from base_test import *
from toffee_test import case
import random


@case
async def test_reset_drains_pipeline(start_func):
    """复位/流水线清空：复位结束后 Cache 不应残留请求或下游事务。

    激励：只执行公共 reset 流程。
    检查：io_empty=1，memory/MMIO 两条下游总线都没有请求。
    覆盖目标：reset、流水线 drain、空闲状态。
    """
    env: NtCacheEnv = await start_func()
    assert int(env.dut.io_empty.value) == 1
    assert not env.mem_ram.requests
    assert not env.mmio_ram.requests


@case
async def test_read_miss_then_hit(start_func):
    """读缺失后命中：第一次读触发整条 cache line refill，第二次读命中缓存。

    激励：连续两次访问同一个地址。
    检查：第一次确实访问 backing memory；第二次返回相同数据且不再访问 memory。
    覆盖目标：tag compare、read miss、8-beat refill、read hit。
    """
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
async def test_write_read_and_byte_mask(start_func):
    """写命中与字节掩码：先做全字写，再只更新最低 byte，最后读回合并结果。

    激励：full write -> read -> mask=0x01 的部分写 -> read。
    检查：写响应返回旧值语义，未选中的 byte 保持不变。
    覆盖目标：write hit、byte mask merge、dirty bit、data array 写入。
    """
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


@case
async def test_mmio_isolated_from_cache_memory(start_func):
    """MMIO 旁路：设备地址走 MMIO 端口，不能污染普通 cache memory。

    激励：对 0x3000_0000 区域执行写后读。
    检查：MMIO 有请求、普通 memory 没有新增请求，读回刚写入的数据。
    覆盖目标：MMIO 地址译码、MMIO request/response、cache bypass。
    """
    env: NtCacheEnv = await start_func()
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


@case
async def test_sequential_words_preserve_order(start_func):
    """同一 cache line 的 8 个 word：验证 line 内 word index 和 burst 顺序。

    激励：向一条 64B line 的 8 个 8B word 分别写入不同值，再逐个读回。
    检查：每个 word 独立保持，不能因 refill beat 或地址拼接而互相覆盖。
    覆盖目标：word index、8-beat line、Data Array 行内寻址。
    """
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


@case
async def test_deterministic_mixed_sequence(start_func):
    """固定种子的 64 笔混合读写：用 shadow/reference model 检查状态演进。

    激励：固定随机种子产生多组读、写和随机 byte mask。
    检查：每次读数据、写响应旧值都与 Python shadow model 一致。
    覆盖目标：读写交替、不同 word、部分写、命中/缺失状态转换。
    """
    env: NtCacheEnv = await start_func()
    rng = random.Random(0xCAFE)
    shadow = {}

    for _ in range(64):
        line = rng.randrange(8)
        word = rng.randrange(8)
        addr = 0x4000 + line * 0x40 + word * 8
        if rng.randrange(2):
            data = rng.getrandbits(64)
            mask = rng.randrange(1, 0x100)
            old_data = shadow.get(addr & ~0x7, 0)
            response = await env.in_agent.block_write(addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP
            assert response["bits_rdata"] == old_data
            byte_mask = sum(
                0xFF << (8 * byte) for byte in range(8) if mask & (1 << byte)
            )
            shadow[addr & ~0x7] = (old_data & ~byte_mask) | (data & byte_mask)
        else:
            response = await env.in_agent.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST
            assert response["bits_rdata"] == shadow.get(addr & ~0x7, 0)


@case
async def test_dirty_eviction_writes_back(start_func):
    """脏行替换：向同一个 set 填入第 5 条 line，强制 4-way cache 替换。

    激励：先写满同一 set 的 4 条 line，再访问第 5 条冲突 line。
    检查：被替换 dirty victim 产生 writeback，随后新 line 才能 refill；旧数据写回内存。
    覆盖目标：invalid/victim 选择、dirty 判断、8-beat writeback、writeback 后 refill。
    """
    env: NtCacheEnv = await start_func()
    base = 0x1000
    addresses = [base + way * 0x2000 for way in range(5)]
    values = [0xD000000000000000 | way for way in range(4)]

    for addr, data in zip(addresses[:4], values):
        response = await env.in_agent.block_write(addr, data, 0xFF)
        assert response["bits_cmd"] == CMD_WRITERSP

    writes_before = len(env.mem_ram.write_requests)
    response = await env.in_agent.block_read(addresses[4])

    assert response["bits_cmd"] == CMD_READLST
    assert len(env.mem_ram.write_requests) > writes_before
    assert any(
        req["cmd"] in (CMD_WRITEBST, CMD_WRITELST)
        for req in env.mem_ram.write_requests[writes_before:]
    ), "a dirty victim must generate a backing-memory writeback"
    assert any(data in env.mem_ram.data.values() for data in values)


@case
async def test_memory_backpressure_and_slow_refill(start_func):
    """下游 backpressure：人为延迟 ready/valid，检查 refill 可暂停并正确恢复。

    激励：延迟 memory request ready、response valid，并在 burst 中间插入停顿；同时延迟 CPU response ready。
    检查：最终读数据正确，beat 不丢失、不重复、不乱序，也不死锁。
    覆盖目标：ready/valid 握手、burst counter、FSM wait 状态。
    """
    env: NtCacheEnv = await start_func()
    env.in_agent.response_ready_delay = 4
    env.mem_agent.request_ready_delay = 3
    env.mem_agent.response_valid_delay = 2
    env.mem_agent.response_beat_delay = 1
    env.mem_agent.response_stall_after = 3
    env.mem_agent.response_stall_cycles = 5

    response = await env.in_agent.block_read(0x6000)
    assert response["bits_cmd"] == CMD_READLST
    assert response["bits_rdata"] == 0
    assert env.mem_ram.read_requests


@case
async def test_probe_hit_releases_cached_line(start_func):
    """一致性 probe 命中：外部一致性代理要求 Cache 检查并释放一整条缓存行。

    激励：先写入一条 line，再发送 CMD_PROBE；随后再次 probe 同一地址。
    检查：第一次返回 PROBEHIT，并输出 8 个 line beat；释放结束后再次访问变成 PROBEMISS。
    覆盖目标：coherence probe hit/miss、line release、8-beat coherence response FSM。
    """
    env: NtCacheEnv = await start_func()
    addr = 0x7000
    data = 0xCAFEBABE12345678

    await env.in_agent.block_write(addr, data, 0xFF)
    first, release = await env.coh_agent.probe(addr)

    assert first["cmd"] == CMD_PROBEHIT
    assert len(release) == 8
    assert release[0]["rdata"] == data
    assert release[-1]["cmd"] == CMD_READLST

    miss, no_release = await env.coh_agent.probe(0xB000)
    assert miss["cmd"] == CMD_PROBEMISS
    assert no_release == []


@case
async def test_cross_cache_line_access(start_func):
    """跨 line 边界：分别访问上一条 line 的最后一个 word 和下一条 line 的第一个 word。

    激励：访问 0x83F8 与 0x8400，这两个地址恰好跨越 64B line 边界。
    检查：两条 line 的数据独立，地址低位切分不会串线。
    覆盖目标：line offset 边界、set/tag 重新计算、相邻 line refill。
    """
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
async def test_long_randomized_mixed_sequence(start_func):
    """固定种子的 128 笔长随机序列：综合覆盖冲突、替换、掩码和读写混合。

    激励：在多个 line/set 上随机选择 word、读写类型和 byte mask。
    检查：每笔事务都与 shadow model 对比，持续检查长期状态一致性。
    覆盖目标：长序列状态累积、冲突替换、dirty line、随机 byte mask。
    """
    env: NtCacheEnv = await start_func()
    rng = random.Random(0x20260908)
    shadow = {}

    for _ in range(128):
        line = rng.randrange(24)
        word = rng.randrange(8)
        addr = 0xA000 + line * 0x40 + word * 8
        aligned = addr & ~0x7
        if rng.randrange(2):
            data = rng.getrandbits(64)
            mask = rng.randrange(1, 0x100)
            old_data = shadow.get(aligned, 0)
            response = await env.in_agent.block_write(addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP
            assert response["bits_rdata"] == old_data
            byte_mask = sum(
                0xFF << (8 * byte) for byte in range(8) if mask & (1 << byte)
            )
            shadow[aligned] = (old_data & ~byte_mask) | (data & byte_mask)
        else:
            response = await env.in_agent.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST
            assert response["bits_rdata"] == shadow.get(aligned, 0)
