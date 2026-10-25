"""First Python/Toffee end-to-end MESI smoke test for the dual-L1 subsystem."""

import csv
import json
import math
import random
from pathlib import Path

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, case, fixture

from dv.agents.coherent_cpu_agent import CpuRequest, DualCoreCpuDriver
from dv.agents.line_memory_axi_agent import LineMemoryAxiAgent
from dv.coverage.coherence_coverage import CoherenceCoverage
from dv.monitors.cache_perf_monitor import CachePerfMonitor
from dv.monitors.snoop_data_monitor import SnoopDataMonitor
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard

try:
    from coherent_python import DUTCoherentCachePythonWrapper
except ImportError:
    DUTCoherentCachePythonWrapper = None

PYTHON_COVERAGE = CoherenceCoverage()
COVERAGE_PATH = (Path(__file__).resolve().parents[2] / "benchmarks" /
                 "results" / "coherence_python_functional_coverage.json")


def _record_model(model):
    PYTHON_COVERAGE.observe_model(model)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.write_text(json.dumps(PYTHON_COVERAGE.to_dict(), indent=2) + "\n",
                             encoding="utf-8")


@fixture
async def coherent_env(toffee_request: ToffeeRequest):
    if DUTCoherentCachePythonWrapper is None:
        pytest.skip("run make coherence_python_build before the subsystem Python test")
    dut = toffee_request.create_dut(DUTCoherentCachePythonWrapper, "clock")
    async def start(response_delay=2, *, backpressure_periods=None,
                    response_gap_periods=None):
        memory = LineMemoryAxiAgent(
            dut, response_delay=response_delay,
            backpressure_periods=backpressure_periods,
            response_gap_periods=response_gap_periods,
        )
        perf = CachePerfMonitor(dut)
        snoop_data = SnoopDataMonitor(dut)
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
            executor(snoop_data.run(), sche_group="snoop_data_monitor")
        memory.snoop_data = snoop_data
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
    _record_model(scoreboard)


@case
async def test_python_parallel_misses_l2_hit_and_dirty_writeback(coherent_env):
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()

    # One packed driver accepts two independent cold misses in the same window.
    parallel = await cpu.access_pair(
        CpuRequest(0x0020_4100), CpuRequest(0x0020_8100)
    )
    PYTHON_COVERAGE.sample_external("parallel_cold_miss_pair")
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
    PYTHON_COVERAGE.sample_external("byte_mask_write")

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
    PYTHON_COVERAGE.sample_external("dirty_writeback", len(memory.write_requests))
    PYTHON_COVERAGE.sample_external("write_response", len(memory.write_responses))

    _record_model(model)
    assert PYTHON_COVERAGE.l2_live_evictions >= 1, "live inclusive L2 eviction was not modeled"


