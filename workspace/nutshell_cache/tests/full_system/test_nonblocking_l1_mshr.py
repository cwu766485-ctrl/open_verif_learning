"""Directed checks for the two-entry-per-core L1 miss trackers."""

from toffee import ClockCycles
from toffee_test import case

from dv.checkers.l1_mshr_lifecycle_checker import L1MshrLifecycleChecker
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker


CORE_MASK = 0b11
DATA_MASK = (1 << 64) - 1


def _pack_addresses(core0, core1):
    return (int(core0) & 0xFFFF_FFFF) | ((int(core1) & 0xFFFF_FFFF) << 32)


async def _offer_reads(env, addresses, *, timeout=300):
    """Offer one request per core, holding each lane until its handshake."""
    dut = env.dut
    pending = {int(core): int(address) & 0xFFFF_FFFF
               for core, address in addresses.items()}
    dut.cpu_req_addr.value = _pack_addresses(
        pending.get(0, 0), pending.get(1, 0)
    )
    dut.cpu_req_write.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_wmask.value = 0
    valid = sum(1 << core for core in pending)
    dut.cpu_req_valid.value = valid
    accepted = {}
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        ready = int(dut.cpu_req_ready.value)
        for core in tuple(pending):
            if ready & (1 << core):
                address = pending.pop(core)
                accepted[core] = address
                env.monitor.record_cpu_request_accept(
                    core, address, 0, cycle=env.monitor.cycle
                )
                valid &= ~(1 << core)
                dut.cpu_req_valid.value = valid
        if not pending:
            return accepted
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"CPU request lanes did not handshake: {pending}")


async def _collect_responses(env, expected_count, *, timeout=1800):
    dut = env.dut
    results = []
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        valid = int(dut.cpu_resp_valid.value)
        ready = int(dut.cpu_resp_ready.value)
        fire = valid & ready & CORE_MASK
        for core in range(2):
            if not (fire & (1 << core)):
                continue
            response = {
                "core": core,
                "address": (int(dut.cpu_resp_addr.value) >> (32 * core)) & 0xFFFF_FFFF,
                "data": (int(dut.cpu_resp_rdata.value) >> (64 * core)) & DATA_MASK,
                "txn_id": (int(dut.cpu_resp_txn_id.value) >> (3 * core)) & 0x7,
                "write": (int(dut.cpu_resp_write.value) >> core) & 1,
            }
            results.append(response)
            env.monitor.record_cpu_response_complete(
                core, response["address"], response["write"],
                response["data"], response["txn_id"],
                cycle=env.monitor.cycle,
            )
        if len(results) == expected_count:
            return results
    raise TimeoutError(f"received {len(results)}/{expected_count} CPU responses")


async def _hold_until_both_lanes_accept(env, addresses, *, timeout=1200):
    """Hold a two-lane request stable through backpressure and sample responses."""
    dut = env.dut
    pending = dict(addresses)
    valid = sum(1 << core for core in pending)
    dut.cpu_req_addr.value = _pack_addresses(pending.get(0, 0), pending.get(1, 0))
    dut.cpu_req_write.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_wmask.value = 0
    dut.cpu_req_valid.value = valid
    responses = []
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        resp_fire = int(dut.cpu_resp_valid.value) & int(dut.cpu_resp_ready.value) & CORE_MASK
        for core in range(2):
            if resp_fire & (1 << core):
                response = {
                    "core": core,
                    "address": (int(dut.cpu_resp_addr.value) >> (32 * core)) & 0xFFFF_FFFF,
                    "data": (int(dut.cpu_resp_rdata.value) >> (64 * core)) & DATA_MASK,
                    "txn_id": (int(dut.cpu_resp_txn_id.value) >> (3 * core)) & 0x7,
                    "write": (int(dut.cpu_resp_write.value) >> core) & 1,
                }
                responses.append(response)
                env.monitor.record_cpu_response_complete(
                    core, response["address"], response["write"],
                    response["data"], response["txn_id"],
                    cycle=env.monitor.cycle,
                )
        ready = int(dut.cpu_req_ready.value)
        for core in tuple(pending):
            if ready & (1 << core):
                address = pending.pop(core)
                env.monitor.record_cpu_request_accept(core, address, 0,
                                                      cycle=env.monitor.cycle)
                valid &= ~(1 << core)
                dut.cpu_req_valid.value = valid
        if not pending:
            return responses
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"third request lanes remained backpressured: {pending}")


