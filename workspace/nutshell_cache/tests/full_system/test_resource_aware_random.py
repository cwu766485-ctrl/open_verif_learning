"""Seeded resource-aware coherence stress at the AXI integrated top."""

import random
import os

import pytest
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest


L2_SET_STRIDE = 512 * 64


def _resource_seeds():
    count = int(os.environ.get("FULL_SYSTEM_RESOURCE_SEED_COUNT", "4"))
    base = int(os.environ.get("FULL_SYSTEM_RESOURCE_BASE_SEED", "0xC000"), 0)
    if not 1 <= count <= 200:
        raise ValueError("FULL_SYSTEM_RESOURCE_SEED_COUNT must be in [1, 200]")
    return [base + index for index in range(count)]


@pytest.mark.parametrize("seed", _resource_seeds())
@case
async def test_seeded_same_and_distinct_l2_set_snoop_refill(full_system_env,
                                                            seed):
    """Compare legal owner snoops against an overlapping refill by set.

    The sequence deliberately creates an M owner, starts a cold miss on the
    other line, then delays the peer request by a seeded number of cycles so
    the refill MSHR is live when the owner Snoop is requested. Address stride
    selects either the same L2 set or a distinct L2 set; no DUT state is poked.
    """
    rng = random.Random(seed)
    same_set = bool(seed & 1)
    latency = 36 + rng.randrange(13)
    snoop_delay = 2 + rng.randrange(4)
    owner_core = (seed >> 1) & 1
    snooper_core = 1 - owner_core
    owner_addr = 0x0240_0000 + ((seed & 0xF) << 8)
    refill_addr = owner_addr + (L2_SET_STRIDE if same_set else 0x40)
    owner_value = rng.getrandbits(64)
    refill_value = rng.getrandbits(64)

    assert (owner_addr >> 6) % 512 == (refill_addr >> 6) % 512 if same_set else \
        (owner_addr >> 6) % 512 != (refill_addr >> 6) % 512

    env = await full_system_env(
        seed=seed,
        axi_options={
            "latency": latency,
            "ar_stall_period": 2 + rng.randrange(3),
            "r_valid_gap_period": 2 + rng.randrange(3),
            "read_reorder_window": 2,
        },
    )
    env.trace_scenario_id = "RESOURCE_AWARE_SNOOP_REFILL"
    env.trace_config.update({
        "resource_seed": seed,
        "l2_set_relation": "same" if same_set else "distinct",
        "owner_core": owner_core,
        "snoop_request_delay": snoop_delay,
        "memory_latency": latency,
    })

    env.seed_word(owner_addr, 0x1234_5678)
    env.seed_word(refill_addr, refill_value)
    await env.cpu_access(owner_core, owner_addr, write=True,
                         data=owner_value, mask=0xFF)

    requests = [None, None]
    requests[owner_core] = CpuRequest(refill_addr)
    requests[snooper_core] = CpuRequest(owner_addr)
    event_start = len(env.monitor.events)
    read_start = len(env.axi.read_addresses)
    results = await env.cpu_access_pair(
        requests[0], requests[1],
        request_delay_cycles={snooper_core: snoop_delay},
        response_stall_cycles=rng.randrange(1, 4),
    )

    assert results[owner_core] == refill_value
    assert results[snooper_core] == owner_value
    events = env.monitor.events[event_start:]
    refill_ar = next(
        event for event in events
        if event["source"] == "axi" and
        event["event_type"] == "read_address" and
        event["address"] == (refill_addr & ~0x3F)
    )
    snoop_accept = next(
        event for event in events
        if event["source"] == "snoop" and
        event["event_type"] == "accept" and
        event["core"] == owner_core and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    refill_end = next(
        event for event in events
        if event["source"] == "l2" and event["event_type"] == "refill_end"
    )
    owner_cpu_accept = next(
        event for event in events
        if event["source"] == "cpu" and
        event["event_type"] == "request_accept" and
        event["core"] == snooper_core and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    owner_dir_accept = next(
        event for event in events
        if event["source"] == "directory" and
        event["event_type"] == "request_accept" and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    )
    snoop_response = next(
        event for event in events
        if event["source"] == "snoop" and
        event["event_type"] == "response" and
        event["txn_id"] == snoop_accept["txn_id"]
    )
    owner_downgrade = [
        event for event in events
        if event["source"] == "l1" and
        event["event_type"] == "metadata_commit" and
        event["core"] == owner_core and
        event["address"] & ~0x3F == (owner_addr & ~0x3F) and
        event["old_state"] == 3 and event["new_state"] == 1
    ]
    assert owner_downgrade, "M owner did not commit the checked Snoop downgrade"
    assert snoop_response["cycle"] >= snoop_accept["cycle"]
    owner_beats = [
        event for event in events
        if event["source"] == "coherence" and
        event["event_type"] == "owner_data_beat" and
        event["address"] & ~0x3F == (owner_addr & ~0x3F)
    ]
    assert [event["beat"] for event in owner_beats] == list(range(8))
    assert owner_beats[0]["data"] == owner_value
    assert owner_beats[-1]["last"]
    assert any(address & ~0x3F == (refill_addr & ~0x3F)
               for _txn_id, address, _cycle
               in env.axi.read_addresses[read_start:])

    assert owner_cpu_accept["cycle"] < refill_end["cycle"], (
        "the peer CPU request must be accepted while the refill is active"
    )
    assert refill_ar["cycle"] < refill_end["cycle"]
    if same_set:
        assert owner_dir_accept["cycle"] > refill_end["cycle"], (
            "same-set request unexpectedly entered the Directory before refill retirement"
        )
        assert snoop_accept["cycle"] >= owner_dir_accept["cycle"]
        env.coverage.sample_checked_event(
            "FS.RESOURCE.SNOOP_REFILL_SAME_L2_SET", checked=True
        )
        env.coverage.sample_checked_cross(
            "FS.CROSS.SNOOP_REFILL_SAME_L2_SET", checked=True
        )
    else:
        assert owner_dir_accept["cycle"] < refill_end["cycle"], (
            "different-set request did not enter the Directory during refill"
        )
        assert snoop_accept["cycle"] < refill_end["cycle"], (
            "different-set owner Snoop failed to complete during active refill"
        )
        env.coverage.sample_checked_event(
            "FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET", checked=True
        )
        env.coverage.sample_checked_cross(
            "FS.CROSS.SNOOP_REFILL_DISTINCT_L2_SET", checked=True
        )

    assert int(env.dut.protocol_error.value) == 0
