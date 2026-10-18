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


async def measure_reads(env, name, addresses, description):
    """Measure accepted CPU demand reads and RTL cycles for one cold-cache trace."""
    tb = env.testbench
    await tb.reset(pulse_cycles=2, recovery_cycles=128)
    properties = tb.properties
    properties.clear_cache_metrics()
    start_cycle = properties.sampled_cycles

    for addr in addresses:
        await env.cpu.block_read(addr)

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
    return {
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


@pytest.mark.benchmark
@case
async def test_dcache_performance_benchmark(start_func):
    """Run hot-line, cache-fitting, and same-set conflict read patterns."""
    env = await start_func()

    hot_addr = 0x1000
    hot = await measure_reads(
        env,
        "hot_line",
        [hot_addr] * 64,
        "64 repeated reads of one cold line; first access fills the line.",
    )
    assert (hot["hits"], hot["misses"]) == (63, 1)

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

    # NutShell's 32 KiB, 4-way, 64 B geometry has 128 sets. Adding 8 KiB
    # preserves the set index while changing the tag, producing five lines in
    # one set and exposing conflict behavior beyond the four-way capacity.
    conflict_set = 0x100000
    conflict_lines = [conflict_set + way * (CACHE_BYTES // WAYS) for way in range(5)]
    conflict_trace = conflict_lines * 5
    conflict = await measure_reads(
        env,
        "five_way_conflict",
        conflict_trace,
        "Five tags mapped to one 4-way set, replayed for five sweeps.",
    )
    assert conflict["accesses"] == 25
    assert conflict["misses"] >= 5

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
        "scenarios": [hot, fit, conflict],
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\nDCACHE_BENCHMARK_JSON=" + json.dumps(result, sort_keys=True))
