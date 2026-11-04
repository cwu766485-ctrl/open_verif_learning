"""Seeded full-system traffic mixing the four external verification roles."""

import asyncio
import os
import random

import pytest
from toffee import ClockCycles
from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest


def _mixed_seeds():
    count = int(os.environ.get("FULL_SYSTEM_MIXED_SEED_COUNT", "4"))
    base = int(os.environ.get("FULL_SYSTEM_MIXED_BASE_SEED", "0xD100"), 0)
    if not 1 <= count <= 200:
        raise ValueError("FULL_SYSTEM_MIXED_SEED_COUNT must be in [1, 200]")
    return [base + index for index in range(count)]


@pytest.mark.parametrize("seed", _mixed_seeds())
@case
async def test_seeded_cpu_mmio_apb_axi_overlap(full_system_env, seed):
    """Run checked cache misses beside MMIO, APB sampling and AXI stalls.

    The AXI memory role injects ARREADY backpressure and legal source-side
    RVALID gaps. The integrated product currently keeps RREADY asserted, so
    this test does not label source pacing as receiver backpressure.
    """
    rng = random.Random(seed)
    env = await full_system_env(
        seed=seed,
        axi_options={
            "latency": 24 + seed % 5,
            "ar_stall_period": 2,
            "aw_stall_period": 2 + seed % 3,
            "w_stall_period": 3 + seed % 3,
            "r_valid_gap_period": 3 + seed % 2,
            "read_reorder_window": 2,
        },
        mmio_options={
            "request_stall_period": 2 + seed % 3,
            "response_delay": 64,
            "response_stall_period": 3 + seed % 3,
        },
    )
    env.trace_scenario_id = "SEEDED_MIXED_CPU_MMIO_APB_AXI"
    rounds = int(os.environ.get("FULL_SYSTEM_MIXED_ROUNDS", "6"))
    if not 1 <= rounds <= 2000:
        raise ValueError("FULL_SYSTEM_MIXED_ROUNDS must be in [1, 2000]")
    env.trace_config.update({"mixed_random_seed": seed, "rounds": rounds})

    mmio_addrs = (0x3000_1200, 0x3000_1208)
    for index, address in enumerate(mmio_addrs):
        env.mmio.words[address] = 0xA500_0000_0000_0000 | (seed << 8) | index

    checked_rounds = []
    # Keep the generated prefix available even if a checker fails mid-seed.
    # The seed plus this operation list is sufficient to replay the stimulus.
    env.trace_operations = checked_rounds
    for operation in range(rounds):
        cache_core = (operation + seed) & 1
        mmio_core = 1 - cache_core
        line = 0x0020_0000 + ((seed & 0xFF) * 0x1000) + operation * 0x40
        word_addr = line + 8 * rng.randrange(8)
        initial = rng.getrandbits(64)
        env.seed_word(word_addr, initial)
        write = bool(rng.getrandbits(1))
        write_data = rng.getrandbits(64) if write else 0
        write_mask = rng.randrange(1, 0x100) if write else 0xFF
        cache_request = CpuRequest(word_addr, write, write_data, write_mask)

        mmio_addr = mmio_addrs[operation & 1]
        mmio_write = bool(rng.getrandbits(1))
        mmio_data = rng.getrandbits(64) if mmio_write else 0
        mmio_mask = rng.randrange(1, 0x100) if mmio_write else 0xFF
        mmio_old = env.mmio.words[mmio_addr]
        mmio_expected = 0 if mmio_write else mmio_old
        mmio_request = CpuRequest(mmio_addr, mmio_write, mmio_data, mmio_mask)

        requests = [None, None]
        requests[cache_core] = cache_request
        requests[mmio_core] = mmio_request
        expected_cache, _ = env.reference.predict(
            cache_core, word_addr, write=write, write_data=write_data,
            write_mask=write_mask,
        )
        transition_start = len(env.reference.transitions)
        event_start = len(env.monitor.events)
        ar_start = len(env.axi.read_addresses)
        group = env.cpu.request_group
        response_stall = rng.randrange(1, 4)

        operation_record = {
            "operation": operation,
            "cache_core": cache_core,
            "cache_address": word_addr,
            "cache_write": write,
            "cache_data": write_data,
            "cache_mask": write_mask,
            "cache_initial_data": initial,
            "mmio_core": mmio_core,
            "mmio_address": mmio_addr,
            "mmio_write": mmio_write,
            "mmio_data": mmio_data,
            "mmio_mask": mmio_mask,
            "mmio_initial_data": mmio_old,
            "response_stall_cycles": response_stall,
        }
        checked_rounds.append(operation_record)

        async def apb_read_during_this_refill():
            for _ in range(300):
                await ClockCycles(env.dut, 1)
                if len(env.axi.read_addresses) > ar_start:
                    break
            else:
                raise TimeoutError("mixed random cache miss did not reach AXI AR")
            # This read is sampled while the newly accepted refill is active.
            value = await env.apb.read(env.apb.CSR_MISS_COUNT)
            return value

        cpu_task = asyncio.create_task(env.cpu.access_pair(
            requests[0], requests[1], response_stall_cycles=response_stall,
        ))
        apb_task = asyncio.create_task(apb_read_during_this_refill())
        results = await cpu_task
        apb_misses = await apb_task

        cache_result = results[cache_core]
        mmio_result = results[mmio_core]
        if not write and cache_result != expected_cache:
            raise AssertionError(
                f"seed={seed:#x} op={operation}: cache data "
                f"{cache_result:#x} != model {expected_cache:#x}"
            )
        if mmio_result != mmio_expected:
            raise AssertionError(
                f"seed={seed:#x} op={operation}: MMIO data "
                f"{mmio_result:#x} != model {mmio_expected:#x}"
            )

        env.reference.observe(
            cache_core, word_addr, write=write, write_data=write_data,
            write_mask=write_mask, response_data=cache_result,
        )
        observed_commits = env._check_observed_commits(line, event_start)
        cache_txn = next(
            txn for txn in env.cpu.transactions
            if txn["request_group"] == group and txn["core"] == cache_core
        )
        env._credit_cpu(
            cache_core, write, word_addr, cache_txn["accepted_cycle"],
            cache_txn["response_cycle"], transition_start, observed_commits,
        )

        mmio_txn = next(
            txn for txn in env.cpu.transactions
            if txn["request_group"] == group and txn["core"] == mmio_core
        )
        assert mmio_txn["response_cycle"] > mmio_txn["accepted_cycle"]
        request_record = env.mmio.requests[-1]
        completion_record = env.mmio.completions[-1]
        assert request_record["addr"] == mmio_addr
        assert request_record["write"] == int(mmio_write)
        assert request_record["mask"] == (mmio_mask if mmio_write else 0)
        assert completion_record["data"] == mmio_expected
        if mmio_write:
            expected_after = env.mmio._merge(mmio_old, mmio_data, mmio_mask)
            assert env.mmio.words[mmio_addr] == expected_after

        events = env.monitor.events[event_start:]
        ar = next(event for event in events
                  if event["source"] == "axi" and
                  event["event_type"] == "read_address" and
                  event["address"] == line)
        last_beat = next(event for event in events
                         if event["source"] == "axi" and
                         event["event_type"] == "read_beat" and
                         event["address"] == line + 56 and event["last"])
        mmio_accept = next(event for event in events
                           if event["source"] == "mmio" and
                           event["event_type"] == "request_accept" and
                           event["address"] == mmio_addr)
        mmio_complete = next(event for event in events
                             if event["source"] == "mmio" and
                             event["event_type"] == "response_complete" and
                             event["address"] == mmio_addr)
        apb_event = next(event for event in events
                         if event["source"] == "apb" and
                         event["event_type"] == "access_complete" and
                         event["address"] == env.apb.CSR_MISS_COUNT)
        assert (mmio_accept["cycle"] < ar["cycle"] < apb_event["cycle"] <
                last_beat["cycle"] < mmio_complete["cycle"])
        assert apb_misses == operation + 1

        # Confirm the gray-box stream has the lifecycle evidence used by the
        # checker: observed metadata transition, MSHR allocation/retirement,
        # L2 refill boundary, and AXI stall/gap evidence.
        assert any(event["source"] == "l1" and
                   event["event_type"] == "metadata_commit" and
                   event["address"] & ~0x3F == line for event in events)
        assert any(event["source"] == "mshr" and
                   event["event_type"] == "allocate" for event in events)
        assert any(event["source"] == "l2" and
                   event["event_type"] == "refill_start" for event in events)
        assert env.axi.stalls["R"] == 0

        # The MMIO request has its own model and response checker. MMIO is not
        # part of the cache data scoreboard and must not allocate cache state.
        env.coverage.sample_checked_cpu(
            mmio_core, mmio_write, accepted=True, completed=True,
        )
        assert not any(
            event["source"] == "directory" and
            event["event_type"] == "request_accept" and
            event["address"] == mmio_addr for event in events
        )
        env.coverage.sample_checked_event(
            "FS.STRESS.MIXED_CPU_MMIO_APB_AXI", checked=True,
        )
        env.coverage.sample_checked_cross(
            "FS.CROSS.MIXED_CPU_MMIO_APB_AXI", checked=True,
        )
        env.coverage.sample_checked_event("FS.APB.READ_DURING_AXI", checked=True)
        env.coverage.sample_checked_cross("FS.CROSS.APB_WITH_AXI_TRAFFIC",
                                          checked=True)
        operation_record["apb_miss_count"] = apb_misses
        operation_record["checker_status"] = "passed"

    assert len(env.axi.read_addresses) - len(env.axi.read_completions) == 0
    assert env.axi.stalls["AR"] > 0, "randomized AR backpressure was not exercised"
    assert env.axi.valid_gaps["R"] > 0, "randomized R source gaps were not exercised"
    assert env.cpu.response_stall_cycles[0] + env.cpu.response_stall_cycles[1] > 0
    assert int(env.dut.protocol_error.value) == 0
