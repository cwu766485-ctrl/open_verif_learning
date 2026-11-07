"""Reusable checked cross-agent coherence sequences for the integrated top."""

import asyncio
import random

from toffee import ClockCycles

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker


async def run_owner_transfer_refill_apb(env, *, seed, trace=None):
    """Overlap a dirty-owner GetS, an unrelated refill, and an APB read.

    All state is constructed through CPU transactions. The helper checks both
    architectural data and observed Snoop/Directory/AXI/APB ordering before it
    credits existing functional and cross bins.
    """
    rng = random.Random(seed)
    owner_core = rng.randrange(2)
    snooper_core = 1 - owner_core
    owner_line = 0x0240_0000 + ((seed & 0xF) << 8)
    # Adjacent lines select distinct L2 sets; the existing same-set policy
    # intentionally serializes those requests and is covered separately.
    refill_line = owner_line + 0x40
    owner_addr = owner_line + rng.randrange(8) * 8
    refill_addr = refill_line + rng.randrange(8) * 8
    owner_data = rng.getrandbits(64)
    owner_mask = rng.randrange(1, 0x100)
    owner_initial = [rng.getrandbits(64) for _ in range(8)]
    refill_words = [rng.getrandbits(64) for _ in range(8)]

    for beat, value in enumerate(owner_initial):
        env.seed_word(owner_line + beat * 8, value)
    for beat, value in enumerate(refill_words):
        env.seed_word(refill_line + beat * 8, value)
    await env.cpu_access(owner_core, owner_addr, write=True,
                         data=owner_data, mask=owner_mask)
    assert env.reference.states[owner_line][owner_core] == "M"

    expected_owner, owner_class = env.reference.predict(snooper_core, owner_addr)
    expected_refill, refill_class = env.reference.predict(owner_core, refill_addr)
    assert owner_class == "remote_read_from_M"
    assert refill_class == "cold_read"

    read_start = len(env.axi.read_addresses)
    completion_start = len(env.axi.read_completions)
    # Keep the refill response window open long enough for the owner transfer
    # and APB observation, independent of the surrounding random workload.
    # This configures only the Python backing-memory model; it does not change
    # the DUT or claim a physical memory latency.
    original_memory_latency = env.axi.latency
    env.axi.latency = max(original_memory_latency, 48)
    response_stall = rng.randrange(4)
    apb_before = await env.apb.read(env.apb.CSR_SNOOP_COUNT)
    event_start = len(env.monitor.events)
    transition_start = len(env.reference.transitions)
    request_group = env.cpu.request_group

    requests = [None, None]
    requests[owner_core] = CpuRequest(refill_addr)
    requests[snooper_core] = CpuRequest(owner_addr)

    def refill_address_accepted():
        return any(
            event["source"] == "axi" and
            event["event_type"] == "read_address" and
            event["address"] & 0xFFFF_FFC0 == refill_line
            for event in env.monitor.events[event_start:]
        )

    async def sample_snoop_counter_while_refill_is_active():
        for _ in range(500):
            await ClockCycles(env.dut, 1)
            observed = env.monitor.events[event_start:]
            snoop_response = any(
                event["source"] == "snoop" and
                event["event_type"] == "response" and
                event["core"] == owner_core
                for event in observed
            )
            refill_active = (
                len(env.axi.read_addresses) > read_start and
                len(env.axi.read_completions) == completion_start
            )
            if snoop_response and refill_active:
                return await env.apb.read(env.apb.CSR_SNOOP_COUNT)
        raise TimeoutError(
            "owner Snoop response and independent AXI refill did not overlap"
        )

    cpu_task = asyncio.create_task(env.cpu.access_pair(
        requests[0], requests[1],
        response_stall_cycles=response_stall,
        request_release_predicates={snooper_core: refill_address_accepted},
    ))
    apb_task = asyncio.create_task(
        sample_snoop_counter_while_refill_is_active()
    )
    try:
        results = await cpu_task
        apb_snoop_count = await apb_task
    finally:
        env.axi.latency = original_memory_latency
        if not apb_task.done():
            apb_task.cancel()
            await asyncio.gather(apb_task, return_exceptions=True)
    assert results[owner_core] == expected_refill
    assert results[snooper_core] == expected_owner
    assert apb_snoop_count == apb_before + 1

    events = env.monitor.events[event_start:]
    refill_lifecycle = MshrLifecycleChecker.check(
        events, expected_lines={refill_line},
        expected_words={refill_line: expected_refill},
        expected_cores={refill_line: owner_core},
    )
    refill_ar = next(event for event in events
                     if event["source"] == "axi" and
                     event["event_type"] == "read_address" and
                     event["address"] & 0xFFFF_FFC0 == refill_line)
    refill_last = next(event for event in events
                       if event["source"] == "axi" and
                       event["event_type"] == "read_beat" and event["last"])
    snoop_accept = next(event for event in events
                        if event["source"] == "snoop" and
                        event["event_type"] == "accept" and
                        event["core"] == owner_core and
                        event["address"] & 0xFFFF_FFC0 == owner_line)
    snoop_response = next(event for event in events
                          if event["source"] == "snoop" and
                          event["event_type"] == "response" and
                          event["core"] == owner_core and
                          event["txn_id"] == snoop_accept["txn_id"])
    apb_event = next(event for event in events
                     if event["source"] == "apb" and
                     event["event_type"] == "access_complete" and
                     event["address"] == env.apb.CSR_SNOOP_COUNT)
    # The owner Snoop is released only after the unrelated refill AR handshake.
    # Check that the accepted events confirm the intended overlap window.
    assert refill_ar["cycle"] < snoop_accept["cycle"]
    assert snoop_accept["cycle"] <= snoop_response["cycle"]
    assert snoop_response["cycle"] < apb_event["cycle"] < refill_last["cycle"]
    assert apb_event["payload"]["read_data"] == apb_snoop_count

    owner_beats = sorted(
        (event for event in events
         if event["source"] == "coherence" and
         event["event_type"] == "owner_data_beat" and
         event["address"] & 0xFFFF_FFC0 == owner_line),
        key=lambda event: event["beat"],
    )
    expected_owner_line = [env.reference.word(owner_line + beat * 8)
                           for beat in range(8)]
    assert [event["beat"] for event in owner_beats] == list(range(8))
    assert [event["data"] for event in owner_beats] == expected_owner_line
    assert owner_beats[-1]["last"]

    owner_commit = next(event for event in events
                        if event["source"] == "l1" and
                        event["event_type"] == "metadata_commit" and
                        event["core"] == owner_core and
                        event["address"] & 0xFFFF_FFC0 == owner_line and
                        event["is_snoop"] and event["old_state"] == 3 and
                        event["new_state"] == 1)
    requester_commit = next(event for event in events
                            if event["source"] == "l1" and
                            event["event_type"] == "metadata_commit" and
                            event["core"] == snooper_core and
                            event["address"] & 0xFFFF_FFC0 == owner_line and
                            event["new_state"] == 1)
    dir_commit = [event for event in events
                  if event["source"] == "directory" and
                  event["event_type"] == "metadata_commit" and
                  event["address"] & 0xFFFF_FFC0 == owner_line]
    assert dir_commit and dir_commit[-1]["state"] == 1
    assert dir_commit[-1]["sharers"] == 0b11

    env.reference.observe(snooper_core, owner_addr,
                          response_data=results[snooper_core])
    env.reference.observe(owner_core, refill_addr,
                          response_data=results[owner_core])
    owner_observed = env._check_observed_commits(owner_line, event_start)
    refill_observed = env._check_observed_commits(refill_line, event_start)
    txns = {txn["core"]: txn for txn in env.cpu.transactions
            if txn["request_group"] == request_group}
    assert set(txns) == {owner_core, snooper_core}
    for core, address in ((owner_core, refill_addr),
                          (snooper_core, owner_addr)):
        observed = refill_observed if core == owner_core else owner_observed
        txn = txns[core]
        env._credit_cpu(core, False, address, txn["accepted_cycle"],
                        txn["response_cycle"], transition_start, observed)

    assert owner_commit["cycle"] <= snoop_response["cycle"]
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
    env.coverage.sample_checked_event(
        "FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.SNOOP_REFILL_DISTINCT_L2_SET", checked=True
    )

    record = {
        "kind": "checked_coherence_prelude",
        "scenario_id": "CR01_OWNER_TRANSFER_REFILL_APB",
        "seed": seed,
        "owner_core": owner_core,
        "snooper_core": snooper_core,
        "owner_address": owner_addr,
        "owner_write_data": owner_data,
        "owner_write_mask": owner_mask,
        "refill_address": refill_addr,
        "request_release_policy": "after_refill_ar_handshake",
        "memory_latency_cycles": max(original_memory_latency, 48),
        "response_stall_cycles": response_stall,
        "apb_snoop_count": apb_snoop_count,
        "refill_lifecycle": refill_lifecycle,
        "snoop_accept_cycle": snoop_accept["cycle"],
        "snoop_response_cycle": snoop_response["cycle"],
        "refill_last_cycle": refill_last["cycle"],
        "checker_status": "passed",
    }
    if trace is not None:
        trace.append(record)
    return record