async def _wait_until(env, predicate, description, *, timeout=800):
    for _ in range(timeout):
        if predicate():
            return
        await ClockCycles(env.dut, 1)
    raise TimeoutError(f"timed out waiting for {description}")


async def _offer_one(env, core, address, *, write=False, data=0, mask=0xFF,
                     timeout=1000):
    """Drive one raw CPU lane and hold its payload until a real handshake."""
    dut = env.dut
    bit = 1 << core
    addr = _pack_addresses(address if core == 0 else 0,
                           address if core == 1 else 0)
    dut.cpu_req_addr.value = addr
    dut.cpu_req_write.value = bit if write else 0
    dut.cpu_req_wdata.value = (int(data) << (64 * core))
    dut.cpu_req_wmask.value = (int(mask) << (8 * core)) if write else 0
    dut.cpu_req_valid.value = bit
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        if int(dut.cpu_req_ready.value) & bit:
            env.monitor.record_cpu_request_accept(
                core, address, write, cycle=env.monitor.cycle
            )
            dut.cpu_req_valid.value = 0
            return
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"core{core} request did not handshake: {address:#x}")


async def _take_one_response(env, core, *, timeout=1800):
    """Accept and return one CPU response on the selected lane."""
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
async def test_four_l1_misses_occupy_two_entries_per_core(full_system_env):
    """Four CPU misses are retained before the first CPU response completes.

    Downstream Directory/refill/AXI concurrency is measured independently; the
    test does not assume that four CPU entries imply four AXI requests.
    """
    env = await full_system_env(
        seed=0x13_0404,
        axi_options={"latency": 140, "r_valid_gap_period": 2,
                     "read_reorder_window": 3},
    )
    env.trace_scenario_id = "V13_L1_MSHR_FOUR_CPU_MISSES"
    addresses = {
        0: [0x0041_0008, 0x0041_0088],
        1: [0x0041_0108, 0x0041_0188],
    }
    expected = []
    words = {}
    for core, core_addresses in addresses.items():
        for index, address in enumerate(core_addresses):
            line = address & 0xFFFF_FFC0
            for beat in range(8):
                word_address = line + beat * 8
                value = (0xD000_0000_0000_0000 |
                         (core << 48) | (index << 40) | word_address)
                env.seed_word(word_address, value)
            words[address] = env.axi.read_word(address)
            expected.append((core, address, words[address]))

    blocked = {0: 0x0041_2008, 1: 0x0041_2088}
    for core, address in blocked.items():
        line = address & 0xFFFF_FFC0
        for beat in range(8):
            word_address = line + beat * 8
            env.seed_word(word_address, 0xE000_0000_0000_0000 |
                          (core << 48) | word_address)
        expected.append((core, address, env.axi.read_word(address)))

    env.trace_config.update({
        "l1_mshr_entries_per_core": 2,
        "l1_mshr_total_entries": 4,
        "memory_latency_cycles": 140,
        "addresses_by_core": {str(core): values for core, values in addresses.items()},
        "axi_reorder": "reverse_first_two_read_ids",
        "response_ready_during_allocation": 0,
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "seed_four_distinct_lines",
         "addresses_by_core": {str(core): values for core, values in addresses.items()}},
        {"kind": "stimulus", "operation": "two_wave_paired_cold_reads",
         "waves": [[addresses[0][0], addresses[1][0]],
                   [addresses[0][1], addresses[1][1]]]},
    ])
    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)
    ar_start = len(env.axi.read_addresses)
    completion_start = len(env.axi.read_completions)
    env.axi.force_next_reads_out_of_order(2)

    await _offer_reads(env, {0: addresses[0][0], 1: addresses[1][0]})
    await _wait_until(
        env, lambda: len(env.axi.read_addresses) - ar_start >= 2,
        "first two cold misses to issue AXI reads",
    )
    await _offer_reads(env, {0: addresses[0][1], 1: addresses[1][1]})
    await _wait_until(
        env, lambda: env.monitor.max_l1_mshr_occupancy == 4,
        "all four L1 MSHR entries to be allocated",
    )

    allocations = [event for event in env.monitor.events[event_start:]
                   if event["source"] == "l1_mshr" and
                   event["event_type"] == "allocate"]
    assert len(allocations) == 4
    assert all(not (event["source"] == "cpu" and
                    event["event_type"] == "response_complete")
               for event in env.monitor.events[event_start:]), (
        "a CPU response completed before all four L1 MSHRs were occupied"
    )
    assert len(env.axi.read_completions) == completion_start, (
        "memory latency did not preserve the four-entry allocation window"
    )
    assert env.monitor.max_l1_mshr_per_core == {0: 2, 1: 2}
    assert env.monitor.max_l1_mshr_active_per_core == {0: 1, 1: 1}
    assert env.monitor.max_l1_mshr_issued_per_core == {0: 1, 1: 1}
    assert env.monitor.max_l1_mshr_issued <= 2
    assert env.monitor.max_directory_contexts == 2
    assert env.monitor.max_mshr_occupancy == 2
    assert env.axi.peak_reads == 2

    # Keep third requests stable through full-bank backpressure. They handshake
    # only after response retirement releases an L1 entry.
    env.dut.cpu_req_addr.value = _pack_addresses(blocked[0], blocked[1])
    env.dut.cpu_req_write.value = 0
    env.dut.cpu_req_wdata.value = 0
    env.dut.cpu_req_wmask.value = 0
    env.dut.cpu_req_valid.value = CORE_MASK
    for _ in range(8):
        await ClockCycles(env.dut, 1)
        assert int(env.dut.cpu_req_ready.value) & CORE_MASK == 0, (
            "full L1 MSHR bank accepted a third request"
        )

    # First two AXI reads must actually complete in reverse ID order, and each
    # line's R beats must retain the right ID/address/data association.
    await _wait_until(
        env, lambda: len(env.axi.read_completions) - completion_start >= 2,
        "first two AXI refills",
        timeout=1000,
    )
    first_ar = env.axi.read_addresses[ar_start:ar_start + 2]
    first_r = env.axi.read_completions[completion_start:completion_start + 2]
    assert [item[0] for item in first_r] == [item[0] for item in reversed(first_ar)], (
        f"first AXI reads did not return out of order: AR={first_ar}, R={first_r}"
    )

    env.dut.cpu_resp_ready.value = CORE_MASK
    early_results = await _hold_until_both_lanes_accept(env, blocked)
    results = early_results + await _collect_responses(env, 6 - len(early_results))
    # Let the passive monitor sample the post-handshake MSHR retirement edge.
    await ClockCycles(env.dut, 2)
    actual = {(item["core"], item["address"]): item["data"] for item in results}
    assert actual == {(core, address): value for core, address, value in expected}
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0

    # Advance the independent model only after each response/data check passed.
    for core, address, _value in expected:
        env.reference.observe(core, address, response_data=actual[(core, address)])
    for _core, address, _value in expected:
        env._check_observed_commits(address & 0xFFFF_FFC0, event_start)

    l1_evidence = L1MshrLifecycleChecker.check(
        env.monitor.events[event_start:], expected_requests=expected,
        first_response_must_follow_all_allocs=False,
    )
    refill_evidence = MshrLifecycleChecker.check(
        env.monitor.events[event_start:],
        expected_lines={address for _core, address, _value in expected},
        expected_words={address: value for _core, address, value in expected},
        expected_cores={address: core for core, address, _value in expected},
    )
    env.trace_operations.append({
        "kind": "checker_evidence",
        "checker": "L1MshrLifecycleChecker",
        "result": l1_evidence,
    })
    env.trace_operations.append({
        "kind": "checker_evidence",
        "checker": "MshrLifecycleChecker",
        "result": refill_evidence,
    })
    env.trace_operations.append({
        "kind": "resource_peaks",
        "l1_mshr_allocated_total": env.monitor.max_l1_mshr_occupancy,
        "l1_mshr_allocated_per_core": dict(env.monitor.max_l1_mshr_per_core),
        "l1_controller_owned_per_core": dict(
            env.monitor.max_l1_mshr_active_per_core
        ),
        "l1_directory_issued_per_core": dict(
            env.monitor.max_l1_mshr_issued_per_core
        ),
        "directory_contexts": env.monitor.max_directory_contexts,
        "refill_mshrs": env.monitor.max_mshr_occupancy,
        "axi_read_outstanding": env.axi.peak_reads,
    })
    env.trace_operations.append({
        "kind": "replay",
        "seed": env.trace_seed,
        "configuration": env.trace_config,
        "operations": [
            {"core": core, "address": address, "write": False}
            for core, address, _value in expected
        ],
    })

    assert env.monitor.max_l1_mshr_occupancy == 4
    assert env.monitor.max_l1_mshr_per_core == {0: 2, 1: 2}
    assert env.monitor.max_l1_mshr_active_per_core == {0: 1, 1: 1}
    assert env.monitor.max_l1_mshr_issued_per_core == {0: 1, 1: 1}
    assert env.monitor.max_l1_mshr_issued <= 2
    assert env.monitor.max_directory_contexts == 2
    assert env.monitor.max_mshr_occupancy == 2
    assert env.axi.peak_reads >= 2


