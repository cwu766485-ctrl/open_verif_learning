"""Directed Python/Toffee test against the complete AXI subsystem top."""

import asyncio
import random

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker
from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)
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
    env = await full_system_env(
        seed=0xC006,
        axi_options={"latency": 48, "r_valid_gap_period": 2,
                     "read_reorder_window": 2},
    )
    env.trace_scenario_id = "CR06_DUAL_COLD_MISS_OOO_AXI_R_APB"
    env.trace_config.update({
        "core0_line": 0x0040_0000,
        "core1_line": 0x0040_1040,
        "axi_read_reorder": "reverse_two_ids",
        "memory_latency_cycles": 48,
        "apb_sample": "during_outstanding_refills",
    })
    line0, line1 = 0x0040_0000, 0x0040_1040
    addr0, addr1 = line0 + 0x08, line1 + 0x08
    signatures = {
        line0 + beat * 8: (0xA0 << 56) | (beat << 48) | (line0 + beat * 8)
        for beat in range(8)
    }
    signatures.update({
        line1 + beat * 8: (0xB0 << 56) | (beat << 48) | (line1 + beat * 8)
        for beat in range(8)
    })
    for address, value in signatures.items():
        env.seed_word(address, value)
    value0, value1 = signatures[addr0], signatures[addr1]

    event_start = len(env.monitor.events)
    env.axi.force_next_reads_out_of_order(2)
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "seed_line",
         "addresses": [addr0, addr1], "values": [value0, value1]},
        {"kind": "stimulus", "operation": "paired_cold_read",
         "cores": [0, 1], "axi_reorder": "reverse_two_ids"},
    ])
    pair_task = asyncio.create_task(env.cpu_access_pair(
        CpuRequest(addr0), CpuRequest(addr1)
    ))
    for _ in range(500):
        await ClockCycles(env.dut, 1)
        if len(env.axi.read_addresses) >= 2:
            break
    assert len(env.axi.read_addresses) >= 2, "both AXI read IDs were not accepted"
    assert not env.axi.read_completions, "refill completed before APB sampling"
    apb_value = await env.apb.read(env.apb.CSR_ACCESS_CYCLES)
    apb_events = [event for event in env.monitor.events[event_start:]
                  if event["source"] == "apb" and
                  event["event_type"] == "access_complete" and
                  event["address"] == env.apb.CSR_ACCESS_CYCLES]
    assert len(apb_events) == 1 and apb_events[0]["payload"]["read_data"] == apb_value
    assert len(env.axi.read_completions) < 2, "APB sample missed the outstanding refill window"
    result0, result1 = await pair_task
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
    read_events = [event for event in env.monitor.events[event_start:]
                   if event["source"] == "axi" and
                   event["event_type"] == "read_beat" and
                   event["address"] & ~0x3F in (line0, line1)]
    assert len(read_events) == 16
    by_id = {}
    for event in read_events:
        by_id.setdefault(event["txn_id"], []).append(event)
    id_by_line = {line: next(txn_id for txn_id, address, _cycle in first_two_ar
                             if address == line)
                  for line in (line0, line1)}
    for line, txn_id in id_by_line.items():
        beats = sorted(by_id[txn_id], key=lambda event: event["beat"])
        assert [event["beat"] for event in beats] == list(range(8))
        assert [event["data"] for event in beats] == [
            signatures[line + beat * 8] for beat in range(8)
        ]
        assert [event["last"] for event in beats] == [0] * 7 + [1]
    rid_switch = next((right for left, right in zip(read_events, read_events[1:])
                       if left["txn_id"] != right["txn_id"]), None)
    assert rid_switch is not None, "AXI R beats never switched RID between bursts"
    first_completion_cycle = min(event["cycle"] for event in read_events
                                 if event["last"])
    assert rid_switch["cycle"] < first_completion_cycle
    assert len({event["txn_id"] for event in read_events}) == 2
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

    # The independent CPU/reference checker, MSHR lifecycle checker, and AXI
    # ID/beat checker have all completed before this three-role proof is built.
    events = env.monitor.events[event_start:]
    cpu_events = [event for event in events
                  if event["source"] == "cpu" and
                  event["event_type"] in ("request_accept", "response_complete")
                  and event["address"] in (addr0, addr1)]
    cpu_by = {}
    for core, address in ((0, addr0), (1, addr1)):
        cpu_by[core] = {
            "request": next(event for event in cpu_events
                            if event["event_type"] == "request_accept" and
                            event["core"] == core and event["address"] == address),
            "response": next(event for event in cpu_events
                             if event["event_type"] == "response_complete" and
                             event["core"] == core and event["address"] == address),
        }
    ar_by_line = {
        line: next(event for event in events
                   if event["source"] == "axi" and
                   event["event_type"] == "read_address" and
                   event["address"] == line)
        for line in (addr0 & ~0x3F, addr1 & ~0x3F)
    }
    last_r_by_id = {}
    for event in events:
        if event["source"] == "axi" and event["event_type"] == "read_beat" and event["last"]:
            last_r_by_id[event["txn_id"]] = event
    mshr_allocations = [event for event in events
                        if event["source"] == "mshr" and
                        event["event_type"] == "allocate"]
    mshr_retirements = [event for event in events
                        if event["source"] == "mshr" and
                        event["event_type"] == "retire"]
    assert len(mshr_allocations) == len(mshr_retirements) == 2
    allocations_by_slot = {event["slot"]: event for event in mshr_allocations}
    retirements_by_slot = {event["slot"]: event for event in mshr_retirements}
    assert set(allocations_by_slot) == set(retirements_by_slot) == {0, 1}
    l2_fill_beats = [event for event in events
                     if event["source"] == "l2" and
                     event["event_type"] == "line_write_beat"]
    grant_events = [event for event in events
                    if event["source"] == "directory" and
                    event["event_type"] == "grant_accept"]
    assert len(l2_fill_beats) == 16 and len(grant_events) == 2
    l1_commits = {}
    for core, address in ((0, addr0), (1, addr1)):
        l1_commits[core] = next(event for event in events
                                if event["source"] == "l1" and
                                event["event_type"] == "metadata_commit" and
                                event["core"] == core and
                                event["address"] & ~0x3F == address & ~0x3F)
    dir_commits = [event for event in events
                   if event["source"] == "directory" and
                   event["event_type"] == "metadata_commit" and
                   event["address"] & ~0x3F in (addr0 & ~0x3F, addr1 & ~0x3F)]
    assert len(dir_commits) >= 2
    apb_event = apb_events[0]
    assert all(ar_by_line[line]["cycle"] <= apb_event["cycle"] <
               last_r_by_id[ar_by_line[line]["txn_id"]]["cycle"]
               for line in ar_by_line), "APB read did not overlap both AXI refills"

    axi0_line, axi1_line = addr0 & ~0x3F, addr1 & ~0x3F
    event_refs = [
        event_reference("cpu0_request", "cpu0_miss", cpu_by[0]["request"]),
        event_reference("cpu0_response", "cpu0_miss", cpu_by[0]["response"]),
        event_reference("cpu1_request", "cpu1_miss", cpu_by[1]["request"]),
        event_reference("cpu1_response", "cpu1_miss", cpu_by[1]["response"]),
        event_reference("axi0_ar", "axi0_refill", ar_by_line[axi0_line]),
        event_reference("axi1_ar", "axi1_refill", ar_by_line[axi1_line]),
        event_reference("axi0_rlast", "axi0_refill", last_r_by_id[ar_by_line[axi0_line]["txn_id"]]),
        event_reference("axi1_rlast", "axi1_refill", last_r_by_id[ar_by_line[axi1_line]["txn_id"]]),
        event_reference("apb_sample", "apb_sample", apb_event),
        event_reference("l1_commit_core0", "mesi_commit", l1_commits[0]),
        event_reference("l1_commit_core1", "mesi_commit", l1_commits[1]),
    ]
    for index, event in enumerate(dir_commits[-2:]):
        event_refs.append(event_reference(f"directory_commit_{index}", "directory_commit", event))
    for slot in (0, 1):
        event_refs.append(event_reference(
            f"mshr_allocate_{slot}", f"mshr{slot}", allocations_by_slot[slot]
        ))
        event_refs.append(event_reference(
            f"mshr_retire_{slot}", f"mshr{slot}", retirements_by_slot[slot]
        ))
    for index, event in enumerate(l2_fill_beats):
        event_refs.append(event_reference(f"l2_fill_beat_{index}", "l2_fill", event))
    for index, event in enumerate(grant_events):
        event_refs.append(event_reference(f"directory_grant_{index}", "directory_grant", event))
    for index, event in enumerate(events):
        if event["source"] == "axi" and event["event_type"] == "read_beat":
            event_refs.append(event_reference(f"axi_read_beat_{index}", "axi_beat", event))
    first_r_event = min(read_events, key=lambda event: event["cycle"])
    last_r_event = max(read_events, key=lambda event: event["cycle"])
    for index, event in enumerate(read_events):
        event_refs.append(event_reference(
            f"axi_interleaved_beat_{index}", "axi_r_interleave", event
        ))
    event_refs.extend([
        event_reference("axi_r_first", "axi_r_interleave", first_r_event),
        event_reference("axi_r_last", "axi_r_interleave", last_r_event),
    ])
    proof = checked_overlap_proof(
        checker=("paired cold-miss CPU/reference + per-ID eight-beat signature "
                 "and RLAST + observed pre-RLAST RID switch + MSHR/L2 lifecycle + APB"),
        checker_pass=True,
        role_endpoints={
            "cpu0_miss": ("cpu0_request", "cpu0_response"),
            "cpu1_miss": ("cpu1_request", "cpu1_response"),
            "axi0_refill": ("axi0_ar", "axi0_rlast"),
            "axi1_refill": ("axi1_ar", "axi1_rlast"),
            "mshr0": ("mshr_allocate_0", "mshr_retire_0"),
            "mshr1": ("mshr_allocate_1", "mshr_retire_1"),
            "apb_sample": ("apb_sample", "apb_sample"),
        },
        event_refs=event_refs,
        transactions=[
            {"role": "cpu0_miss", "protocol": "CPU", "txn_id": cpu_by[0]["response"]["txn_id"],
             "address": addr0, "event_ref_ids": ["cpu0_request", "cpu0_response"]},
            {"role": "cpu1_miss", "protocol": "CPU", "txn_id": cpu_by[1]["response"]["txn_id"],
             "address": addr1, "event_ref_ids": ["cpu1_request", "cpu1_response"]},
            {"role": "axi0_refill", "protocol": "AXI4-R", "txn_id": ar_by_line[axi0_line]["txn_id"],
             "address": axi0_line, "event_ref_ids": ["axi0_ar", "axi0_rlast"]},
            {"role": "axi1_refill", "protocol": "AXI4-R", "txn_id": ar_by_line[axi1_line]["txn_id"],
             "address": axi1_line, "event_ref_ids": ["axi1_ar", "axi1_rlast"]},
            {"role": "mshr0", "protocol": "refill_mshr", "event_ref_ids": ["mshr_allocate_0", "mshr_retire_0"]},
            {"role": "mshr1", "protocol": "refill_mshr", "event_ref_ids": ["mshr_allocate_1", "mshr_retire_1"]},
            {"role": "directory_grant0", "protocol": "MESI", "event_ref_ids": ["directory_grant_0"]},
            {"role": "directory_grant1", "protocol": "MESI", "event_ref_ids": ["directory_grant_1"]},
            {"role": "apb_sample", "protocol": "APB", "address": env.apb.CSR_ACCESS_CYCLES,
             "event_ref_ids": ["apb_sample"]},
            *[{"role": f"axi_r_line_{index}", "protocol": "AXI4-R",
               "txn_id": id_by_line[line], "address": line,
               "event_ref_ids": [f"axi_interleaved_beat_{beat}"
                                 for beat, event in enumerate(read_events)
                                 if event["address"] & ~0x3F == line]}
              for index, line in enumerate((line0, line1))],
        ],
        state_transitions=[
            {"event_ref_id": "l1_commit_core0", "old_state": l1_commits[0]["old_state"],
             "new_state": l1_commits[0]["new_state"]},
            {"event_ref_id": "l1_commit_core1", "old_state": l1_commits[1]["old_state"],
             "new_state": l1_commits[1]["new_state"]},
            *[{"event_ref_id": f"directory_commit_{index}", "state": event["state"],
               "owner": event["owner"], "sharers": event["sharers"]}
              for index, event in enumerate(dir_commits[-2:])],
        ],
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.MSHR_LIFECYCLE_END_TO_END", checked=True, evidence=proof
    )
    proof["axi_interleaving"] = {
        "rid_switch_cycle": rid_switch["cycle"],
        "switch_to_id": rid_switch["txn_id"],
        "first_rlast_cycle": first_completion_cycle,
        "switch_preceded_rlast": True,
        "beat_ids": [event["txn_id"] for event in read_events],
    }
    env.coverage.sample_checked_cross(
        "FS.CROSS.AXI_R_BEAT_INTERLEAVE", checked=True, evidence=proof
    )
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
