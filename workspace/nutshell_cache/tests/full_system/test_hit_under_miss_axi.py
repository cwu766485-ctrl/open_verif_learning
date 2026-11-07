"""AXI-integrated hit-under-miss checks with response-ID correlation."""

from toffee import ClockCycles
from toffee_test import case

from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)


CORE0 = 0x1
CORE1 = 0x2
CPU_ADDR_MASK = (1 << 32) - 1
CPU_DATA_MASK = (1 << 64) - 1


def _cpu0_response(dut):
    return (
        (int(dut.cpu_resp_addr.value) >> 0) & CPU_ADDR_MASK,
        (int(dut.cpu_resp_rdata.value) >> 0) & CPU_DATA_MASK,
        (int(dut.cpu_resp_txn_id.value) >> 0) & 0x7,
        (int(dut.cpu_resp_write.value) >> 0) & 1,
    )


async def _issue_cpu0_read(env, address, *, timeout=300):
    """Offer one core-0 request and return only after its ready/valid handshake."""
    dut = env.dut
    dut.cpu_req_addr.value = address & CPU_ADDR_MASK
    dut.cpu_req_write.value = 0
    dut.cpu_req_wmask.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_valid.value = CORE0
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        if int(dut.cpu_req_ready.value) & CORE0:
            # The driver sampled a real ready/valid handshake. Record it here
            # as well because the passive pin sampler can run later on this
            # same Toffee edge and miss a one-cycle direct drive.
            env.monitor.record_cpu_request_accept(0, address, 0)
            dut.cpu_req_valid.value = 0
            return
    dut.cpu_req_valid.value = 0
    raise TimeoutError(f"core0 request was not accepted for {address:#x}")


async def _wait_cpu0_valid(env, *, timeout=500):
    for _ in range(timeout):
        await ClockCycles(env.dut, 1)
        if int(env.dut.cpu_resp_valid.value) & CORE0:
            return _cpu0_response(env.dut)
    raise TimeoutError("core0 response did not become valid")


async def _accept_cpu0_response(env, *, timeout=500):
    for _ in range(timeout):
        await ClockCycles(env.dut, 1)
        if ((int(env.dut.cpu_resp_valid.value) &
             int(env.dut.cpu_resp_ready.value)) & CORE0):
            response = _cpu0_response(env.dut)
            env.monitor.record_cpu_response_complete(
                0, response[0], response[3], response[1], response[2]
            )
            return response
    raise TimeoutError("core0 response did not handshake")


async def _wait_for_axi_read(env, address, *, start=0, timeout=300):
    line = address & ~0x3F
    for _ in range(timeout):
        for item in env.axi.read_addresses[start:]:
            if (item[1] & ~0x3F) == line:
                return item
        await ClockCycles(env.dut, 1)
    raise TimeoutError(f"line {line:#x} did not reach integrated AXI AR")


def _directory_request(env, address):
    line = address & ~0x3F
    requests = [event for event in env.monitor.events
                if event["source"] == "directory" and
                event["event_type"] == "request_accept" and
                (event["address"] & ~0x3F) == line]
    if not requests:
        raise AssertionError(f"Directory did not accept request for {line:#x}")
    return requests[-1]