@case
async def test_same_line_second_miss_waits_then_relooks_up_as_hit(full_system_env):
    """A same-line request is serialized and rechecked after the first fill."""
    env = await full_system_env(axi_options={"latency": 32})
    address = 0x0052_4008
    value = 0x51A6_1E00_0000_0042
    env.seed_word(address, value)
    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)

    await _offer_one(env, 0, address)
    await _wait_until(
        env, lambda: env.monitor.max_l1_mshr_occupancy == 1,
        "first same-line miss allocation",
    )
    env.dut.cpu_req_addr.value = _pack_addresses(address, 0)
    env.dut.cpu_req_write.value = 0
    env.dut.cpu_req_wdata.value = 0
    env.dut.cpu_req_wmask.value = 0
    env.dut.cpu_req_valid.value = 1
    for _ in range(12):
        await ClockCycles(env.dut, 1)
        assert not (int(env.dut.cpu_req_ready.value) & 1), (
            "same-line request was merged/accepted while its miss was pending"
        )

    first = await _take_one_response(env, 0)
    assert first["address"] == address and first["data"] == value
    for _ in range(20):
        await ClockCycles(env.dut, 1)
        if int(env.dut.cpu_req_ready.value) & 1:
            env.monitor.record_cpu_request_accept(
                0, address, False, cycle=env.monitor.cycle
            )
            env.dut.cpu_req_valid.value = 0
            break
    else:
        env.dut.cpu_req_valid.value = 0
        raise TimeoutError("held same-line request did not retry as a hit")
    second = await _take_one_response(env, 0)
    env.dut.cpu_req_valid.value = 0
    env.dut.cpu_resp_ready.value = 0

    assert second["address"] == address and second["data"] == value
    events = env.monitor.events[event_start:]
    assert sum(event.get("source") == "directory" and
               event.get("event_type") == "request_accept" and
               (event.get("address", 0) & 0xFFFF_FFC0) ==
               (address & 0xFFFF_FFC0) for event in events) == 1
    assert sum(event.get("source") == "l1_mshr" and
               event.get("event_type") == "allocate" for event in events) == 1
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0


