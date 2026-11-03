"""Directed sign-off scenarios for outstanding gaps at the AXI system top."""

import asyncio

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest


L2_SET_STRIDE = 512 * 64


async def _dirty_l2_set(env, count, *, base=0x0080_2000):
    """Create dirty lines mapping to one L2 set using legal CPU stores."""
    values = {}
    for index in range(count):
        address = base + index * L2_SET_STRIDE
        value = 0xD17A_0000_0000_0000 | index
        env.seed_word(address, 0x1000 + index)
        await env.cpu_access(0, address, write=True, data=value, mask=0xFF)
        values[address] = value
    return values


async def _wait_until(dut, predicate, *, cycles=500, message="condition"):
    for _ in range(cycles):
        if predicate():
            return
        await ClockCycles(dut, 1)
    raise TimeoutError(f"timed out waiting for {message}")


@case
async def test_same_line_dual_core_store_ordering_and_data(full_system_env):
    """Simultaneous writes to different words must serialize coherently."""
    env = await full_system_env(axi_options={"latency": 12})
    line = 0x0060_1000
    addr0, addr1 = line, line + 8
    initial0, initial1 = 0x0102_0304_0506_0708, 0x1112_1314_1516_1718
    value0, value1 = 0xA0A1_A2A3_A4A5_A6A7, 0xB0B1_B2B3_B4B5_B6B7
    env.seed_word(addr0, initial0)
    env.seed_word(addr1, initial1)
    event_start = len(env.monitor.events)

    await env.cpu.access_pair(
        CpuRequest(addr0, write=True, data=value0),
        CpuRequest(addr1, write=True, data=value1),
        response_stall_cycles=2,
    )

    group = env.cpu.request_group - 1
    transactions = [item for item in env.cpu.transactions
                    if item["request_group"] == group]
    assert {(item["core"], item["addr"]) for item in transactions} == {
        (0, addr0), (1, addr1)
    }
    assert all(item["response_cycle"] > item["accepted_cycle"]
               for item in transactions)

    line_events = [event for event in env.monitor.events[event_start:]
                   if event.get("address") is not None and
                   event["address"] & ~0x3F == line]
    accepted_sources = [event["source_id"] for event in line_events
                        if event["source"] == "directory" and
                        event["event_type"] == "request_accept" and
                        event["opcode"] in (0b001, 0b010)]
    assert set(accepted_sources) == {0, 1}, (
        f"same-line CPU stores did not both reach Directory: {accepted_sources}"
    )
    # Feed the independent model in observed Directory arbitration order.
    # The two writes update different words, so either legal order must retain
    # both values while the final owner follows the last accepted request.
    modeled_sources = []
    for source in accepted_sources:
        if source in modeled_sources:
            continue
        request_addr, value = ((addr0, value0) if source == 0 else
                               (addr1, value1))
        env.reference.observe(source, request_addr, write=True,
                              write_data=value, write_mask=0xFF)
        modeled_sources.append(source)

    # The later readbacks independently check that both partial-line updates
    # survived whichever Directory request won arbitration.
    assert await env.cpu_access(0, addr0) == value0
    assert await env.cpu_access(1, addr1) == value1

    final_l1 = {}
    for event in line_events:
        if event["source"] == "l1" and event["event_type"] == "metadata_commit":
            final_l1[event["core"]] = event["new_state"]
    assert sum(state == 3 for state in final_l1.values()) <= 1
    assert not (2 in final_l1.values() and len(final_l1) > 1)
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event("FS.CONCURRENCY.SAME_LINE_DUAL_STORE",
                                      checked=True)


