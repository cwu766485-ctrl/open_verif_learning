"""System tests for owner Snoop progress with live L1 miss contexts."""

from toffee import ClockCycles
from toffee_test import case

from dv.checkers.l1_mshr_collision_checker import L1MshrCollisionChecker
from dv.checkers.l1_mshr_lifecycle_checker import L1MshrLifecycleChecker
from dv.checkers.l1_mshr_reset_reuse_checker import L1MshrResetReuseChecker
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker


DATA_MASK = (1 << 64) - 1
LINE_MASK = 0xFFFF_FFC0


async def _offer_one(env, core, address, *, timeout=1200):
    dut = env.dut
    bit = 1 << core
    dut.cpu_req_addr.value = (int(address) & 0xFFFF_FFFF) << (32 * core)
    dut.cpu_req_write.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_wmask.value = 0
    dut.cpu_req_valid.value = bit
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        if int(dut.cpu_req_ready.value) & bit:
            env.monitor.record_cpu_request_accept(
                core, address, False, cycle=env.monitor.cycle
            )
            dut.cpu_req_valid.value = 0
            return
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"core{core} request {address:#x} was not accepted")


async def _offer_pair(env, address0, address1, *, timeout=1600):
    """Hold both packed CPU lanes until their independent handshakes."""
    dut = env.dut
    pending = {0: int(address0), 1: int(address1)}
    valid = 0b11
    dut.cpu_req_addr.value = (int(address0) & 0xFFFF_FFFF) | \
        ((int(address1) & 0xFFFF_FFFF) << 32)
    dut.cpu_req_write.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_wmask.value = 0
    dut.cpu_req_valid.value = valid
    accepted = {}
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        ready = int(dut.cpu_req_ready.value)
        for core in tuple(pending):
            if ready & (1 << core):
                address = pending.pop(core)
                accepted[core] = env.monitor.cycle
                env.monitor.record_cpu_request_accept(
                    core, address, False, cycle=env.monitor.cycle
                )
                valid &= ~(1 << core)
                dut.cpu_req_valid.value = valid
        if not pending:
            return accepted
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"paired requests were not both accepted: {pending}")


async def _wait(env, predicate, label, *, timeout=2000):
    for _ in range(timeout):
        if predicate():
            return
        await ClockCycles(env.dut, 1)
    raise TimeoutError(f"timed out waiting for {label}")


async def _collect_responses(env, count, *, timeout=2400):
    dut = env.dut
    dut.cpu_resp_ready.value = 0b11
    responses = []
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        fire = int(dut.cpu_resp_valid.value) & int(dut.cpu_resp_ready.value) & 0b11
        for core in range(2):
            if not fire & (1 << core):
                continue
            response = {
                "core": core,
                "address": (int(dut.cpu_resp_addr.value) >> (32 * core)) &
                           0xFFFF_FFFF,
                "data": (int(dut.cpu_resp_rdata.value) >> (64 * core)) &
                        DATA_MASK,
                "txn_id": (int(dut.cpu_resp_txn_id.value) >> (3 * core)) & 7,
                "write": (int(dut.cpu_resp_write.value) >> core) & 1,
            }
            responses.append(response)
            env.monitor.record_cpu_response_complete(
                core, response["address"], response["write"], response["data"],
                response["txn_id"], cycle=env.monitor.cycle,
            )
        if len(responses) == count:
            dut.cpu_resp_ready.value = 0
            return responses
    dut.cpu_resp_ready.value = 0
    raise TimeoutError(f"CPU responses incomplete: {len(responses)}/{count}")


async def _take_one_response(env, core, *, timeout=1800):
    """Accept and return one response while preserving per-core ordering."""
    dut = env.dut
    bit = 1 << core
    dut.cpu_resp_ready.value = bit
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        if (int(dut.cpu_resp_valid.value) &
                int(dut.cpu_resp_ready.value) & bit):
            response = {
                "core": core,
                "address": (int(dut.cpu_resp_addr.value) >> (32 * core)) &
                           0xFFFF_FFFF,
                "data": (int(dut.cpu_resp_rdata.value) >> (64 * core)) &
                        DATA_MASK,
                "txn_id": (int(dut.cpu_resp_txn_id.value) >> (3 * core)) & 7,
                "write": (int(dut.cpu_resp_write.value) >> core) & 1,
            }
            env.monitor.record_cpu_response_complete(
                core, response["address"], response["write"],
                response["data"], response["txn_id"],
                cycle=env.monitor.cycle,
            )
            return response
    raise TimeoutError(f"core{core} response did not handshake")


