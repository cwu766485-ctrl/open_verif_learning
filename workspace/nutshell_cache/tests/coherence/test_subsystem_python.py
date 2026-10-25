"""First Python/Toffee end-to-end MESI smoke test for the dual-L1 subsystem."""

import csv
import json
import math
from pathlib import Path

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, case, fixture

from dv.agents.coherent_cpu_agent import CpuRequest, DualCoreCpuDriver
from dv.agents.line_memory_axi_agent import LineMemoryAxiAgent
from dv.coverage.coherence_coverage import CoherenceCoverage
from dv.monitors.cache_perf_monitor import CachePerfMonitor
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard

try:
    from coherent_python import DUTCoherentCachePythonWrapper
except ImportError:
    DUTCoherentCachePythonWrapper = None


@fixture
async def coherent_env(toffee_request: ToffeeRequest):
    if DUTCoherentCachePythonWrapper is None:
        pytest.skip("run make coherence_python_build before the subsystem Python test")
    dut = toffee_request.create_dut(DUTCoherentCachePythonWrapper, "clock")
    async def start(response_delay=2):
        memory = LineMemoryAxiAgent(dut, response_delay=response_delay)
        perf = CachePerfMonitor(dut)
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        dut.cpu_req_valid.value = 0
        dut.cpu_resp_ready.value = 0
        dut.mem_rd_req_ready.value = 0
        dut.mem_rd_data_valid.value = 0
        dut.mem_wr_req_ready.value = 0
        dut.mem_wr_data_ready.value = 0
        dut.mem_wr_rsp_valid.value = 0
        start_clock(dut)
        await ClockCycles(dut, 4)
        dut.reset.value = 0
        async with Executor(exit="none") as executor:
            executor(memory.run(), sche_group="line_memory")
            executor(perf.run(), sche_group="perf_monitor")
        return dut, memory, perf

    return start