@case
async def test_same_address_dual_core_store_serialization(full_system_env):
    """The final value of conflicting writes follows observed acceptance order."""
    env = await full_system_env(axi_options={"latency": 10})
    address = 0x0060_3008
    initial = 0x1111_2222_3333_4444
    values = {0: 0xAAAA_BBBB_CCCC_DDDD, 1: 0x5555_6666_7777_8888}
    env.seed_word(address, initial)
    start = len(env.monitor.events)
    group = env.cpu.request_group

    await env.cpu.access_pair(
        CpuRequest(address, write=True, data=values[0]),
        CpuRequest(address, write=True, data=values[1]),
        response_stall_cycles=1,
    )

    transactions = [item for item in env.cpu.transactions
                    if item["request_group"] == group]
    assert {(item["core"], item["addr"]) for item in transactions} == {
        (0, address), (1, address)
    }
    assert all(item["accepted_cycle"] < item["response_cycle"]
               for item in transactions)
    line = address & ~0x3F
    events = [event for event in env.monitor.events[start:]
              if event.get("address") is not None and
              event["address"] & ~0x3F == line]
    accepted = []
    for event in events:
        if (event["source"] == "directory" and
                event["event_type"] == "request_accept" and
                event["opcode"] in (0b001, 0b010) and
                event["source_id"] not in accepted):
            accepted.append(event["source_id"])
    assert accepted == [0, 1] or accepted == [1, 0], (
        f"expected both same-address stores to serialize at Directory: {accepted}"
    )

    # This is an explicit ordering oracle: advance the reference model in the
    # order the DUT accepted the two conflicting ownership requests.
    for core in accepted:
        env.reference.observe(core, address, write=True,
                              write_data=values[core], write_mask=0xFF)
    expected = values[accepted[-1]]
    assert await env.cpu_access(0, address) == expected
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event(
        "FS.CONCURRENCY.SAME_ADDRESS_DUAL_WRITE", checked=True
    )


@case
async def test_l1_replacement_putm_races_remote_snoop(full_system_env):
    """A dirty L1 victim and a remote GetS of that line must not lose data."""
    env = await full_system_env(axi_options={"latency": 8})
    line = 0x00A0_0000
    peer_lines = [line + index * L2_SET_STRIDE for index in range(5)]
    owner_value = 0xCAFE_F00D_1234_5678
    env.seed_word(peer_lines[0], 0x1234)
    await env.cpu_access(1, peer_lines[0], write=True,
                         data=owner_value, mask=0xFF)
    for index, address in enumerate(peer_lines[1:4], start=1):
        value = 0x2200_0000 + index
        env.seed_word(address, value)
        assert await env.cpu_access(1, address) == value

    evict_line = peer_lines[0]
    replacement = peer_lines[4]
    replacement_value = 0x5566_7788_99AA_BBCC
    env.seed_word(replacement, replacement_value)
    start = len(env.monitor.events)
    # Core 1's fifth same-set request evicts its dirty line while Core 0 asks
    # for that same line. This exercises PutM/Snoop ordering through the real
    # CPU, Directory, L1 snoop, and shared-L2 interfaces.
    result0, result1 = await env.cpu.access_pair(
        CpuRequest(evict_line), CpuRequest(replacement),
        response_stall_cycles=1,
    )
    assert result0 == owner_value
    assert result1 == replacement_value

    events = env.monitor.events[start:]
    putm = [event for event in events
            if event["source"] == "directory" and
            event["event_type"] == "request_accept" and
            event["address"] & ~0x3F == evict_line and
            event["opcode"] == 0b101 and event["source_id"] == 1]
    snoop = [event for event in events
             if event["source"] == "snoop" and
             event["event_type"] == "accept" and
             event["core"] == 1 and event["address"] & ~0x3F == evict_line]
    assert putm, "dirty replacement did not issue PutM for the victim"
    assert snoop, "remote GetS did not snoop the dirty victim owner"
    assert abs(putm[0]["cycle"] - snoop[0]["cycle"]) <= 80, (
        "PutM and Snoop were not part of the same concurrent race window"
    )
    assert any(event["source"] == "snoop" and
               event["event_type"] == "response" for event in events)
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event("FS.RACE.REPLACEMENT_PUTM_SNOOP",
                                      checked=True)


