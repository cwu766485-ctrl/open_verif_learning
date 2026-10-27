"""First Python/Toffee end-to-end MESI smoke test for the dual-L1 subsystem."""

import csv
import asyncio
import json
import os
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
COVERAGE_PATH = Path(os.environ.get(
    "COHERENCE_COVERAGE_PATH",
    str(Path(__file__).resolve().parents[2] / "benchmarks" / "results" /
        "coherence_python_functional_coverage.json"),
))


def _randomized_seeds():
    count = int(os.environ.get("COHERENCE_STRESS_SEED_COUNT", "0"))
    if count <= 0:
        return (0x1A2B, 0x5EED, 0xC0FFEE, 0xD15EA5E)
    if not 1 <= count <= 50:
        raise ValueError("COHERENCE_STRESS_SEED_COUNT must be in [1, 50]")
    # Keep the minimized Directory lookup race replay first, then add stable,
    # independent seeds so a failing case can be replayed from its pytest ID.
    return (0x5EED,) + tuple(0xA0000000 + index * 0x9E3779B9
                             for index in range(count - 1))


def _record_model(model):
    PYTHON_COVERAGE.observe_model(model)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.write_text(json.dumps(PYTHON_COVERAGE.to_dict(), indent=2) + "\n",
                             encoding="utf-8")


_PUT_OPCODES = {0b011, 0b100, 0b101}
_PUT_OPCODE_BY_STATE = {"S": 0b011, "E": 0b100, "M": 0b101}


def _assert_replacement_put_trace(model, memory, *, model_cursor=0,
                                  request_cursor=0):
    """Compare independently predicted L1 victims with accepted Put traffic."""
    expected = [
        (item["core"], item["line"], _PUT_OPCODE_BY_STATE[item["state"]])
        for item in model.l1_evictions[model_cursor:]
        if item.get("state") in _PUT_OPCODE_BY_STATE
    ]
    actual = [
        (item["core"], item["line"], item["opcode"])
        for item in memory.snoop_data.directory_requests[request_cursor:]
        if item["opcode"] in _PUT_OPCODES
    ]
    assert actual == expected, (
        "L1 replacement victim/Put mismatch: "
        f"accepted={actual}, independently predicted={expected}"
    )
    return actual


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


async def _model_access(cpu, model, snoop_data, core, addr, *, write=False,
                        data=0, mask=0xFF, response_stall_cycles=0):
    """Execute one CPU operation and update only from accepted protocol traffic."""
    put_cursor = len(snoop_data.directory_requests)
    result = await cpu.access(core, addr, write=write, data=data, mask=mask,
                              response_stall_cycles=response_stall_cycles)
    for event in snoop_data.directory_requests[put_cursor:]:
        if event["opcode"] in _PUT_OPCODES:
            model.observe_l1_put(event["core"], event["line"], event["opcode"])
    if write:
        model.observe(core, addr, write=True, write_data=data, write_mask=mask)
    else:
        model.observe(core, addr, response_data=result)
    return result


@case
async def test_python_l1_replacement_victim_matches_put(coherent_env):
    """Check the reference replacement way against the accepted Put line."""
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    base = 0x0060_4000
    line_stride = 32768  # same 4-way L1 set; distinct tags
    request_cursor = len(memory.snoop_data.directory_requests)

    for index in range(6):
        address = base + index * line_stride
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        response = await cpu.access(0, address)
        assert response == expected
        model.observe(0, address, response_data=response)

    matched = _assert_replacement_put_trace(model, memory,
                                            request_cursor=request_cursor)
    assert len(matched) == 2
    assert [line for _, line, _ in matched] == [base, base + line_stride]
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("l1_replacement_put_match")
    _record_model(model)


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

    # Force a shared S victim from an 8-way L2 set. Both L1s retain the seventh
    # line as S while the ninth line allocates, so both copies must be invalidated.
    shared_base = 0x0100_0000
    shared_target = shared_base + 6 * 32768
    shared_lines = [shared_base + index * 32768 for index in range(9)]
    for index in range(6):
        core = 0 if index < 3 else 1
        address = shared_lines[index]
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        response = await cpu.access(core, address)
        assert response == expected
        model.observe(core, address, response_data=response)

    for core in (0, 1):
        expected = memory.word(shared_target, (shared_target >> 3) & 7)
        model.seed_word(shared_target, expected)
        response = await cpu.access(core, shared_target)
        assert response == expected
        model.observe(core, shared_target, response_data=response)
        memory.snoop_data.assert_directory_matches(model, shared_target)

    address = shared_lines[7]
    expected = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, expected)
    response = await cpu.access(0, address)
    assert response == expected
    model.observe(0, address, response_data=response)
    assert model.states[shared_target] == ["S", "S"]
    assert model.l1_way_view(0, shared_target) is not None
    assert model.l1_way_view(1, shared_target) is not None

    set_index = model._l2_set(shared_target)
    predicted_victim = model.l2_ways[set_index][model.l2_next_way[set_index] % 8]
    assert predicted_victim == shared_target
    shared_expected_words = [memory.word(shared_target, beat)
                             for beat in range(8)]
    snoop_cursor = len(memory.snoop_data.snoops)
    write_cursor = len(memory.write_requests)
    address = shared_lines[8]
    expected = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, expected)
    response = await cpu.access(0, address)
    assert response == expected
    model.observe(0, address, response_data=response)

    shared_victims = [item for item in model.l2_evictions
                      if item["line"] == shared_target and item["state"] == "S"]
    assert {item["core"] for item in shared_victims} == {0, 1}
    assert {item["core"] for item in memory.snoop_data.snoops[snoop_cursor:]
            if item["line"] == shared_target} == {0, 1}
    if any((write[0] & ~0x3F) == shared_target
           for write in memory.write_requests[write_cursor:]):
        # An E→S owner transfer may conservatively mark the L2 data dirty;
        # if it writes back, verify every beat rather than requiring no AW.
        assert tuple(memory._read_word(shared_target, beat)
                     for beat in range(8)) == tuple(shared_expected_words)
    assert not model.l2_contains(shared_target)
    memory.snoop_data.assert_directory_matches(model, shared_target)
    PYTHON_COVERAGE.sample_external("l2_shared_victim_back_invalidation")

    _record_model(model)
    assert PYTHON_COVERAGE.l2_live_evictions >= 1, "live inclusive L2 eviction was not modeled"


