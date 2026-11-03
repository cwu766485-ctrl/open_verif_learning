"""Directed Python/Toffee test against the complete AXI subsystem top."""

import asyncio
import random

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker
from dv.sequences.full_system_sequences import run_legal_mesi_transition_scenario


@case
async def test_dual_core_coherence_uses_axi_backing_memory(full_system_env):
    env = await full_system_env()
    address = 0x0000_2408
    initial = 0x0123_4567_89AB_CDEF
    env.seed_word(address, initial)

    assert await env.cpu_access(0, address) == initial
    assert await env.cpu_access(1, address) == initial
    await env.cpu_access(1, address, write=True,
                         data=0xFEDC_BA98_7654_3210, mask=0xFF)
    assert await env.cpu_access(0, address) == 0xFEDC_BA98_7654_3210
    await env.cpu_access(0, address, write=True,
                         data=0x0FED_CBA9_8765_4321, mask=0xFF)
    assert await env.cpu_access(1, address) == 0x0FED_CBA9_8765_4321

    assert env.monitor.counts["directory.request_accept"] >= 3
    assert env.monitor.counts["snoop.accept"] >= 1
    assert env.axi.read_addresses, "cold coherent miss did not reach AXI memory"
    assert env.coverage.bins["FS.CPU.READ.CORE0"] >= 2
    assert env.coverage.bins["FS.CPU.READ.CORE1"] >= 1
    assert env.coverage.bins["FS.CPU.WRITE.CORE1"] == 1
    assert env.coverage.bins["FS.CPU.WRITE.CORE0"] == 1
    for bin_id in ("FS.MESI.I_TO_E", "FS.MESI.I_TO_S", "FS.MESI.S_TO_M",
                   "FS.MESI.M_TO_S"):
        assert env.coverage.bins[bin_id] >= 1, f"unhit checked transition {bin_id}"
    line_addr = address & ~0x3F
    completed = next(item for item in env.axi.read_completions
                     if item[1] == line_addr)
    txn_id = completed[0]
    assert sum(1 for beat in env.axi.read_beats if beat[0] == txn_id) == 8
    env.coverage.sample_checked_event("FS.AXI.READ_BURST", checked=True)
    assert int(env.dut.protocol_error.value) == 0


@case
async def test_cold_store_silent_upgrade_and_remote_getm(full_system_env):
    """Check all required legal MESI transitions through architectural traffic."""
    env = await full_system_env()
    remote_addr, shared_addr, invalidate_addr = (
        0x0001_8008, 0x0002_4008, 0x0003_0008
    )
    await run_legal_mesi_transition_scenario(
        env, (remote_addr, shared_addr, invalidate_addr), random.Random(0x5EED)
    )

    required_transitions = (
        "I_TO_E", "I_TO_S", "I_TO_M", "E_TO_M", "E_TO_S", "E_TO_I",
        "S_TO_M", "S_TO_I", "M_TO_S", "M_TO_I",
    )
    for transition in required_transitions:
        bin_id = f"FS.MESI.{transition}"
        assert env.coverage.bins[bin_id] >= 1, f"unhit checked transition {bin_id}"

    remote_getm = [event for event in env.monitor.events
                   if event["source"] == "directory" and
                   event["event_type"] == "request_accept" and
                   (event["address"] & ~0x3F) == (remote_addr & ~0x3F) and
                   event["opcode"] == 0b001]
    cold_getm = [event for event in env.monitor.events
                 if event["source"] == "directory" and
                 event["event_type"] == "request_accept" and
                 (event["address"] & ~0x3F) == (invalidate_addr & ~0x3F) and
                 event["opcode"] == 0b001]
    assert remote_getm, "remote write did not issue an observed GetM"
    assert cold_getm, "cold I->M store did not issue an observed GetM"
    assert int(env.dut.protocol_error.value) == 0