@case
async def test_live_l2_victim_back_invalidates_resident_l1(full_system_env):
    """Inclusive L2 replacement snoops a clean line still resident in L1."""
    env = await full_system_env(axi_options={"latency": 4})
    target = 0x0200_0000
    stride = L2_SET_STRIDE
    target_value = 0xABCD_1234_9876_0001
    # The L2 array chooses the highest free way, then advances its replacement
    # pointer from the committed way. Fill six tags first so target lands in
    # way 1; the eighth line leaves the pointer at way 1 for the ninth miss.
    for index in range(1, 7):
        address = target + index * stride
        value = 0xA000_0000_0000_0000 | index
        env.seed_word(address, value)
        assert await env.cpu_access(1, address) == value

    env.seed_word(target, target_value)
    assert await env.cpu_access(0, target) == target_value

    # The target remains live in Core0 while the eighth tag fills the set;
    # the following miss requests the known target victim way.
    for index in range(7, 8):
        address = target + index * stride
        value = 0xA000_0000_0000_0000 | index
        env.seed_word(address, value)
        assert await env.cpu_access(1, address) == value

    event_start = len(env.monitor.events)
    refills_before = len(env.axi.read_addresses)
    ninth = target + 8 * stride
    ninth_value = 0xA000_0000_0000_0008
    env.seed_word(ninth, ninth_value)
    assert await env.cpu_access(1, ninth) == ninth_value

    events = env.monitor.events[event_start:]
    victim_snoop = [event for event in events
                    if event["source"] == "l2_victim" and
                    event["event_type"] == "snoop_accept" and
                    event["core"] == 0 and event["address"] == target]
    invalidation = [event for event in events
                    if event["source"] == "l1" and
                    event["event_type"] == "metadata_commit" and
                    event["core"] == 0 and event["address"] & ~0x3F == target and
                    event["is_snoop"] and event["new_state"] == 0]
    assert victim_snoop, (
        "the first full-set victim should be the live Core0 target line"
    )
    assert invalidation, "live L2 victim did not back-invalidate Core0's L1 copy"

    # A direct lane transaction avoids using a model state that predates the
    # inclusive eviction; the actual refill and data are checked at the pins.
    assert await env.cpu.access(0, target) == target_value
    assert any(addr & ~0x3F == target
               for _txn_id, addr, _cycle in env.axi.read_addresses[refills_before:]), (
        "Core0 read hit stale L1 metadata instead of refilling the evicted line"
    )
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event("FS.L2.LIVE_VICTIM_SNOOP", checked=True)