@case
async def test_owner_snoop_progresses_while_two_l1_misses_are_live(full_system_env):
    """A dirty-owner transfer completes while its L1 tracks two other misses."""
    env = await full_system_env(
        seed=0x13_0C02,
        axi_options={"latency": 180, "r_valid_gap_period": 2,
                     "read_reorder_window": 2},
    )
    env.trace_scenario_id = "V13_TWO_LIVE_MSHR_OWNER_SNOOP_PROGRESS"

    dirty_line = 0x00A0_0000
    miss_a = dirty_line + 0x100
    miss_b = dirty_line + 0x180
    owner_words = [0xCAFE_F00D_1234_5678] + [
        0xD17A_0000_0000_0000 | beat for beat in range(1, 8)
    ]
    miss_values = {
        miss_a: 0xA110_0000_0000_0101,
        miss_b: 0xA110_0000_0000_0202,
    }
    for address, words in ((dirty_line, owner_words),):
        for beat, value in enumerate(words):
            env.seed_word(address + beat * 8, value)
    for address, value in miss_values.items():
        for beat in range(8):
            env.seed_word((address & LINE_MASK) + beat * 8,
                          value ^ (beat << 48))

    # Legal prelude: Core1 obtains M ownership of the dirty line. The two
    # subsequent misses map to different L1 sets and need no replacement.
    assert await env.cpu_access(1, dirty_line, write=True,
                                data=owner_words[0]) == owner_words[0]
    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)
    env.trace_config.update({
        "l1_mshr_entries_per_core": 2,
        "owner_core": 1,
        "remote_gets_core": 0,
        "dirty_owner_line": dirty_line,
        "concurrent_miss_lines": [miss_a, miss_b],
        "memory_latency_cycles": 180,
        "cpu_response_ready_during_overlap": 0,
        "required_overlap": "two Core1 MSHRs active during all owner data beats",
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "establish_core1_dirty_owner",
         "core": 1, "address": dirty_line, "data": owner_words[0]},
        {"kind": "stimulus", "operation": "first_miss_then_owner_gets_and_second_miss",
         "core1_misses": [miss_a, miss_b], "core0_remote_gets": [dirty_line]},
    ])

    await _offer_one(env, 1, miss_a)
    await _wait(env, lambda: any(
        event.get("source") == "directory" and
        event.get("event_type") == "request_accept" and
        int(event.get("source_id", -1)) == 1 and
        int(event.get("address", -1)) & LINE_MASK == miss_a & LINE_MASK
        for event in env.monitor.events[event_start:]), "first Core1 Directory request")

    await _offer_pair(env, dirty_line, miss_b)
    await _wait(env, lambda: env.monitor.max_l1_mshr_per_core.get(1, 0) == 2,
                "both Core1 L1 MSHRs")
    await _wait(env, lambda: sum(
        event.get("source") == "directory" and
        event.get("event_type") == "request_accept" and
        int(event.get("source_id", -1)) == 1 and
        (int(event.get("address", -1)) & LINE_MASK) in
        {miss_a & LINE_MASK, miss_b & LINE_MASK}
        for event in env.monitor.events[event_start:]) == 2,
        "both Core1 Directory handshakes")
    await _wait(env, lambda: sum(
        event.get("source") == "coherence" and
        event.get("event_type") == "owner_data_beat" and
        int(event.get("core", -1)) == 1 and
        int(event.get("address", -1)) & LINE_MASK == dirty_line & LINE_MASK
        for event in env.monitor.events[event_start:]) == 8,
        "complete eight-beat dirty-owner stream")
    await _wait(env, lambda: any(
        event.get("source") == "snoop" and
        event.get("event_type") == "response" and
        int(event.get("core", -1)) == 1
        for event in env.monitor.events[event_start:]),
        "owner Snoop response handshake")

    events = env.monitor.events[event_start:]
    assert int(env.dut.monitor_l1_mshr_valid.value) & 0b1100 == 0b1100
    assert not any(event.get("source") == "cpu" and
                   event.get("event_type") == "response_complete" and
                   event.get("core") == 1 for event in events)
    collision = L1MshrCollisionChecker.check(
        events, dirty_line=dirty_line, owner_core=1, requester_core=0,
        expected_owner_words=owner_words, concurrent_miss_lines=(miss_a, miss_b),
    )

    responses = await _collect_responses(env, 3)
    await ClockCycles(env.dut, 2)
    actual = {(item["core"], item["address"]): item["data"]
              for item in responses}
    events = env.monitor.events[event_start:]
    expected = {
        (0, dirty_line): owner_words[0],
        (1, miss_a): env.axi.read_word(miss_a),
        (1, miss_b): env.axi.read_word(miss_b),
    }
    assert actual == expected
    core1_order = [item["address"] for item in responses if item["core"] == 1]
    assert core1_order == [miss_a, miss_b], core1_order

    requests = [(1, miss_a, expected[(1, miss_a)]),
                (1, miss_b, expected[(1, miss_b)])]
    l1_evidence = L1MshrLifecycleChecker.check(
        events, expected_requests=requests,
        first_response_must_follow_all_allocs=False,
    )
    refill_evidence = MshrLifecycleChecker.check(
        events,
        expected_lines={miss_a & LINE_MASK, miss_b & LINE_MASK},
        expected_words={miss_a: expected[(1, miss_a)],
                        miss_b: expected[(1, miss_b)]},
        expected_cores={miss_a: 1, miss_b: 1},
    )
    assert env.monitor.max_l1_mshr_per_core[1] == 2
    assert env.monitor.max_directory_contexts >= 2
    assert env.monitor.max_mshr_occupancy >= 2
    assert env.axi.peak_reads >= 2
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    assert not env.axi.errors, env.axi.errors

    env.trace_operations.extend([
        {"kind": "checker_evidence", "checker": "L1MshrCollisionChecker",
         "result": collision},
        {"kind": "checker_evidence", "checker": "L1MshrLifecycleChecker",
         "result": l1_evidence},
        {"kind": "checker_evidence", "checker": "MshrLifecycleChecker",
         "result": refill_evidence},
        {"kind": "resource_peaks",
         "l1_mshr_per_core": dict(env.monitor.max_l1_mshr_per_core),
         "directory_contexts": env.monitor.max_directory_contexts,
         "refill_mshrs": env.monitor.max_mshr_occupancy,
         "axi_read_outstanding": env.axi.peak_reads},
    ])
    env.coverage.sample_checked_event("FS.RACE.OWNER_SNOOP_WITH_TWO_L1_MSHR",
                                      checked=True)
    await ClockCycles(env.dut, 2)


