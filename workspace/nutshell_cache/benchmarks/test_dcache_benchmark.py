"""Cycle-based DCache microbenchmarks using the maintained RTL DUT."""

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from toffee import ClockCycles
from toffee_test import case

from base_test import *  # noqa: F401,F403 - supplies the Toffee start_func fixture


RESULT_PATH = Path("benchmarks/results/dcache_baseline.json")
CACHE_BYTES = 32 * 1024
WAYS = 4
LINE_BYTES = 64


async def measure_reads(env, name, addresses, description, capture_miss_trace=False):
    """Measure accepted CPU demand reads and RTL cycles for one cold-cache trace."""
    tb = env.testbench
    await tb.reset(pulse_cycles=2, recovery_cycles=128)
    properties = tb.properties
    properties.clear_cache_metrics()
    start_cycle = properties.sampled_cycles

    miss_trace = []
    for addr in addresses:
        misses_before = properties.cache_misses
        await env.cpu.block_read(addr)
        if capture_miss_trace:
            miss_trace.append(properties.cache_misses != misses_before)

    # Each access event is observed before its CPU response is returned. Check
    # accounting here so a monitor scheduling regression cannot silently skew
    # the result.
    end_cycle = properties.sampled_cycles
    access_count = properties.cache_accesses
    hits = properties.cache_hits
    misses = properties.cache_misses
    assert access_count == len(addresses), (
        f"{name}: expected {len(addresses)} measured CPU accesses, got {access_count}"
    )
    assert hits + misses == access_count

    cycles = end_cycle - start_cycle
    result = {
        "name": name,
        "description": description,
        "accesses": access_count,
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / access_count, 6),
        "miss_rate": round(misses / access_count, 6),
        "rtl_cycles": cycles,
        "cycles_per_access": round(cycles / access_count, 6),
    }
    if capture_miss_trace:
        result["miss_trace"] = miss_trace
    return result


@pytest.mark.benchmark
@case
async def test_dcache_performance_benchmark(start_func):
    """Run representative locality, capacity, and conflict read patterns."""
    env = await start_func()

    hot_addr = 0x1000
    hot = await measure_reads(
        env,
        "hot_line",
        [hot_addr] * 64,
        "64 repeated reads of one cold line; first access fills the line.",
    )
    assert (hot["hits"], hot["misses"]) == (63, 1)

    # A contiguous scan issues one 8-byte load per word in each 64-byte line.
    # This 4 KiB trace stays short while preserving the line-locality pattern.
    stream_base = 0x40000
    stream_lines = 64
    sequential_addresses = [
        stream_base + line * LINE_BYTES + word * 8
        for line in range(stream_lines)
        for word in range(LINE_BYTES // 8)
    ]
    sequential = await measure_reads(
        env,
        "sequential_array_scan_4k",
        sequential_addresses,
        "One sequential 4 KiB array scan using 8-byte loads across 64-byte lines.",
    )
    assert (sequential["hits"], sequential["misses"]) == (448, 64)

    # 256 lines occupy 16 KiB, below the documented 32 KiB L1 DCache size.
    # The first pass is cold; the second pass should hit every warmed line.
    fit_addresses = [0x20000 + line * LINE_BYTES for line in range(256)]
    fit = await measure_reads(
        env,
        "working_set_fits",
        fit_addresses + fit_addresses,
        "Two sequential passes over 256 lines (16 KiB) in a cold 32 KiB DCache.",
    )
    assert (fit["hits"], fit["misses"]) == (256, 256)

    # A compact loop kernel revisits a 1 KiB array over four passes. The cold
    # first touch of each line accounts for 16 misses; all later loads hit.
    small_addresses = [
        0x60000 + line * LINE_BYTES + word * 8
        for line in range(16)
        for word in range(LINE_BYTES // 8)
    ]
    repeated = await measure_reads(
        env,
        "repeated_array_kernel_1k_4_passes",
        small_addresses * 4,
        "Four passes over a 1 KiB array using sequential 8-byte loads.",
    )
    assert (repeated["hits"], repeated["misses"]) == (496, 16)

    # NutShell's 32 KiB, 4-way, 64 B geometry has 128 sets. Adding 8 KiB
    # preserves the set index while changing the tag, producing five lines in
    # one set and exposing conflict behavior beyond the four-way capacity.
    conflict_set = 0x100000
    conflict_lines = [conflict_set + way * (CACHE_BYTES // WAYS) for way in range(5)]
    conflict_sweeps = 5
    conflict_trace = conflict_lines * conflict_sweeps
    conflict = await measure_reads(
        env,
        "five_way_conflict",
        conflict_trace,
        f"Five tags mapped to one 4-way set, replayed for {conflict_sweeps} sweeps.",
        capture_miss_trace=True,
    )
    assert conflict["accesses"] == 5 * conflict_sweeps
    miss_trace = conflict.pop("miss_trace")
    cold_misses = sum(miss_trace[:5])
    steady_state_misses = sum(miss_trace[5:])
    steady_state_accesses = len(miss_trace) - 5
    conflict["cold_first_sweep_misses"] = cold_misses
    conflict["steady_state_accesses"] = steady_state_accesses
    conflict["steady_state_hits"] = steady_state_accesses - steady_state_misses
    conflict["steady_state_misses"] = steady_state_misses
    conflict["steady_state_hit_rate"] = round(
        conflict["steady_state_hits"] / steady_state_accesses, 6
    )
    assert cold_misses == 5

    result = {
        "benchmark": "NutShell L1 DCache standalone RTL microbench",
        "measurement_source": "accepted Stage2-to-Stage3 CPU READ event; MMIO/coherence excluded",
        "cache": {
            "capacity_bytes": CACHE_BYTES,
            "ways": WAYS,
            "line_bytes": LINE_BYTES,
            "sets": CACHE_BYTES // WAYS // LINE_BYTES,
        },
        "clock_measurement": "sampled RTL rising-edge cycles; excludes reset sweep",
        "host": platform.platform(),
        "simulator": subprocess.check_output(["verilator", "--version"], text=True).strip(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenarios": [hot, sequential, fit, repeated, conflict],
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\nDCACHE_BENCHMARK_JSON=" + json.dumps(result, sort_keys=True))