@case
async def test_cpu_response_backpressure_retains_active_and_queued_mshrs(full_system_env):
    """A stalled CPU response must retain its active entry and queued miss."""
    env = await full_system_env(axi_options={"latency": 36})
    addresses = (0x0052_8008, 0x0052_8088)
    values = (0xBACC_0000_0000_0001, 0xBACC_0000_0000_0002)
    for address, value in zip(addresses, values):
        env.seed_word(address, value)
    expected = [(0, address, env.axi.read_word(address))
                for address in addresses]
    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)

    await _offer_one(env, 0, addresses[0])
    await _wait_until(env, lambda: bool(env.axi.read_addresses),
                      "first refill to issue before response stall")
    await _offer_one(env, 0, addresses[1])
    await _wait_until(
        env, lambda: env.monitor.max_l1_mshr_per_core[0] == 2,
        "active and queued L1 MSHRs",
    )
    await _wait_until(
        env, lambda: int(env.dut.cpu_resp_valid.value) & 1,
        "first CPU response to become valid under backpressure",
        timeout=1200,
    )

    def response_payload():
        return (
            int(env.dut.cpu_resp_addr.value) & 0xFFFF_FFFF,
            int(env.dut.cpu_resp_rdata.value) & DATA_MASK,
            int(env.dut.cpu_resp_txn_id.value) & 0x7,
            int(env.dut.cpu_resp_write.value) & 1,
        )

    stalled_payload = response_payload()
    assert stalled_payload[0] == addresses[0]
    assert stalled_payload[1] == expected[0][2]
    for _ in range(8):
        await ClockCycles(env.dut, 1)
        assert int(env.dut.cpu_resp_valid.value) & 1
        assert response_payload() == stalled_payload, (
            "CPU response payload changed while ready was low"
        )
        assert int(env.dut.monitor_l1_mshr_valid.value) & 0b0011 == 0b0011, (
            "an L1 MSHR retired before its CPU response handshake"
        )

    # Release backpressure once and collect both ordered responses as a single
    # stream. This avoids introducing an edge-racy READY pulse between them.
    env.dut.cpu_resp_ready.value = 1
    responses = await _collect_responses(env, 2)
    env.dut.cpu_resp_ready.value = 0
    # Let the independent monitor sample the final response/retire edge before
    # evaluating lifecycle evidence. The interface handshake was already
    # captured above; this is only a monitor sampling drain.
    await ClockCycles(env.dut, 2)
    assert [item["address"] for item in responses] == list(addresses)
    assert [item["data"] for item in responses] == [item[2] for item in expected]

    l1_evidence = L1MshrLifecycleChecker.check(
        env.monitor.events[event_start:], expected_requests=expected
    )
    refill_evidence = MshrLifecycleChecker.check(
        env.monitor.events[event_start:],
        expected_lines={address for _core, address, _value in expected},
        expected_words={address: value for _core, address, value in expected},
        expected_cores={address: 0 for _core, address, _value in expected},
    )
    assert l1_evidence["checked_requests"] == 2
    assert refill_evidence
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0