@case
async def test_dirty_l2_victim_snoops_live_modified_owner(full_system_env):
    """A dirty inclusive victim collects its live M owner before writeback."""
    env = await full_system_env(axi_options={
        "latency": 6, "ar_stall_period": 3,
        "aw_stall_period": 2, "w_stall_period": 2,
    })
    target = 0x0210_0000
    owner_value = 0xD1A7_0A11_0B0B_1E55
    expected_words = [0x7100_0000_0000_0000 | beat for beat in range(8)]
    for beat, value in enumerate(expected_words):
        env.seed_word(target + beat * 8, value)

    # Match the clean inclusive-victim test's way placement. The target stays
    # resident in Core0, but is explicitly made Modified after allocation.
    for index in range(1, 7):
        address = target + index * L2_SET_STRIDE
        for beat in range(8):
            env.seed_word(address + beat * 8,
                          0x7200_0000_0000_0000 | (index << 8) | beat)
        assert await env.cpu_access(1, address) == env.axi.read_word(address)

    await env.cpu_access(0, target, write=True,
                         data=owner_value, mask=0xFF)
    expected_words[0] = owner_value

    for index in range(7, 8):
        address = target + index * L2_SET_STRIDE
        for beat in range(8):
            env.seed_word(address + beat * 8,
                          0x7300_0000_0000_0000 | (index << 8) | beat)
        assert await env.cpu_access(1, address) == env.axi.read_word(address)

    event_start = len(env.monitor.events)
    aw_start = len(env.axi.write_addresses)
    w_start = len(env.axi.write_beats)
    b_start = len(env.axi.write_completions)
    ar_start = len(env.axi.read_addresses)
    ninth = target + 8 * L2_SET_STRIDE
    ninth_value = 0x7400_0000_0000_0008
    for beat in range(8):
        env.seed_word(ninth + beat * 8,
                      0x7400_0000_0000_0000 | (8 << 8) | beat)
    env.seed_word(ninth, ninth_value)

    assert await env.cpu_access(1, ninth) == ninth_value
    events = env.monitor.events[event_start:]
    victim_select = [event for event in events
                     if event["source"] == "l2_victim" and
                     event["event_type"] == "select" and
                     event["address"] == target]
    victim_snoop = [event for event in events
                    if event["source"] == "l2_victim" and
                    event["event_type"] == "snoop_accept" and
                    event["core"] == 0 and event["address"] == target]
    invalidation = [event for event in events
                    if event["source"] == "l1" and
                    event["event_type"] == "metadata_commit" and
                    event["core"] == 0 and event["address"] & ~0x3F == target and
                    event["is_snoop"] and event["old_state"] == 3 and
                    event["new_state"] == 0]
    # A live Modified L1 owner is the newest copy, so the backing L2 data
    # array may still be clean.  Check the directory's owner state instead of
    # requiring the stale L2 data-array dirty bit to be set.
    assert victim_select and victim_select[0]["directory_state"] == 2 and \
        victim_select[0]["owner"] == 0, (
            "the selected inclusive victim did not record Core0 as its M owner"
        )
    assert victim_snoop, "dirty live victim did not back-snoop Core0"
    assert invalidation, "dirty owner was not invalidated by inclusive eviction"

    owner_beats = [event for event in events
                   if event["source"] == "coherence" and
                   event["event_type"] == "owner_data_beat" and
                   event["core"] == 0 and event["address"] & ~0x3F == target]
    assert [event["beat"] for event in owner_beats] == list(range(8))
    assert [event["data"] for event in owner_beats] == expected_words
    assert [event["last"] for event in owner_beats] == [0] * 7 + [1]

    victim_writes = [item for item in env.axi.write_addresses[aw_start:]
                     if item[1] == target]
    assert victim_writes, "dirty live victim did not reach AXI AW"
    assert len(env.axi.write_completions[b_start:]) >= len(victim_writes)
    for txn_id, address, _cycle in victim_writes:
        beats = [item for item in env.axi.write_beats[w_start:]
                 if item[0] == txn_id]
        assert [item[1] for item in beats] == list(range(8))
        assert [item[2] for item in beats] == expected_words
        assert all(item[3] == 0xFF for item in beats)
        assert any(item[0] == txn_id and item[1] == address
                   for item in env.axi.write_completions[b_start:])
    assert all(env.axi.read_word(target + beat * 8) == expected_words[beat]
               for beat in range(8)), "AXI backing memory lost owner data"

    # The victim must no longer hit in Core0's inclusive L1 after invalidation.
    assert await env.cpu.access(0, target) == owner_value
    assert any(address & ~0x3F == target
               for _txn_id, address, _cycle in env.axi.read_addresses[ar_start:]), (
        "Core0 did not refill the evicted target line from backing memory"
    )
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event("FS.L2.DIRTY_OWNER_LIVE_VICTIM",
                                      checked=True)


@case
async def test_owner_snoop_overlaps_independent_memory_refill(full_system_env):
    """A dirty-owner snoop must progress beside a different cold-line refill."""
    env = await full_system_env(axi_options={"latency": 48})
    owner_addr = 0x0220_4000
    refill_addr = 0x0220_8000
    owner_value = 0x0D1E_0A11_0B0B_1E55
    refill_value = 0xBEEF_0000_0000_0042
    env.seed_word(owner_addr, 0x1234)
    await env.cpu_access(0, owner_addr, write=True, data=owner_value,
                         mask=0xFF)
    env.seed_word(refill_addr, refill_value)

    event_start = len(env.monitor.events)
    context_hist_start = env.monitor.directory_context_histogram.copy()
    group = env.cpu.request_group
    results = await env.cpu.access_pair(
        CpuRequest(refill_addr), CpuRequest(owner_addr), response_stall_cycles=2,
        request_delay_cycles={1: 8},
    )
    assert results == (refill_value, owner_value)

    events = env.monitor.events[event_start:]
    owner_snoops = [event for event in events
                    if event["source"] == "snoop" and
                    event["event_type"] == "accept" and event["core"] == 0 and
                    event["address"] & ~0x3F == owner_addr]
    owner_responses = [event for event in events
                       if event["source"] == "snoop" and
                       event["event_type"] == "response" and owner_snoops and
                       event["txn_id"] == owner_snoops[0]["txn_id"]]
    refill_ars = [event for event in events
                  if event["source"] == "axi" and
                  event["event_type"] == "read_address" and
                  event["address"] & ~0x3F == refill_addr]
    assert owner_snoops and owner_responses, (
        "the remote read did not complete a snoop against the dirty owner"
    )
    assert refill_ars, "the independent cold line did not start an AXI refill"
    assert refill_ars[0]["cycle"] <= owner_snoops[0]["cycle"] < \
        owner_responses[0]["cycle"], (
            "the independent AXI refill was not outstanding during owner snoop"
        )

    context_hist_delta = env.monitor.directory_context_histogram.copy()
    overlap_cycles = sum(
        count - context_hist_start.get(context_count, 0)
        for context_count, count in context_hist_delta.items()
        if context_count >= 2
    )
    assert overlap_cycles > 0, (
        "no cycle observed two active Directory contexts during Snoop/refill"
    )
    group_transactions = [item for item in env.cpu.transactions
                          if item["request_group"] == group]
    assert {item["core"] for item in group_transactions} == {0, 1}
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event(
        "FS.CONCURRENCY.SNOOP_WITH_REFILL", checked=True
    )


