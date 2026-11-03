"""Hit-under-miss microbenchmark and functional check for the MESI L1 path."""

import json
import os
from pathlib import Path

import pytest
from toffee import ClockCycles
from toffee_test import case


@pytest.mark.asyncio
@case
async def test_hit_under_miss_benchmark(coherent_env):
    """Measure warm hits while a different cold line waits for memory."""
    env = await coherent_env(response_delay=2)
    dut, memory = env.dut, env.memory
    hit_addr = 0x0000_2080
    miss_addr = 0x0000_8000
    hit_expected = await env.cpu.access(0, hit_addr)

    # Keep a real warm L1 line resident while forcing the second line through
    # the backing-memory path. Both addresses are on different cache lines.
    memory.response_delay = 80
    # Read responses are consumed without backpressure so every sampled valid
    # cycle corresponds to a distinct completed read transaction.
    dut.cpu_resp_ready.value = 1
    dut.cpu_req_addr.value = miss_addr
    dut.cpu_req_write.value = 0
    dut.cpu_req_wmask.value = 0
    dut.cpu_req_wdata.value = 0
    dut.cpu_req_valid.value = 1

    cycle = 0
    miss_accept_cycle = None
    for _ in range(100):
        await ClockCycles(dut, 1)
        cycle += 1
        if int(dut.cpu_req_ready.value) & 1:
            miss_accept_cycle = cycle
            dut.cpu_req_valid.value = 0
            break
    assert miss_accept_cycle is not None, "cold miss request was not accepted"

    requested_hits = 24
    accepted_hits = 0
    hit_accept_cycles = []
    hit_response_cycles = []
    miss_response_cycle = None
    miss_response_txn_id = None
    response_count = 0
    hit_responses = 0
    hit_response_txn_ids = []
    dut.cpu_req_addr.value = hit_addr
    dut.cpu_req_valid.value = 1

    for _ in range(2000):
        await ClockCycles(dut, 1)
        cycle += 1

        if accepted_hits < requested_hits:
            dut.cpu_req_valid.value = 1
            if int(dut.cpu_req_ready.value) & 1:
                accepted_hits += 1
                hit_accept_cycles.append(cycle)
                if accepted_hits == requested_hits:
                    dut.cpu_req_valid.value = 0
        else:
            dut.cpu_req_valid.value = 0

        if int(dut.cpu_resp_valid.value) & 1:
            addr = int(dut.cpu_resp_addr.value) & 0xFFFFFFFF
            data = int(dut.cpu_resp_rdata.value) & ((1 << 64) - 1)
            txn_id = int(dut.cpu_resp_txn_id.value) & 0x7
            response_count += 1
            if addr == (miss_addr & ~0x3F):
                assert data == memory.word(miss_addr, 0)
                miss_response_cycle = cycle
                miss_response_txn_id = txn_id
            else:
                assert addr == (hit_addr & ~0x3F), f"unexpected response {addr:#x}"
                assert data == hit_expected
                hit_responses += 1
                hit_response_cycles.append(cycle)
                hit_response_txn_ids.append(txn_id)

        if response_count == requested_hits + 1:
            break

    assert accepted_hits == requested_hits, (
        f"accepted {accepted_hits}/{requested_hits} warm hits"
    )
    assert response_count == requested_hits + 1, (
        f"completed {response_count}/{requested_hits + 1} CPU reads"
    )
    assert miss_response_cycle is not None
    assert miss_response_txn_id is not None
    expected_txn_id = (miss_response_txn_id + 1) & 0x7
    for txn_id in hit_response_txn_ids:
        if expected_txn_id == miss_response_txn_id:
            expected_txn_id = (expected_txn_id + 1) & 0x7
        assert txn_id == expected_txn_id, "bypass response transaction IDs are not ordered"
        assert txn_id != miss_response_txn_id, "bypass reused the active miss transaction ID"
        expected_txn_id = (expected_txn_id + 1) & 0x7
    overlap_accepts = sum(c < miss_response_cycle for c in hit_accept_cycles)
    overlap_responses = sum(c < miss_response_cycle for c in hit_response_cycles)
    window_cycles = cycle - miss_accept_cycle
    metrics = {
        "workload": "one cold L1 miss plus 24 warm reads to another resident line",
        "memory_response_delay_cycles": memory.response_delay,
        "requested_operations": requested_hits + 1,
        "accepted_hit_operations": accepted_hits,
        "window_cycles": window_cycles,
        "operations_per_cycle": (requested_hits + 1) / window_cycles,
        "hit_requests_accepted_before_miss_completion": overlap_accepts,
        "hit_responses_completed_before_miss_completion": overlap_responses,
        "miss_latency_cycles": miss_response_cycle - miss_accept_cycle,
        "all_response_data_checked": True,
    }

    required = os.environ.get("HIT_UNDER_MISS_REQUIRED", "1") == "1"
    if required:
        assert overlap_accepts == requested_hits, metrics
        assert overlap_responses == requested_hits, metrics

    result_path = Path(os.environ.get(
        "HIT_UNDER_MISS_RESULT",
        "reports/rtl_optimization/hit_under_miss.json",
    ))
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"HIT_UNDER_MISS_METRICS={json.dumps(metrics, sort_keys=True)}")