@case
async def test_dual_cold_misses_overlap_and_route_axi_responses(full_system_env):
    env = await full_system_env(axi_options={"latency": 10})
    addr0, addr1 = 0x0040_0008, 0x0040_1048
    value0, value1 = 0xA0A1_A2A3_A4A5_A6A7, 0xB0B1_B2B3_B4B5_B6B7
    env.seed_word(addr0, value0)
    env.seed_word(addr1, value1)

    event_start = len(env.monitor.events)
    result0, result1 = await env.cpu_access_pair(
        CpuRequest(addr0), CpuRequest(addr1)
    )
    assert (result0, result1) == (value0, value1)
    assert env.axi.peak_reads >= 2, (
        "two independent CPU cold misses did not overlap at AXI AR"
    )
    first_two_ar = env.axi.read_addresses[:2]
    first_two_r = env.axi.read_completions[:2]
    assert len(first_two_ar) == len(first_two_r) == 2
    assert [item[0] for item in first_two_r] == [
        item[0] for item in reversed(first_two_ar)
    ], f"AXI R completions were not out of order: AR={first_two_ar}, R={first_two_r}"
    assert env.monitor.mshr_occupancy_histogram[2] > 0
    lifecycle = MshrLifecycleChecker.check(
        env.monitor.events[event_start:],
        expected_lines={addr0, addr1},
        expected_words={addr0: value0, addr1: value1},
        expected_cores={addr0: 0, addr1: 1},
    )
    assert lifecycle["mshr_allocations"] == 2
    assert lifecycle["mshr_retirements"] == 2
    assert lifecycle["axi_read_beats"] == lifecycle["l2_refill_beats"] == 16
    env.coverage.sample_checked_event("FS.AXI.READ_OUT_OF_ORDER", checked=True)
    env.coverage.sample_checked_event("FS.MSHR.OCCUPANCY_2", checked=True)
    env.coverage.sample_checked_event("FS.MSHR.LIFECYCLE_END_TO_END",
                                      checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.MSHR_LIFECYCLE_END_TO_END",
                                      checked=True)
    assert int(env.dut.protocol_error.value) == 0


@case
async def test_mmio_slave_byte_mask_and_apb_readonly_csr(full_system_env):
    env = await full_system_env()
    address = 0x3000_0100
    await env.cpu.access(0, address, write=True,
                         data=0x1122_3344_5566_7788, mask=0x0F)
    result = await env.cpu.access(1, address)
    assert result == 0x0000_0000_5566_7788
    # The Toffee CPU driver and the passive MMIO slave resume in separate
    # scheduler groups after the response edge; allow the slave's completion
    # bookkeeping to observe that same accepted response.
    await ClockCycles(env.dut, 2)
    assert env.mmio.requests[0]["size"] == 3
    assert env.mmio.requests[0]["mask"] == 0x0F
    assert len(env.mmio.requests) == 2
    assert len(env.mmio.completions) == 2
    env.coverage.sample_checked_event("FS.MMIO.BYTE_MASK", checked=True)

    pair0, pair1 = await env.cpu.access_pair(
        CpuRequest(0x3000_0200, write=True,
                   data=0xCAFE_BABE_0000_0000, mask=0xF0),
        CpuRequest(0x3000_0208, write=True,
                   data=0x0000_0000_DEAD_BEEF, mask=0x0F),
    )
    assert (pair0, pair1) == (0, 0)
    await ClockCycles(env.dut, 2)
    pair_addresses = {item["addr"] for item in env.mmio.requests[2:]}
    assert pair_addresses == {0x3000_0200, 0x3000_0208}
    assert len(env.mmio.completions) == 4
    assert await env.cpu.access(0, 0x3000_0200) == 0xCAFE_BABE_0000_0000
    assert await env.cpu.access(1, 0x3000_0208) == 0x0000_0000_DEAD_BEEF
    env.coverage.sample_checked_event("FS.MMIO.CORE_ARBITRATION", checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.MMIO_TWO_CORE_ARB",
                                      checked=True)

    assert await env.apb.read(env.apb.CSR_HIT_COUNT) >= 0
    denied_write = await env.apb.write(env.apb.CSR_HIT_COUNT, 0xDEAD_BEEF)
    bad_address = await env.apb.access(0x1C)
    assert denied_write["slverr"] == 1
    assert bad_address["slverr"] == 1
    env.coverage.sample_checked_event("FS.APB.READONLY_ERROR", checked=True)
    assert int(env.dut.protocol_error.value) == 0


@case
async def test_mmio_request_overlaps_other_core_cache_miss(full_system_env):
    env = await full_system_env(axi_options={"latency": 12})
    mmio_addr, cache_addr = 0x3000_0400, 0x0040_4008
    expected = 0xD15E_A5ED_1234_5678
    env.seed_word(cache_addr, expected)
    predicted, _ = env.reference.predict(1, cache_addr)
    transition_start = len(env.reference.transitions)
    event_start = len(env.monitor.events)

    # One CPU lane takes the bypass route while the other misses in cache.
    async def issue_pair():
        return await env.cpu.access_pair(
            CpuRequest(mmio_addr, write=True,
                       data=0x8877_6655_4433_2211, mask=0xF0),
            CpuRequest(cache_addr),
        )

    async def read_csr_during_axi():
        for _ in range(100):
            await ClockCycles(env.dut, 1)
            if env.axi.read_addresses:
                return await env.apb.read(env.apb.CSR_ACCESS_CYCLES)
        raise TimeoutError("cache miss did not reach AXI while waiting for APB")

    (mmio_result, cache_result), access_cycles = await asyncio.gather(
        issue_pair(), read_csr_during_axi()
    )
    assert mmio_result == 0
    assert cache_result == predicted == expected
    env.reference.observe(1, cache_addr, response_data=cache_result)
    observed = env._check_observed_commits(cache_addr & ~0x3F, event_start)
    cpu_txn = next(txn for txn in env.cpu.transactions
                   if txn["request_group"] == env.cpu.request_group - 1 and
                   txn["core"] == 1)
    env._credit_cpu(1, False, cache_addr, cpu_txn["accepted_cycle"],
                    cpu_txn["response_cycle"], transition_start, observed)
    assert any(item["addr"] == mmio_addr and item["mask"] == 0xF0
               for item in env.mmio.requests)
    assert env.axi.read_addresses, "cache miss did not progress beside MMIO"
    env.coverage.sample_checked_event("FS.MMIO.CACHE_CONCURRENT", checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.MMIO_WITH_CACHE_TRAFFIC",
                                      checked=True)
    assert access_cycles >= 0
    env.coverage.sample_checked_event("FS.APB.READ_DURING_AXI", checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.APB_WITH_AXI_TRAFFIC",
                                      checked=True)
    assert int(env.dut.protocol_error.value) == 0