@case
async def test_apb_counters_writeback_and_reset_semantics(full_system_env):
    """Check exact basic event deltas, writeback count, and counter reset."""
    env = await full_system_env(axi_options={"latency": 4,
                                              "aw_stall_period": 3,
                                              "w_stall_period": 2})
    csr = env.apb
    offsets = (csr.CSR_HIT_COUNT, csr.CSR_MISS_COUNT, csr.CSR_SNOOP_COUNT,
               csr.CSR_DIRTY_WRITEBACK_COUNT, csr.CSR_ERROR_STATUS,
               csr.CSR_ACCESS_CYCLES, csr.CSR_COMPLETED_ACCESSES)
    assert [await csr.read(offset) for offset in offsets] == [0] * len(offsets)

    address = 0x0024_1000
    value = 0xF00D_F00D_1234_5678
    env.seed_word(address, value)
    assert await env.cpu_access(0, address) == value  # cold miss
    assert await env.cpu_access(0, address) == value  # local hit
    assert await env.cpu_access(1, address) == value  # remote-owner miss/snoop
    before_eviction = [await csr.read(offset) for offset in offsets]
    assert before_eviction[:5] == [1, 2, 1, 0, 0], before_eviction
    assert before_eviction[5] > 0
    assert before_eviction[6] == 3

    aw_before = len(env.axi.write_addresses)
    write_cursor = len(env.axi.write_beats)
    dirty_values = await _dirty_l2_set(env, 10, base=0x0140_2000)
    # Ten dirty lines in one 8-way L2 set require at least two dirty victims.
    # Set-up may have happened in _dirty_l2_set, so its traffic is retained.
    aw_after_setup = len(env.axi.write_addresses)
    assert aw_after_setup >= 2, (
        f"expected dirty L2 victims to reach AXI, observed {aw_after_setup} AW"
    )
    assert len(env.axi.write_completions) == aw_after_setup
    assert env.axi.peak_writes == 1, (
        "top-level SharedLineEngine is expected to serialize victim writebacks"
    )
    assert [item[1] for item in env.axi.write_completions[aw_before:]] == [
        item[1] for item in env.axi.write_addresses[aw_before:]
    ], "serialized top-level AW/B address order mismatch"
    for txn_id, addr, _cycle in env.axi.write_addresses[aw_before:]:
        beats = [beat for beat in env.axi.write_beats[write_cursor:]
                 if beat[0] == txn_id]
        assert len(beats) == 8, f"AW ID {txn_id} had {len(beats)} W beats"
        assert [beat[1] for beat in beats] == list(range(8))
        assert all(beat[3] == 0xFF for beat in beats)
        assert any(item[0] == txn_id and item[1] == addr
                   for item in env.axi.write_completions)
        assert addr in dirty_values
        assert env.axi.read_word(addr) == dirty_values[addr], (
            f"writeback data lost for dirty victim {addr:#x}"
        )
    for channel in ("AW", "W"):
        assert env.axi.stalls[channel] > 0, (
            f"integrated dirty writeback did not exercise AXI {channel} stall"
        )

    after_eviction = [await csr.read(offset) for offset in offsets]
    assert after_eviction[3] - before_eviction[3] == aw_after_setup
    assert after_eviction[6] - before_eviction[6] == 10
    assert after_eviction[5] > before_eviction[5]
    assert after_eviction[4] == 0
    assert int(env.dut.protocol_error.value) == 0
    await env.reset(cycles=3)
    reset_values = [await csr.read(offset) for offset in offsets]
    assert reset_values == [0] * len(offsets), reset_values
    env.coverage.sample_checked_event("FS.APB.COUNTER_WRITEBACK_RESET",
                                      checked=True)

    # The integrated line engine accepts only one victim write at a time.
    # The accepted AW/W/B logs above prove this serialized ordering contract;
    # the adapter Block tests separately check arbitrary multi-ID B reordering.
    env.coverage.sample_checked_event("FS.AXI.WRITE_SERIALIZED",
                                      checked=True)


