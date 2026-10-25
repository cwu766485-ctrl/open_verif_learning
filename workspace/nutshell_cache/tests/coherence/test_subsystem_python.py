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


@pytest.mark.parametrize("seed", [0x1A2B, 0x5EED, 0xC0FFEE, 0xD15EA5E])
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
    lookup_conflict_cursor = len(memory.snoop_data.lookup_conflicts)
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
    conflicts = memory.snoop_data.lookup_conflicts[lookup_conflict_cursor:]
    distinct_conflicts = [item for item in conflicts
                          if item["incoming"] != item["active"]]
    transfer_conflicts = [item for item in distinct_conflicts
                          if item["active_kind"] == "transfer"]
    # This fixed seed is the minimized replay that consistently overlaps a
    # different-address Directory request with the active owner-transfer
    # lookup. All normal data, MESI, beat and directory checkers above remain
    # enabled while request and R-beat backpressure are active.
    if seed == 0x5EED:
        assert transfer_conflicts, (
            f"seed={seed:#x} failed to recreate a distinct-address transfer "
            f"lookup race: {conflicts}"
        )
        assert memory.stalls["read_req"] > 0
        PYTHON_COVERAGE.sample_external("directory_lookup_race_regression")
        PYTHON_COVERAGE.sample_external("directory_lookup_conflict_transfer")
        PYTHON_COVERAGE.sample_interleaving(
            "active_transfer_distinct_address_ready_stall")
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