@case
async def test_axi_top_hit_under_miss_response_id_wrap_and_stall(full_system_env):
    """A resident hit completes around a pending AXI refill and ID wrap."""
    env = await full_system_env(axi_options={"latency": 2})
    miss_addr = 0x0040_4008
    hit_addr = 0x0040_4088  # different L2 set from the pending miss
    miss_data = 0xA11C_E001_1234_5678
    hit_data = 0xB22D_F002_8765_4321
    env.seed_word(miss_addr, miss_data)
    env.seed_word(hit_addr, hit_data)
    assert await env.cpu_access(0, hit_addr) == hit_data

    # Stretch the backing-memory response only after the hit line is resident.
    env.axi.latency = 100
    env.dut.cpu_resp_ready.value = 0
    start_ar = len(env.axi.read_addresses)
    start_rbeat = len(env.axi.read_beats)
    miss_expected, _ = env.reference.predict(0, miss_addr)
    event_start = len(env.monitor.events)
    await _issue_cpu0_read(env, miss_addr)
    ar = await _wait_for_axi_read(env, miss_addr, start=start_ar)
    miss_request = _directory_request(env, miss_addr)
    pending_id = miss_request["txn_id"] & 0x7
    assert not any((item[1] & ~0x3F) == (miss_addr & ~0x3F)
                   for item in env.axi.read_completions), (
        "miss returned before hit-under-miss checks"
    )

    # Hold the hit response, checking its full payload stays stable under stall.
    await _issue_cpu0_read(env, hit_addr)
    held = await _wait_cpu0_valid(env)
    assert held == (hit_addr, hit_data, held[2], 0)
    for _ in range(4):
        await ClockCycles(env.dut, 1)
        assert int(env.dut.cpu_resp_valid.value) & CORE0
        assert _cpu0_response(env.dut) == held
    env.dut.cpu_resp_ready.value = CORE0 | CORE1
    hit_response = await _accept_cpu0_response(env)
    assert hit_response == held
    assert hit_response[2] != pending_id, "hit reused the live miss transaction ID"

    # One active refill plus more than one full 3-bit ID space of completed
    # resident hits proves wrap-around while preserving the miss ID reservation.
    hit_ids = [hit_response[2]]
    for _ in range(12):
        await _issue_cpu0_read(env, hit_addr)
        response = await _accept_cpu0_response(env)
        assert response[0] == hit_addr and response[1] == hit_data and response[3] == 0
        assert response[2] != pending_id, "wrapped hit ID collided with live miss ID"
        hit_ids.append(response[2])
    assert any(right < left for left, right in zip(hit_ids, hit_ids[1:])), (
        f"response transaction ID did not wrap: {hit_ids}"
    )
    assert not any((item[1] & ~0x3F) == (miss_addr & ~0x3F)
                   for item in env.axi.read_completions), (
        "pending miss completed before ID-wrap sequence"
    )

    miss_response = await _accept_cpu0_response(env)
    assert miss_response == (miss_addr, miss_expected, pending_id, 0), (
        f"pending miss response was misrouted: {miss_response}"
    )
    completion = next(item for item in env.axi.read_completions
                       if (item[1] & ~0x3F) == (miss_addr & ~0x3F))
    assert completion[0] == ar[0]
    assert (completion[1] & ~0x3F) == (miss_addr & ~0x3F)
    miss_beats = env.axi.read_beats[start_rbeat:]
    assert [beat[0] for beat in miss_beats] == [ar[0]] * 8
    env.reference.observe(0, miss_addr, response_data=miss_response[1])
    env.reference.observe(0, hit_addr, response_data=hit_data)
    env._check_observed_commits(miss_addr & ~0x3F, event_start)
    assert int(env.dut.protocol_error.value) == 0

    # Credit only after request/response correlation, data, ID, burst and hold
    # checks have all passed.
    env.coverage.sample_checked_event("FS.HIT_UNDER_MISS.PENDING_MISS_HIT",
                                      checked=True)
    env.coverage.sample_checked_event("FS.HIT_UNDER_MISS.RESPONSE_STALL",
                                      checked=True)
    env.coverage.sample_checked_event("FS.HIT_UNDER_MISS.TXN_ID_WRAP",
                                      checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.HIT_UNDER_MISS_X_AXI_REFILL",
                                      checked=True)