@case
async def test_reset_cancels_active_and_queued_l1_mshrs(full_system_env):
    """Reset cancels both accepted entries and prevents stale responses."""
    env = await full_system_env(axi_options={"latency": 180})
    addresses = (0x0053_0008, 0x0053_0088)
    values = (0xA110_0000_0000_0001, 0xA110_0000_0000_0002)
    for address, value in zip(addresses, values):
        env.seed_word(address, value)
    env.dut.cpu_resp_ready.value = 0
    event_start = len(env.monitor.events)

    await _offer_one(env, 0, addresses[0])
    await _wait_until(
        env, lambda: bool(env.axi.read_addresses), "AXI refill before reset"
    )
    await _offer_one(env, 0, addresses[1])
    await ClockCycles(env.dut, 2)
    assert int(env.dut.monitor_l1_mshr_valid.value) & 0b0011 == 0b0011
    epoch = env.monitor.reset_epoch
    await env.reset(cycles=3)
    assert env.monitor.reset_epoch == epoch + 1
    await ClockCycles(env.dut, 8)
    assert int(env.dut.monitor_l1_mshr_valid.value) == 0
    assert int(env.dut.cpu_resp_valid.value) == 0, "stale response after reset"
    reset_events = [event for event in env.monitor.events[event_start:]
                    if event["source"] == "system" and
                    event["event_type"] == "reset_cancel"]
    assert reset_events and reset_events[-1]["payload"]["l1_mshr_entries"] == 2
    assert env.axi.reset_cancelled["reads"] >= 1

    replay_address = 0x0053_1008
    replay_value = 0xA110_0000_0000_0003
    env.seed_word(replay_address, replay_value)
    assert await env.cpu.access(0, replay_address) == replay_value
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0