@case
async def test_axi_bresp_error_fails_stop_on_dirty_victim_writeback(full_system_env):
    """An integrated AXI BRESP error must reach the system fatal status."""
    env = await full_system_env(axi_options={"latency": 32})
    await _dirty_l2_set(env, 8, base=0x0180_2000)
    assert not env.axi.write_addresses, "unexpected writeback before L2 is full"

    ninth = 0x0180_2000 + 8 * L2_SET_STRIDE
    env.seed_word(ninth, 0x9999)
    pending = asyncio.create_task(
        env.cpu.access(0, ninth, write=True,
                       data=0xD17A_0000_0000_0008, mask=0xFF)
    )
    try:
        await _wait_until(env.dut, lambda: bool(env.axi.write_addresses),
                          message="dirty victim AXI AW")
        victim_addr = env.axi.write_addresses[-1][1]
        env.axi.write_error_addrs.add(victim_addr)
        await _wait_until(env.dut,
                          lambda: any(error["channel"] == "B" and
                                      error["address"] == victim_addr
                                      for error in env.axi.errors),
                          cycles=300, message="AXI BRESP error handshake")
        assert int(env.dut.fatal_error.value) == 1
        assert int(env.dut.cpu_resp_valid.value) == 0
        status = await env.apb.read(env.apb.CSR_ERROR_STATUS)
        assert status & 0b00101 == 0b00101, f"APB error status={status:#x}"
        assert env.axi.write_completions[-1][1] == victim_addr
        env.coverage.sample_checked_event("FS.AXI.BRESP_ERROR", checked=True)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_cancels_integrated_axi_writeback_before_b(full_system_env):
    """Reset while a dirty victim write is in flight drops its B completion."""
    env = await full_system_env(axi_options={"latency": 96, "w_stall_period": 3})
    await _dirty_l2_set(env, 8, base=0x01C0_2000)
    ninth = 0x01C0_2000 + 8 * L2_SET_STRIDE
    env.seed_word(ninth, 0xAAAA)
    pending = asyncio.create_task(
        env.cpu.access(0, ninth, write=True,
                       data=0xD17A_0000_0000_0008, mask=0xFF)
    )
    try:
        await _wait_until(env.dut, lambda: bool(env.axi.write_addresses),
                          message="dirty victim AXI AW before reset")
        accepted_writes = len(env.axi.write_addresses)
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        assert env.axi.reset_cancelled["writes"] >= 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert len(env.axi.write_completions) < accepted_writes
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_event("FS.AXI.WRITE_RESET_CANCEL",
                                          checked=True)
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_axi_ar_backpressure(full_system_env):
    """Reset cancels a miss held at the AXI AR request handshake."""
    env = await full_system_env(axi_options={"latency": 8,
                                              "ar_stall_period": 2})
    address, value = 0x01E0_1008, 0xA11C_E001_0000_0001
    env.seed_word(address, value)
    pending = asyncio.create_task(env.cpu.access(0, address))
    try:
        await _wait_until(
            env.dut,
            lambda: int(env.dut.axi_arvalid.value) and
                    not int(env.dut.axi_arready.value),
            message="AXI ARVALID held by ARREADY backpressure",
        )
        assert not env.axi.read_addresses, "AR handshake occurred during observed stall"
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert not env.axi.read_completions
        assert await env.cpu_access(0, address) == value
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_AXI_AR_STALL", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_axi_r_valid_gap(full_system_env):
    """Reset cancels an accepted read while the memory inserts an RVALID gap."""
    env = await full_system_env(axi_options={"latency": 1,
                                              "r_valid_gap_period": 3})
    address, value = 0x01E0_2008, 0xA11C_E002_0000_0002
    env.seed_word(address, value)
    pending = asyncio.create_task(env.cpu.access(0, address))
    try:
        await _wait_until(
            env.dut,
            lambda: bool(env.axi.read_addresses) and
                    not int(env.dut.axi_rvalid.value),
            message="accepted AXI read during source RVALID gap",
        )
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        assert env.axi.reset_cancelled["reads"] >= 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert await env.cpu_access(0, address) == value
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_AXI_R_VALID_GAP", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_axi_aw_backpressure(full_system_env):
    """Reset cancels a dirty victim before its stalled AW handshake."""
    env = await full_system_env(axi_options={"latency": 12,
                                              "aw_stall_period": 2})
    await _dirty_l2_set(env, 8, base=0x01E0_4000)
    ninth = 0x01E0_4000 + 8 * L2_SET_STRIDE
    env.seed_word(ninth, 0xA11C_E004)
    pending = asyncio.create_task(
        env.cpu.access(0, ninth, write=True,
                       data=0xA11C_E004_0000_0004, mask=0xFF)
    )
    try:
        await _wait_until(
            env.dut,
            lambda: int(env.dut.axi_awvalid.value) and
                    not int(env.dut.axi_awready.value),
            message="AXI AWVALID held by AWREADY backpressure",
        )
        assert not env.axi.write_addresses, "AW handshake occurred during observed stall"
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert not env.axi.write_completions
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_AXI_AW_STALL", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_axi_w_backpressure(full_system_env):
    """Reset cancels an accepted dirty write while WREADY is low."""
    env = await full_system_env(axi_options={"latency": 12,
                                              "w_stall_period": 2})
    await _dirty_l2_set(env, 8, base=0x01E0_6000)
    ninth = 0x01E0_6000 + 8 * L2_SET_STRIDE
    env.seed_word(ninth, 0xA11C_E006)
    pending = asyncio.create_task(
        env.cpu.access(0, ninth, write=True,
                       data=0xA11C_E006_0000_0006, mask=0xFF)
    )
    try:
        await _wait_until(
            env.dut,
            lambda: int(env.dut.axi_wvalid.value) and
                    not int(env.dut.axi_wready.value),
            message="AXI WVALID held by WREADY backpressure",
        )
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        assert env.axi.reset_cancelled["writes"] >= 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert not env.axi.write_completions
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_AXI_W_STALL", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_cpu_response_backpressure(full_system_env):
    """Reset while a completed CPU result is held by response READY low."""
    env = await full_system_env(axi_options={"latency": 1})
    address, value = 0x01E0_8008, 0xA11C_E008_0000_0008
    env.seed_word(address, value)
    pending = asyncio.create_task(
        env.cpu.access(0, address, response_stall_cycles=100)
    )
    try:
        await _wait_until(
            env.dut,
            lambda: (int(env.dut.cpu_resp_valid.value) & 1) and
                    not (int(env.dut.cpu_resp_ready.value) & 1),
            message="CPU response held by response backpressure",
        )
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert await env.cpu_access(0, address) == value
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_CPU_RESPONSE_STALL", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0


@case
async def test_reset_during_mmio_request_backpressure(full_system_env):
    """Reset cancels a CPU MMIO operation stalled at the request handshake."""
    env = await full_system_env(mmio_options={"request_stall_period": 2,
                                               "response_delay": 1})
    address = 0x3000_0600
    pending = asyncio.create_task(env.cpu.access(0, address))
    try:
        await _wait_until(
            env.dut,
            lambda: int(env.dut.mmio_req_valid.value) and
                    not int(env.dut.mmio_req_ready.value),
            message="MMIO request held by request READY backpressure",
        )
        assert not env.mmio.requests, "MMIO request accepted during observed stall"
        old_epoch = env.monitor.reset_epoch
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=3)
        assert env.monitor.reset_epoch == old_epoch + 1
        await ClockCycles(env.dut, 8)
        assert int(env.dut.cpu_resp_valid.value) == 0
        assert int(env.dut.mmio_resp_valid.value) == 0
        assert await env.cpu.access(0, address) == 0
        assert len(env.mmio.completions) == 1
        assert int(env.dut.fatal_error.value) == 0
        env.coverage.sample_checked_cross(
            "FS.CROSS.RESET_MMIO_REQUEST_STALL", checked=True
        )
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0