@pytest.mark.parametrize("owner_core", [0, 1])
@case
async def test_clean_snoop_overlaps_l2_fill_stream(coherent_env, owner_core):
    """A clean invalidate on another set must not wait for the refill writer."""
    dut, memory, _ = await coherent_env(response_delay=2)
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    other_core = 1 - owner_core
    owner_addr = 0x0020_3000
    refill_addr = 0x0020_2000
    store_data = 0xC1EA_5EED_7654_3210
    model.seed_word(owner_addr, memory.word(owner_addr, (owner_addr >> 3) & 7))

    first = await cpu.access(owner_core, owner_addr)
    assert first == model.word(owner_addr)
    model.observe(0, owner_addr, response_data=first)
    second = await cpu.access(other_core, owner_addr)
    assert second == model.word(owner_addr)
    model.observe(1, owner_addr, response_data=second)
    memory.snoop_data.assert_directory_matches(model, owner_addr)

    d = dut
    d.cpu_resp_ready.value = 0
    snoop_start = len(memory.snoop_data.snoops)

    async def issue(core, address, *, write=False, data=0):
        bit = 1 << core
        d.cpu_req_valid.value = bit
        d.cpu_req_addr.value = (address & 0xFFFFFFFF) << (32 * core)
        d.cpu_req_write.value = bit if write else 0
        d.cpu_req_wmask.value = (0xFF << (8 * core)) if write else 0
        d.cpu_req_wdata.value = (data & ((1 << 64) - 1)) << (64 * core)
        for _ in range(200):
            await ClockCycles(d, 1)
            if int(d.cpu_req_ready.value) & bit:
                accepted_cycle = memory.snoop_data.cycle
                d.cpu_req_valid.value = 0
                return accepted_cycle
        d.cpu_req_valid.value = 0
        raise TimeoutError(f"core{core} request {address:#x} was not accepted")

    async def response(core, address, *, write=False, expected=None):
        bit = 1 << core
        d.cpu_resp_ready.value = bit
        for _ in range(300):
            await ClockCycles(d, 1)
            if int(d.cpu_resp_valid.value) & bit:
                got_addr = (int(d.cpu_resp_addr.value) >> (32 * core)) & 0xFFFFFFFF
                got_write = (int(d.cpu_resp_write.value) >> core) & 1
                got_data = (int(d.cpu_resp_rdata.value) >> (64 * core)) & ((1 << 64) - 1)
                assert got_addr == address
                assert got_write == int(write)
                if expected is not None:
                    assert got_data == expected
                d.cpu_resp_ready.value = 0
                await ClockCycles(d, 1)
                return got_data, memory.snoop_data.cycle
        d.cpu_resp_ready.value = 0
        raise TimeoutError(
            f"core{core} response {address:#x} timed out; "
            f"fill={int(d.monitor_l2_fill_active.value)} "
            f"protocol_error={int(d.protocol_error.value)} "
            f"reads={memory.read_requests} "
            f"snoops={memory.snoop_data.snoops[snoop_start:]} "
            f"l1_rsp={memory.snoop_data.snoop_response_cycles[-20:]} "
            f"dir_rsp={memory.snoop_data.directory_snoop_response_cycles[-20:]} "
            f"commits={memory.snoop_data.directory_commits[-8:]}"
        )

    refill_expected = memory.word(refill_addr, (refill_addr >> 3) & 7)
    model.seed_word(refill_addr, refill_expected)
    refill_accept_cycle = await issue(owner_core, refill_addr)
    for _ in range(300):
        if int(d.monitor_l2_fill_active.value):
            break
        await ClockCycles(d, 1)
    else:
        raise TimeoutError("memory refill never entered the shared L2 fill stream")
    fill_start_cycle = memory.snoop_data.cycle

    store_accept_cycle = await issue(other_core, owner_addr, write=True, data=store_data)
    _, store_response_cycle = await response(other_core, owner_addr, write=True)
    _, refill_response_cycle = await response(
        owner_core, refill_addr, expected=refill_expected
    )

    invalidations = [
        event for event in memory.snoop_data.snoops[snoop_start:]
        if event["line"] == (owner_addr & ~0x3F) and event["opcode"] == 1
    ]
    assert invalidations, "shared-line store did not issue a clean invalidation"
    overlapped = any(event["during_l2_fill"] for event in invalidations)

    model.observe(other_core, owner_addr, write=True, write_data=store_data,
                  write_mask=0xFF)
    model.observe(owner_core, refill_addr, response_data=refill_expected)
    updated = await cpu.access(owner_core, owner_addr)
    assert updated == store_data
    model.observe(owner_core, owner_addr, response_data=updated)
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    memory.snoop_data.assert_directory_matches(model, refill_addr)
    assert int(d.protocol_error.value) == 0

    row = {
        "workload": "clean_snoop_during_l2_fill",
        "owner_core": owner_core,
        "seed": 0xC1EA5EED,
        "fill_start_to_snoop_accept_cycles": invalidations[0]["cycle"] - fill_start_cycle,
        "store_request_to_snoop_accept_cycles": invalidations[0]["cycle"] - store_accept_cycle,
        "store_request_to_response_cycles": store_response_cycle - store_accept_cycle,
        "fill_snoop_overlap": overlapped,
        "refill_request_to_response_cycles": refill_response_cycle - refill_accept_cycle,
        "data_check": "PASS",
        "directory_check": "PASS",
    }
    print("P2_FILL_SNOOP," + json.dumps(row, sort_keys=True))
    PYTHON_COVERAGE.sample_external("clean_snoop_during_l2_fill")
    PYTHON_COVERAGE.sample_interleaving("clean_snoop_fill_writer_overlap")
    _record_model(model)
    expect_overlap = bool(int(os.environ.get("P2_EXPECT_OVERLAP", "1")))
    assert overlapped == expect_overlap, (
        f"clean Snoop/refill overlap={overlapped}, expected {expect_overlap}"
    )