@case
async def test_queued_store_relooks_up_after_remote_snoop(full_system_env):
    """A peer invalidation before queued dispatch must affect the fresh lookup."""
    env = await full_system_env(axi_options={"latency": 96})
    shared = 0x0054_0008
    pending = 0x0054_1088
    initial = 0xBBBB_0000_0000_0001
    peer_store = 0xBBBB_0000_0000_0002
    queued_store = 0xBBBB_0000_0000_0003
    pending_value = 0xAAAA_0000_0000_0004
    env.seed_word(shared, initial)
    env.seed_word(pending, pending_value)
    assert await env.cpu.access(0, shared) == initial
    env.reference.observe(0, shared, response_data=initial)
    assert await env.cpu.access(1, shared) == initial
    env.reference.observe(1, shared, response_data=initial)

    event_start = len(env.monitor.events)
    env.dut.cpu_resp_ready.value = 0
    await _offer_one(env, 0, pending)
    await _wait_until(
        env, lambda: bool(env.axi.read_addresses),
        "first core0 refill to be active",
    )
    await _offer_one(env, 0, shared, write=True, data=queued_store)
    await _wait_until(
        env, lambda: env.monitor.max_l1_mshr_per_core[0] == 2,
        "queued core0 store MSHR",
    )

    # Core1 obtains M while core0's Store-to-S upgrade is still queued behind
    # its unrelated miss. The resulting real Snoop must invalidate core0's S
    # copy before the queued operation is replayed and looked up again.
    assert await env.cpu.access(1, shared, write=True,
                                data=peer_store) == initial
    env.reference.observe(1, shared, write=True, write_data=peer_store,
                          write_mask=0xFF)
    queued_snoop_commit_end = len(env.monitor.events)
    env._check_observed_commits(shared & 0xFFFF_FFC0, event_start)
    peer_snoop = [event for event in env.monitor.events[event_start:]
                  if event["source"] == "snoop" and
                  event["event_type"] == "accept" and event["core"] == 0 and
                  (event.get("address", 0) & 0xFFFF_FFC0) ==
                  (shared & 0xFFFF_FFC0)]
    assert peer_snoop, "peer Store did not invalidate queued core0 line"

    env.dut.cpu_resp_ready.value = 1
    first = await _take_one_response(env, 0)
    assert first["address"] == pending and first["data"] == pending_value
    second = await _take_one_response(env, 0)
    env.dut.cpu_resp_ready.value = 0
    assert second["address"] == shared and second["write"] == 1
    assert second["data"] == peer_store

    core0_upgrade = [event for event in env.monitor.events[event_start:]
                     if event["source"] == "directory" and
                     event["event_type"] == "request_accept" and
                     event["source_id"] == 0 and
                     (event.get("address", 0) & 0xFFFF_FFC0) ==
                     (shared & 0xFFFF_FFC0)]
    assert core0_upgrade and peer_snoop[0]["cycle"] < core0_upgrade[-1]["cycle"], (
        "queued Store was not dispatched after the intervening Snoop"
    )
    env.reference.observe(0, shared, write=True, write_data=queued_store,
                          write_mask=0xFF)
    queued_store_commit_end = len(env.monitor.events)
    env._check_observed_commits(shared & 0xFFFF_FFC0,
                                queued_snoop_commit_end)
    assert await env.cpu.access(1, shared) == queued_store
    env.reference.observe(1, shared, response_data=queued_store)
    env._check_observed_commits(shared & 0xFFFF_FFC0,
                                queued_store_commit_end)
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