@case
async def test_axi_top_snoop_completes_during_other_line_pending_miss(full_system_env):
    """A remote owner read is checked while core0 waits for another refill."""
    env = await full_system_env(axi_options={"latency": 2})
    miss_addr = 0x0060_6008
    owner_addr = 0x0060_6088
    miss_data = 0xC33E_0003_1111_2222
    owner_data = 0xD44F_0004_3333_4444
    env.seed_word(miss_addr, miss_data)
    env.seed_word(owner_addr, 0x0102_0304_0506_0708)
    await env.cpu_access(0, owner_addr, write=True, data=owner_data)
    expected_owner, owner_class = env.reference.predict(1, owner_addr)
    assert owner_class == "remote_read_from_M"

    env.axi.latency = 80
    event_start = len(env.monitor.events)
    ar_start = len(env.axi.read_addresses)
    await _issue_cpu0_read(env, miss_addr)
    ar = await _wait_for_axi_read(env, miss_addr, start=ar_start)
    pending_id = _directory_request(env, miss_addr)["txn_id"] & 0x7
    assert not any((item[1] & ~0x3F) == (miss_addr & ~0x3F)
                   for item in env.axi.read_completions)

    # Core1's GetS must snoop core0's M copy even though core0's CPU miss is
    # pending on a different L2 set.
    result = await env.cpu.access(1, owner_addr)
    assert result == owner_data == expected_owner
    snoops = [event for event in env.monitor.events[event_start:]
              if event["source"] == "snoop" and
              event["event_type"] == "accept" and event.get("core") == 0 and
              (event.get("address", 0) & ~0x3F) == (owner_addr & ~0x3F)]
    assert snoops, "pending miss prevented the independent owner snoop"
    assert not any((item[1] & ~0x3F) == (miss_addr & ~0x3F)
                   for item in env.axi.read_completions), (
        "miss returned before snoop checker finished"
    )
    # The original request still returns the correct line through its AXI ID.
    env.dut.cpu_resp_ready.value = CORE0 | CORE1
    miss_response = await _accept_cpu0_response(env)
    assert miss_response[0] == miss_addr and miss_response[1] == miss_data
    assert miss_response[2] == pending_id
    completion = next(item for item in env.axi.read_completions
                      if (item[1] & ~0x3F) == (miss_addr & ~0x3F))
    assert completion[0] == ar[0]
    assert (completion[1] & ~0x3F) == (miss_addr & ~0x3F)
    env.reference.observe(1, owner_addr, response_data=result)
    env.reference.observe(0, miss_addr, response_data=miss_data)
    env._check_observed_commits(owner_addr & ~0x3F, event_start)
    env._check_observed_commits(miss_addr & ~0x3F, event_start)
    assert int(env.dut.protocol_error.value) == 0

    events = env.monitor.events[event_start:]
    miss_cpu_request = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "request_accept" and
        event["core"] == 0 and event["address"] == miss_addr
    )
    miss_cpu_response = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "response_complete" and
        event["core"] == 0 and event["address"] == miss_addr
    )
    owner_cpu_request = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "request_accept" and
        event["core"] == 1 and event["address"] == owner_addr
    )
    owner_cpu_response = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "response_complete" and
        event["core"] == 1 and event["address"] == owner_addr
    )
    dir_miss_request = _directory_request(env, miss_addr)
    ar_event = next(
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_address" and
        event["txn_id"] == ar[0] and
        event["address"] & ~0x3F == (miss_addr & ~0x3F)
    )
    r_beats = [
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_beat" and
        event["txn_id"] == ar[0] and
        event["address"] & ~0x3F == (miss_addr & ~0x3F)
    ]
    assert [event["beat"] for event in r_beats] == list(range(8))
    assert r_beats[-1]["last"]
    snoop_accept = next(
        event for event in events
        if event["source"] == "snoop" and
        event["event_type"] == "accept" and event["core"] == 0 and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    snoop_response = next(
        event for event in events
        if event["source"] == "snoop" and
        event["event_type"] == "response" and event["core"] == 0 and
        event["txn_id"] == snoop_accept["txn_id"]
    )
    owner_beats = [
        event for event in events
        if event["source"] == "coherence" and
        event["event_type"] == "owner_data_beat" and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    ]
    assert [event["beat"] for event in owner_beats] == list(range(8))
    owner_commit = next(
        event for event in events
        if event["source"] == "l1" and
        event["event_type"] == "metadata_commit" and event["core"] == 0 and
        event["address"] & ~0x3F == (owner_addr & ~0x3F) and
        event["old_state"] == 3 and event["new_state"] == 1
    )
    requester_commit = next(
        event for event in events
        if event["source"] == "l1" and
        event["event_type"] == "metadata_commit" and event["core"] == 1 and
        event["address"] & ~0x3F == (owner_addr & ~0x3F) and
        event["old_state"] == 0 and event["new_state"] == 1
    )
    owner_dir_commit = next(
        event for event in reversed(events)
        if event["source"] == "directory" and
        event["event_type"] == "metadata_commit" and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    assert (miss_cpu_request["cycle"] <= snoop_accept["cycle"] <=
            snoop_response["cycle"] <= miss_cpu_response["cycle"])
    assert ar_event["cycle"] <= snoop_accept["cycle"]
    assert snoop_response["cycle"] <= r_beats[-1]["cycle"]

    refs = [
        event_reference("miss_cpu_request", "pending_miss", miss_cpu_request),
        event_reference("miss_cpu_response", "pending_miss", miss_cpu_response),
        event_reference("miss_directory_request", "pending_miss", dir_miss_request),
        event_reference("miss_ar", "axi_refill", ar_event),
        event_reference("miss_rlast", "axi_refill", r_beats[-1]),
        event_reference("owner_cpu_request", "remote_snoop", owner_cpu_request),
        event_reference("owner_cpu_response", "remote_snoop", owner_cpu_response),
        event_reference("snoop_accept", "remote_snoop", snoop_accept),
        event_reference("snoop_response", "remote_snoop", snoop_response),
        event_reference("owner_l1_commit", "remote_snoop", owner_commit),
        event_reference("requester_l1_commit", "remote_snoop", requester_commit),
        event_reference("owner_directory_commit", "remote_snoop", owner_dir_commit),
    ]
    refs.extend(
        event_reference(f"owner_data_beat_{event['beat']}", "remote_snoop", event)
        for event in owner_beats
    )
    refs.extend(
        event_reference(f"miss_r_beat_{event['beat']}", "axi_refill", event)
        for event in r_beats
    )
    owner_dir_request = next(
        event for event in events
        if event["source"] == "directory" and
        event["event_type"] == "request_accept" and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    refs.append(event_reference("owner_directory_request", "remote_snoop",
                                owner_dir_request))
    proof = checked_overlap_proof(
        checker="Hit-under-Miss independent data/MESI/Directory checker",
        checker_pass=True,
        role_endpoints={
            "pending_miss": ("miss_cpu_request", "miss_cpu_response"),
            "axi_refill": ("miss_ar", "miss_rlast"),
            "remote_snoop": ("snoop_accept", "snoop_response"),
        },
        event_refs=refs,
        transactions=[
            {"role": "pending_miss", "protocol": "CPU",
             "txn_id": miss_cpu_response["txn_id"], "address": miss_addr,
             "event_ref_ids": ["miss_cpu_request", "miss_cpu_response"]},
            {"role": "directory_miss", "protocol": "Directory",
             "txn_id": dir_miss_request["txn_id"],
             "address": miss_addr & ~0x3F,
             "event_ref_ids": ["miss_directory_request"]},
            {"role": "axi_refill", "protocol": "AXI4-R",
             "txn_id": ar_event["txn_id"], "address": miss_addr & ~0x3F,
             "event_ref_ids": ["miss_ar", "miss_rlast"]},
            {"role": "owner_gets", "protocol": "CPU",
             "txn_id": owner_cpu_response["txn_id"], "address": owner_addr,
             "event_ref_ids": ["owner_cpu_request", "owner_cpu_response"]},
            {"role": "owner_snoop", "protocol": "Snoop",
             "txn_id": snoop_accept["txn_id"], "address": owner_addr & ~0x3F,
             "event_ref_ids": ["snoop_accept", "snoop_response"]},
        ],
        state_transitions=[
            {"event_ref_id": "owner_l1_commit", "old_state": 3, "new_state": 1},
            {"event_ref_id": "requester_l1_commit", "old_state": 0, "new_state": 1},
            {"event_ref_id": "owner_directory_commit", "state": 1},
        ],
    )
    env.coverage.sample_checked_event("FS.HIT_UNDER_MISS.SNOOP_PROGRESS",
                                      checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.HIT_UNDER_MISS_X_SNOOP",
                                      checked=True, evidence=proof)


@case
async def test_axi_top_reset_cancels_pending_hit_under_miss_request(full_system_env):
    """Reset cancels an integrated miss and permits a clean retry."""
    env = await full_system_env(axi_options={"latency": 80})
    address = 0x0080_8008
    expected = 0xE550_0005_AAAA_BBBB
    env.seed_word(address, expected)
    env.dut.cpu_resp_ready.value = CORE0 | CORE1
    ar_start = len(env.axi.read_addresses)
    await _issue_cpu0_read(env, address)
    ar = await _wait_for_axi_read(env, address, start=ar_start)
    assert not env.axi.read_completions
    epoch = env.monitor.reset_epoch

    await env.reset(cycles=3)
    assert env.monitor.reset_epoch == epoch + 1
    await ClockCycles(env.dut, 8)
    assert not (int(env.dut.cpu_resp_valid.value) & CORE0), (
        "cancelled hit-under-miss request produced a stale CPU response"
    )
    assert env.axi.reset_cancelled["reads"] >= 1

    assert await env.cpu.access(0, address) == expected
    retried = [item for item in env.axi.read_completions
               if (item[1] & ~0x3F) == (address & ~0x3F)]
    assert len(retried) == 1 and retried[0][0] == ar[0]
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    env.coverage.sample_checked_event("FS.HIT_UNDER_MISS.RESET_CANCEL",
                                      checked=True)
    env.coverage.sample_checked_cross("FS.CROSS.HIT_UNDER_MISS_X_RESET",
                                      checked=True)