@case
async def test_reset_cancels_outstanding_axi_read_and_reuses_id(full_system_env):
    env = await full_system_env(axi_options={"latency": 80,
                                              "read_reorder_window": 20})
    address, value = 0x0040_5008, 0xFACE_CAFE_0123_4567
    env.seed_word(address, value)
    pending = asyncio.create_task(env.cpu.access(0, address))
    for _ in range(200):
        await ClockCycles(env.dut, 1)
        if env.axi.read_addresses:
            break
    assert env.axi.read_addresses, "cold miss never reached AXI AR"
    cancelled_id = env.axi.read_addresses[0][0]
    assert not env.axi.read_completions
    pre_reset_epoch = env.monitor.reset_epoch

    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await env.reset(cycles=3)
    assert env.monitor.reset_epoch == pre_reset_epoch + 1
    reset_event = next(event for event in reversed(env.monitor.events)
                       if event["source"] == "system" and
                       event["event_type"] == "reset_cancel")
    assert reset_event["reset_epoch"] == pre_reset_epoch
    assert env.axi.reset_cancelled["reads"] >= 1
    await ClockCycles(env.dut, 8)
    assert int(env.dut.cpu_resp_valid.value) == 0, "stale CPU response after reset"
    assert not env.axi.read_completions, "cancelled AXI read completed after reset"

    assert await env.cpu_access(0, address) == value
    assert env.monitor.events[-1]["reset_epoch"] == pre_reset_epoch + 1
    assert len(env.axi.read_completions) == 1
    assert env.axi.read_completions[0][0] == cancelled_id
    assert int(env.dut.fatal_error.value) == 0
    env.coverage.sample_checked_event("FS.AXI.RESET_CANCEL", checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.RESET_WITH_OUTSTANDING",
                                      checked=True)


@case
async def test_reset_cancels_pending_mmio_response(full_system_env):
    env = await full_system_env(mmio_options={"response_delay": 80})
    address = 0x3000_0500
    pending = asyncio.create_task(env.cpu.access(0, address))
    for _ in range(100):
        await ClockCycles(env.dut, 1)
        if env.mmio.requests:
            break
    assert env.mmio.requests, "CPU MMIO read never reached the device"

    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    env.dut.cpu_req_valid.value = 0
    await env.reset(cycles=3)
    assert env.mmio.reset_cancelled >= 1
    await ClockCycles(env.dut, 8)
    assert int(env.dut.cpu_resp_valid.value) == 0
    assert int(env.dut.mmio_resp_valid.value) == 0

    assert await env.cpu.access(0, address) == 0
    assert len(env.mmio.completions) == 1
    env.coverage.sample_checked_event("FS.MMIO.RESET_CANCEL", checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.RESET_WITH_OUTSTANDING",
                                      checked=True)


@case
async def test_axi_read_error_fails_stop_without_success_response(full_system_env):
    address = 0x0040_6008
    env = await full_system_env(
        axi_options={"latency": 1,
                     "read_error_addrs": {address & ~0x7}}
    )
    env.seed_word(address, 0xA5A5_5A5A_0123_4567)
    pending = asyncio.create_task(env.cpu.access(0, address))
    for _ in range(200):
        await ClockCycles(env.dut, 1)
        if int(env.dut.fatal_error.value):
            break
    assert int(env.dut.fatal_error.value) == 1, "AXI RRESP error was not fail-stop"
    assert int(env.dut.cpu_resp_valid.value) == 0, (
        "DUT returned a successful CPU response after an AXI memory error"
    )
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    env.dut.cpu_req_valid.value = 0
    assert env.axi.errors and env.axi.errors[0]["channel"] == "R"
    env.coverage.sample_checked_event("FS.AXI.ERROR_RESPONSE", checked=True)
