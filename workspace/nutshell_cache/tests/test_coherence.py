from toffee_test import case
from base_test import *
import random
import asyncio


@case
async def test_probe_hit_releases_cached_line(start_func):
    """娑撯偓閼峰瓨鈧?probe 閸涙垝鑵戦敍姘樆闁劋绔撮懛瀛樷偓褌鍞悶鍡氼洣濮?Cache 濡偓閺屻儱鑻熼柌濠冩杹娑撯偓閺佸瓨娼紓鎾崇摠鐞涘被鈧?
    濠碘偓閸旀唻绱伴崗鍫濆晸閸忋儰绔撮弶?line閿涘苯鍟€閸欐垿鈧?CMD_PROBE閿涙盯娈㈤崥搴″晙濞?probe 閸氬奔绔撮崷鏉挎絻閵?    濡偓閺屻儻绱扮粭顑跨濞喡ょ箲閸?PROBEHIT閿涘苯鑻熸潏鎾冲毉 8 娑?line beat閿涙盯鍣撮弨鍓х波閺夌喎鎮楅崘宥嗩偧鐠佸潡妫堕崣妯诲灇 PROBEMISS閵?    鐟曞棛娲婇惄顔界垼閿涙瓭oherence probe hit/miss閵嗕勾ine release閵?-beat coherence response FSM閵?    """
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
async def test_probe_during_stalled_refill_with_response_backpressure(start_func):
    """Exercise a pending refill and a hit probe while both response sinks stall."""
    env: NtCacheEnv = await start_func()
    cached_addr = 0x7C00
    miss_addr = 0x18000
    cached_data = 0xA55A1234DEADBEEF
    await env.in_agent.block_write(cached_addr, cached_data, 0xFF)

    # Hold the memory response long enough to launch a coherence probe while
    # the cache is actively waiting on a critical-word-first line refill.
    env.mem_agent.response_valid_delay = 80
    env.mem_agent.response_stall_after = 3
    env.mem_agent.response_stall_cycles = 5
    env.coh_agent.response_ready_delay = 1000

    reads_before = len(env.mem_ram.read_requests)
    read_task = asyncio.create_task(env.in_agent.block_read(miss_addr))
    for _ in range(1000):
        if len(env.mem_ram.read_requests) > reads_before:
            break
        await env.in_agent.bundle.step()
    assert len(env.mem_ram.read_requests) > reads_before, "CPU miss did not reach backing memory"

    probe_task = asyncio.create_task(env.coh_agent.probe(cached_addr))
    read_rsp, probe_result = await asyncio.gather(read_task, probe_task)
    first, release = probe_result

    assert read_rsp["bits_cmd"] == CMD_READLST
    assert read_rsp["bits_rdata"] == 0
    assert first["cmd"] == CMD_PROBEHIT
    assert len(release) == 8
    assert [beat["rdata"] for beat in release] == [cached_data] + [0] * 7
    assert release[-1]["cmd"] == CMD_READLST
    assert env.coh_agent.protocol_checker.stall_cycles_by_channel.get("rsp", 0) >= 4
