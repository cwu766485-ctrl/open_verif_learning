"""Cross-agent integration scenarios with cycle-level overlap evidence."""

import asyncio
import random

import pytest
from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)


@case
async def test_mmio_read_cache_miss_and_apb_miss_counter_overlap(full_system_env):
    """Exercise MMIO, cache refill, and APB against one running DUT at once."""
    env = await full_system_env(
        axi_options={"latency": 24, "read_reorder_window": 2,
                     "r_valid_gap_period": 2},
        mmio_options={"response_delay": 80},
    )
    mmio_addr = 0x3000_0120
    mmio_value = 0xA55A_0123_CDEF_9876
    cache_addr = 0x0040_8008
    cache_value = 0x1357_9BDF_2468_ACE0
    env.mmio.words[mmio_addr & ~0x7] = mmio_value
    env.seed_word(cache_addr, cache_value)

    predicted, _ = env.reference.predict(1, cache_addr)
    transition_start = len(env.reference.transitions)
    event_start = len(env.monitor.events)

    # Both CPU lanes launch together. The MMIO slave holds its response long
    # enough for the cache refill and APB read to overlap its lifecycle.
    cpu_pair = asyncio.create_task(env.cpu.access_pair(
        CpuRequest(mmio_addr), CpuRequest(cache_addr)
    ))
    for _ in range(200):
        await ClockCycles(env.dut, 1)
        if env.axi.read_addresses:
            break
    assert env.axi.read_addresses, "cache miss did not issue an AXI read"
    assert not env.axi.read_completions, "AXI refill completed before APB observation"

    miss_count = await env.apb.read(env.apb.CSR_MISS_COUNT)
    assert not env.axi.read_completions, "APB read did not overlap the outstanding refill"
    mmio_result, cache_result = await cpu_pair

    assert mmio_result == mmio_value
    assert cache_result == predicted == cache_value
    assert len(env.mmio.requests) == len(env.mmio.completions) == 1
    assert env.mmio.requests[0]["addr"] == mmio_addr
    assert env.mmio.requests[0]["write"] == 0
    assert env.mmio.completions[0]["data"] == mmio_value
    assert miss_count == 1, f"APB miss counter included unexpected traffic: {miss_count}"
    assert env.axi.valid_gaps["R"] > 0, "AXI R channel had no injected response gaps"
    assert env.axi.stalls["R"] == 0, (
        "the integrated DUT unexpectedly deasserted RREADY; update the test's "
        "documented receiver-backpressure expectation"
    )
    assert len(env.axi.read_beats) == 8
    assert [beat[1] for beat in env.axi.read_beats] == list(range(8))
    assert env.axi.read_completions, "AXI refill did not complete"

    events = env.monitor.events[event_start:]
    apb_event = next(event for event in events
                     if event["source"] == "apb" and
                     event["event_type"] == "access_complete" and
                     event["address"] == env.apb.CSR_MISS_COUNT)
    axi_ar_event = next(event for event in events
                        if event["source"] == "axi" and
                        event["event_type"] == "read_address")
    axi_last_beat = next(event for event in events
                         if event["source"] == "axi" and
                         event["event_type"] == "read_beat" and event["last"])
    mmio_request = next(event for event in events
                        if event["source"] == "mmio" and
                        event["event_type"] == "request_accept")
    mmio_response = next(event for event in events
                         if event["source"] == "mmio" and
                         event["event_type"] == "response_complete")
    assert axi_ar_event["cycle"] < apb_event["cycle"] < axi_last_beat["cycle"]
    assert mmio_request["cycle"] < apb_event["cycle"] < mmio_response["cycle"]
    assert apb_event["payload"]["read_data"] == miss_count

    # MMIO bypass must not allocate a cache line or create a directory request.
    mmio_line = mmio_addr & ~0x3F
    assert not any(event["source"] == "l1" and
                   event["event_type"] == "metadata_commit" and
                   event["address"] & ~0x3F == mmio_line for event in events)
    assert not any(event["source"] == "directory" and
                   event["event_type"] == "request_accept" and
                   event["address"] == mmio_addr for event in events)

    # The independent data/coherence model checks the cacheable lane. The CPU
    # driver and MMIO register model independently check the bypass lane.
    env.reference.observe(1, cache_addr, response_data=cache_result)
    observed = env._check_observed_commits(cache_addr & ~0x3F, event_start)
    cpu_txn = next(txn for txn in env.cpu.transactions
                   if txn["request_group"] == env.cpu.request_group - 1 and
                   txn["core"] == 1)
    env._credit_cpu(1, False, cache_addr, cpu_txn["accepted_cycle"],
                    cpu_txn["response_cycle"], transition_start, observed)
    env.coverage.sample_checked_event(
        "FS.XAGENT.MMIO_READ_CACHE_MISS_APB_COUNTER", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.MMIO_READ_CACHE_MISS_APB", checked=True
    )

    assert int(env.dut.protocol_error.value) == 0


