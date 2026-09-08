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
    """The reset sequence leaves the Cache pipeline empty."""
    env: NtCacheEnv = await start_func()
    assert int(env.dut.io_empty.value) == 1
    assert not env.mem_ram.requests
    assert not env.mmio_ram.requests


@case
async def test_read_miss_then_hit(start_func):
    """A first read refills from memory; a repeated read is served by Cache."""
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
    """Full-line data and a byte-masked update survive a read-after-write."""
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
    """MMIO addresses use the MMIO SimpleBus and do not touch cache RAM."""
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
    """Adjacent words in one cache line remain independently addressable."""
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
    """A reproducible mixed read/write stream checks state over many requests."""
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
    """Five lines mapping to one set force a dirty four-way eviction."""
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
    """Delayed ready/valid beats must not corrupt a refill or its response."""
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
    """A coherence probe reports a hit and drains the released cache line."""
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
    """Adjacent words on opposite sides of a 64-byte line stay independent."""
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
    """A longer deterministic stream combines conflicts, masks and evictions."""
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
