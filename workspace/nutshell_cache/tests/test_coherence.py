from toffee_test import case
from base_test import *
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
import random
import asyncio


async def _collect_probe_response(agent):
    """Collect and publish a probe response after its request was accepted."""
    agent.bundle.rsp.ready.value = 1
    first = await agent._get_probe_beat()
    agent.monitor.publish(SimpleBusResponse(first["cmd"], first["rdata"]))
    release = []
    if first["cmd"] == CMD_PROBEHIT:
        while True:
            beat = await agent._get_probe_beat()
            release.append(beat)
            agent.monitor.publish(SimpleBusResponse(beat["cmd"], beat["rdata"]))
            if beat["cmd"] == CMD_READLST:
                break
    agent.bundle.rsp.ready.value = 0
    return first, release


async def _accept_cpu_and_probe_together(env, cpu_addr, probe_addr):
    """Assert both request valids before stepping, then record handshakes."""
    cpu, coh = env.cpu, env.coherence
    cpu_req = SimpleBusRequest(cpu_addr, 7, CMD_READ, 0, 0)
    coh_req = SimpleBusRequest(probe_addr, 7, CMD_PROBE, 0, 0)
    cpu.bundle.req.assign({
        "valid": 1, "addr": cpu_req.addr, "size": cpu_req.size,
        "cmd": cpu_req.cmd, "wmask": cpu_req.wmask, "wdata": cpu_req.wdata,
    })
    coh.bundle.req.assign({
        "valid": 1, "addr": coh_req.addr, "size": coh_req.size,
        "cmd": coh_req.cmd, "wmask": coh_req.wmask, "wdata": coh_req.wdata,
    })
    assert int(cpu.bundle.req.valid.value) == 1
    assert int(coh.bundle.req.valid.value) == 1

    accepted_at = {}
    for cycle in range(1000):
        await cpu.bundle.step()
        for name, agent, request in (
            ("coherence", coh, coh_req),
            ("cpu", cpu, cpu_req),
        ):
            bundle = agent.bundle.req
            valid, ready = int(bundle.valid.value), int(bundle.ready.value)
            payload = tuple(int(getattr(bundle, pin).value)
                            for pin in ("addr", "size", "cmd", "wmask", "wdata"))
            agent.protocol_checker.observe("req", valid, ready, payload)
            if valid and ready:
                if name == "coherence":
                    assert int(cpu.bundle.req.valid.value) == 1
                    assert int(cpu.bundle.req.ready.value) == 0, (
                        "CPU ready must stay low while the higher-priority probe is valid"
                    )
                accepted_at[name] = cycle
                bundle.valid.value = 0
                agent.monitor.publish(request)
        if len(accepted_at) == 2:
            return accepted_at
    raise TimeoutError("CPU and coherence requests did not both handshake")


@case
async def test_probe_hit_releases_cached_line(start_func):
    """Coherence probe：验证 probe hit/miss 响应，以及 hit 时按 8 个 beat 释放整条 cache line。"""
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


@case
async def test_coherence_probe_wins_simultaneous_cpu_read(start_func):
    """The fixed-priority arbiter accepts a coincident probe before the CPU read."""
    env = await start_func(
        start_cpu_handlers=False, start_cpu_response_handler=False
    )
    probe_addr, cpu_addr = 0x7000, 0x9000
    probe_data, cpu_data = 0x0123456789ABCDEF, 0xFEDCBA9876543210
    for addr, data in ((probe_addr, probe_data), (cpu_addr, cpu_data)):
        await env.cpu.send_req(addr, 7, CMD_WRITE, 0xFF, data)
        response = await env.cpu.get_resp(response_ready_delay=0)
        assert response["cmd"] == CMD_WRITERSP

    reads_before = len(env.mem_ram.read_requests)
    accepted_at = await _accept_cpu_and_probe_together(env, cpu_addr, probe_addr)
    assert accepted_at["coherence"] < accepted_at["cpu"], (
        "coherence input 0 must win the same-cycle arbitration; CPU must retry"
    )

    cpu_response, probe_result = await asyncio.gather(
        env.cpu.get_resp(response_ready_delay=0),
        _collect_probe_response(env.coherence),
    )
    first, release = probe_result
    assert cpu_response["cmd"] == CMD_READLST
    assert cpu_response["rdata"] == cpu_data
    assert first["cmd"] == CMD_PROBEHIT
    assert len(release) == 8
    assert release[0]["rdata"] == probe_data
    assert release[-1]["cmd"] == CMD_READLST
    assert len(env.mem_ram.read_requests) == reads_before, (
        "both colliding requests target resident lines and must not refill"
    )
    env.coverage.sample(arbitration="coherence_wins_cpu")


