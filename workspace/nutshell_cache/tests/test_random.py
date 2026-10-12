from toffee_test import case
from base_test import *
import random
import os


@case
async def test_long_randomized_mixed_sequence(start_func):
    """Seven fixed seeds × 64 mixed operations, checked against a shadow model."""
    env: NtCacheEnv = await start_func()
    seeds = (
        0x20260908, 0x5EED, 0xC0FFEE,
        0xDEADBEEF, 0xBAD5EED, 0x13579BDF, 0xCAFE,
    )
    extra_seeds = os.getenv("NUTSHELL_RANDOM_SEEDS", "")
    if extra_seeds.strip():
        seeds += tuple(int(value.strip(), 0) for value in extra_seeds.split(",") if value.strip())
    for seed_index, seed in enumerate(seeds):
        rng = random.Random(seed)
        shadow = {}
        base = 0xA000 + seed_index * 0x10000

        for _ in range(64):
            line = rng.randrange(24)
            word = rng.randrange(8)
            addr = base + line * 0x40 + word * 8
            aligned = addr & ~0x7
            if rng.randrange(2):
                data = rng.getrandbits(64)
                mask = rng.randrange(1, 0x100)
                old_data = shadow.get(aligned, 0)
                response = await env.in_agent.block_write(addr, data, mask)
                assert response["bits_cmd"] == CMD_WRITERSP, f"seed=0x{seed:x} addr=0x{addr:x}"
                assert response["bits_rdata"] == old_data, f"seed=0x{seed:x} addr=0x{addr:x}"
                byte_mask = sum(
                    0xFF << (8 * byte) for byte in range(8) if mask & (1 << byte)
                )
                shadow[aligned] = (old_data & ~byte_mask) | (data & byte_mask)
            else:
                response = await env.in_agent.block_read(addr)
                assert response["bits_cmd"] == CMD_READLST, f"seed=0x{seed:x} addr=0x{addr:x}"
                assert response["bits_rdata"] == shadow.get(aligned, 0), f"seed=0x{seed:x} addr=0x{addr:x}"