@case
async def test_shared_upgrade_overlaps_pending_mmio(full_system_env):
    """CR02: a real S->M upgrade completes while a peer MMIO is pending."""
    seed = 0xC002
    rng = random.Random(seed)
    env = await full_system_env(
        seed=seed,
        mmio_options={"response_delay": 96},
    )
    env.trace_scenario_id = "CR02_SHARED_UPGRADE_MMIO_PENDING"
    cache_addr = 0x0062_4008 + (rng.randrange(8) * 64)
    mmio_addr = 0x3000_2000 + (rng.randrange(16) * 8)
    original = rng.getrandbits(64)
    new_value = rng.getrandbits(64)
    mmio_data = rng.getrandbits(64)
    env.trace_config.update({
        "core0": 0,
        "core1": 1,
        "cache_address": cache_addr,
        "mmio_address": mmio_addr,
        "mmio_response_delay_cycles": 96,
        "seed": seed,
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "establish_shared_copy",
         "address": cache_addr, "cores": [0, 1]},
        {"kind": "stimulus", "operation": "core0_upgrade_and_core1_mmio_write",
         "cache_address": cache_addr, "mmio_address": mmio_addr,
         "cache_data": new_value, "mmio_data": mmio_data},
    ])
    env.seed_word(cache_addr, original)
    assert await env.cpu_access(0, cache_addr) == original
    assert await env.cpu_access(1, cache_addr) == original
    assert env.reference.states[cache_addr & ~0x3F] == ["S", "S"]

    transition_start = len(env.reference.transitions)
    event_start = len(env.monitor.events)
    pair = asyncio.create_task(env.cpu.access_pair(
        CpuRequest(cache_addr, write=True, data=new_value),
        CpuRequest(mmio_addr, write=True, data=mmio_data, mask=0xFF),
    ))
    (cache_result, mmio_result) = await pair
    # Store responses return the pre-write word through the current LSU
    # contract; the independent scoreboard then applies the committed store.
    assert cache_result == original and mmio_result == 0
    assert env.mmio.words[mmio_addr & ~0x7] == mmio_data
    assert len(env.mmio.requests) == len(env.mmio.completions) == 1

    # Advance only the independent architectural model from the accepted CPU
    # request and returned CPU response, then compare all observed commits.
    env.reference.observe(0, cache_addr, write=True, write_data=new_value,
                          response_data=cache_result)
    observed = env._check_observed_commits(cache_addr & ~0x3F, event_start)
    cpu_txn = next(txn for txn in env.cpu.transactions
                   if txn["request_group"] == env.cpu.request_group - 1 and
                   txn["core"] == 0)
    env._credit_cpu(0, True, cache_addr, cpu_txn["accepted_cycle"],
                    cpu_txn["response_cycle"], transition_start, observed)

    events = env.monitor.events[event_start:]
    line = cache_addr & ~0x3F
    cpu_events = [event for event in events
                  if event["source"] == "cpu" and event["core"] == 0 and
                  event["address"] == cache_addr]
    cpu_req = next(event for event in cpu_events
                   if event["event_type"] == "request_accept")
    cpu_rsp = next(event for event in cpu_events
                   if event["event_type"] == "response_complete")
    mmio_req = next(event for event in events
                    if event["source"] == "mmio" and
                    event["event_type"] == "request_accept" and
                    event["address"] == mmio_addr)
    mmio_rsp = next(event for event in events
                    if event["source"] == "mmio" and
                    event["event_type"] == "response_complete" and
                    event["address"] == mmio_addr)
    upgrade_req = next(event for event in events
                       if event["source"] == "directory" and
                       event["event_type"] == "request_accept" and
                       event["address"] & ~0x3F == line)
    assert upgrade_req["opcode"] == 2, "shared store did not issue Upgrade"
    snoop_accept = next(event for event in events
                        if event["source"] == "snoop" and
                        event["event_type"] == "accept" and
                        event["core"] == 1 and
                        event["address"] & ~0x3F == line)
    snoop_response = next(event for event in events
                          if event["source"] == "snoop" and
                          event["event_type"] == "response" and
                          event["core"] == 1 and
                          event["txn_id"] == snoop_accept["txn_id"])
    commits = [event for event in events
               if event["source"] == "l1" and
               event["event_type"] == "metadata_commit" and
               event["address"] & ~0x3F == line]
    core0_commit = next(event for event in commits
                        if event["core"] == 0 and event["old_state"] == 1 and
                        event["new_state"] == 3 and not event["is_snoop"])
    core1_commit = next(event for event in commits
                        if event["core"] == 1 and event["old_state"] == 1 and
                        event["new_state"] == 0 and event["is_snoop"])
    directory_commit = next(event for event in events
                            if event["source"] == "directory" and
                            event["event_type"] == "metadata_commit" and
                            event["address"] & ~0x3F == line)

    # The MMIO request must be accepted while the upgrade is in flight, and
    # its response must remain pending until after the cache response.
    assert mmio_req["cycle"] <= upgrade_req["cycle"] <= snoop_accept["cycle"]
    assert snoop_response["cycle"] <= cpu_rsp["cycle"] < mmio_rsp["cycle"]
    assert cpu_req["cycle"] <= upgrade_req["cycle"]
    assert env.reference.states[line] == ["M", "I"]
    assert int(env.dut.protocol_error.value) == 0

    refs = [
        event_reference("cpu_request", "upgrade", cpu_req),
        event_reference("cpu_response", "upgrade", cpu_rsp),
        event_reference("directory_upgrade", "upgrade", upgrade_req),
        event_reference("mmio_request", "mmio_pending", mmio_req),
        event_reference("mmio_response", "mmio_pending", mmio_rsp),
        event_reference("snoop_accept", "snoop", snoop_accept),
        event_reference("snoop_response", "snoop", snoop_response),
        event_reference("l1_core0_commit", "mesi_commit", core0_commit),
        event_reference("l1_core1_commit", "mesi_commit", core1_commit),
        event_reference("directory_commit", "directory_commit", directory_commit),
    ]
    cpu_txn_id = cpu_rsp["txn_id"]
    proof = checked_overlap_proof(
        checker="independent MESI/MMIO data models + S-to-M commit + snoop lifecycle checker",
        checker_pass=True,
        role_endpoints={
            "upgrade": ("directory_upgrade", "cpu_response"),
            "mmio_pending": ("mmio_request", "mmio_response"),
            "snoop": ("snoop_accept", "snoop_response"),
        },
        event_refs=refs,
        transactions=[
            {"role": "upgrade", "protocol": "CPU/MESI", "txn_id": cpu_txn_id,
             "address": cache_addr, "event_ref_ids": ["cpu_request", "cpu_response",
                                                         "directory_upgrade"]},
            {"role": "mmio_pending", "protocol": "MMIO", "address": mmio_addr,
             "event_ref_ids": ["mmio_request", "mmio_response"]},
            {"role": "snoop", "protocol": "MESI-Snoop", "txn_id": snoop_accept["txn_id"],
             "address": line, "event_ref_ids": ["snoop_accept", "snoop_response"]},
        ],
        state_transitions=[
            {"event_ref_id": "l1_core0_commit", "old_state": 1, "new_state": 3},
            {"event_ref_id": "l1_core1_commit", "old_state": 1, "new_state": 0},
            {"event_ref_id": "directory_commit", "state": 2, "owner": 0},
        ],
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.SHARED_UPGRADE_MMIO_PENDING", checked=True, evidence=proof
    )