@case
async def test_dirty_replacement_putm_overlaps_owner_snoop_with_two_requester_mshrs(
        full_system_env):
    """A dirty replacement and remote owner Snoop overlap two peer misses."""
    env = await full_system_env(
        seed=0x13_0C04,
        axi_options={"latency": 240, "r_valid_gap_period": 2,
                     "read_reorder_window": 2},
    )
    env.trace_scenario_id = "V13_PUTM_OWNER_SNOOP_TWO_REQUESTER_MSHR"

    dirty_victim_line = 0x00C0_0000
    dirty_owner_line = dirty_victim_line + 0x2000
    miss_a = dirty_victim_line + 0x100
    replacement = dirty_victim_line + 4 * 0x2000
    owner_words = [0xCAFE_C011_0000_0000 | beat for beat in range(8)]
    replacement_words = [0xBEEF_0000_0000_0000 | beat for beat in range(8)]
    miss_words = [0xA110_0000_0000_0000 | (0x10 + beat)
                  for beat in range(8)]

    for address, words in ((dirty_owner_line, owner_words),
                           (dirty_victim_line, replacement_words),
                           (replacement, replacement_words),
                           (miss_a, miss_words)):
        for beat, value in enumerate(words):
            env.seed_word(address + beat * 8, value)

    # L1 uses address[12:6] for its set and L2 uses address[14:6]. These
    # lines alias in L1 while occupying distinct L2 sets, allowing the dirty
    # victim PutM and owner-data Snoop to refer to different lines.
    # Core1 makes the first line dirty, then keeps dirty_owner_line resident.
    assert await env.cpu_access(1, dirty_victim_line, write=True,
                                data=replacement_words[0]) == replacement_words[0]
    assert await env.cpu_access(1, dirty_owner_line, write=True,
                                data=owner_words[0]) == owner_words[0]
    for index, address in enumerate((dirty_victim_line + 2 * 0x2000,
                                     dirty_victim_line + 3 * 0x2000), start=1):
        words = [0xC100_0000_0000_0000 | (index << 8) | beat
                 for beat in range(8)]
        for beat, value in enumerate(words):
            env.seed_word(address + beat * 8, value)
        assert await env.cpu_access(1, address) == words[0]

    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)
    env.trace_config.update({
        "seed": 0x13_0C04,
        "owner_core": 1,
        "requester_core": 0,
        "dirty_victim_line": dirty_victim_line,
        "dirty_owner_line": dirty_owner_line,
        "replacement_line": replacement,
        "concurrent_miss_lines": [miss_a, dirty_owner_line],
        "concurrent_miss_core": 0,
        "memory_latency_cycles": 240,
        "required_overlap": "owner PutM + matching Snoop + 8 data beats while requester L1 MSHRs=2",
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "establish_dirty_owner_and_fill_l1_set",
         "core": 1, "dirty_victim_line": dirty_victim_line,
         "dirty_owner_line": dirty_owner_line,
         "other_lines": [dirty_victim_line + index * 0x2000
                         for index in range(2, 4)]},
        {"kind": "stimulus", "operation": "overlap_remote_gets_with_dirty_putm_replacement",
         "requester_core": 0, "requester_misses": [miss_a, dirty_owner_line],
         "owner_core": 1, "replacement_line": replacement},
    ])

    # Start one cold miss first, then present the remote owner-line miss and
    # Core1's replacement together. Long memory latency keeps the first
    # requester context live while the independent PutM/Snoop requests contend.
    await _offer_one(env, 0, miss_a)
    await _wait(env, lambda: any(
        event.get("source") == "directory" and
        event.get("event_type") == "request_accept" and
        int(event.get("address", -1)) & LINE_MASK == miss_a & LINE_MASK
        for event in env.monitor.events[event_start:]),
        "first requester Directory handshake")
    await _offer_pair(env, dirty_owner_line, replacement)

    def putm_seen():
        return any(event.get("source") == "directory" and
                   event.get("event_type") == "request_accept" and
                   int(event.get("opcode", -1)) == 0b101 and
                   int(event.get("address", -1)) & LINE_MASK == dirty_victim_line
                   for event in env.monitor.events[event_start:])

    def snoop_seen():
        return any(event.get("source") == "snoop" and
                   event.get("event_type") == "accept" and
                   int(event.get("core", -1)) == 1 and
                   int(event.get("address", -1)) & LINE_MASK == dirty_owner_line
                   for event in env.monitor.events[event_start:])

    await _wait(env, lambda: env.monitor.max_l1_mshr_per_core.get(0, 0) == 2,
                "two requester L1 MSHRs", timeout=2400)
    await _wait(env, lambda: putm_seen() and snoop_seen(),
                "replacement PutM and matching owner Snoop", timeout=2400)
    await _wait(env, lambda: sum(
        event.get("source") == "coherence" and
        event.get("event_type") == "owner_data_beat" and
        int(event.get("core", -1)) == 1 and
        int(event.get("address", -1)) & LINE_MASK == dirty_owner_line
        for event in env.monitor.events[event_start:]) == 8,
        "eight owner-data beats", timeout=2400)
    await _wait(env, lambda: any(
        event.get("source") == "snoop" and
        event.get("event_type") == "response" and
        int(event.get("core", -1)) == 1
        for event in env.monitor.events[event_start:]),
        "owner Snoop response", timeout=2400)

    events = env.monitor.events[event_start:]
    assert int(env.dut.monitor_l1_mshr_valid.value) & 0b0011 == 0b0011
    collision = L1MshrCollisionChecker.check(
        events, dirty_line=dirty_owner_line, putm_line=dirty_victim_line,
        owner_core=1, requester_core=0,
        expected_owner_words=owner_words, expect_putm=True,
        concurrent_miss_lines=(miss_a, dirty_owner_line),
        concurrent_miss_core=0,
    )

    responses = await _collect_responses(env, 3)
    await ClockCycles(env.dut, 2)
    # Include the monitor edge that observes retirement after the final
    # accepted response; the race checker above intentionally used the live
    # event window before responses were released.
    events = env.monitor.events[event_start:]
    core0_order = [item["address"] for item in responses if item["core"] == 0]
    assert core0_order == [miss_a, dirty_owner_line], core0_order
    expected = {
        (0, miss_a): env.axi.read_word(miss_a),
        (0, dirty_owner_line): owner_words[0],
        (1, replacement): env.axi.read_word(replacement),
    }
    observed = {(item["core"], item["address"]): item["data"]
                for item in responses}
    assert observed == expected

    # The cold miss has a memory refill; the remote owner line is checked by
    # the independent eight-beat checker above and the CPU response scoreboard.
    l1_evidence = L1MshrLifecycleChecker.check(
        events, expected_requests=[(0, miss_a, expected[(0, miss_a)])],
        first_response_must_follow_all_allocs=False,
    )
    refill_evidence = MshrLifecycleChecker.check(
        # Both cold misses allocate lower-level refill MSHRs: the requester
        # miss and Core1's replacement line. The remote owner line is supplied
        # by the checked Snoop stream and is deliberately not counted as an AXI
        # refill.
        events, expected_lines={miss_a & LINE_MASK, replacement & LINE_MASK},
        expected_words={miss_a: expected[(0, miss_a)],
                        replacement: expected[(1, replacement)]},
        expected_cores={miss_a: 0, replacement: 1},
    )
    assert env.monitor.max_l1_mshr_per_core[0] == 2
    assert env.monitor.max_directory_contexts >= 2
    assert env.monitor.max_mshr_occupancy >= 1
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    assert not env.axi.errors, env.axi.errors

    evidence = {"collision": collision, "l1_lifecycle": l1_evidence,
                "refill_lifecycle": refill_evidence,
                "l1_mshr_peak_requester": env.monitor.max_l1_mshr_per_core[0],
                "directory_context_peak": env.monitor.max_directory_contexts,
                "refill_mshr_peak": env.monitor.max_mshr_occupancy,
                "axi_read_peak": env.axi.peak_reads}
    env.trace_operations.append({"kind": "checker_evidence",
                                 "checker": "PutMOwnerSnoopTwoMshrCheckers",
                                 "result": evidence})
    env.coverage.sample_checked_event(
        "FS.RACE.OWNER_SNOOP_WITH_TWO_L1_MSHR", checked=True
    )


