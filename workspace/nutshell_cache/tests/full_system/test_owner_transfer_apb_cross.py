"""Cross-agent owner transfer, AXI refill, and APB observation checks."""

import asyncio

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest


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

    env.coverage.sample_checked_event(
        "FS.XAGENT.OWNER_TRANSFER_REFILL_APB", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET", checked=True
    )