@pytest.mark.parametrize("seed", [0xC105, 0xC107])
@case
async def test_same_set_directory_conflict_overlaps_axi_ar_stall(full_system_env,
                                                                 seed):
    """CR05: a legal same-L2-set Directory conflict overlaps AXI AR stall."""
    rng = random.Random(seed)
    owner_core = (seed >> 1) & 1
    snooper_core = 1 - owner_core
    owner_addr = 0x0240_0000 + rng.randrange(16) * 0x100
    refill_addr = owner_addr + 512 * 64
    owner_value = rng.getrandbits(64)
    refill_value = rng.getrandbits(64)
    ar_stall_period = 2 + rng.randrange(2)
    snoop_delay = 1 + rng.randrange(3)
    assert (owner_addr >> 6) % 512 == (refill_addr >> 6) % 512

    env = await full_system_env(
        seed=seed,
        axi_options={"latency": 40 + rng.randrange(9),
                     "ar_stall_period": ar_stall_period,
                     "r_valid_gap_period": 2 + rng.randrange(3)},
    )
    env.trace_scenario_id = "CR05_SAME_SET_DIRECTORY_CONFLICT_AXI_AR_STALL"
    env.trace_config.update({
        "seed": seed,
        "owner_core": owner_core,
        "snooper_core": snooper_core,
        "owner_address": owner_addr,
        "refill_address": refill_addr,
        "l2_set_relation": "same",
        "ar_stall_period": ar_stall_period,
        "snoop_delay_cycles": snoop_delay,
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "make_modified_owner",
         "core": owner_core, "address": owner_addr, "data": owner_value},
        {"kind": "stimulus", "operation": "same_set_refill_and_remote_gets",
         "refill_core": owner_core, "refill_address": refill_addr,
         "snoop_core": snooper_core, "snoop_address": owner_addr,
         "snoop_delay_cycles": snoop_delay},
    ])
    env.seed_word(owner_addr, 0x1234_5678)
    env.seed_word(refill_addr, refill_value)
    await env.cpu_access(owner_core, owner_addr, write=True,
                         data=owner_value, mask=0xFF)
    assert env.reference.states[owner_addr & ~0x3F][owner_core] == "M"

    requests = [None, None]
    requests[owner_core] = CpuRequest(refill_addr)
    requests[snooper_core] = CpuRequest(owner_addr)
    event_start = len(env.monitor.events)
    results = await env.cpu_access_pair(
        requests[0], requests[1],
        request_delay_cycles={snooper_core: snoop_delay},
    )
    assert results[owner_core] == refill_value
    assert results[snooper_core] == owner_value

    events = env.monitor.events[event_start:]
    refill_line = refill_addr & ~0x3F
    owner_line = owner_addr & ~0x3F
    conflicts = [event for event in events
                 if event["source"] == "directory" and
                 event["event_type"] == "same_set_conflict"]
    ar_stalls = [event for event in events
                 if event["source"] == "axi" and
                 event["event_type"] == "stall" and
                 event.get("channel") == "AR"]
    refill_start = next(event for event in events
                        if event["source"] == "l2" and
                        event["event_type"] == "refill_start")
    refill_end = next(event for event in events
                      if event["source"] == "l2" and
                      event["event_type"] == "refill_end")
    mshr_allocate = next(event for event in events
                         if event["source"] == "mshr" and
                         event["event_type"] == "allocate")
    mshr_retire = next(event for event in events
                       if event["source"] == "mshr" and
                       event["event_type"] == "retire")
    ar_event = next(event for event in events
                    if event["source"] == "axi" and
                    event["event_type"] == "read_address" and
                    event["address"] == refill_line)
    r_beats = [event for event in events
               if event["source"] == "axi" and
               event["event_type"] == "read_beat" and
               event["txn_id"] == ar_event["txn_id"]]
    assert len(r_beats) == 8 and [event["beat"] for event in r_beats] == list(range(8))
    assert [event["last"] for event in r_beats] == [0] * 7 + [1]
    assert ar_stalls, "configured AXI AR backpressure was not observed"
    assert conflicts, "Directory same-set interlock was not observed"
    overlap_conflict, overlap_stall = next(
        ((conflict, stall) for conflict in conflicts for stall in ar_stalls
         if conflict["cycle"] == stall["cycle"]), (None, None)
    )
    assert overlap_conflict is not None, (
        "no cycle contained both a same-set Directory conflict and AXI AR stall"
    )
    assert mshr_allocate["cycle"] <= overlap_stall["cycle"] <= mshr_retire["cycle"]

    cpu_requests = [event for event in events
                    if event["source"] == "cpu" and
                    event["event_type"] == "request_accept"]
    cpu_responses = [event for event in events
                     if event["source"] == "cpu" and
                     event["event_type"] == "response_complete"]
    refill_cpu_req = next(event for event in cpu_requests
                          if event["core"] == owner_core and
                          event["address"] == refill_addr)
    refill_cpu_rsp = next(event for event in cpu_responses
                          if event["core"] == owner_core and
                          event["address"] == refill_addr)
    owner_cpu_req = next(event for event in cpu_requests
                         if event["core"] == snooper_core and
                         event["address"] == owner_addr)
    owner_cpu_rsp = next(event for event in cpu_responses
                         if event["core"] == snooper_core and
                         event["address"] == owner_addr)
    snoop_accept = next(event for event in events
                        if event["source"] == "snoop" and
                        event["event_type"] == "accept" and
                        event["core"] == owner_core and
                        event["address"] & ~0x3F == owner_line)
    snoop_response = next(event for event in events
                          if event["source"] == "snoop" and
                          event["event_type"] == "response" and
                          event["core"] == owner_core and
                          event["txn_id"] == snoop_accept["txn_id"])
    owner_commit = next(event for event in events
                        if event["source"] == "l1" and
                        event["event_type"] == "metadata_commit" and
                        event["core"] == owner_core and
                        event["address"] & ~0x3F == owner_line and
                        event["old_state"] == 3 and event["new_state"] == 1)
    refill_commit = next(event for event in events
                         if event["source"] == "l1" and
                         event["event_type"] == "metadata_commit" and
                         event["core"] == owner_core and
                         event["address"] & ~0x3F == refill_line)
    directory_accept = next(event for event in events
                            if event["source"] == "directory" and
                            event["event_type"] == "request_accept" and
                            event["address"] & ~0x3F == owner_line)
    directory_commits = [event for event in events
                         if event["source"] == "directory" and
                         event["event_type"] == "metadata_commit"]
    owner_dir_commit = next(event for event in directory_commits
                            if event["address"] & ~0x3F == owner_line)
    refill_dir_commit = next(event for event in directory_commits
                             if event["address"] & ~0x3F == refill_line)
    assert directory_accept["cycle"] > refill_end["cycle"], (
        "same-set request bypassed the Directory serialization constraint"
    )
    assert snoop_accept["cycle"] >= directory_accept["cycle"]
    assert sum(event["source"] == "mshr" and
               event["event_type"] == "allocate" for event in events) == 1
    assert sum(event["source"] == "mshr" and
               event["event_type"] == "retire" for event in events) == 1
    assert int(env.dut.protocol_error.value) == 0

    refs = [
        event_reference("same_set_conflict_start", "directory_conflict", conflicts[0]),
        event_reference("same_set_conflict_end", "directory_conflict", conflicts[-1]),
        event_reference("coincident_ar_stall", "axi_ar_stall", overlap_stall),
        event_reference("refill_start", "refill", refill_start),
        event_reference("refill_end", "refill", refill_end),
        event_reference("mshr_allocate", "refill", mshr_allocate),
        event_reference("mshr_retire", "refill", mshr_retire),
        event_reference("axi_ar", "refill", ar_event),
        event_reference("axi_rlast", "refill", r_beats[-1]),
        event_reference("refill_cpu_request", "refill_cpu", refill_cpu_req),
        event_reference("refill_cpu_response", "refill_cpu", refill_cpu_rsp),
        event_reference("owner_cpu_request", "owner_snoop", owner_cpu_req),
        event_reference("owner_cpu_response", "owner_snoop", owner_cpu_rsp),
        event_reference("directory_owner_request", "owner_snoop", directory_accept),
        event_reference("snoop_accept", "owner_snoop", snoop_accept),
        event_reference("snoop_response", "owner_snoop", snoop_response),
        event_reference("owner_commit", "mesi_commit", owner_commit),
        event_reference("refill_commit", "mesi_commit", refill_commit),
        event_reference("directory_owner_commit", "directory_commit", owner_dir_commit),
        event_reference("directory_refill_commit", "directory_commit", refill_dir_commit),
    ]
    proof = checked_overlap_proof(
        checker="independent CPU/reference model + AXI burst/ID + owner Snoop + same-set interlock checker",
        checker_pass=True,
        role_endpoints={
            "directory_conflict": ("same_set_conflict_start", "same_set_conflict_end"),
            "axi_ar_stall": ("coincident_ar_stall", "coincident_ar_stall"),
            "refill": ("mshr_allocate", "mshr_retire"),
        },
        event_refs=refs,
        transactions=[
            {"role": "refill", "protocol": "AXI4-R", "txn_id": ar_event["txn_id"],
             "address": refill_line, "event_ref_ids": ["axi_ar", "axi_rlast",
                                                          "refill_cpu_request",
                                                          "refill_cpu_response"]},
            {"role": "owner_snoop", "protocol": "MESI-Snoop",
             "txn_id": snoop_accept["txn_id"], "address": owner_line,
             "event_ref_ids": ["owner_cpu_request", "owner_cpu_response",
                               "directory_owner_request", "snoop_accept",
                               "snoop_response"]},
        ],
        state_transitions=[
            {"event_ref_id": "owner_commit", "old_state": 3, "new_state": 1},
            {"event_ref_id": "directory_owner_commit",
             "state": owner_dir_commit["state"],
             "sharers": owner_dir_commit["sharers"]},
            {"event_ref_id": "directory_refill_commit",
             "state": refill_dir_commit["state"],
             "owner": refill_dir_commit["owner"]},
        ],
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.DIRECTORY_SAME_SET_AXI_AR_STALL", checked=True, evidence=proof
    )