@case
async def test_two_l1_mshrs_reset_cancel_and_reuse_ids_with_response_backpressure(
        full_system_env):
    """Reset cancels two live misses; replay reuses IDs and retires in order."""
    env = await full_system_env(
        seed=0x13_0C05,
        axi_options={"latency": 420, "r_valid_gap_period": 2,
                     "read_reorder_window": 2},
    )
    env.trace_scenario_id = "V13_TWO_MSHR_RESET_ID_REUSE_BACKPRESSURE"
    addresses = (0x00D0_0008, 0x00D0_0108)
    values = (0xDADA_0000_0000_0001, 0xDADA_0000_0000_0002)
    for address, value in zip(addresses, values):
        for beat in range(8):
            env.seed_word((address & LINE_MASK) + beat * 8,
                          value ^ (beat << 48))

    env.dut.cpu_resp_ready.value = 0
    pre_epoch = env.monitor.reset_epoch
    event_start = len(env.monitor.events)
    env.trace_config.update({
        "seed": 0x13_0C05,
        "core": 0,
        "addresses": list(addresses),
        "axi_latency_cycles": 420,
        "response_backpressure": True,
        "expected_reset_cancel": {"l1_mshr_entries": 2, "axi_reads": 2},
        "expected_after_reset": "same per-protocol IDs reused by same address; ordered responses",
    })
    env.trace_operations.append({
        "kind": "stimulus", "operation": "two_misses_reset_then_replay_same_lines",
        "core": 0, "addresses": list(addresses),
    })

    await _offer_one(env, 0, addresses[0])
    await _wait(env, lambda: len(env.axi.read_addresses) >= 1,
                "first AXI read address", timeout=800)
    await _offer_one(env, 0, addresses[1])
    await _wait(env, lambda: len(env.axi.read_addresses) >= 2 and
                env.monitor.max_l1_mshr_per_core.get(0, 0) == 2,
                "two live L1 misses and AXI reads", timeout=800)
    assert env.axi.peak_reads >= 2, env.axi.peak_reads
    assert int(env.dut.monitor_l1_mshr_valid.value) & 0b0011 == 0b0011
    pre_events = env.monitor.events[event_start:]
    assert not any(event.get("source") == "cpu" and
                   event.get("event_type") == "response_complete"
                   for event in pre_events)

    await env.reset(cycles=3)
    post_epoch = env.monitor.reset_epoch
    assert post_epoch == pre_epoch + 1
    await ClockCycles(env.dut, 8)
    assert int(env.dut.monitor_l1_mshr_valid.value) == 0
    assert int(env.dut.cpu_resp_valid.value) == 0
    reset_event = next(event for event in reversed(env.monitor.events)
                       if event.get("source") == "system" and
                       event.get("event_type") == "reset_cancel" and
                       event.get("reset_epoch") == pre_epoch)
    assert reset_event["payload"]["l1_mshr_entries"] == 2
    assert reset_event["payload"]["axi_reads"] == 2

    replay_start = len(env.monitor.events)
    axi_start = len(env.axi.read_addresses)
    for address in addresses:
        await _offer_one(env, 0, address)
    await _wait(env, lambda: len(env.axi.read_addresses) >= axi_start + 2,
                "both replay AXI reads", timeout=800)
    await _wait(env, lambda: int(env.dut.cpu_resp_valid.value) & 1,
                "response held under CPU backpressure", timeout=1200)
    assert int(env.dut.cpu_resp_ready.value) & 1 == 0
    assert int(env.dut.monitor_l1_mshr_valid.value) & 0b0011 == 0b0011

    responses = await _collect_responses(env, 2)
    await ClockCycles(env.dut, 2)
    assert [item["address"] for item in responses] == list(addresses)
    assert [item["data"] for item in responses] == [
        env.axi.read_word(address) for address in addresses
    ]
    post_events = env.monitor.events[replay_start:]
    # The direct driver callback and passive pin sampler can timestamp the
    # same ready/valid edge on adjacent monitor ticks. Use the passive pin
    # observation as the single handshake source for lifecycle accounting;
    # the raw trace retains both records for audit.
    lifecycle_events = [
        event for event in post_events
        if not (event.get("source") == "cpu" and
                event.get("event_type") == "request_accept" and
                event.get("payload", {}).get("observed_by") == "cpu_driver")
    ]
    lifecycle = L1MshrLifecycleChecker.check(
        lifecycle_events,
        expected_requests=[(0, address, env.axi.read_word(address))
                           for address in addresses],
        first_response_must_follow_all_allocs=True,
    )
    reuse = L1MshrResetReuseChecker.check(
        env.monitor.events, core=0, addresses=addresses,
        pre_reset_epoch=pre_epoch, post_reset_epoch=post_epoch,
        expected_cancelled_mshrs=2, expected_cancelled_axi_reads=2,
    )
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    assert not env.axi.errors, env.axi.errors
    env.trace_operations.extend([
        {"kind": "checker_evidence", "checker": "L1MshrLifecycleChecker",
         "result": lifecycle},
        {"kind": "checker_evidence", "checker": "L1MshrResetReuseChecker",
         "result": reuse},
        {"kind": "resource_peaks",
         "l1_mshr_per_core": dict(env.monitor.max_l1_mshr_per_core),
         "directory_contexts": env.monitor.max_directory_contexts,
         "refill_mshrs": env.monitor.max_mshr_occupancy,
         "axi_read_outstanding": env.axi.peak_reads},
    ])