@pytest.mark.asyncio
@case
async def test_hit_under_miss_response_backpressure(coherent_env):
    """A bypass hit response must remain stable while the CPU stalls it."""
    env = await coherent_env(response_delay=2)
    dut, memory = env.dut, env.memory
    hit_addr = 0x0000_3080
    miss_addr = 0x0000_9000
    expected_hit = await env.cpu.access(0, hit_addr)
    memory.response_delay = 48

    async def submit_read(address):
        dut.cpu_req_addr.value = address
        dut.cpu_req_write.value = 0
        dut.cpu_req_wmask.value = 0
        dut.cpu_req_wdata.value = 0
        dut.cpu_req_valid.value = 1
        for _ in range(100):
            await ClockCycles(dut, 1)
            if int(dut.cpu_req_ready.value) & 1:
                dut.cpu_req_valid.value = 0
                return
        pytest.fail(f"request was not accepted: {address:#x}")

    dut.cpu_resp_ready.value = 1
    await submit_read(miss_addr)
    dut.cpu_resp_ready.value = 0
    await submit_read(hit_addr)

    for _ in range(120):
        await ClockCycles(dut, 1)
        if int(dut.cpu_resp_valid.value) & 1:
            break
    else:
        pytest.fail("hit-under-miss response did not become valid")

    held = (
        int(dut.cpu_resp_addr.value) & 0xFFFFFFFF,
        int(dut.cpu_resp_rdata.value) & ((1 << 64) - 1),
        int(dut.cpu_resp_write.value) & 1,
        int(dut.cpu_resp_txn_id.value) & 0x7,
    )
    assert held[:3] == (hit_addr & ~0x3F, expected_hit, 0)
    for _ in range(4):
        await ClockCycles(dut, 1)
        assert int(dut.cpu_resp_valid.value) & 1
        assert (
            int(dut.cpu_resp_addr.value) & 0xFFFFFFFF,
            int(dut.cpu_resp_rdata.value) & ((1 << 64) - 1),
            int(dut.cpu_resp_write.value) & 1,
            int(dut.cpu_resp_txn_id.value) & 0x7,
        ) == held

    dut.cpu_resp_ready.value = 1
    await ClockCycles(dut, 1)
    dut.cpu_resp_ready.value = 0
    for _ in range(120):
        await ClockCycles(dut, 1)
        if int(dut.cpu_resp_valid.value) & 1:
            break
    else:
        pytest.fail("miss response was lost behind a stalled hit response")
    assert (int(dut.cpu_resp_addr.value) & 0xFFFFFFFF) == (miss_addr & ~0x3F)
    assert int(dut.cpu_resp_rdata.value) == memory.word(miss_addr, 0)
    assert (int(dut.cpu_resp_txn_id.value) & 0x7) == ((held[3] - 1) & 0x7)
    assert int(dut.protocol_error.value) == 0