@case
async def test_python_masked_stores_to_modified_line(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    address = 0x0020_0100
    model.seed_word(address, memory.word(address, (address >> 3) & 7))

    # The first partial store allocates the line with GetM; the second exercises
    # the silent M-hit store path and checks that untouched bytes are preserved.
    for value, mask in ((0xA5869770CC27FDBA, 0x3F),
                        (0xCD388E7C56F288BF, 0x40)):
        await cpu.access(0, address, write=True, data=value, mask=mask)
        model.observe(0, address, write=True, write_data=value,
                      write_mask=mask)
    independent_address = address + 0x40
    model.seed_word(independent_address,
                    memory.word(independent_address, (independent_address >> 3) & 7))
    snoop_cursor = len(memory.snoop_data.transfers)
    snoop_req_cursor = len(memory.snoop_data.snoops)
    result0, result1 = await cpu.access_pair(
        CpuRequest(independent_address), CpuRequest(address)
    )
    model.observe(0, independent_address, response_data=result0)
    memory.snoop_data.assert_directory_matches(model, independent_address)
    model.observe(1, address, response_data=result1)
    assert result1 == model.word(address)
    line = address & ~0x3F
    expected_line = [model.data.get(line + 8 * beat, memory.word(line, beat))
                     for beat in range(8)]
    assert any(item["line"] == line and item["core"] == 0 and item["opcode"] == 0
               for item in memory.snoop_data.snoops[snoop_req_cursor:])
    memory.snoop_data.assert_line_data(address, expected_line, since=snoop_cursor)
    memory.snoop_data.assert_directory_matches(model, address)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("byte_mask_m_hit")
    _record_model(model)


@case
async def test_python_memory_and_cpu_backpressure(coherent_env):
    dut, memory, _ = await coherent_env(
        response_delay=3,
        response_gap_periods={"read_data": 5},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()

    # Stall a CPU response after it becomes valid and verify the held payload.
    address = 0x0012_3450
    model.seed_word(address, memory.word(address, (address >> 3) & 7))
    memory.arm_stall("read_req", 2)
    result = await cpu.access(0, address, response_stall_cycles=4)
    model.observe(0, address, response_data=result)
    assert cpu.response_stall_cycles[0] >= 4

    # Dirty eight lines in one L2 set, then force a live inclusive victim.
    # Periodic ready deassertion stalls the line request and write-data paths.
    dirty_base = 0x0080_6000
    for index in range(8):
        line = dirty_base + index * 32768
        value = 0xBACC000000000000 | index
        core = 0 if index < 4 or index == 8 else 1
        model.seed_word(line, memory.word(line, 0))
        await cpu.access(core, line, write=True, data=value)
        model.observe(core, line, write=True, write_data=value,
                      write_mask=0xFF)

    # Arm two-cycle stalls before the ninth line causes the live dirty victim
    # write request and eight-beat write data stream.
    memory.arm_stall("write_req", 2)
    memory.arm_stall("write_data", 2)
    line = dirty_base + 8 * 32768
    value = 0xBACC000000000008
    model.seed_word(line, memory.word(line, 0))
    await cpu.access(0, line, write=True, data=value)
    model.observe(0, line, write=True, write_data=value, write_mask=0xFF)

    assert memory.stalls["read_req"] > 0
    assert memory.stalls["write_req"] > 0
    assert memory.stalls["write_data"] > 0
    assert memory.response_gaps["read_data"] > 0
    assert memory.write_beats >= 8
    assert len(memory.write_responses) == len(memory.write_requests)
    assert int(dut.protocol_error.value) == 0

    PYTHON_COVERAGE.sample_external("cpu_response_backpressure",
                                    cpu.response_stall_cycles[0])
    PYTHON_COVERAGE.sample_external("memory_read_request_backpressure",
                                    memory.stalls["read_req"])
    PYTHON_COVERAGE.sample_external("memory_write_request_backpressure",
                                    memory.stalls["write_req"])
    PYTHON_COVERAGE.sample_external("memory_write_data_backpressure",
                                    memory.stalls["write_data"])
    PYTHON_COVERAGE.sample_external("memory_read_response_gaps",
                                    memory.response_gaps["read_data"])
    _record_model(model)


@case
async def test_python_reset_cancels_active_refill(coherent_env):
    dut, memory, _ = await coherent_env(response_delay=80)
    cpu = DualCoreCpuDriver(dut)
    address = 0x0018_9020
    prior_requests = len(memory.read_requests)

    # Submit a cold miss and wait for the memory agent to accept its line read.
    dut.cpu_req_addr.value = address
    dut.cpu_req_write.value = 0
    dut.cpu_req_wmask.value = 0xFF
    dut.cpu_req_wdata.value = 0
    dut.cpu_resp_ready.value = 0
    dut.cpu_req_valid.value = 1
    accepted = False
    for _ in range(40):
        await ClockCycles(dut, 1)
        if int(dut.cpu_req_ready.value) & 1:
            accepted = True
            break
    dut.cpu_req_valid.value = 0
    assert accepted, "cold miss was not accepted before reset"
    for _ in range(40):
        if len(memory.read_requests) > prior_requests:
            break
        await ClockCycles(dut, 1)
    assert len(memory.read_requests) > prior_requests, "refill did not reach memory"

    dut.reset.value = 1
    await ClockCycles(dut, 3)
    dut.reset.value = 0
    assert memory.reset_cancelled["reads"] > 0
    await ClockCycles(dut, 140)
    for _ in range(5):
        await ClockCycles(dut, 1)
        assert int(dut.cpu_resp_valid.value) == 0, "reset leaked a stale CPU response"

    # The reset canceled the cache transaction, not backing-memory contents or
    # the ability to issue the same line again.
    model = CoherenceScoreboard()
    model.seed_word(address, memory.word(address, (address >> 3) & 7))
    result = await cpu.access(0, address)
    model.observe(0, address, response_data=result)
    assert result == memory.word(address, (address >> 3) & 7)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("reset_during_refill")
    _record_model(model)


@pytest.mark.parametrize("seed", [0x1A2B, 0x5EED, 0xC0FFEE, 0xD15EA5E])
@case
async def test_python_seeded_randomized_coherence(coherent_env, seed):
    dut, memory, _ = await coherent_env(response_delay=seed % 5 + 1)
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    rng = random.Random(seed)
    addresses = [0x0200_0000 + index * 64 for index in range(12)]

    def request_for(address):
        write = rng.random() < 0.4
        return CpuRequest(
            address, write=write,
            data=rng.getrandbits(64) if write else 0,
            mask=rng.randrange(1, 256) if write else 0xFF,
        )

    def seed_if_needed(address):
        word_address = address & ~0x7
        if word_address not in model.data:
            model.seed_word(address, memory.word(address, (address >> 3) & 7))

    operations = 36
    history = []
    for index in range(operations):
        if index % 6 == 5:
            # Distinct lines allow the two lanes to be checked independently
            # even if the subsystem retires their responses out of order.
            first, second = rng.sample(addresses, 2)
            req0, req1 = request_for(first), request_for(second)
            seed_if_needed(first)
            seed_if_needed(second)
            if (not req1.write and model.states[req1.addr & ~0x3F][0] == "M"):
                # Check the latest owner word locally before exercising a
                # simultaneous independent miss and remote GetS.
                owner_data = await cpu.access(0, req1.addr)
                model.observe(0, req1.addr, response_data=owner_data)
            snoop_cursor = len(memory.snoop_data.transfers)
            snoop_req_cursor = len(memory.snoop_data.snoops)
            dir_commit_cursor = len(memory.snoop_data.directory_commits)
            result0, result1 = await cpu.access_pair(req0, req1)
            if (not req1.write and
                    model.states[req1.addr & ~0x3F][0] == "M"):
                line = req1.addr & ~0x3F
                expected_line = [model.data.get(
                    line + 8 * beat, memory.word(line, beat))
                    for beat in range(8)]
                owner_snoops = [
                    item for item in memory.snoop_data.snoops[snoop_req_cursor:]
                    if item["line"] == line and item["core"] == 0
                ]
                assert owner_snoops and owner_snoops[-1]["opcode"] == 0, (
                    f"remote read of Core0 M line {line:#x} must issue SnoopRead; "
                    f"observed {owner_snoops}"
                )
                memory.snoop_data.assert_line_data(
                    req1.addr, expected_line, since=snoop_cursor)
            for core, req, result in ((0, req0, result0), (1, req1, result1)):
                history.append((index, core, req.addr, req.write, req.data,
                                req.mask, result))
                try:
                    model.observe(core, req.addr, write=req.write,
                                  write_data=req.data, write_mask=req.mask,
                                  response_data=result)
                    memory.snoop_data.assert_directory_matches(model, req.addr)
                except AssertionError as error:
                    line_snoops = [
                        item for item in memory.snoop_data.snoops
                        if item["line"] == (req.addr & ~0x3F)
                    ]
                    line_commits = [
                        item for item in memory.snoop_data.directory_commits
                        if item["line"] == (req.addr & ~0x3F)
                    ]
                    raise AssertionError(
                        f"seed={seed:#x}, recent operations={history[-12:]}, "
                        f"new snoops={memory.snoop_data.snoops[snoop_req_cursor:]}, "
                        f"new dir commits="
                        f"{memory.snoop_data.directory_commits[dir_commit_cursor:]}, "
                        f"line snoops={line_snoops}, "
                        f"line commits={line_commits}, "
                        f"new owner-data={memory.snoop_data.transfers[snoop_cursor:]}"
                    ) from error
                if req.write:
                    readback = await cpu.access(core, req.addr)
                    history.append((index, core, req.addr, False, 0, 0xFF,
                                    readback))
                    model.observe(core, req.addr, response_data=readback)
                    memory.snoop_data.assert_directory_matches(model, req.addr)
            PYTHON_COVERAGE.sample_external("random_dual_lane_pairs")
        else:
            core = rng.randrange(2)
            address = rng.choice(addresses)
            req = request_for(address)
            seed_if_needed(address)
            result = await cpu.access(core, req.addr, write=req.write,
                                      data=req.data, mask=req.mask)
            history.append((index, core, req.addr, req.write, req.data,
                            req.mask, result))
            try:
                model.observe(core, req.addr, write=req.write,
                              write_data=req.data, write_mask=req.mask,
                              response_data=result)
                memory.snoop_data.assert_directory_matches(model, req.addr)
            except AssertionError as error:
                raise AssertionError(
                    f"seed={seed:#x}, recent operations={history[-12:]}"
                ) from error
            if req.write:
                readback = await cpu.access(core, req.addr)
                history.append((index, core, req.addr, False, 0, 0xFF,
                                readback))
                model.observe(core, req.addr, response_data=readback)
                memory.snoop_data.assert_directory_matches(model, req.addr)

    model.assert_covered("cold_read", "cold_write", "read_hit", "write_hit")
    assert int(dut.protocol_error.value) == 0, f"protocol error for seed={seed:#x}"
    PYTHON_COVERAGE.sample_external("randomized_seeded_regression")
    PYTHON_COVERAGE.sample_external("randomized_cpu_operations", operations)
    _record_model(model)


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