@case
async def test_same_set_second_miss_waits_for_first_retirement(full_system_env):
    """A same-L1-set miss is held stable, then progresses after retirement."""
    env = await full_system_env(
        seed=0x13_0C03,
        axi_options={"latency": 80, "r_valid_gap_period": 2},
    )
    env.trace_scenario_id = "V13_SAME_SET_MISS_BACKPRESSURE_RECOVERY"
    first = 0x00B0_0008
    second = first + 0x8000  # Same L1 and L2 set, different cache line/tag.
    values = {
        first: 0x51A0_0000_0000_0001,
        second: 0x51A0_0000_0000_0002,
    }
    for address, value in values.items():
        line = address & LINE_MASK
        for beat in range(8):
            env.seed_word(line + beat * 8, value ^ (beat << 48))
    expected_data = {address: env.axi.read_word(address) for address in values}

    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)
    env.trace_config.update({
        "l1_mshr_entries_per_core": 2,
        "same_l1_set_addresses": [first, second],
        "expected_behavior": "second request stalls until first MSHR retires",
    })
    await _offer_one(env, 0, first)
    await _wait(
        env,
        lambda: any(event.get("source") == "directory" and
                    event.get("event_type") == "request_accept" and
                    int(event.get("source_id", -1)) == 0 and
                    (int(event.get("address", -1)) & LINE_MASK) ==
                    (first & LINE_MASK)
                    for event in env.monitor.events[event_start:]),
        "first same-set Directory request",
    )

    # Keep the second request and all payload fields unchanged through the
    # backpressure interval. It must not allocate a second context or issue a
    # Directory transaction while the first same-set miss owns the array path.
    env.dut.cpu_req_addr.value = second
    env.dut.cpu_req_write.value = 0
    env.dut.cpu_req_wdata.value = 0
    env.dut.cpu_req_wmask.value = 0
    env.dut.cpu_req_valid.value = 1
    for _ in range(8):
        await ClockCycles(env.dut, 1)
        assert not (int(env.dut.cpu_req_ready.value) & 1), (
            "same-set second miss was accepted while the first MSHR was live"
        )
        assert (int(env.dut.cpu_req_addr.value) & 0xFFFF_FFFF) == second
        assert int(env.dut.monitor_l1_mshr_valid.value) & 0b11 == 0b01
        assert sum(event.get("source") == "directory" and
                   event.get("event_type") == "request_accept" and
                   int(event.get("source_id", -1)) == 0
                   for event in env.monitor.events[event_start:]) == 1

    first_response = await _take_one_response(env, 0)
    env.dut.cpu_resp_ready.value = 0
    assert first_response["address"] == first
    assert first_response["data"] == expected_data[first]

    # The held request must eventually handshake after capacity is released.
    accepted = False
    for _ in range(200):
        await ClockCycles(env.dut, 1)
        if int(env.dut.cpu_req_ready.value) & 1:
            env.monitor.record_cpu_request_accept(
                0, second, False, cycle=env.monitor.cycle
            )
            accepted = True
            env.dut.cpu_req_valid.value = 0
            break
    env.dut.cpu_req_valid.value = 0
    assert accepted, "held same-set request did not make forward progress"
    second_response = await _take_one_response(env, 0)
    env.dut.cpu_resp_ready.value = 0
    assert second_response["address"] == second
    assert second_response["data"] == expected_data[second]
    # Drain the monitor's sampling edge after the final response handshake so
    # its independently observed MSHR retire event is included below.
    await ClockCycles(env.dut, 2)

    events = env.monitor.events[event_start:]
    requests = [event for event in events
                if event.get("source") == "directory" and
                event.get("event_type") == "request_accept" and
                int(event.get("source_id", -1)) == 0]
    assert [event["address"] & LINE_MASK for event in requests] == [
        first & LINE_MASK, second & LINE_MASK,
    ]
    assert requests[0]["cycle"] < requests[1]["cycle"]
    lifecycle = L1MshrLifecycleChecker.check(
        events,
        expected_requests=[(0, first, expected_data[first]),
                           (0, second, expected_data[second])],
        first_response_must_follow_all_allocs=False,
    )
    refill = MshrLifecycleChecker.check(
        events,
        expected_lines={first & LINE_MASK, second & LINE_MASK},
        expected_words=expected_data,
        expected_cores={first: 0, second: 0},
    )
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    env.trace_operations.extend([
        {"kind": "checker_evidence", "checker": "L1MshrLifecycleChecker",
         "result": lifecycle},
        {"kind": "checker_evidence", "checker": "MshrLifecycleChecker",
         "result": refill},
        {"kind": "backpressure_evidence", "scenario": "same_l1_set",
         "stall_cycles": 8, "accepted_after_first_retire": accepted},
    ])


