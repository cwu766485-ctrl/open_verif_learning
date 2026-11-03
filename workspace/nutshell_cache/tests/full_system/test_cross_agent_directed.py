"""Cross-agent integration scenarios with cycle-level overlap evidence."""

import asyncio

from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest


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
