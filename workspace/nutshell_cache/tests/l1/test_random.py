from toffee_test import case
from base_test import *
import random
import os
import pytest
from dv.coverage import CacheCoverage


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


MEGA_RANDOM_SEEDS = (
    0xA11CE001, 0xA11CE002, 0xA11CE003, 0xA11CE004,
    0xA11CE005, 0xA11CE006, 0xA11CE007, 0xA11CE008,
    0xA11CE009, 0xA11CE00A, 0xA11CE00B, 0xA11CE00C,
    0xA11CE00D, 0xA11CE00E, 0xA11CE00F, 0xA11CE010,
    0xA11CE011, 0xA11CE012, 0xA11CE013, 0xA11CE014,
    0xA11CE015, 0xA11CE016, 0xA11CE017, 0xA11CE018,
    0xA11CE019, 0xA11CE01A, 0xA11CE01B, 0xA11CE01C,
    0xA11CE01D, 0xA11CE01E, 0xA11CE01F, 0xA11CE020,
)
MEGA_RANDOM_OPERATIONS_PER_SEED = 512


@pytest.mark.slow
@case
async def test_mega_randomized_cache_mmio_traffic(start_func):
    """Run reproducible mixed traffic with explicit cache/MMIO coverage goals.

    Each seed first drives clean and dirty same-set conflicts, hot and cold
    lines, an adjacent-line pair, and a minimum MMIO quota. It then runs a
    weighted randomized mix and reads back every random write. The scoreboard
    checks CPU-visible data and every dirty writeback beat.
    """
    env: NtCacheEnv = await start_func()

    seeds = MEGA_RANDOM_SEEDS
    extra_seeds = os.getenv("NUTSHELL_MEGA_RANDOM_SEEDS", "")
    if extra_seeds.strip():
        seeds += tuple(
            int(value.strip(), 0)
            for value in extra_seeds.split(",")
            if value.strip()
        )
    if len(seeds) > 126:
        raise ValueError("mega random supports at most 126 seeds (one unique set per seed)")

    operations_per_seed = int(
        os.getenv("NUTSHELL_MEGA_RANDOM_OPS", str(MEGA_RANDOM_OPERATIONS_PER_SEED))
    )
    if operations_per_seed <= 0:
        raise ValueError("NUTSHELL_MEGA_RANDOM_OPS must be positive")

    # Sets 0..N-1 are reserved for one guaranteed clean/dirty conflict
    # sequence per seed. All other generated cache traffic avoids those sets.
    conflict_sets = tuple(range(len(seeds)))
    safe_sets = tuple(range(len(seeds), 128))
    assert safe_sets, "mega random needs at least one set outside the conflict pool"
    boundary_set = safe_sets[0]

    async def read(addr, seed, phase):
        try:
            response = await env.cpu.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST
            return response
        except Exception as exc:
            raise AssertionError(
                f"mega random seed=0x{seed:x} phase={phase} read addr=0x{addr:08x}"
            ) from exc

    async def write(addr, data, mask, seed, phase):
        try:
            response = await env.cpu.block_write(addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP
            return response
        except Exception as exc:
            raise AssertionError(
                f"mega random seed=0x{seed:x} phase={phase} write addr=0x{addr:08x}"
            ) from exc

    def line_base(tag, set_index):
        return (tag << 13) | (set_index << 6)

    for seed_index, seed in enumerate(seeds):
        rng = random.Random(seed)
        conflict_set = conflict_sets[seed_index]
        tag_base = 0x1000 + seed_index * 0x200

        # Vary sink/request stalls and memory response timing deterministically
        # per seed. Nonzero downstream request delays guarantee real
        # ready/valid stalls on cache and MMIO requests.
        env.cpu.response_ready_delay = 1 + (seed_index % 3)
        env.mem_agent.request_ready_delay = 1 + (seed_index % 3)
        env.mem_agent.response_valid_delay = rng.randrange(3)
        env.mem_agent.response_beat_delay = rng.randrange(3)
        env.mem_agent.response_stall_after = 2 + (seed_index % 5)
        env.mem_agent.response_stall_cycles = 1 + (seed_index % 4)
        env.mmio_agent.request_ready_delay = 1 + (seed_index % 2)
        env.mmio_agent.response_valid_delay = rng.randrange(3)

        # Five clean lines mapping to one set: the fifth read must evict a
        # clean line. The set is isolated from every random pool and seed.
        clean_addrs = [
            line_base(tag_base + tag_offset, conflict_set)
            for tag_offset in range(5)
        ]
        writes_before_clean_conflict = len(env.mem_ram.write_requests)
        for addr in clean_addrs:
            await read(addr, seed, "clean-conflict-fill")
        assert len(env.mem_ram.write_requests) == writes_before_clean_conflict, (
            f"seed=0x{seed:x}: clean conflict unexpectedly wrote back data"
        )

        # Four dirty lines fill the same set; a fifth distinct tag forces a
        # dirty eviction. A partial write miss and partial write hit are both
        # guaranteed before the randomized portion begins.
        dirty_addrs = [
            line_base(tag_base + 0x10 + way, conflict_set) + (way * 8)
            for way in range(4)
        ]
        dirty_values = {}
        for way, addr in enumerate(dirty_addrs):
            first_data = rng.getrandbits(64)
            first_mask = 0x0F if way == 0 else 0xFF
            await write(addr, first_data, first_mask, seed, "dirty-conflict-fill")
            dirty_values[addr] = first_data & sum(
                0xFF << (8 * lane)
                for lane in range(8)
                if first_mask & (1 << lane)
            )
            if way == 0:
                second_data = rng.getrandbits(64)
                await write(addr, second_data, 0xF0, seed, "partial-write-hit")
                dirty_values[addr] = (
                    (dirty_values[addr] & 0x00000000FFFFFFFF)
                    | (second_data & 0xFFFFFFFF00000000)
                )
            response = await read(addr, seed, "dirty-line-readback")
            assert response["bits_rdata"] == dirty_values[addr], (
                f"seed=0x{seed:x}: dirty fill mismatch at 0x{addr:08x}"
            )

        dirty_victim = line_base(tag_base + 0x14, conflict_set)
        await read(dirty_victim, seed, "dirty-victim-trigger")
        for addr, expected in dirty_values.items():
            response = await read(addr, seed, "dirty-victim-reload")
            assert response["bits_rdata"] == expected, (
                f"seed=0x{seed:x}: dirty data lost after eviction at 0x{addr:08x}"
            )

        # Four hot lines fit in one set; first pass misses and the second pass
        # must hit. Cold lines use fresh tags and spread across nonreserved sets.
        hot_set = safe_sets[0]
        hot_addrs = [
            line_base(tag_base + 0x20 + index, hot_set) + (index * 8)
            for index in range(4)
        ]
        for addr in hot_addrs:
            await read(addr, seed, "hot-pool-prime")
        for addr in hot_addrs:
            await read(addr, seed, "hot-pool-hit")

        cold_addrs = [
            line_base(tag_base + 0x40 + index, rng.choice(safe_sets))
            + (rng.randrange(8) * 8)
            for index in range(64)
        ]

        # Two independent word transactions at a 64-byte line boundary.
        # The pair is consecutive on the bus so coverage records the boundary.
        boundary_line = line_base(tag_base + 0x100, boundary_set)
        boundary_addrs = (boundary_line + 0x38, boundary_line + 0x40)
        for addr in boundary_addrs:
            await write(addr, rng.getrandbits(64), 0xFF, seed, "boundary-pair")
        for addr in boundary_addrs:
            await read(addr, seed, "boundary-readback")

        # A minimum MMIO quota prevents a huge cache address space from making
        # bypass traffic statistically disappear.
        mmio_addrs = [
            0x30000000 + seed_index * 0x1000 + index * 8
            for index in range(8)
        ]
        for addr in mmio_addrs:
            mask = rng.choice((0xFF, 0x0F, 0x55, 0x80))
            await write(addr, rng.getrandbits(64), mask, seed, "mmio-quota")
            await read(addr, seed, "mmio-readback")

        hot_pool = hot_addrs
        conflict_pool = dirty_addrs + [dirty_victim]
        boundary_pool = list(boundary_addrs)
        classes = ("hot", "cold", "conflict", "boundary", "mmio")
        weights = (40, 30, 15, 8, 7)
        partial_masks = (0x01, 0x03, 0x0F, 0x55, 0x80, 0xAA)

        for operation_index in range(operations_per_seed):
            address_class = rng.choices(classes, weights=weights, k=1)[0]
            if address_class == "hot":
                addr = rng.choice(hot_pool)
            elif address_class == "cold":
                addr = rng.choice(cold_addrs)
            elif address_class == "conflict":
                addr = rng.choice(conflict_pool)
            elif address_class == "boundary":
                addr = rng.choice(boundary_pool)
            else:
                addr = rng.choice(mmio_addrs)

            phase = f"random-{operation_index}-{address_class}"
            if rng.random() < 0.5:
                mask = 0xFF if rng.random() < 0.6 else rng.choice(partial_masks)
                await write(addr, rng.getrandbits(64), mask, seed, phase)
                # Read-after-write makes every generated store immediately
                # observable; later conflict traffic also checks writeback.
                await read(addr, seed, phase + "-readback")
            else:
                await read(addr, seed, phase)

    missing = [
        goal for goal in CacheCoverage.MEGA_RANDOM_GOALS
        if not env.coverage.bins.get(goal, 0)
    ]
    assert not missing, "mega-random coverage goal(s) missed: " + ", ".join(missing)
    assert env.mem_agent.protocol_checker.stall_cycles_by_channel.get("req", 0) > 0, (
        "mega random did not backpressure cache memory requests"
    )
    assert env.mmio_agent.protocol_checker.stall_cycles_by_channel.get("req", 0) > 0, (
        "mega random did not backpressure MMIO requests"
    )