@case
async def test_resident_hit_is_backpressured_when_both_l1_mshrs_are_full(full_system_env):
    """Full miss tracking blocks a hit, then the held hit proceeds safely."""
    env = await full_system_env(
        seed=0x13_0C04,
        axi_options={"latency": 180, "r_valid_gap_period": 2},
    )
    env.trace_scenario_id = "V13_FULL_MSHR_HIT_BACKPRESSURE_FORWARD_PROGRESS"
    resident = 0x00C0_0048
    miss_a = 0x00C1_0008
    miss_b = 0x00C2_0108
    expected = {
        resident: 0xF011_0000_0000_0001,
        miss_a: 0xF011_0000_0000_0002,
        miss_b: 0xF011_0000_0000_0003,
    }
    for address, value in expected.items():
        line = address & LINE_MASK
        for beat in range(8):
            env.seed_word(line + beat * 8, value ^ (beat << 48))
    expected_data = {address: env.axi.read_word(address) for address in expected}
    assert await env.cpu_access(0, resident) == expected_data[resident]

    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)
    await _offer_one(env, 0, miss_a)
    await _wait(
        env,
        lambda: any(event.get("source") == "axi" and
                    event.get("event_type") == "read_address" and
                    (int(event.get("address", -1)) & LINE_MASK) ==
                    (miss_a & LINE_MASK)
                    for event in env.monitor.events[event_start:]),
        "first miss AXI read address",
    )
    await _offer_one(env, 0, miss_b)
    await _wait(
        env,
        lambda: (int(env.dut.monitor_l1_mshr_valid.value) & 0b11) == 0b11,
        "both L1 miss entries live",
    )
    await _wait(
        env,
        lambda: bool(int(env.dut.cpu_resp_valid.value) & 1),
        "miss response held while both entries remain allocated",
    )

    # A genuine resident read is offered while both miss contexts are occupied.
    # The legacy bypass predicate intentionally requires occupancy == 1.
    env.dut.cpu_req_addr.value = resident
    env.dut.cpu_req_write.value = 0
    env.dut.cpu_req_wdata.value = 0
    env.dut.cpu_req_wmask.value = 0
    env.dut.cpu_req_valid.value = 1
    for _ in range(8):
        await ClockCycles(env.dut, 1)
        assert not (int(env.dut.cpu_req_ready.value) & 1), (
            "resident hit bypassed while both L1 MSHRs were occupied"
        )
        assert (int(env.dut.cpu_req_addr.value) & 0xFFFF_FFFF) == resident
        assert int(env.dut.monitor_l1_mshr_valid.value) & 0b11 == 0b11

    # Retiring misses frees an entry. Keep the hit stable while collecting all
    # responses; it may complete between the two FIFO-ordered miss responses.
    env.dut.cpu_resp_ready.value = 1
    responses = []
    hit_accepted = False
    for _ in range(2400):
        await ClockCycles(env.dut, 1)
        if not hit_accepted and int(env.dut.cpu_req_ready.value) & 1:
            env.monitor.record_cpu_request_accept(
                0, resident, False, cycle=env.monitor.cycle
            )
            env.dut.cpu_req_valid.value = 0
            hit_accepted = True
        fire = int(env.dut.cpu_resp_valid.value) & int(
            env.dut.cpu_resp_ready.value) & 1
        if fire:
            response = {
                "core": 0,
                "address": int(env.dut.cpu_resp_addr.value) & 0xFFFF_FFFF,
                "data": int(env.dut.cpu_resp_rdata.value) & DATA_MASK,
                "txn_id": int(env.dut.cpu_resp_txn_id.value) & 7,
                "write": int(env.dut.cpu_resp_write.value) & 1,
            }
            responses.append(response)
            env.monitor.record_cpu_response_complete(
                0, response["address"], response["write"], response["data"],
                response["txn_id"], cycle=env.monitor.cycle,
            )
        if hit_accepted and len(responses) == 3:
            break
    env.dut.cpu_req_valid.value = 0
    env.dut.cpu_resp_ready.value = 0
    assert hit_accepted, "held resident hit did not progress after an MSHR retired"
    assert len(responses) == 3, f"observed {len(responses)}/3 CPU responses"
    by_address = {item["address"]: item for item in responses}
    assert set(by_address) == set(expected)
    for address, value in expected_data.items():
        assert by_address[address]["data"] == value
    miss_response_order = [item["address"] for item in responses
                           if item["address"] in (miss_a, miss_b)]
    assert miss_response_order == [miss_a, miss_b], miss_response_order

    events = env.monitor.events[event_start:]
    lifecycle = L1MshrLifecycleChecker.check(
        events,
        expected_requests=[(0, miss_a, expected_data[miss_a]),
                           (0, miss_b, expected_data[miss_b])],
    )
    refill = MshrLifecycleChecker.check(
        events,
        expected_lines={miss_a & LINE_MASK, miss_b & LINE_MASK},
        expected_words={miss_a: expected_data[miss_a],
                        miss_b: expected_data[miss_b]},
        expected_cores={miss_a: 0, miss_b: 0},
    )
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    env.trace_operations.extend([
        {"kind": "checker_evidence", "checker": "L1MshrLifecycleChecker",
         "result": lifecycle},
        {"kind": "checker_evidence", "checker": "MshrLifecycleChecker",
         "result": refill},
        {"kind": "backpressure_evidence", "scenario": "full_mshr_resident_hit",
         "stall_cycles": 8, "accepted_after_capacity_freed": hit_accepted,
         "miss_response_order": miss_response_order},
    ])