@pytest.mark.parametrize("seed", [0xC010, 0xC110])
@case
async def test_ownership_pingpong_overlaps_mmio_and_apb(full_system_env, seed):
    """CR10: two checked ownership transfers overlap peer MMIO and APB."""
    rng = random.Random(seed)
    first_owner = rng.randrange(2)
    peer = 1 - first_owner
    line = 0x006A_0000 + rng.randrange(16) * 64
    address = line + rng.randrange(8) * 8
    mmio_addr = 0x3000_4000 + rng.randrange(32) * 8
    initial_data, owner_data, peer_data, final_data, mmio_data = (
        rng.getrandbits(64) for _ in range(5)
    )
    env = await full_system_env(
        seed=seed, mmio_options={"response_delay": 160}
    )
    env.trace_scenario_id = "CR10_OWNERSHIP_PINGPONG_MMIO_APB"
    env.trace_config.update({
        "seed": seed, "first_owner_core": first_owner, "peer_core": peer,
        "cache_line": line, "cache_word_address": address,
        "mmio_address": mmio_addr, "mmio_response_delay_cycles": 160,
        "cpu_response_stall_cycles": 12,
    })
    env.trace_operations.extend([
        {"kind": "legal_prelude", "operation": "first_core_acquires_M",
         "core": first_owner, "address": address, "data": owner_data},
        {"kind": "stimulus", "operation": "ownership_pingpong_with_peer_mmio",
         "first_requester": peer, "second_requester": first_owner,
         "address": address, "mmio_address": mmio_addr,
         "first_transfer_data": peer_data,
         "second_transfer_data": final_data, "mmio_data": mmio_data},
    ])
    env.seed_word(address, initial_data)
    env.mmio.words[mmio_addr & ~0x7] = mmio_data

    # Legal M-owner prelude and first M-to-M ownership transfer. cpu_access
    # advances the independent architectural reference only after response.
    assert await env.cpu_access(first_owner, address, write=True,
                                data=owner_data) == initial_data
    assert env.reference.states[line][first_owner] == "M"
    assert await env.cpu_access(peer, address, write=True,
                                data=peer_data) == owner_data
    assert env.reference.states[line][peer] == "M"

    expected_old, _ = env.reference.predict(
        first_owner, address, write=True, write_data=final_data
    )
    assert expected_old == peer_data
    event_start = len(env.monitor.events)
    transition_start = len(env.reference.transitions)
    request_group = env.cpu.request_group
    requests = [None, None]
    requests[first_owner] = CpuRequest(address, write=True, data=final_data)
    requests[peer] = CpuRequest(mmio_addr)

    # Hold the CPU responses and MMIO completion long enough to sample APB
    # after the real second Snoop accept, inside the ownership transfer.
    cpu_pair = asyncio.create_task(env.cpu.access_pair(
        requests[0], requests[1], response_stall_cycles=12
    ))
    apb_task = None
    for _ in range(500):
        await ClockCycles(env.dut, 1)
        active = env.monitor.events[event_start:]
        mmio_pending = any(
            event["source"] == "mmio" and
            event["event_type"] == "request_accept" and
            event["address"] == mmio_addr for event in active
        )
        directory_accepted = any(
            event["source"] == "directory" and
            event["event_type"] == "request_accept" and
            event["address"] & ~0x3F == line and
            event.get("source_id") == first_owner for event in active
        )
        snoop_accepted = any(
            event["source"] == "snoop" and event["event_type"] == "accept" and
            event.get("core") == peer and event["address"] & ~0x3F == line
            for event in active
        )
        if mmio_pending and directory_accepted and snoop_accepted:
            apb_task = asyncio.create_task(
                env.apb.read(env.apb.CSR_SNOOP_COUNT)
            )
            break
        if cpu_pair.done():
            break
    assert apb_task is not None, (
        "second Directory request, peer Snoop, and pending MMIO did not "
        "coexist before the CPU pair completed"
    )

    results = await cpu_pair
    snoop_count = await apb_task
    cache_result, mmio_result = results[first_owner], results[peer]
    assert cache_result == expected_old
    assert mmio_result == mmio_data
    # The legal prelude transferred M once; the APB sample observes the
    # second transfer while the peer MMIO response is still pending.
    assert snoop_count == 2
    assert len(env.mmio.requests) == len(env.mmio.completions) == 1
    assert env.mmio.requests[0]["addr"] == mmio_addr
    assert env.mmio.requests[0]["write"] == 0
    assert env.mmio.completions[0]["data"] == mmio_data

    env.reference.observe(first_owner, address, write=True,
                          write_data=final_data, response_data=cache_result)
    observed = env._check_observed_commits(line, event_start)
    transactions = {
        txn["core"]: txn for txn in env.cpu.transactions
        if txn["request_group"] == request_group
    }
    assert set(transactions) == {first_owner, peer}
    for core, write, addr in ((first_owner, True, address),
                              (peer, False, mmio_addr)):
        txn = transactions[core]
        assert txn["addr"] == addr
        env._credit_cpu(core, write, addr, txn["accepted_cycle"],
                        txn["response_cycle"], transition_start,
                        observed if core == first_owner else set())

    # Complete the return leg after the peer MMIO response. This gives the
    # scenario a real two-transfer ownership ping-pong, while the first leg
    # overlaps MMIO and the APB observation above.
    return_data = rng.getrandbits(64)
    expected_return, _ = env.reference.predict(
        peer, address, write=True, write_data=return_data
    )
    assert expected_return == final_data
    return_event_start = len(env.monitor.events)
    assert await env.cpu_access(peer, address, write=True,
                                data=return_data) == final_data
    return_observed = env._check_observed_commits(line, return_event_start)
    assert return_observed

    events = env.monitor.events[event_start:]
    directory_requests = [
        event for event in events
        if event["source"] == "directory" and
        event["event_type"] == "request_accept" and
        event["address"] & ~0x3F == line
    ]
    first_directory = next(event for event in directory_requests
                           if event.get("source_id") == first_owner)
    second_directory = next(event for event in directory_requests
                            if event.get("source_id") == peer and
                            event["cycle"] > first_directory["cycle"])
    assert first_directory["opcode"] in (0b001, 0b010)
    assert second_directory["opcode"] in (0b001, 0b010)

    snoop_accepts = [
        event for event in events
        if event["source"] == "snoop" and event["event_type"] == "accept" and
        event["address"] & ~0x3F == line
    ]
    first_snoop = next(event for event in snoop_accepts
                       if event["core"] == peer)
    second_snoop = next(event for event in snoop_accepts
                        if event["core"] == first_owner and
                        event["cycle"] > first_snoop["cycle"])
    first_snoop_response = next(
        event for event in events
        if event["source"] == "snoop" and event["event_type"] == "response" and
        event["core"] == peer and event["txn_id"] == first_snoop["txn_id"]
    )
    second_snoop_response = next(
        event for event in events
        if event["source"] == "snoop" and event["event_type"] == "response" and
        event["core"] == first_owner and event["txn_id"] == second_snoop["txn_id"]
    )
    cpu_events = [event for event in events if event["source"] == "cpu"]
    first_req = next(event for event in cpu_events
                     if event["event_type"] == "request_accept" and
                     event["core"] == first_owner and event["address"] == address)
    first_rsp = next(event for event in cpu_events
                     if event["event_type"] == "response_complete" and
                     event["core"] == first_owner and event["address"] == address)
    second_req = next(event for event in cpu_events
                      if event["event_type"] == "request_accept" and
                      event["core"] == peer and event["address"] == address and
                      event["cycle"] > first_req["cycle"])
    second_rsp = next(event for event in cpu_events
                      if event["event_type"] == "response_complete" and
                      event["core"] == peer and event["address"] == address and
                      event["cycle"] > second_req["cycle"])
    mmio_req = next(event for event in events
                    if event["source"] == "mmio" and
                    event["event_type"] == "request_accept" and
                    event["address"] == mmio_addr)
    mmio_rsp = next(event for event in events
                    if event["source"] == "mmio" and
                    event["event_type"] == "response_complete" and
                    event["address"] == mmio_addr)
    apb = next(event for event in events
               if event["source"] == "apb" and
               event["event_type"] == "access_complete" and
               event["address"] == env.apb.CSR_SNOOP_COUNT)

    commits = [event for event in events
               if event["source"] == "l1" and
               event["event_type"] == "metadata_commit" and
               event["address"] & ~0x3F == line]
    old_owner_i = next(event for event in commits
                       if event["core"] == peer and
                       event["old_state"] == 3 and event["new_state"] == 0 and
                       event["is_snoop"])
    peer_m = next(event for event in commits
                  if event["core"] == first_owner and event["old_state"] == 0 and
                  event["new_state"] == 3 and not event["is_snoop"])
    peer_i = next(event for event in commits
                  if event["core"] == first_owner and event["old_state"] == 3 and
                  event["new_state"] == 0 and event["is_snoop"] and
                  event["cycle"] > old_owner_i["cycle"])
    owner_m = next(event for event in commits
                   if event["core"] == peer and
                   event["old_state"] == 0 and event["new_state"] == 3 and
                   not event["is_snoop"] and event["cycle"] > peer_i["cycle"])
    directory_commits = [event for event in events
                         if event["source"] == "directory" and
                         event["event_type"] == "metadata_commit" and
                         event["address"] & ~0x3F == line]
    peer_dir = next(event for event in directory_commits
                    if event["owner"] == first_owner)
    owner_dir = next(event for event in directory_commits
                     if event["owner"] == peer and
                     event["cycle"] > peer_dir["cycle"])

    assert first_req["cycle"] <= first_directory["cycle"] <= first_snoop["cycle"]
    assert first_snoop["cycle"] <= first_snoop_response["cycle"] <= first_rsp["cycle"]
    assert second_req["cycle"] <= second_directory["cycle"] <= second_snoop["cycle"]
    assert second_snoop["cycle"] <= second_snoop_response["cycle"] <= second_rsp["cycle"]
    assert mmio_req["cycle"] < apb["cycle"] < mmio_rsp["cycle"]
    assert first_req["cycle"] <= apb["cycle"] <= first_rsp["cycle"]
    assert apb["payload"]["read_data"] == 2
    assert env.reference.states[line] == [
        "M" if peer == 0 else "I",
        "M" if peer == 1 else "I",
    ]
    assert env.reference.directory_view(line) == {
        "state": "U", "owner": peer, "sharers": 0,
    }
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0

    refs = [
        event_reference("first_request", "pingpong", first_req),
        event_reference("first_response", "pingpong", first_rsp),
        event_reference("first_directory", "pingpong", first_directory),
        event_reference("first_snoop", "pingpong", first_snoop),
        event_reference("first_snoop_response", "pingpong", first_snoop_response),
        event_reference("first_old_owner_invalidate", "pingpong", old_owner_i),
        event_reference("first_peer_grant", "pingpong", peer_m),
        event_reference("first_directory_commit", "pingpong", peer_dir),
        event_reference("return_request", "pingpong", second_req),
        event_reference("return_response", "pingpong", second_rsp),
        event_reference("return_directory", "pingpong", second_directory),
        event_reference("return_snoop", "pingpong", second_snoop),
        event_reference("return_snoop_response", "pingpong", second_snoop_response),
        event_reference("return_peer_invalidate", "pingpong", peer_i),
        event_reference("return_owner_grant", "pingpong", owner_m),
        event_reference("return_directory_commit", "pingpong", owner_dir),
        event_reference("mmio_request", "mmio", mmio_req),
        event_reference("mmio_response", "mmio", mmio_rsp),
        event_reference("apb_sample", "apb", apb),
    ]
    proof = checked_overlap_proof(
        checker="independent MESI/data reference, two Snoop transfers, MMIO model, APB counter",
        checker_pass=True,
        role_endpoints={
            "pingpong": ("first_request", "return_response"),
            "mmio": ("mmio_request", "mmio_response"),
            "apb": ("apb_sample", "apb_sample"),
        },
        event_refs=refs,
        transactions=[
            {"role": "first_transfer", "protocol": "CPU-MESI",
             "txn_id": first_rsp["txn_id"], "address": address,
             "event_ref_ids": ["first_request", "first_response",
                               "first_directory", "first_snoop",
                               "first_snoop_response"]},
            {"role": "ownership_return", "protocol": "CPU-MESI",
             "txn_id": second_rsp["txn_id"], "address": address,
             "event_ref_ids": ["return_request", "return_response",
                               "return_directory", "return_snoop",
                               "return_snoop_response"]},
            {"role": "mmio", "protocol": "SimpleBus-MMIO",
             "transaction_key": f"mmio@{mmio_addr:#x}",
             "address": mmio_addr,
             "event_ref_ids": ["mmio_request", "mmio_response"]},
            {"role": "apb", "protocol": "APB3",
             "address": env.apb.CSR_SNOOP_COUNT,
             "event_ref_ids": ["apb_sample"]},
        ],
        state_transitions=[
            {"event_ref_id": "first_old_owner_invalidate", "old_state": 3, "new_state": 0},
            {"event_ref_id": "first_peer_grant", "old_state": 0, "new_state": 3},
            {"event_ref_id": "first_directory_commit", "state": 2, "owner": first_owner},
            {"event_ref_id": "return_peer_invalidate", "old_state": 3, "new_state": 0},
            {"event_ref_id": "return_owner_grant", "old_state": 0, "new_state": 3},
            {"event_ref_id": "return_directory_commit", "state": 2, "owner": peer},
        ],
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.CR10_OWNERSHIP_PINGPONG_MMIO_APB",
        checked=True, evidence=proof,
    )
