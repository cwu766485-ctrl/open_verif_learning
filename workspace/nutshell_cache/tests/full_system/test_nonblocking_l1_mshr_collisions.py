"""System tests for owner Snoop progress with live L1 miss contexts."""

from toffee import ClockCycles
from toffee_test import case

from dv.checkers.l1_mshr_collision_checker import L1MshrCollisionChecker
from dv.checkers.l1_mshr_lifecycle_checker import L1MshrLifecycleChecker
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