@case
async def test_seeded_constrained_cache_stress(start_func):
    """固定 seed 的受约束压力序列：冲突替换、MMIO、probe、随机等待和复位恢复。"""
    env: NtCacheEnv = await start_func()
    seeds = (
        0x51A7, 0xDCA4E, 0xBADC0DE, 0x1234ABCD,
        0xC001D00D, 0x7E57CA5E,
    )
    extra_seeds = os.getenv("NUTSHELL_RANDOM_SEEDS", "")
    if extra_seeds.strip():
        seeds += tuple(int(value.strip(), 0) for value in extra_seeds.split(",") if value.strip())

    used_sets = set()
    for seed_index, seed in enumerate(seeds):
        rng = random.Random(seed)
        available_sets = [index for index in range(128) if index not in used_sets]
        set_index = rng.choice(available_sets)
        used_sets.add(set_index)

        # Randomize legal bus latency/backpressure settings for this seed.
        env.cpu.response_ready_delay = rng.randrange(4)
        env.mem_agent.request_ready_delay = rng.randrange(4)
        env.mem_agent.response_valid_delay = rng.randrange(3)
        env.mem_agent.response_beat_delay = rng.randrange(3)
        env.mem_agent.response_stall_after = rng.randrange(2, 7)
        env.mem_agent.response_stall_cycles = rng.randrange(1, 5)
        env.mmio_agent.request_ready_delay = rng.randrange(3)
        env.mmio_agent.response_valid_delay = rng.randrange(3)

        # Five distinct tags in one set guarantee a replacement after four fills.
        tag_base = 0x200 + seed_index * 0x40
        tags = rng.sample(range(tag_base, tag_base + 0x40), 5)
        line_bases = [(tag << 13) | (set_index << 6) for tag in tags]
        words = [rng.randrange(8) for _ in line_bases]
        shadow = {}

        for line_base, word in zip(line_bases[:4], words[:4]):
            addr = line_base + word * 8
            data = rng.getrandbits(64)
            mask = rng.choice((0xFF, rng.randrange(1, 0xFF)))
            old_data = shadow.get(addr, 0)
            response = await env.cpu.block_write(addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP, f"seed=0x{seed:x} write cmd"
            assert response["bits_rdata"] == old_data, f"seed=0x{seed:x} write old data"
            byte_mask = sum(0xFF << (8 * lane) for lane in range(8) if mask & (1 << lane))
            shadow[addr] = (old_data & ~byte_mask) | (data & byte_mask)

            response = await env.cpu.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST, f"seed=0x{seed:x} read cmd"
            assert response["bits_rdata"] == shadow[addr], f"seed=0x{seed:x} readback"

        # This fifth conflicting line must evict a dirty one and write back 8 beats.
        writebacks_before = len(env.mem_ram.write_requests)
        victim_addr = line_bases[4] + words[4] * 8
        response = await env.cpu.block_read(victim_addr)
        assert response["bits_cmd"] == CMD_READLST
        assert response["bits_rdata"] == 0
        assert len(env.mem_ram.write_requests) > writebacks_before, (
            f"seed=0x{seed:x} did not trigger a dirty-victim writeback"
        )

        # Re-read all four original lines; an evicted dirty line must now come from RAM intact.
        for line_base, word in zip(line_bases[:4], words[:4]):
            addr = line_base + word * 8
            response = await env.cpu.block_read(addr)
            assert response["bits_rdata"] == shadow[addr], (
                f"seed=0x{seed:x} conflict-set data mismatch at 0x{addr:08x}"
            )

        # Preload a clean line in both independent memory/reference views, then probe
        # from a random beat and check the complete wrapped 8-beat line release.
        probe_set = (set_index + 1) % 128
        probe_tag = tag_base + 0x80
        probe_line = (probe_tag << 13) | (probe_set << 6)
        probe_data = [rng.getrandbits(64) for _ in range(8)]
        for beat, data in enumerate(probe_data):
            beat_addr = probe_line + beat * 8
            env.mem_ram.data[beat_addr] = data
            env.testbench.scoreboard.reference.data[beat_addr] = data
        fill_word = rng.randrange(8)
        fill_rsp = await env.cpu.block_read(probe_line + fill_word * 8)
        assert fill_rsp["bits_rdata"] == probe_data[fill_word]

        probe_word = rng.randrange(8)
        first, release = await env.coherence.probe(probe_line + probe_word * 8)
        assert first["cmd"] == CMD_PROBEHIT, f"seed=0x{seed:x} expected probe hit"
        expected_release = [probe_data[(probe_word + beat) % 8] for beat in range(8)]
        assert [beat["rdata"] for beat in release] == expected_release
        assert release[-1]["cmd"] == CMD_READLST

        absent_line = ((probe_tag + 1) << 13) | (probe_set << 6)
        miss, no_release = await env.coherence.probe(absent_line)
        assert miss["cmd"] == CMD_PROBEMISS, f"seed=0x{seed:x} expected probe miss"
        assert no_release == []

        # Random MMIO values/masks exercise bypass without polluting cache state.
        mmio_addr = 0x30000000 + seed_index * 0x100
        mmio_shadow = 0
        for _ in range(3):
            data = rng.getrandbits(64)
            mask = rng.choice((0xFF, rng.randrange(1, 0xFF)))
            response = await env.cpu.block_write(mmio_addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP
            byte_mask = sum(0xFF << (8 * lane) for lane in range(8) if mask & (1 << lane))
            mmio_shadow = (mmio_shadow & ~byte_mask) | (data & byte_mask)
            response = await env.cpu.block_read(mmio_addr)
            assert response["bits_rdata"] == mmio_shadow, f"seed=0x{seed:x} MMIO data"

        # Reset only at an idle sequence boundary; then prove a fresh line refills cleanly.
        await env.testbench.reset(recovery_cycles=128)
        cold_addr = ((tag_base + 0x100) << 13) | (probe_set << 6) | (rng.randrange(8) * 8)
        response = await env.cpu.block_read(cold_addr)
        assert response["bits_cmd"] == CMD_READLST
        assert response["bits_rdata"] == 0, f"seed=0x{seed:x} post-reset cold read"