@case
async def test_dual_core_owner_transfer_and_data_visibility(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    addr = 0x4010
    initial = memory.word(addr, (addr >> 3) & 7)
    scoreboard = CoherenceScoreboard()
    scoreboard.seed_word(addr, initial)

    response = await cpu.access(0, addr)
    scoreboard.observe(0, addr, response_data=response)
    assert len(memory.read_requests) == 1

    # A second core reads the line while core0 owns it. The directory should
    # obtain the current line from the owner instead of issuing another DRAM read.
    response = await cpu.access(1, addr)
    scoreboard.observe(1, addr, response_data=response)
    assert len(memory.read_requests) == 1

    updated = 0xD00DFEED12345678
    write_response = await cpu.access(1, addr, write=True, data=updated)
    scoreboard.observe(1, addr, write=True, write_data=updated,
                       response_data=write_response)
    response = await cpu.access(0, addr)
    scoreboard.observe(0, addr, response_data=response)
    scoreboard.assert_covered("cold_read", "remote_read_from_E",
                              "shared_upgrade", "remote_read_from_M")
    assert len(memory.read_requests) == 1
    assert int(dut.protocol_error.value) == 0


@case
async def test_python_parallel_misses_l2_hit_and_dirty_writeback(coherent_env):
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    coverage = CoherenceCoverage()

    # One packed driver accepts two independent cold misses in the same window.
    parallel = await cpu.access_pair(
        CpuRequest(0x0020_4100), CpuRequest(0x0020_8100)
    )
    coverage.sample_external("parallel_cold_miss_pair")
    for core, addr, result in ((0, 0x0020_4100, parallel[0]),
                               (1, 0x0020_8100, parallel[1])):
        expected = memory.word(addr, (addr >> 3) & 7)
        model.seed_word(addr, expected)
        model.observe(core, addr, response_data=result)
        assert result == expected
    assert len(memory.read_requests) == 2

    # Core1 reads Core0's E line, then Core0 upgrades S->M with a byte mask.
    addr = 0x0020_4100
    response = await cpu.access(1, addr)
    model.observe(1, addr, response_data=response)
    old_word = model.word(addr)
    update = 0x1122334455667788
    mask = 0b01010101
    await cpu.access(0, addr, write=True, data=update, mask=mask)
    model.observe(0, addr, write=True, write_data=update, write_mask=mask)
    merged = model.word(addr)
    response = await cpu.access(1, addr)
    model.observe(1, addr, response_data=response)
    assert response == merged and response != old_word
    coverage.sample_external("byte_mask_write")

    # Five addresses share L1 and L2 set indices. The L1 copy of the first
    # line is replaced while its inclusive L2 copy remains available.
    l2_before = perf.snapshot()
    reads_before = len(memory.read_requests)
    l2_addr = 0x0040_1000
    for way in range(5):
        address = l2_addr + way * 32768
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        result = await cpu.access(0, address)
        model.observe(0, address, response_data=result)
        assert result == expected
    assert model.l1_way_view(0, l2_addr) is None
    result = await cpu.access(0, l2_addr)
    model.observe(0, l2_addr, response_data=result)
    assert result == memory.word(l2_addr, (l2_addr >> 3) & 7)
    l2_after = perf.snapshot()
    assert len(memory.read_requests) == reads_before + 5
    assert l2_after["l2_refill_hit"] > l2_before["l2_refill_hit"]

    # Keep four M lines live in each L1 for one L2 set. The ninth line first
    # performs Core0's local PutM, then forces L2 to invalidate a still-live
    # Core1 owner, collect its data, and write the victim to memory.
    dirty_base = 0x0080_2000
    expected_values = {}
    for n in range(9):
        line_addr = dirty_base + n * 32768
        value = 0xCAFE000000000000 | n
        core = 0 if n < 4 or n == 8 else 1
        await cpu.access(core, line_addr, write=True, data=value)
        model.seed_word(line_addr, memory.word(line_addr, 0))
        model.observe(core, line_addr, write=True, write_data=value,
                      write_mask=0xFF)
        expected_values[line_addr] = value
    assert memory.write_requests, "dirty L2 replacement should issue a writeback"
    assert memory.write_beats >= 8
    assert int(dut.protocol_error.value) == 0

    first = memory.write_requests[0][0]
    assert first in expected_values
    assert not model.l2_contains(first)
    reads_before = len(memory.read_requests)
    result = await cpu.access(1, first)
    model.observe(1, first, response_data=result)
    assert result == expected_values[first]
    assert len(memory.read_requests) > reads_before
    assert len(memory.write_responses) == len(memory.write_requests)
    coverage.sample_external("dirty_writeback", len(memory.write_requests))
    coverage.sample_external("write_response", len(memory.write_responses))

    coverage.observe_model(model)
    coverage.require("cold_read", "remote_read_from_E", "shared_upgrade",
                     "remote_read_from_M", "l2_refill_hit", "l2_refill_miss",
                     "l1_eviction", "l2_live_eviction", "parallel_cold_miss_pair",
                     "byte_mask_write", "dirty_writeback", "write_response")
    assert coverage.l2_live_evictions >= 1, "live inclusive L2 eviction was not modeled"
    coverage_path = (Path(__file__).resolve().parents[2] / "benchmarks" /
                     "results" / "coherence_python_functional_coverage.json")
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(json.dumps(coverage.to_dict(), indent=2) + "\n",
                             encoding="utf-8")


def _p95(samples):
    if not samples:
        return None
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


@pytest.mark.asyncio
@case
@pytest.mark.benchmark
async def test_coherence_benchmark_v2(coherent_env):
    """Run deterministic dual-core workloads at 2/20/50/100-cycle memory delay."""
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    rows = []

    async def measure(name, delay, initial_state, ops, workload):
        memory.response_delay = delay
        before_perf = perf.snapshot()
        before_read_req = len(memory.read_requests)
        before_write_req = len(memory.write_requests)
        before_read_beats = memory.read_beats
        before_write_beats = memory.write_beats
        before_latencies = (len(cpu.latencies[0]), len(cpu.latencies[1]))
        await workload()
        after_perf = perf.snapshot()
        after_read_req = len(memory.read_requests)
        after_write_req = len(memory.write_requests)
        after_read_beats = memory.read_beats
        after_write_beats = memory.write_beats
        samples = (cpu.latencies[0][before_latencies[0]:] +
                   cpu.latencies[1][before_latencies[1]:])
        delta = {key: after_perf[key] - before_perf[key]
                 for key in before_perf}
        cycles = delta["cycles"]
        l1_hits = delta["l1_hit_core0"] + delta["l1_hit_core1"]
        l1_misses = delta["l1_miss_core0"] + delta["l1_miss_core1"]
        l2_hits = delta["l2_refill_hit"]
        l2_misses = delta["l2_refill_miss"]
        read_beats = after_read_beats - before_read_beats
        write_beats = after_write_beats - before_write_beats
        read_bytes = read_beats * 8
        write_bytes = write_beats * 8
        total_bytes = read_bytes + write_bytes
        row = {
            "workload": name,
            "memory_response_latency_cycles": delay,
            "seed": 0,
            "initial_cache_state": initial_state,
            "ops": ops,
            "window_cycles": cycles,
            "mean_req_to_resp_cycles": (sum(samples) / len(samples)
                                        if samples else None),
            "p95_req_to_resp_cycles": _p95(samples),
            "ops_per_cycle": _rate(ops, cycles),
            "l1_hit_count": l1_hits,
            "l1_miss_count": l1_misses,
            "l1_hit_rate": _rate(l1_hits, l1_hits + l1_misses),
            "l1_miss_rate": _rate(l1_misses, l1_hits + l1_misses),
            "l1_core0_hit_count": delta["l1_hit_core0"],
            "l1_core0_miss_count": delta["l1_miss_core0"],
            "l1_core1_hit_count": delta["l1_hit_core1"],
            "l1_core1_miss_count": delta["l1_miss_core1"],
            "l2_refill_hit_count": l2_hits,
            "l2_refill_miss_count": l2_misses,
            "l2_refill_hit_rate": _rate(l2_hits, l2_hits + l2_misses),
            "l2_refill_miss_rate": _rate(l2_misses, l2_hits + l2_misses),
            "snoops": delta["snoops"],
            "dirty_writebacks": delta["dirty_writebacks"],
            "memory_read_lines": after_read_req - before_read_req,
            "memory_write_lines": after_write_req - before_write_req,
            "memory_read_bytes": read_bytes,
            "memory_write_bytes": write_bytes,
            "memory_read_bytes_per_cycle": _rate(read_bytes, cycles),
            "memory_write_bytes_per_cycle": _rate(write_bytes, cycles),
            "memory_total_bytes_per_cycle": _rate(total_bytes, cycles),
            "memory_read_mib_per_second": (
                _rate(read_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "memory_write_mib_per_second": (
                _rate(write_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "memory_total_mib_per_second": (
                _rate(total_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "paired_vs_serialized_speedup": None,
        }
        rows.append(row)
        print("COHERENCE_BENCHMARK_V2," + json.dumps(row, sort_keys=True))

    for latency_index, delay in enumerate((2, 20, 50, 100)):
        # Use separate L2 set ranges per latency point so earlier delay runs
        # cannot evict the retained L2-hit line of a later point.
        base = 0x10000000 + latency_index * 0x2000

        warm = base
        await cpu.access(0, warm)
        async def warm_reads(addr=warm):
            for _ in range(64):
                await cpu.access(0, addr)
        await measure("warm_l1_reads", delay,
                      "Core0 line resident before the 64 measured reads", 64,
                      warm_reads)

        l2_addr = base + 0x1000
        await cpu.access(0, l2_addr)
        for way in range(1, 5):
            await cpu.access(0, l2_addr + way * 32768)
        async def l2_read(addr=l2_addr):
            await cpu.access(0, addr)
        await measure("l2_hit_after_l1_replacement", delay,
                      "L1 line replaced by four same-index lines; inclusive L2 copy retained",
                      1, l2_read)

        serial_base = base + 0x40000
        async def serialized_cold():
            for n in range(16):
                await cpu.access(0, serial_base + 64 * n)
        await measure("serialized_cold_misses", delay,
                      "16 distinct lines absent from both L1s and shared L2", 16,
                      serialized_cold)

        parallel_base = base + 0x80000
        async def parallel_cold():
            for n in range(8):
                await cpu.access_pair(
                    CpuRequest(parallel_base + 128 * n),
                    CpuRequest(parallel_base + 128 * n + 64),
                )
        await measure("parallel_dual_l1_cold_misses", delay,
                      "16 distinct lines absent from both L1s and shared L2; paired issue",
                      16, parallel_cold)

        ping_addr = base + 0xC0000
        await cpu.access(0, ping_addr, write=True, data=0x1000 + delay)
        async def ownership_ping_pong(addr=ping_addr):
            for n in range(16):
                await cpu.access(n & 1, addr, write=True,
                                 data=0xA0000000 + delay * 32 + n)
        await measure("ownership_write_ping_pong", delay,
                      "Core0 owns the line in M before alternating core stores",
                      16, ownership_ping_pong)


    # Run the dirty victim last. It deliberately leaves an evicted dirty line
    # in the backing memory, so it must not alter the starting state of the
    # cold-miss workloads at the other latency points.
    delay = 100
    dirty_base = 0x00802000
    for n in range(8):
        owner = 0 if n < 4 else 1
        await cpu.access(owner, dirty_base + n * 32768, write=True,
                         data=0xD17A0000 + delay * 16 + n)
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error during dirty-set setup line {n} at delay {delay}"
        )

    async def dirty_l2_victim(addr=dirty_base + 8 * 32768,
                              value=0xD17A0000 + delay * 16 + 8):
        await cpu.access(0, addr, write=True, data=value)
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error after dirty L2 victim at delay {delay}"
        )
    await measure("dirty_l2_victim_writeback", delay,
                  "Eight same-set M lines live across both L1s; ninth line triggers L2 victim writeback",
                  1, dirty_l2_victim)

    # The serialized and paired runs carry the same 16 cold misses per latency
    # point. Report the measured overlap benefit without assuming a speedup.
    by_key = {(r["memory_response_latency_cycles"], r["workload"]): r
              for r in rows}
    for row in rows:
        if row["workload"] == "parallel_dual_l1_cold_misses":
            serial = by_key[(row["memory_response_latency_cycles"],
                             "serialized_cold_misses")]
            row["paired_vs_serialized_speedup"] = _rate(
                serial["window_cycles"], row["window_cycles"]
            )

    result_dir = Path(__file__).resolve().parents[2] / "benchmarks" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    json_path = result_dir / "coherence_benchmark_v2.json"
    csv_path = result_dir / "coherence_benchmark_v2.csv"
    payload = {
        "schema_version": 2,
        "dut": "CoherentCacheSubsystem via Picker/Verilator",
        "clock_period_ns": 10,
        "memory_model": "64-byte writable line model; response delay is a simulation parameter",
        "metric_definitions": {
            "l1_hit_miss": "accepted CPU request classified by L1 MESI state; S-store is a miss/upgrade",
            "l2_refill_hit_miss": "accepted Directory L2 refill lookup; not a count of all metadata probes",
            "memory_bandwidth": "accepted 64-bit R/W line beats times eight bytes, divided by benchmark cycles",
            "ops_per_cycle": "completed CPU operations divided by the measured window cycles",
        },
        "results": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # These checks also validate that an L2-hit workload is really a refill
    # hit without another backing-memory transaction, and that ping-pong snoops.
    for row in rows:
        if row["workload"] == "l2_hit_after_l1_replacement":
            assert row["l1_miss_count"] == 1
            assert row["l2_refill_hit_count"] >= 1
            assert row["memory_read_lines"] == 0
        if row["workload"] == "ownership_write_ping_pong":
            assert row["snoops"] > 0
        if row["workload"] == "dirty_l2_victim_writeback":
            assert row["snoops"] > 0
            assert row["dirty_writebacks"] > 0
            assert row["memory_write_lines"] > 0