@pytest.mark.parametrize("owner_core", [0, 1])
@case
async def test_dirty_owner_snoop_and_refill_share_l2_write_port_safely(
        coherent_env, owner_core):
    """Dirty owner data must wait while the L2 refill owns its write port."""
    dut, memory, _ = await coherent_env(
        response_delay=10, response_gap_periods={"read_data": 4},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    requester = 1 - owner_core
    owner_addr = 0x0060_3000
    refill_addr = 0x0060_2000
    model.seed_word(owner_addr,
                    memory.word(owner_addr, (owner_addr >> 3) & 7))
    dirty_value = 0xD17A_0000_0000_0000 | owner_core
    await cpu.access(owner_core, owner_addr, write=True, data=dirty_value)
    model.observe(owner_core, owner_addr, write=True, write_data=dirty_value)
    assert model.states[owner_addr & ~0x3F][owner_core] == "M"

    model.seed_word(refill_addr,
                    memory.word(refill_addr, (refill_addr >> 3) & 7))
    expected_owner_line = [
        model.data.get((owner_addr & ~0x3F) + beat * 8,
                       memory.word((owner_addr & ~0x3F) + beat * 8, beat))
        for beat in range(8)
    ]
    read_cursor = len(memory.read_requests)
    snoop_cursor = len(memory.snoop_data.snoops)
    transfer_cursor = len(memory.snoop_data.transfers)
    conflict_cursor = len(memory.snoop_data.shared_write_conflicts)

    results = await cpu.access_pair(
        CpuRequest(refill_addr), CpuRequest(owner_addr)
    ) if owner_core == 0 else await cpu.access_pair(
        CpuRequest(owner_addr), CpuRequest(refill_addr)
    )
    # access_pair returns by physical lane, so map the values back to requests.
    if owner_core == 0:
        refill_result, owner_result = results
    else:
        owner_result, refill_result = results

    expected_refill = model.word(refill_addr)
    assert refill_result == expected_refill
    assert owner_result == dirty_value
    model.observe(owner_core, refill_addr, response_data=refill_result)
    model.observe(requester, owner_addr, response_data=owner_result)
    memory.snoop_data.assert_line_data(
        owner_addr, expected_owner_line, since=transfer_cursor)
    memory.snoop_data.assert_directory_matches(model, refill_addr)
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    memory.snoop_data.assert_no_shared_write_conflict()
    owner_snoops = [
        event for event in memory.snoop_data.snoops[snoop_cursor:]
        if event["line"] == (owner_addr & ~0x3F) and event["core"] == owner_core
    ]
    assert owner_snoops and owner_snoops[-1]["opcode"] == 0
    assert len(memory.read_requests) == read_cursor + 1, (
        "dirty owner forwarding should not issue an extra memory read"
    )
    assert len(memory.snoop_data.shared_write_conflicts) == conflict_cursor
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("dirty_owner_snoop_during_l2_fill")
    PYTHON_COVERAGE.sample_interleaving("dirty_owner_waits_for_l2_fill_port")
    _record_model(model)


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
    dut, memory, perf = await coherent_env(
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


@pytest.mark.parametrize("seed", [0x7319, 0xD1A6, 0xA11CE, 0xBADC0DE])
@case
async def test_owner_transfer_and_cold_grant_under_backpressure(coherent_env, seed):
    """Check transfer/grant data correctness under memory backpressure."""
    ready_period = 3 + seed % 5
    response_gap = 4 + seed % 4
    dut, memory, perf = await coherent_env(
        response_delay=seed % 5 + 1,
        backpressure_periods={"read_req": ready_period},
        response_gap_periods={"read_data": response_gap},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    owner_addr = 0x0240_0000 + (seed & 0xFF) * 0x1000
    model.seed_word(owner_addr,
                    memory.word(owner_addr, (owner_addr >> 3) & 7))
    # Guarantee each parameterized replay sees a request-channel stall even
    # when its deterministic modulo phase would otherwise miss all valid cycles.
    memory.arm_stall("read_req", cycles=1)

    # Move ownership from Core1 to Core0 so the next Core1 read must retrieve
    # the latest line through SnoopRead while another line requests an L2 grant.
    value1 = 0xC010_0000_0000_0000 | seed
    await cpu.access(1, owner_addr, write=True, data=value1)
    model.observe(1, owner_addr, write=True, write_data=value1)
    value0 = 0xFACE_0000_0000_0000 | seed
    mask0 = 0x55
    await cpu.access(0, owner_addr, write=True, data=value0, mask=mask0)
    model.observe(0, owner_addr, write=True, write_data=value0,
                  write_mask=mask0)
    assert model.states[owner_addr & ~0x3F] == ["M", "I"]
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    for pair_index in range(6):
        grant_addr = 0x0300_0000 + (seed & 0xFF) * 0x10000 + pair_index * 64
        model.seed_word(grant_addr,
                        memory.word(grant_addr, (grant_addr >> 3) & 7))
        snoop_cursor = len(memory.snoop_data.transfers)
        snoop_req_cursor = len(memory.snoop_data.snoops)
        read_cursor = len(memory.read_requests)
        grant_result, owner_result = await cpu.access_pair(
            CpuRequest(grant_addr), CpuRequest(owner_addr),
            response_stall_cycles=1 + seed % 3,
        )
        assert grant_result == memory.word(grant_addr, (grant_addr >> 3) & 7)
        model.observe(0, grant_addr, response_data=grant_result)
        assert owner_result == model.word(owner_addr)
        model.observe(1, owner_addr, response_data=owner_result)
        assert len(memory.read_requests) == read_cursor + 1, (
            "the cold grant must read backing memory once; owner transfer must "
            "come from L1 without a second memory read"
        )
        owner_snoops = [item for item in
                        memory.snoop_data.snoops[snoop_req_cursor:]
                        if item["line"] == (owner_addr & ~0x3F) and
                        item["core"] == 0]
        assert owner_snoops and owner_snoops[-1]["opcode"] == 0, (
            f"seed={seed:#x}: expected Core0 SnoopRead, got {owner_snoops}; "
            f"all snoops={memory.snoop_data.snoops[snoop_req_cursor:]}; "
            f"transfers={memory.snoop_data.transfers[snoop_cursor:]}"
        )
        expected_line = [
            model.data.get((owner_addr & ~0x3F) + beat * 8,
                           memory.word((owner_addr & ~0x3F) + beat * 8, beat))
            for beat in range(8)
        ]
        memory.snoop_data.assert_line_data(owner_addr, expected_line,
                                           since=snoop_cursor)
        memory.snoop_data.assert_directory_matches(model, owner_addr)
        memory.snoop_data.assert_directory_matches(model, grant_addr)
        if pair_index < 5:
            # Restore M ownership so each replay exercises a fresh owner
            # transfer instead of an L1 S-state read hit on later iterations.
            update = 0xBEEF_0000_0000_0000 | (seed << 4) | pair_index
            await cpu.access(0, owner_addr, write=True, data=update, mask=0xAA)
            model.observe(0, owner_addr, write=True, write_data=update,
                          write_mask=0xAA)
            memory.snoop_data.assert_directory_matches(model, owner_addr)

    assert memory.stalls["read_req"] > 0
    assert int(dut.protocol_error.value) == 0
    _record_model(model)


@case
async def test_directory_lookup_grant_conflict_offset_sweep(coherent_env):
    """Sweep request phase to replay a waiter during an active L2 grant."""
    dut, memory, perf = await coherent_env(
        response_delay=2, backpressure_periods={"read_req": 4},
    )
    grant_conflicts = []
    cpu = DualCoreCpuDriver(dut)
    # Sweep offsets around the short grant handshake window. Each grant line
    # is deliberately L2-resident but absent from both L1s; the competing
    # Core0 request is to a distinct cold line.
    for attempt in range(4):
        for offset in range(16):
            grant_addr = 0x0440_0000 + (attempt * 16 + offset) * 64
            await cpu.access(0, grant_addr)
            for way in range(1, 5):
                await cpu.access(0, grant_addr + way * 32768)
            conflict_cursor = len(memory.snoop_data.transfer_grant_conflicts)
            waiting_addr = grant_addr + 0x1000 + offset * 64
            # Core1 launches the L2-resident refill. Core0 is offered after
            # each phase offset while the grant is active. The shared driver
            # owns both packed request lanes and checks both responses.
            try:
                await cpu.access_pair(
                    CpuRequest(waiting_addr), CpuRequest(grant_addr),
                    request_delay_cycles={0: offset},
                )
            except TimeoutError as error:
                raise TimeoutError(
                    f"offset={offset} grant={grant_addr:#x} waiting={waiting_addr:#x}; "
                    f"memory_reads={memory.read_requests[-8:]}; "
                    f"directory_commits={memory.snoop_data.directory_commits[-8:]}; "
                    f"transfer_grant_conflicts="
                    f"{memory.snoop_data.transfer_grant_conflicts[-8:]}; "
                    f"recent_l2={perf.events['l2_lookups'][-8:]}; "
                    f"recent_grants={perf.events['directory_grants'][-8:]}; {error}"
                ) from error
            conflicts = memory.snoop_data.transfer_grant_conflicts[conflict_cursor:]
            grant_conflicts.extend(
                item for item in conflicts
                if item["lookup"] != item["grant"]
            )
            if grant_conflicts:
                PYTHON_COVERAGE.sample_external("directory_lookup_conflict_grant")
                PYTHON_COVERAGE.sample_interleaving(
                    "active_grant_distinct_address_ready_stall")
                _record_model(CoherenceScoreboard())
                assert int(dut.protocol_error.value) == 0
                return
    raise AssertionError(
        "offset sweep failed to overlap a distinct-address waiter with an "
        f"active grant; observed conflicts={memory.snoop_data.lookup_conflicts}"
    )


@case
async def test_python_same_line_dual_lane_requests(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    address = 0x0230_1280
    initial = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, initial)

    results = await cpu.access_pair(CpuRequest(address), CpuRequest(address))
    assert results == (initial, initial)
    model.observe(0, address, response_data=results[0])
    model.observe(1, address, response_data=results[1])

    value0, mask0 = 0x1122334455667788, 0x0F
    value1, mask1 = 0xAABBCCDDEEFF0011, 0xF0
    await cpu.access_pair(CpuRequest(address, True, value0, mask0),
                          CpuRequest(address, True, value1, mask1))
    model.observe(0, address, write=True, write_data=value0,
                  write_mask=mask0)
    model.observe(1, address, write=True, write_data=value1,
                  write_mask=mask1)
    expected = model.word(address)
    readback = await cpu.access(0, address)
    assert readback == expected
    model.observe(0, address, response_data=readback)
    memory.snoop_data.assert_directory_matches(model, address)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("same_line_dual_lane")
    _record_model(model)


@case
async def test_python_message_passing_litmus(coherent_env):
    """Check completed producer stores become visible through distinct lines."""
    dut, memory, _ = await coherent_env(
        response_delay=3,
        backpressure_periods={"read_req": 5},
        response_gap_periods={"read_data": 4},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    model.track_l1_replacement = False
    data_addr, ready_addr = 0x0310_0000, 0x0310_0040
    payload, generation = 0xCAFE_0123_4567_89AB, 1
    for addr in (data_addr, ready_addr):
        model.seed_word(addr, memory.word(addr, (addr >> 3) & 7))

    # The LSU driver waits for each Store response before allowing the next
    # operation. This tests coherence visibility under that ordering contract;
    # it does not claim an ISA acquire/release or RISC-V fence guarantee.
    await _model_access(cpu, model, memory.snoop_data, 0, data_addr,
                        write=True, data=payload)
    await _model_access(cpu, model, memory.snoop_data, 0, ready_addr,
                        write=True, data=generation,
                        response_stall_cycles=2)
    observed_ready = await _model_access(
        cpu, model, memory.snoop_data, 1, ready_addr
    )
    assert observed_ready == generation
    observed_payload = await _model_access(
        cpu, model, memory.snoop_data, 1, data_addr
    )
    assert observed_payload == payload
    for addr in (data_addr, ready_addr):
        memory.snoop_data.assert_directory_matches(model, addr)
    assert memory.stalls["read_req"] > 0
    assert sum(cpu.response_stall_cycles.values()) >= 2
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("litmus_message_passing")
    PYTHON_COVERAGE.sample_interleaving("message_passing_distinct_lines")
    _record_model(model)


@case
async def test_python_false_sharing_ab(coherent_env):
    """Compare two cores writing distinct words in one line vs separate lines."""
    rows = []
    base = 0x0320_0000
    rounds = 16
    dut, memory, perf = await coherent_env(
        response_delay=3,
        backpressure_periods={"read_req": 5},
        response_gap_periods={"read_data": 4},
    )

    async def run_case(name, second_addr):
        if rows:
            dut.reset.value = 1
            await ClockCycles(dut, 3)
            dut.reset.value = 0
            await ClockCycles(dut, 1)
        cpu = DualCoreCpuDriver(dut)
        model = CoherenceScoreboard()
        model.track_l1_replacement = False
        case_base = base + (0x1000 if name == "different_64B_lines" else 0)
        first_addr = case_base
        second_addr = case_base + (second_addr - base)
        first_line, second_line = first_addr & ~0x3F, second_addr & ~0x3F
        for line in {first_line, second_line}:
            memory.lines[line] = [0x9000_0000_0000_0000 + beat
                                  for beat in range(8)]
        model.seed_word(first_addr, memory.lines[first_line][0])
        model.seed_word(second_addr, memory.lines[second_line][(second_addr >> 3) & 7])

        # Warm both participants into the intended starting state: S/S for a
        # shared line, E/E on distinct lines. Setup is excluded from the window.
        for core, addr in ((0, first_addr), (1, second_addr)):
            value = await _model_access(cpu, model, memory.snoop_data, core, addr)
            assert value == model.word(addr)

        before_perf = perf.snapshot()
        before_cycles = cpu.cycle
        before_snoops = len(memory.snoop_data.snoops)
        before_requests = len(memory.snoop_data.directory_requests)
        before_mem_reads = len(memory.read_requests)
        before_mem_writes = len(memory.write_responses)
        latency_start = (len(cpu.latencies[0]), len(cpu.latencies[1]))
        expected = [0, 0]
        for index in range(rounds):
            expected[0] = 0xA000_0000_0000_0000 | (index << 8) | 0x10
            expected[1] = 0xB000_0000_0000_0000 | (index << 8) | 0x20
            await _model_access(cpu, model, memory.snoop_data, 0, first_addr,
                                write=True, data=expected[0],
                                response_stall_cycles=int(index % 5 == 0))
            await _model_access(cpu, model, memory.snoop_data, 1, second_addr,
                                write=True, data=expected[1],
                                response_stall_cycles=int(index % 7 == 0))

        after_perf = perf.snapshot()
        cycles = cpu.cycle - before_cycles
        samples = (cpu.latencies[0][latency_start[0]:] +
                   cpu.latencies[1][latency_start[1]:])
        requests = memory.snoop_data.directory_requests[before_requests:]
        snoops = memory.snoop_data.snoops[before_snoops:]
        mem_read_lines = len(memory.read_requests) - before_mem_reads
        mem_write_lines = len(memory.write_responses) - before_mem_writes
        getm = sum(item["opcode"] == 0b001 for item in requests)
        upgrade = sum(item["opcode"] == 0b010 for item in requests)
        hit0 = after_perf["l1_hit_core0"] - before_perf["l1_hit_core0"]
        hit1 = after_perf["l1_hit_core1"] - before_perf["l1_hit_core1"]
        miss0 = after_perf["l1_miss_core0"] - before_perf["l1_miss_core0"]
        miss1 = after_perf["l1_miss_core1"] - before_perf["l1_miss_core1"]
        l2hit = after_perf["l2_refill_hit"] - before_perf["l2_refill_hit"]
        l2miss = after_perf["l2_refill_miss"] - before_perf["l2_refill_miss"]

        # Verify final distinct words after measuring; these reads are outside
        # the A/B performance window.
        got0 = await _model_access(cpu, model, memory.snoop_data, 0, first_addr)
        got1 = await _model_access(cpu, model, memory.snoop_data, 1, second_addr)
        assert (got0, got1) == tuple(expected)
        for addr in {first_addr, second_addr}:
            memory.snoop_data.assert_directory_matches(model, addr)
        assert int(dut.protocol_error.value) == 0
        return {
            "case": name,
            "line_addresses": [first_line, second_line],
            "writes": rounds * 2,
            "window_cycles": cycles,
            "operations_per_cycle": (rounds * 2 / cycles if cycles else None),
            "mean_latency_cycles": (sum(samples) / len(samples) if samples else None),
            "p95_latency_cycles": _p95(samples),
            "l1_hits": hit0 + hit1,
            "l1_misses": miss0 + miss1,
            "l1_hit_rate": _rate(hit0 + hit1, hit0 + hit1 + miss0 + miss1),
            "l1_miss_rate": _rate(miss0 + miss1, hit0 + hit1 + miss0 + miss1),
            "l2_refill_hits": l2hit,
            "l2_refill_misses": l2miss,
            "l2_hit_rate": _rate(l2hit, l2hit + l2miss),
            "l2_miss_rate": _rate(l2miss, l2hit + l2miss),
            "memory_read_lines": mem_read_lines,
            "memory_write_lines": mem_write_lines,
            "read_bandwidth_bytes_per_cycle": (
                mem_read_lines * 64 / cycles if cycles else None
            ),
            "write_bandwidth_bytes_per_cycle": (
                mem_write_lines * 64 / cycles if cycles else None
            ),
            "total_bandwidth_bytes_per_cycle": (
                (mem_read_lines + mem_write_lines) * 64 / cycles
                if cycles else None
            ),
            "snoops": len(snoops),
            "getm_requests": getm,
            "upgrade_requests": upgrade,
            "final_values": [got0, got1],
        }

    same = await run_case("same_64B_line_different_words", base + 8)
    separate = await run_case("different_64B_lines", base + 64)
    assert same["writes"] == separate["writes"]
    assert same["final_values"] == separate["final_values"]
    assert same["snoops"] > separate["snoops"]
    assert same["getm_requests"] + same["upgrade_requests"] > 0
    assert separate["getm_requests"] + separate["upgrade_requests"] == 0
    rows.extend((same, separate))
    artifact = {
        "schema_version": 1,
        "benchmark": "false_sharing_ab",
        "seed": "deterministic",
        "rounds_per_core": rounds,
        "memory_response_delay_cycles": 3,
        "measurement_units": "Verilator RTL simulation cycles; not silicon PPA",
        "cases": rows,
    }
    result_path = Path("reports/coherence/false_sharing_ab.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    PYTHON_COVERAGE.sample_external("false_sharing_same_line")
    PYTHON_COVERAGE.sample_external("false_sharing_separate_lines")
    PYTHON_COVERAGE.sample_external("false_sharing_data_checked")
    PYTHON_COVERAGE.sample_interleaving("false_sharing_same_line_ping_pong")
    _record_model(CoherenceScoreboard())


@case
async def test_python_generation_counter_litmus(coherent_env):
    """Run 100 DATA/READY/ACK generations with backpressure and exact checks."""
    dut, memory, _ = await coherent_env(
        response_delay=2,
        backpressure_periods={"read_req": 7},
        response_gap_periods={"read_data": 5},
    )
    memory.arm_stall("read_req", cycles=2)
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    model.track_l1_replacement = False
    data_addr, ready_addr, ack_addr = (
        0x0330_0000, 0x0330_0040, 0x0330_0080
    )
    for addr in (data_addr, ready_addr, ack_addr):
        line = addr & ~0x3F
        memory.lines.setdefault(line, [memory.word(line, beat) for beat in range(8)])
        model.seed_word(addr, memory.lines[line][(addr >> 3) & 7])
    memory.lines[ready_addr & ~0x3F][0] = 0
    memory.lines[ack_addr & ~0x3F][0] = 0
    model.seed_word(ready_addr, 0)
    model.seed_word(ack_addr, 0)
    transaction_lock = asyncio.Lock()
    access_count = 0

    async def checked(core, addr, *, write=False, data=0):
        nonlocal access_count
        async with transaction_lock:
            access_count += 1
            return await _model_access(
                cpu, model, memory.snoop_data, core, addr, write=write,
                data=data,
                response_stall_cycles=2 if access_count % 11 == 0 else 0,
            )

    async def producer():
        for generation in range(1, 101):
            payload = 0xDADA_0000_0000_0000 | generation
            await checked(0, data_addr, write=True, data=payload)
            await checked(0, ready_addr, write=True, data=generation)
            for _ in range(32):
                ack = await checked(0, ack_addr)
                if ack == generation:
                    break
                assert ack < generation, (
                    f"producer observed future ACK {ack} at generation {generation}"
                )
            else:
                raise AssertionError(f"generation {generation} ACK timed out")

    consumed = []

    async def consumer():
        for generation in range(1, 101):
            for _ in range(32):
                ready = await checked(1, ready_addr)
                if ready == generation:
                    break
                assert ready < generation, (
                    f"consumer skipped generation {generation}: READY={ready}"
                )
            else:
                raise AssertionError(f"generation {generation} READY timed out")
            payload = await checked(1, data_addr)
            expected = 0xDADA_0000_0000_0000 | generation
            assert payload == expected, (
                f"generation {generation}: DATA={payload:#018x}, "
                f"expected={expected:#018x}"
            )
            await checked(1, ack_addr, write=True, data=generation)
            consumed.append(generation)

    await asyncio.gather(producer(), consumer())
    assert consumed == list(range(1, 101))
    assert await checked(1, ready_addr) == 100
    assert await checked(0, ack_addr) == 100
    assert await checked(0, data_addr) == (0xDADA_0000_0000_0000 | 100)
    for addr in (data_addr, ready_addr, ack_addr):
        memory.snoop_data.assert_directory_matches(model, addr)
    assert memory.stalls["read_req"] > 0
    assert sum(cpu.response_stall_cycles.values()) > 0
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("litmus_generation_counter_100")
    PYTHON_COVERAGE.sample_external("litmus_generation_backpressure")
    PYTHON_COVERAGE.sample_interleaving("data_ready_ack_100_generations")
    _record_model(model)


@pytest.mark.parametrize("seed", _randomized_seeds())
@case
async def test_python_seeded_randomized_coherence(coherent_env, seed):
    ready_period = 3 + seed % 5
    dut, memory, _ = await coherent_env(
        response_delay=seed % 5 + 1,
        backpressure_periods={"read_req": ready_period},
        response_gap_periods={"read_data": ready_period + 1},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    # The randomized stress lets the DUT choose the actual victim way. The
    # reference model tracks coherence from CPU requests and completed Put
    # transactions, avoiding a second, potentially divergent way predictor.
    model.track_l1_replacement = False
    lookup_conflict_cursor = len(memory.snoop_data.lookup_conflicts)
    rng = random.Random(seed)
    stress_mode = bool(os.environ.get("COHERENCE_STRESS_SEED_COUNT"))
    if stress_mode:
        if os.environ.get("COHERENCE_DENSE_L2_SET_STRESS"):
            # Regression for the previously uncovered corner: nine lines
            # collide in one 8-way L2 set while also thrashing one L1 set.
            addresses = [0x0200_0800 + index * 32768 for index in range(9)]
        else:
            # Ten lines conflict in one L1 set while spreading across four L2
            # sets; the remaining addresses spread traffic over other sets. Keep
            # this pool away from the deterministic prologue's L2 sets 0 and 128.
            addresses = ([0x0200_0800 + index * 0x2000 for index in range(10)] +
                         [0x1200_1000 + index * 64 for index in range(16)])
    else:
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

    operations = int(os.environ.get("COHERENCE_STRESS_OPERATIONS", "36"))
    if not 1 <= operations <= 500:
        raise ValueError("COHERENCE_STRESS_OPERATIONS must be in [1, 500]")
    history = []

    def apply_puts_since(cursor):
        for event in memory.snoop_data.directory_requests[cursor:]:
            if event["opcode"] in (0b011, 0b100, 0b101):
                model.observe_l1_put(event["core"], event["line"],
                                     event["opcode"])

    def apply_victim_snoops_since(cursor):
        for event in memory.snoop_data.victim_snoops[cursor:]:
            model.observe_victim_invalidate(event["core"], event["line"])

    async def checked_access(core, address, **kwargs):
        put_cursor = len(memory.snoop_data.directory_requests)
        victim_cursor = len(memory.snoop_data.victim_snoops)
        try:
            result = await cpu.access(core, address, **kwargs)
            apply_puts_since(put_cursor)
            if not model.track_l2_replacement:
                apply_victim_snoops_since(victim_cursor)
            return result
        except TimeoutError as error:
            raise TimeoutError(
                f"seed={seed:#x}, operation={index}, core={core}, "
                f"request={address:#x}, recent operations={history[-12:]}; {error}"
            ) from error

    async def checked_pair(req0, req1):
        put_cursor = len(memory.snoop_data.directory_requests)
        try:
            result = await cpu.access_pair(req0, req1)
            if model.track_l2_replacement:
                apply_puts_since(put_cursor)
            return result
        except TimeoutError as error:
            rtl_state = {
                "engine": int(dut.monitor_engine_state.value),
                "engine_addr": int(dut.monitor_engine_addr.value),
                "victim_addr": int(dut.monitor_victim_addr.value),
                "victim_targets": int(
                    dut.monitor_victim_pending_targets.value
                ),
                "victim_target": int(dut.monitor_victim_target.value),
                "snoop_valid": int(dut.monitor_snoop_offer_valid.value),
                "snoop_ready": int(dut.monitor_snoop_offer_ready.value),
                "mem_mshr_valid": int(dut.monitor_mem_mshr_valid.value),
                "directory_active": int(
                    dut.monitor_directory_active_contexts.value
                ),
                "cpu_states": int(dut.monitor_cpu_state.value),
                "l1_snoop_states": int(dut.monitor_l1_snoop_state.value),
                "cpu_active_addrs": int(dut.monitor_cpu_active_addr.value),
                "l1_replace_states": int(dut.monitor_l1_replace_state.value),
                "dir_req": (
                    int(dut.monitor_dir_req_live_valid.value),
                    int(dut.monitor_dir_req_live_ready.value),
                    int(dut.monitor_dir_req_live_addr.value),
                ),
                "dir_xfer": (
                    int(dut.monitor_dir_xfer_live_valid.value),
                    int(dut.monitor_dir_xfer_live_ready.value),
                ),
            }
            raise TimeoutError(
                f"seed={seed:#x}, operation={index}, pair=({req0}, {req1}), "
                f"recent operations={history[-12:]}; fill="
                f"{int(dut.monitor_l2_fill_active.value)}, "
                f"line_wr=(valid={int(dut.monitor_l2_line_wr_valid.value)},"
                f"ready={int(dut.monitor_l2_line_wr_ready.value)},"
                f"addr={int(dut.monitor_l2_line_wr_addr.value):#x},"
                f"beat={int(dut.monitor_l2_line_wr_beat.value)}), "
                f"dir_snoop=(data={int(dut.monitor_dir_snoop_data_to_l2.value)},"
                f"valid={int(dut.monitor_dir_snoop_valid.value)},"
                f"set_conflict={int(dut.monitor_snoop_set_conflict.value)}), "
                f"read_requests={memory.read_requests[-8:]}, "
                f"write_requests={memory.write_requests[-8:]}, "
                f"write_responses={memory.write_responses[-8:]}, "
                f"memory_state={memory.debug_snapshot}, "
                f"mem_rd=(valid={int(dut.mem_rd_data_valid.value)},"
                f"ready={int(dut.mem_rd_data_ready.value)},"
                f"id={int(dut.mem_rd_data_txn_id.value)},"
                f"beat={int(dut.mem_rd_data_beat_idx.value)}), "
                f"mem_req=(valid={int(dut.mem_rd_req_valid.value)},"
                f"ready={int(dut.mem_rd_req_ready.value)},"
                f"id={int(dut.mem_rd_req_txn_id.value)}), "
                f"snoops={memory.snoop_data.snoops[-12:]}, "
                f"victim_snoops={memory.snoop_data.victim_snoops[-12:]}, "
                f"rtl_state={rtl_state}, "
                f"snoop_responses={memory.snoop_data.snoop_response_cycles[-16:]}, "
                f"dir_snoop_responses="
                f"{memory.snoop_data.directory_snoop_response_cycles[-16:]}, "
                f"dir_commits={memory.snoop_data.directory_commits[-12:]}, "
                    f"dir_requests={memory.snoop_data.directory_requests[-16:]}, "
                    f"dir_grants={memory.snoop_data.directory_grants[-16:]}, "
                    f"l2_lookups={memory.snoop_data.l2_lookups[-16:]}, "
                f"owner_partial={memory.snoop_data.partial}; {error}"
                    f"; error_detail={int(dut.protocol_error_detail.value):012b}"
            ) from error

    # Keep a deterministic eviction prelude on the replay seed so the long
    # random sweep always reaches dirty-owner and two-sharer L2 victims.
    if stress_mode and seed == 0x5EED:
        index = -1
        dirty_base = 0x0080_2000
        dirty_values = {}
        l2_cursor = len(model.l2_evictions)
        write_cursor = len(memory.write_requests)
        for n in range(9):
            address = dirty_base + n * 32768
            value = 0xD17E000000000000 | n
            core = 0 if n < 4 or n == 8 else 1
            seed_if_needed(address)
            await checked_access(core, address, write=True, data=value)
            model.observe(core, address, write=True, write_data=value,
                          write_mask=0xFF)
            dirty_values[address] = value
        dirty_victims = [item for item in model.l2_evictions[l2_cursor:]
                         if item["state"] == "M"]
        dirty_lines = {item["line"] for item in dirty_victims}
        observed_writes = {entry[0] & ~0x3F
                           for entry in memory.write_requests[write_cursor:]}
        assert dirty_lines and dirty_lines & observed_writes, (
            f"seed={seed:#x}: expected dirty live L2 victim/writeback; "
            f"victims={dirty_victims}, writes={memory.write_requests[write_cursor:]}"
        )
        victim = dirty_victims[0]
        victim_line = victim["line"]
        reload = await checked_access(1 - victim["core"], victim_line)
        model.observe(1 - victim["core"], victim_line, response_data=reload)
        assert reload == dirty_values[victim_line], (
            f"seed={seed:#x}: dirty victim data changed after writeback"
        )
        assert len(memory.write_responses) == len(memory.write_requests)

        shared_base = 0x0100_0000
        shared_lines = [shared_base + n * 32768 for n in range(9)]
        shared_target = shared_lines[6]
        for n in range(6):
            core = 0 if n < 3 else 1
            address = shared_lines[n]
            seed_if_needed(address)
            response = await checked_access(core, address)
            model.observe(core, address, response_data=response)
        for core in (0, 1):
            seed_if_needed(shared_target)
            response = await checked_access(core, shared_target)
            model.observe(core, shared_target, response_data=response)
        address = shared_lines[7]
        seed_if_needed(address)
        response = await checked_access(0, address)
        model.observe(0, address, response_data=response)
        assert model.states[shared_target] == ["S", "S"]
        set_index = model._l2_set(shared_target)
        assert model.l2_ways[set_index][model.l2_next_way[set_index] % 8] == shared_target
        shared_expected_words = [memory.word(shared_target, beat)
                                 for beat in range(8)]
        snoop_cursor = len(memory.snoop_data.snoops)
        shared_write_cursor = len(memory.write_requests)
        address = shared_lines[8]
        seed_if_needed(address)
        response = await checked_access(0, address)
        model.observe(0, address, response_data=response)
        shared_victims = [item for item in model.l2_evictions[l2_cursor:]
                          if item["line"] == shared_target and item["state"] == "S"]
        assert {item["core"] for item in shared_victims} == {0, 1}
        assert {item["core"] for item in memory.snoop_data.snoops[snoop_cursor:]
                if item["line"] == shared_target} == {0, 1}
        if any((entry[0] & ~0x3F) == shared_target
               for entry in memory.write_requests[shared_write_cursor:]):
            assert tuple(memory._read_word(shared_target, beat)
                         for beat in range(8)) == tuple(shared_expected_words)
        memory.snoop_data.assert_directory_matches(model, shared_target)
        assert not model.l2_contains(shared_target)

    if stress_mode:
        # Random replacement order is driven by concurrent CPU/snoop events.
        # Keep the reference MESI model event-driven from this point rather
        # than predicting an L2 way from an assumed lane retirement order.
        model.track_l2_replacement = False

    for index in range(operations):
        model.operation_index = index
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
                owner_data = await checked_access(0, req1.addr)
                model.observe(0, req1.addr, response_data=owner_data)
            snoop_cursor = len(memory.snoop_data.transfers)
            snoop_req_cursor = len(memory.snoop_data.snoops)
            victim_snoop_cursor = len(memory.snoop_data.victim_snoops)
            put_cursor = len(memory.snoop_data.directory_requests)
            monitor_cycle_offset = cpu.cycle - memory.snoop_data.cycle
            dir_commit_cursor = len(memory.snoop_data.directory_commits)
            result0, result1 = await checked_pair(req0, req1)
            victim_evicted_req1_owner = any(
                item["line"] == (req1.addr & ~0x3F) and item["core"] == 0
                for item in memory.snoop_data.victim_snoops[victim_snoop_cursor:]
            )
            if (not req1.write and
                    model.states[req1.addr & ~0x3F][0] == "M" and
                    not victim_evicted_req1_owner):
                line = req1.addr & ~0x3F
                expected_line = [model.data.get(
                    line + 8 * beat, memory.word(line, beat))
                    for beat in range(8)]
                owner_snoops = [
                    item for item in memory.snoop_data.snoops[snoop_req_cursor:]
                    if item["line"] == line and item["core"] == 0
                ]
                owner_putm = any(
                    item["line"] == line and item["core"] == 0 and
                    item["opcode"] == 0b101
                    for item in memory.snoop_data.directory_requests[put_cursor:]
                )
                if owner_snoops:
                    assert owner_snoops[-1]["opcode"] == 0, (
                        f"remote read of Core0 M line {line:#x} must not invalidate "
                        f"the owner; observed {owner_snoops}"
                    )
                else:
                    # A concurrent same-L1-set miss from Core0 can retire the
                    # modified owner with PutM before Core1's read reaches the
                    # directory. In that legal ordering, the read is served by
                    # the newly current L2 copy and needs no SnoopRead.
                    assert owner_putm, (
                        f"Core0 M line {line:#x} had neither SnoopRead nor an "
                        f"accepted PutM; pair=({req0}, {req1}), "
                        f"victim_snoops={memory.snoop_data.victim_snoops[victim_snoop_cursor:]}, "
                        f"requests={memory.snoop_data.directory_requests[put_cursor:]}"
                    )
                owner_data = [item for item in memory.snoop_data.transfers[snoop_cursor:]
                              if item["line"] == line and item["core"] == 0]
                if owner_data:
                    memory.snoop_data.assert_line_data(
                        req1.addr, expected_line, since=snoop_cursor)
                else:
                    # Under same-set pressure, Core0 may already have accepted
                    # PutM for this victim while Directory's old snapshot was
                    # issuing SnoopRead. The L1 then correctly returns ACK
                    # without data; Directory retries the now-current L2 line.
                    assert owner_putm, (
                        f"SnoopRead of Core0 M line {line:#x} produced no owner data "
                        "and had no accepted PutM recovery"
                    )
                expected_word = model.data.get(
                    req1.addr & ~0x7, memory.word(req1.addr, (req1.addr >> 3) & 7)
                )
                assert result1 == expected_word, (
                    f"remote read of Core0 M line {line:#x} returned "
                    f"{result1:#018x}, expected current owner value {expected_word:#018x}"
                )
            pair_ops = ((0, req0, result0), (1, req1, result1))
            for core, req, result in pair_ops:
                history.append((index, core, req.addr, req.write, req.data,
                                req.mask, result))
            if stress_mode:
                ordered_events = [
                    (cpu.last_pair_completed_at[core], 1, core, req, result)
                    for core, req, result in pair_ops
                ]
                for event in memory.snoop_data.directory_requests[put_cursor:]:
                    if event["opcode"] in (0b011, 0b100, 0b101):
                        ordered_events.append((event["cycle"] +
                                               monitor_cycle_offset,
                                               0, event["core"], event, None))
                for event in memory.snoop_data.victim_snoops[victim_snoop_cursor:]:
                    ordered_events.append((event["cycle"] + monitor_cycle_offset,
                                           2, event["core"], event, None))
                ordered_events.sort(key=lambda event: (event[0], event[1]))
                try:
                    for _, kind, core, req_or_event, result in ordered_events:
                        if kind == 0:
                            model.observe_l1_put(core, req_or_event["line"],
                                                 req_or_event["opcode"])
                        elif kind == 1:
                            model.observe(core, req_or_event.addr,
                                          write=req_or_event.write,
                                          write_data=req_or_event.data,
                                          write_mask=req_or_event.mask,
                                          response_data=result)
                        else:
                            model.observe_victim_invalidate(
                                core, req_or_event["line"])
                    for core, req, _ in pair_ops:
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
                        f"new directory requests="
                        f"{memory.snoop_data.directory_requests[put_cursor:]}, "
                        f"new dir commits="
                        f"{memory.snoop_data.directory_commits[dir_commit_cursor:]}, "
                        f"line snoops={line_snoops[-8:]}, "
                        f"line commits={line_commits[-8:]}, "
                        f"new owner-data={memory.snoop_data.transfers[snoop_cursor:]}, "
                        f"model_line_states={model.states[req.addr & ~0x3F]}, "
                        f"model_line_history={[event for event in model.transitions if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"put_history={[event for event in memory.snoop_data.directory_requests if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"victim_history={[event for event in memory.snoop_data.victim_snoops if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"model_l2_ways={model.l2_ways[model._l2_set(req.addr)]}, "
                        f"model_l2_next={model.l2_next_way[model._l2_set(req.addr)]}, "
                        f"model_l2_evictions={model.l2_evictions[-16:]}"
                    ) from error
            else:
                for core, req, result in pair_ops:
                    try:
                        model.observe(core, req.addr, write=req.write,
                                      write_data=req.data, write_mask=req.mask,
                                      response_data=result)
                        memory.snoop_data.assert_directory_matches(model, req.addr)
                    except AssertionError as error:
                        raise AssertionError(
                            f"seed={seed:#x}, recent operations={history[-12:]}, "
                            f"line={req.addr & ~0x3F:#x}: {error}"
                        ) from error
                if req.write:
                    readback = await checked_access(core, req.addr)
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
            result = await checked_access(core, req.addr, write=req.write,
                                          data=req.data, mask=req.mask)
            history.append((index, core, req.addr, req.write, req.data,
                            req.mask, result))
            try:
                model.observe(core, req.addr, write=req.write,
                              write_data=req.data, write_mask=req.mask,
                              response_data=result)
                memory.snoop_data.assert_directory_matches(model, req.addr)
            except AssertionError as error:
                line = req.addr & ~0x3F
                line_commits = [
                    item for item in memory.snoop_data.directory_commits
                    if item["line"] == line
                ]
                line_snoops = [
                    item for item in memory.snoop_data.snoops
                    if item["line"] == line
                ]
                raise AssertionError(
                    f"seed={seed:#x}, recent operations={history[-12:]}, "
                    f"line={line:#x}, modeled_states={model.states[line]}, "
                    f"line_history={[item for item in history if item[2] & ~0x3F == line]}, "
                    f"line_transitions={[item for item in model.transitions if item['line'] == line][-16:]}, "
                    f"l1_ways=({model.l1_way_view(0, line)},"
                    f"{model.l1_way_view(1, line)}), "
                    f"model_l1_evictions={model.l1_evictions[-8:]}, "
                    f"snoops={line_snoops[-8:]}, "
                    f"directory_commits={line_commits[-12:]}"
                ) from error
            if req.write:
                readback = await checked_access(core, req.addr)
                history.append((index, core, req.addr, False, 0, 0xFF,
                                readback))
                model.observe(core, req.addr, response_data=readback)
                memory.snoop_data.assert_directory_matches(model, req.addr)

    model.assert_covered("cold_read", "cold_write", "read_hit", "write_hit")
    assert int(dut.protocol_error.value) == 0, f"protocol error for seed={seed:#x}"
    PYTHON_COVERAGE.sample_external("randomized_seeded_regression")
    PYTHON_COVERAGE.sample_external("randomized_cpu_operations", operations)
    conflicts = memory.snoop_data.lookup_conflicts[lookup_conflict_cursor:]
    distinct_conflicts = [item for item in conflicts
                          if item["incoming"] != item["active"]]
    transfer_conflicts = [item for item in distinct_conflicts
                          if item["active_kind"] == "transfer"]
    # This fixed seed is the minimized replay that consistently overlaps a
    # different-address Directory request with the active owner-transfer
    # lookup. All normal data, MESI, beat and directory checkers above remain
    # enabled while request and R-beat backpressure are active.
    if seed == 0x5EED and not stress_mode:
        assert transfer_conflicts, (
            f"seed={seed:#x} failed to recreate a distinct-address transfer "
            f"lookup race: {conflicts}"
        )
        assert memory.stalls["read_req"] > 0
        PYTHON_COVERAGE.sample_external("directory_lookup_race_regression")
        PYTHON_COVERAGE.sample_external("directory_lookup_conflict_transfer")
        PYTHON_COVERAGE.sample_interleaving(
            "active_transfer_distinct_address_ready_stall")
    if stress_mode and seed == 0x5EED:
        assert any(item["state"] == "M" for item in model.l2_evictions), (
            "stress prologue missed a dirty-owner L2 live victim"
        )
        shared_lines_evicted = {}
        for item in model.l2_evictions:
            if item["state"] == "S":
                shared_lines_evicted.setdefault(item["line"], set()).add(item["core"])
        assert any(cores == {0, 1} for cores in shared_lines_evicted.values()), (
            "stress prologue missed a two-sharer L2 live victim"
        )
    _record_model(model)


def _p95(samples):
    if not samples:
        return None
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _phase_samples(starts, ends, start_key="addr", end_key="addr"):
    """Pair ordered same-line milestones and return non-negative cycle deltas."""
    pending = {}
    for item in sorted(starts, key=lambda event: event["cycle"]):
        pending.setdefault(item[start_key], []).append(item["cycle"])
    samples = []
    for item in sorted(ends, key=lambda event: event["cycle"]):
        queue = pending.get(item[end_key], [])
        if queue and queue[0] <= item["cycle"]:
            samples.append(item["cycle"] - queue.pop(0))
    return samples


def _phase_stats(samples):
    return {
        "transactions": len(samples),
        "mean_cycles": (sum(samples) / len(samples) if samples else None),
        "p95_cycles": _p95(samples),
    }


@pytest.mark.asyncio
@case
@pytest.mark.benchmark
async def test_coherence_benchmark_v3(coherent_env):
    """Run repeatable cache, mixed-traffic, and latency-sweep workloads."""
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    rows = []
    benchmark_seeds = (0x1A2B, 0x5EED, 0xC0FFEE, 0xBADC0DE, 0xD15EA5E)

    async def measure(name, delay, initial_state, ops, workload, seed=0):
        memory.response_delay = delay
        before_perf = perf.snapshot()
        before_stage_events = perf.event_snapshot()
        before_read_req = len(memory.read_requests)
        before_read_complete = len(memory.read_completions)
        before_write_req = len(memory.write_requests)
        before_write_rsp = len(memory.write_responses)
        before_read_beats = memory.read_beats
        before_write_beats = memory.write_beats
        before_latencies = (len(cpu.latencies[0]), len(cpu.latencies[1]))
        await workload()
        after_perf = perf.snapshot()
        after_read_req = len(memory.read_requests)
        after_read_complete = len(memory.read_completions)
        after_write_req = len(memory.write_requests)
        after_write_rsp = len(memory.write_responses)
        after_read_beats = memory.read_beats
        after_write_beats = memory.write_beats
        samples = (cpu.latencies[0][before_latencies[0]:] +
                   cpu.latencies[1][before_latencies[1]:])
        delta = {key: after_perf[key] - before_perf[key]
                 for key in before_perf}
        stage_events = perf.events_since(before_stage_events)
        dir_to_lookup = _phase_samples(
            stage_events["directory_accepts"], stage_events["l2_lookups"]
        )
        l1_to_dir = _phase_samples(
            stage_events["l1_misses"], stage_events["directory_accepts"]
        )
        memory_read_requests = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.read_requests[before_read_req:]
        ]
        memory_read_completions = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.read_completions[before_read_complete:]
        ]
        memory_write_requests = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.write_requests[before_write_req:]
        ]
        memory_write_responses = [
            {"id": txn_id, "cycle": cycle}
            for txn_id, cycle in memory.write_responses[before_write_rsp:]
        ]
        l2_hit_events = [event for event in stage_events["l2_lookups"]
                         if event["hit"]]
        l2_miss_events = [event for event in stage_events["l2_lookups"]
                          if not event["hit"]]
        l2_hit_to_grant = _phase_samples(
            l2_hit_events, stage_events["directory_grants"]
        )
        l2_miss_to_memory = _phase_samples(
            l2_miss_events, memory_read_requests
        )
        memory_read_service = _phase_samples(
            memory_read_requests, memory_read_completions,
            start_key="id", end_key="id"
        )
        memory_write_service = _phase_samples(
            memory_write_requests, memory_write_responses,
            start_key="id", end_key="id"
        )
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
            "seed": seed,
            "initial_cache_state": initial_state,
            "ops": ops,
            "window_cycles": cycles,
            "mean_req_to_resp_cycles": (sum(samples) / len(samples)
                                        if samples else None),
            "p95_req_to_resp_cycles": _p95(samples),
            "ops_per_cycle": _rate(ops, cycles),
            "phase_cycles": {
                "l1_miss_to_directory_accept": _phase_stats(l1_to_dir),
                "directory_accept_to_l2_lookup": _phase_stats(dir_to_lookup),
                "l2_hit_lookup_to_grant": _phase_stats(l2_hit_to_grant),
                "l2_miss_lookup_to_memory_request": _phase_stats(l2_miss_to_memory),
                "memory_read_request_to_last_beat": _phase_stats(memory_read_service),
                "memory_write_request_to_response": _phase_stats(memory_write_service),
            },
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
        print("COHERENCE_BENCHMARK_V3," + json.dumps(row, sort_keys=True))

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

        # Eight independent same-set samples per memory-delay point provide
        # 32 L2-hit observations while keeping each target in a separate L2
        # set. Shuffle the four L1 conflict lines from a fixed seed.
        for sample_index in range(8):
            seed = benchmark_seeds[(latency_index * 8 + sample_index) %
                                   len(benchmark_seeds)]
            rng = random.Random(seed)
            l2_addr = base + 0x1000 + sample_index * 64
            await cpu.access(0, l2_addr)
            eviction_ways = list(range(1, 5))
            rng.shuffle(eviction_ways)
            for way in eviction_ways:
                await cpu.access(0, l2_addr + way * 32768)

            async def l2_read(addr=l2_addr):
                result = await cpu.access(0, addr)
                assert result == memory.word(addr, (addr >> 3) & 7)

            await measure(
                "l2_hit_after_l1_replacement", delay,
                "Target absent from L1 and retained in L2 after four same-index L1 conflicts",
                1, l2_read, seed=seed,
            )

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

    # Mixed reads/writes and dual-core pairs use five reproducible seeds. Each
    # seed owns a disjoint address range and an independent architectural
    # reference model; every final line is read back through the DUT.
    for seed_index, seed in enumerate(benchmark_seeds):
        rng = random.Random(seed)
        mixed_base = 0x20000000 + seed_index * 0x01000000
        mixed_addresses = [mixed_base + line * 64 + (line % 8) * 8
                           for line in range(8)]
        model = CoherenceScoreboard()

        def seed_line(address):
            if (address & ~0x7) not in model.data:
                model.seed_word(
                    address, memory.word(address, (address >> 3) & 7)
                )

        async def mixed_workload(addresses=mixed_addresses, reference=model,
                                 randomizer=rng):
            for operation in range(48):
                if operation % 4 == 0:
                    first, second = randomizer.sample(addresses, 2)
                    requests = []
                    for address in (first, second):
                        seed_line(address)
                        write = randomizer.random() < 0.35
                        requests.append(CpuRequest(
                            address, write=write,
                            data=randomizer.getrandbits(64) if write else 0,
                            mask=randomizer.randrange(1, 256) if write else 0xFF,
                        ))
                    result0, result1 = await cpu.access_pair(
                        requests[0], requests[1]
                    )
                    for core, request, result in (
                            (0, requests[0], result0),
                            (1, requests[1], result1)):
                        expected = reference.word(request.addr)
                        if not request.write:
                            assert result == expected, (
                                f"seed={seed:#x} op={operation} "
                                f"addr={request.addr:#x}: {result:#x} != {expected:#x}"
                            )
                        reference.observe(
                            core, request.addr, write=request.write,
                            write_data=request.data, write_mask=request.mask,
                            response_data=result,
                        )
                else:
                    address = randomizer.choice(addresses)
                    seed_line(address)
                    core = randomizer.randrange(2)
                    write = randomizer.random() < 0.35
                    value = randomizer.getrandbits(64) if write else 0
                    mask = randomizer.randrange(1, 256) if write else 0xFF
                    result = await cpu.access(
                        core, address, write=write, data=value, mask=mask
                    )
                    expected = reference.word(address)
                    if not write:
                        assert result == expected, (
                            f"seed={seed:#x} op={operation} "
                            f"addr={address:#x}: {result:#x} != {expected:#x}"
                        )
                    reference.observe(
                        core, address, write=write, write_data=value,
                        write_mask=mask, response_data=result,
                    )

            for address in addresses:
                expected = reference.word(address)
                result = await cpu.access(0, address)
                assert result == expected, (
                    f"seed={seed:#x} final read {address:#x}: "
                    f"{result:#x} != {expected:#x}"
                )
                reference.observe(0, address, response_data=result)

        await measure(
            "seeded_mixed_dual_core", 20,
            "Eight target lines absent from both L1s and L2; disjoint region per seed",
            56, mixed_workload, seed=seed,
        )
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error in mixed benchmark seed {seed:#x}"
        )

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
    json_path = result_dir / "coherence_benchmark_v3.json"
    csv_path = result_dir / "coherence_benchmark_v3.csv"
    payload = {
        "schema_version": 4,
        "benchmark_version": 3,
        "dut": "CoherentCacheSubsystem via Picker/Verilator",
        "clock_period_ns": 10,
        "memory_model": "64-byte writable line model; response delay is a simulation parameter",
        "metric_definitions": {
            "l1_hit_miss": "accepted CPU request classified by L1 MESI state; S-store is a miss/upgrade",
            "l2_refill_hit_miss": "accepted Directory L2 refill lookup; not a count of all metadata probes",
            "memory_bandwidth": "accepted 64-bit R/W line beats times eight bytes, divided by benchmark cycles",
            "ops_per_cycle": "completed CPU operations divided by the measured window cycles",
            "phase_cycles": "observed same-line milestone deltas: L1 miss to Directory acceptance, Directory acceptance to L2 refill lookup, L2 hit to grant or L2 miss to backing-memory request, and accepted memory request to final response beat/write response; L2 metadata lookup itself is combinational",
            "seeded_mixed_dual_core": "five fixed seeds, dual-core paired and single-lane reads/writes, independent architectural scoreboards, final readback of all target lines",
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
        if row["workload"] == "seeded_mixed_dual_core":
            assert row["ops"] == 56
            assert row["l1_hit_count"] + row["l1_miss_count"] >= row["ops"]
        if row["workload"] == "ownership_write_ping_pong":
            assert row["snoops"] > 0
        if row["workload"] == "dirty_l2_victim_writeback":
            assert row["snoops"] > 0
            assert row["dirty_writebacks"] > 0
            assert row["memory_write_lines"] > 0
    l2_samples = [row for row in rows
                  if row["workload"] == "l2_hit_after_l1_replacement"]
    mixed_samples = [row for row in rows
                     if row["workload"] == "seeded_mixed_dual_core"]
    assert len(l2_samples) == 32, f"expected 32 independent L2-hit samples, got {len(l2_samples)}"
    assert sum(row["l2_refill_hit_count"] for row in l2_samples) == 32
    assert sum(row["memory_read_lines"] for row in l2_samples) == 0
    assert len(mixed_samples) == len(benchmark_seeds)
    assert {row["seed"] for row in mixed_samples} == set(benchmark_seeds)