@case
async def test_probe_hit_releases_lines_from_all_four_ways(start_func):
    """Probe each physical way in one set and check its complete wrapped line."""
    env = await start_func()
    line_bases = [0x1000 + way * 0x2000 for way in range(4)]
    expected_lines = {}
    for line_number, line_base in enumerate(line_bases):
        words = [
            0xDCA0000000000000 | (line_number << 12) | beat
            for beat in range(8)
        ]
        expected_lines[line_base] = words
        for beat, data in enumerate(words):
            response = await env.cpu.block_write(line_base + beat * 8, data, 0xFF)
            assert response["bits_cmd"] == CMD_WRITERSP

    tag_model = env.testbench.scoreboard.reference.cache_tags
    ways = {line_base: tag_model.resident_way(line_base) for line_base in line_bases}
    assert set(ways.values()) == {0, 1, 2, 3}, (
        f"the four conflict lines must occupy every physical way, got {ways}"
    )

    for line_base in line_bases:
        way = ways[line_base]
        start_word = (way + 3) % 8
        probe_addr = line_base + start_word * 8
        first, release = await env.coherence.probe(probe_addr)
        expected = expected_lines[line_base][start_word:] + expected_lines[line_base][:start_word]
        assert first["cmd"] == CMD_PROBEHIT
        assert len(release) == 8
        assert [beat["rdata"] for beat in release] == expected
        assert release[-1]["cmd"] == CMD_READLST
        env.coverage.sample(probe_way=way)


@case
async def test_reset_cancels_stalled_probe_release_and_recovers(start_func):
    """Reset cancels a stalled line release; the coherence port works afterward."""
    env = await start_func()
    addr, data = 0xA000, 0xAABBCCDDEEFF0011
    await env.cpu.block_write(addr, data, 0xFF)

    coh = env.coherence
    await coh.send_req(addr, 7, CMD_PROBE)
    coh.bundle.rsp.ready.value = 1
    first = await coh._get_probe_beat()
    assert first["cmd"] == CMD_PROBEHIT
    coh.monitor.publish(SimpleBusResponse(first["cmd"], first["rdata"]))
    received = []
    for _ in range(2):
        beat = await coh._get_probe_beat()
        received.append(beat)
        coh.monitor.publish(SimpleBusResponse(beat["cmd"], beat["rdata"]))
    assert len(received) == 2

    coh.bundle.rsp.ready.value = 0
    stalled_payload = None
    for _ in range(100):
        await coh.bundle.step()
        valid = int(coh.bundle.rsp.valid.value)
        payload = (int(coh.bundle.rsp.cmd.value), int(coh.bundle.rsp.rdata.value))
        coh.protocol_checker.observe("rsp", valid, 0, payload)
        if valid:
            stalled_payload = payload
            break
    assert stalled_payload is not None, "release did not present the next beat to stall"
    for _ in range(3):
        await coh.bundle.step()
        valid = int(coh.bundle.rsp.valid.value)
        payload = (int(coh.bundle.rsp.cmd.value), int(coh.bundle.rsp.rdata.value))
        coh.protocol_checker.observe("rsp", valid, 0, payload)
        assert valid == 1
        assert payload == stalled_payload

    await env.testbench.reset(pulse_cycles=2, recovery_cycles=128)
    assert int(coh.bundle.rsp.valid.value) == 0, "stale probe release survived reset"
    env.coverage.sample(reset="cancelled_probe_release")

    miss, release = await coh.probe(addr)
    assert miss["cmd"] == CMD_PROBEMISS
    assert release == []


@case
async def test_consecutive_probes_keep_responses_ordered(start_func):
    """A hit/miss/hit sequence has no stray or cross-transaction release beats."""
    env = await start_func()
    addr_a, addr_b, absent_addr = 0x5100, 0x6200, 0x7300
    data_a, data_b = 0x1111222233334444, 0xAAAABBBBCCCCDDDD
    await env.cpu.block_write(addr_a, data_a, 0xFF)
    await env.cpu.block_write(addr_b, data_b, 0xFF)

    first_a, release_a = await env.coherence.probe(addr_a)
    middle_miss, no_release = await env.coherence.probe(absent_addr)
    last_b, release_b = await env.coherence.probe(addr_b)

    assert first_a["cmd"] == CMD_PROBEHIT
    assert len(release_a) == 8 and release_a[0]["rdata"] == data_a
    assert release_a[-1]["cmd"] == CMD_READLST
    assert middle_miss["cmd"] == CMD_PROBEMISS
    assert no_release == []
    assert last_b["cmd"] == CMD_PROBEHIT
    assert len(release_b) == 8 and release_b[0]["rdata"] == data_b
    assert release_b[-1]["cmd"] == CMD_READLST
    env.coverage.sample(probe_sequence="consecutive")


@case
async def test_probe_hit_keeps_line_for_following_lsu_read(start_func):
    """A probe hit releases data but leaves the line available for a CPU hit."""
    env = await start_func()
    addr, data = 0xB000, 0xCAFEBABE12345678
    await env.cpu.block_write(addr, data, 0xFF)

    first, release = await env.coherence.probe(addr)
    assert first["cmd"] == CMD_PROBEHIT
    assert len(release) == 8
    reads_after_probe = len(env.mem_ram.read_requests)

    response = await env.cpu.block_read(addr)
    assert response["bits_cmd"] == CMD_READLST
    assert response["bits_rdata"] == data
    assert len(env.mem_ram.read_requests) == reads_after_probe, (
        "LSU read after a probe hit must hit in the retained DCache line"
    )
    env.coverage.sample(probe_post_state="retained_hit")
