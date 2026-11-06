"""Cross-agent owner transfer, AXI refill, and APB observation checks."""

import asyncio

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)


@case
async def test_dirty_owner_transfer_during_refill_with_apb_snoop_count(
        full_system_env):
    """Check dirty data and Snoop accounting while an unrelated refill is live."""
    env = await full_system_env(
        axi_options={
            "latency": 96,
            "ar_stall_period": 3,
            "r_valid_gap_period": 3,
            "read_reorder_window": 2,
        }
    )
    owner_core = 0
    snooper_core = 1
    owner_line = 0x0240_0000
    owner_addr = owner_line + 0x18
    refill_addr = owner_line + 0x40
    owner_words = [0xA500_0000_0000_0000 + beat for beat in range(8)]
    refill_data = 0x6D45_20A1_9B3C_7E8F
    owner_value = 0xD1A7_0A11_5EED_9876

    for beat, value in enumerate(owner_words):
        env.seed_word(owner_line + beat * 8, value)
    env.seed_word(refill_addr, refill_data)

    # Establish M ownership through the public CPU interface and advance the
    # independent model from the accepted architectural store.
    await env.cpu.access(owner_core, owner_addr, write=True, data=owner_value)
    env.reference.observe(owner_core, owner_addr, write=True,
                          write_data=owner_value, write_mask=0xFF)
    assert env.reference.states[owner_line] == ["M", "I"]

    expected_owner, owner_class = env.reference.predict(snooper_core, owner_addr)
    expected_refill, refill_class = env.reference.predict(owner_core, refill_addr)
    assert owner_class == "remote_read_from_M"
    assert refill_class == "cold_read"

    event_start = len(env.monitor.events)
    refill_start = len(env.axi.read_addresses)
    refill_end = len(env.axi.read_completions)

    async def read_snoop_count_while_refill_is_active():
        snoop_response_seen = False
        for _ in range(500):
            await ClockCycles(env.dut, 1)
            events = env.monitor.events[event_start:]
            snoop_response_seen |= any(
                event["source"] == "snoop" and
                event["event_type"] == "response"
                for event in events
            )
            refill_active = (
                len(env.axi.read_addresses) > refill_start and
                len(env.axi.read_completions) == refill_end
            )
            if snoop_response_seen and refill_active:
                value = await env.apb.read(env.apb.CSR_SNOOP_COUNT)
                return value
        raise TimeoutError(
            "could not sample the Snoop counter after owner response and "
            "before the unrelated AXI refill completed"
        )

    cpu_pair = asyncio.create_task(env.cpu.access_pair(
        CpuRequest(refill_addr), CpuRequest(owner_addr),
        # Start refill first so the accepted owner Snoop overlaps it.
        request_delay_cycles={snooper_core: 4},
        response_stall_cycles=2,
    ))
    apb_task = asyncio.create_task(read_snoop_count_while_refill_is_active())
    results = await cpu_pair
    snoop_count = await apb_task

    assert results[owner_core] == refill_data == expected_refill
    assert results[snooper_core] == owner_value == expected_owner
    assert snoop_count == 1, f"expected one accepted owner Snoop, got {snoop_count}"
    assert env.axi.valid_gaps["R"] > 0
    assert env.axi.stalls["AR"] > 0

    events = env.monitor.events[event_start:]
    refill_ar = next(
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_address" and
        event["address"] == (refill_addr & ~0x3F)
    )
    refill_last = next(
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_beat" and event["last"]
    )
    snoop_accept = next(
        event for event in events
        if event["source"] == "snoop" and event["event_type"] == "accept" and
        event["core"] == owner_core and
        event["address"] & ~0x3F == owner_line
    )
    snoop_response = next(
        event for event in events
        if event["source"] == "snoop" and event["event_type"] == "response" and
        event["core"] == owner_core and
        event["txn_id"] == snoop_accept["txn_id"]
    )
    apb_event = next(
        event for event in events
        if event["source"] == "apb" and
        event["event_type"] == "access_complete" and
        event["address"] == env.apb.CSR_SNOOP_COUNT
    )
    assert refill_ar["cycle"] < snoop_accept["cycle"]
    assert snoop_accept["cycle"] <= snoop_response["cycle"]
    assert snoop_response["cycle"] < apb_event["cycle"] < refill_last["cycle"]
    assert apb_event["payload"]["read_data"] == snoop_count

    owner_beats = [
        event for event in events
        if event["source"] == "coherence" and
        event["event_type"] == "owner_data_beat" and
        event["address"] & ~0x3F == owner_line
    ]
    expected_owner_words = list(owner_words)
    expected_owner_words[(owner_addr - owner_line) // 8] = owner_value
    assert [event["beat"] for event in owner_beats] == list(range(8))
    assert [event["data"] for event in owner_beats] == expected_owner_words
    assert owner_beats[-1]["last"]

    owner_commit = next(
        event for event in events
        if event["source"] == "l1" and
        event["event_type"] == "metadata_commit" and
        event["core"] == owner_core and event["address"] & ~0x3F == owner_line and
        event["old_state"] == 3 and event["new_state"] == 1
    )
    requester_commit = next(
        event for event in events
        if event["source"] == "l1" and
        event["event_type"] == "metadata_commit" and
        event["core"] == snooper_core and
        event["address"] & ~0x3F == owner_line and
        event["old_state"] == 0 and event["new_state"] == 1
    )
    owner_dir_commit = [
        event for event in events
        if event["source"] == "directory" and
        event["event_type"] == "metadata_commit" and
        event["address"] & ~0x3F == owner_line
    ]
    assert owner_dir_commit
    assert owner_dir_commit[-1]["state"] == 1
    assert owner_dir_commit[-1]["sharers"] == 0b11
    assert owner_commit["cycle"] <= snoop_response["cycle"]
    assert requester_commit["cycle"] < refill_last["cycle"]

    # Advance the reference independently and verify final ownership/data.
    env.reference.observe(snooper_core, owner_addr, response_data=results[snooper_core])
    env.reference.observe(owner_core, refill_addr, response_data=results[owner_core])
    assert env.reference.states[owner_line] == ["S", "S"]
    assert env.reference.directory_view(owner_line) == {
        "state": "S", "owner": None, "sharers": 0b11,
    }
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0

    # Strict cross evidence binds the observed three-way overlap to the exact
    # monitor events. The APB sample overlaps the AXI refill and the complete
    # remote GetS request/response lifecycle, including the owner Snoop.
    owner_request = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "request_accept" and
        event["core"] == snooper_core and event["address"] == owner_addr
    )
    owner_response = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "response_complete" and
        event["core"] == snooper_core and event["address"] == owner_addr
    )
    refill_beats = [
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_beat" and
        event["txn_id"] == refill_ar["txn_id"] and
        event["address"] & ~0x3F == (refill_addr & ~0x3F)
    ]
    assert [event["beat"] for event in refill_beats] == list(range(8))
    assert refill_beats[-1]["last"]
    assert refill_ar["cycle"] <= apb_event["cycle"] <= refill_beats[-1]["cycle"]
    assert owner_request["cycle"] <= apb_event["cycle"] <= owner_response["cycle"]

    event_refs = [
        event_reference("refill_ar", "refill", refill_ar),
        event_reference("refill_last", "refill", refill_beats[-1]),
        event_reference("owner_request", "owner_transfer", owner_request),
        event_reference("owner_response", "owner_transfer", owner_response),
        event_reference("apb_sample", "apb_sample", apb_event),
        event_reference("snoop_accept", "owner_transfer", snoop_accept),
        event_reference("snoop_response", "owner_transfer", snoop_response),
        event_reference("owner_l1_commit", "owner_transfer", owner_commit),
        event_reference("requester_l1_commit", "owner_transfer", requester_commit),
        event_reference("directory_commit", "owner_transfer", owner_dir_commit[-1]),
    ]
    event_refs.extend(
        event_reference(f"owner_data_beat_{event['beat']}", "owner_transfer", event)
        for event in owner_beats
    )
    event_refs.extend(
        event_reference(f"refill_read_beat_{event['beat']}", "refill", event)
        for event in refill_beats
    )
    event_refs.extend(
        event_reference(f"directory_request_{index}", "owner_transfer", event)
        for index, event in enumerate(
            event for event in events
            if event["source"] == "directory" and
            event["event_type"] == "request_accept" and
            event["address"] & ~0x3F in {owner_line, refill_addr & ~0x3F}
        )
    )
    proof = checked_overlap_proof(
        checker="owner-transfer/refill/APB independent scoreboard and protocol checker",
        checker_pass=True,
        role_endpoints={
            "refill": ("refill_ar", "refill_last"),
            "owner_transfer": ("owner_request", "owner_response"),
            "apb_sample": ("apb_sample", "apb_sample"),
        },
        event_refs=event_refs,
        transactions=[
            {"role": "refill", "protocol": "AXI4-R",
             "txn_id": refill_ar["txn_id"], "address": refill_addr & ~0x3F,
             "event_ref_ids": ["refill_ar", "refill_last"]},
            {"role": "owner_gets", "protocol": "CPU",
             "txn_id": owner_response["txn_id"], "address": owner_addr,
             "event_ref_ids": ["owner_request", "owner_response"]},
            {"role": "owner_snoop", "protocol": "Snoop",
             "txn_id": snoop_accept["txn_id"], "address": owner_line,
             "event_ref_ids": ["snoop_accept", "snoop_response"]},
            {"role": "apb_sample", "protocol": "APB",
             "address": env.apb.CSR_SNOOP_COUNT,
             "event_ref_ids": ["apb_sample"]},
        ],
        state_transitions=[
            {"event_ref_id": "owner_l1_commit", "old_state": 3, "new_state": 1},
            {"event_ref_id": "requester_l1_commit", "old_state": 0, "new_state": 1},
            {"event_ref_id": "directory_commit", "state": 1, "sharers": 0b11},
        ],
    )

    env.coverage.sample_checked_event(
        "FS.XAGENT.OWNER_TRANSFER_REFILL_APB", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET", checked=True,
        evidence=proof,
    )
