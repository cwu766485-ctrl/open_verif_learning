"""Seeded reset and AXI error recovery scenarios for the integrated top."""

import asyncio
import os
import random

import pytest
from toffee import ClockCycles
from toffee_test import case

from dv.coverage.checked_cross_evidence import (
    checked_overlap_proof,
    event_reference,
)


CORE0 = 1
MMIO_ADDR = 0x3000_1800


def _seeds():
    count = int(os.environ.get("FULL_SYSTEM_RECOVERY_SEED_COUNT", "4"))
    base = int(os.environ.get("FULL_SYSTEM_RECOVERY_BASE_SEED", "0xE770"), 0)
    if not 1 <= count <= 100:
        raise ValueError("FULL_SYSTEM_RECOVERY_SEED_COUNT must be in [1, 100]")
    return [base + index for index in range(count)]


def _reset_phase(seed):
    """Assign each consecutive four-seed block all reset phases once."""
    base = int(os.environ.get("FULL_SYSTEM_RECOVERY_BASE_SEED", "0xE770"), 0)
    phases = ("ar_stall", "r_gap", "cpu_response", "mmio_request")
    return phases[(seed - base) % len(phases)]


async def _wait_until(dut, predicate, message, timeout=500, pending=None):
    for _ in range(timeout):
        await ClockCycles(dut, 1)
        if predicate():
            return
        if pending is not None and pending.done():
            pending.result()
    d = dut
    observed = {
        name: int(getattr(d, name).value)
        for name in ("cpu_req_valid", "cpu_req_ready", "axi_arvalid",
                     "axi_arready", "axi_rvalid", "axi_rready",
                     "cpu_resp_valid", "cpu_resp_ready", "mmio_req_valid",
                     "mmio_req_ready") if hasattr(d, name)
    }
    raise TimeoutError(f"{message}; pins={observed}")


@pytest.mark.parametrize("seed", _seeds())
@case
async def test_seeded_reset_during_randomized_stall(full_system_env, seed):
    rng = random.Random(seed)
    phase = _reset_phase(seed)
    address = 0x0060_0000 + (seed & 0x3FF) * 0x40 + 8 * rng.randrange(8)
    value = rng.getrandbits(64)
    env = await full_system_env(
        seed=seed,
        axi_options={
            "latency": 1 + seed % 5,
            "ar_stall_period": 2 + seed % 4,
            "r_valid_gap_period": 2 + seed % 3 if phase == "r_gap" else 0,
        },
        mmio_options={
            "request_stall_period": 2 + seed % 4,
            "response_delay": 1,
        },
    )
    env.trace_scenario_id = "RANDOMIZED_RESET_PHASE"
    env.trace_config.update({"recovery_seed": seed, "reset_phase": phase})
    env.trace_operations = [{"kind": "reset_phase", "phase": phase,
                             "cache_address": address, "seed": seed}]
    env.seed_word(address, value)
    env.mmio.words[MMIO_ADDR] = 0xCACE_0000_0000_0000 | seed

    if phase == "mmio_request":
        env.mmio.force_request_stall(32 + seed % 8)
        pending = asyncio.create_task(env.cpu.access(0, MMIO_ADDR))
        await _wait_until(
            env.dut,
            lambda: bool(int(env.dut.mmio_req_valid.value) & CORE0) and
                    not bool(int(env.dut.mmio_req_ready.value) & CORE0),
            "random reset seed did not reach MMIO request stall",
            pending=pending,
        )
        assert not env.mmio.requests
    else:
        response_stall = 80 if phase == "cpu_response" else 0
        pending = asyncio.create_task(
            env.cpu.access(0, address, response_stall_cycles=response_stall)
        )
        if phase == "ar_stall":
            await _wait_until(
                env.dut,
                lambda: bool(int(env.dut.axi_arvalid.value)) and
                        not bool(int(env.dut.axi_arready.value)),
                "random reset seed did not reach AXI AR stall",
                pending=pending,
            )
            assert not env.axi.read_addresses
        elif phase == "r_gap":
            await _wait_until(
                env.dut,
                lambda: bool(env.axi.read_addresses) and
                        not bool(int(env.dut.axi_rvalid.value)),
                "random reset seed did not reach accepted AXI R gap",
                pending=pending,
            )
            assert not env.axi.read_completions
        else:
            await _wait_until(
                env.dut,
                lambda: bool(int(env.dut.cpu_resp_valid.value) & CORE0) and
                        not bool(int(env.dut.cpu_resp_ready.value) & CORE0),
                "random reset seed did not reach CPU response stall",
                pending=pending,
            )

    previous_epoch = env.monitor.reset_epoch
    # Assert reset while VALID is still held. A source may not withdraw an
    # unaccepted MMIO request before reset cancels the transfer.
    env.dut.reset.value = 1
    await ClockCycles(env.dut, 1)
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await env.reset(cycles=2 + seed % 3)
    assert env.monitor.reset_epoch == previous_epoch + 1
    await ClockCycles(env.dut, 5)
    assert int(env.dut.cpu_resp_valid.value) == 0, "stale CPU response after reset"
    assert int(env.dut.mmio_resp_valid.value) == 0, "stale MMIO response after reset"
    if phase == "r_gap":
        assert env.axi.reset_cancelled["reads"] >= 1
    if phase == "mmio_request":
        result = await env.cpu.access(0, MMIO_ADDR)
        assert result == (0xCACE_0000_0000_0000 | seed)
        assert len(env.mmio.completions) == 1
        bin_id = "FS.STRESS.RESET_MMIO_REQUEST_STALL"
        cross_id = "FS.CROSS.STRESS_RESET_MMIO_REQUEST_STALL"
    else:
        result = await env.cpu_access(0, address)
        assert result == value
        phase_bins = {
            "ar_stall": ("RESET_AR_STALL", "RESET_AR_STALL"),
            "r_gap": ("RESET_R_GAP", "RESET_R_GAP"),
            "cpu_response": ("RESET_CPU_RESPONSE_STALL",
                             "RESET_CPU_RESPONSE_STALL"),
        }
        bin_suffix, cross_suffix = phase_bins[phase]
        bin_id = f"FS.STRESS.{bin_suffix}"
        cross_id = f"FS.CROSS.STRESS_{cross_suffix}"
    assert int(env.dut.protocol_error.value) == 0
    assert int(env.dut.fatal_error.value) == 0
    env.coverage.sample_checked_event(bin_id, checked=True)
    env.coverage.sample_checked_cross(cross_id, checked=True)
    env.trace_operations[0]["checker_status"] = "passed"


@pytest.mark.parametrize("seed", _seeds())
@case
async def test_seeded_axi_read_error_beat_and_recovery(full_system_env, seed):
    rng = random.Random(seed ^ 0xA5A5)
    core = rng.randrange(2)
    beat = rng.randrange(8)
    line = 0x0070_0000 + (seed & 0x3FF) * 0x40
    error_address = line + beat * 8
    values = [rng.getrandbits(64) for _ in range(8)]
    env = await full_system_env(
        seed=seed,
        axi_options={
            "latency": 1 + seed % 5,
            "ar_stall_period": 2 + seed % 4,
            "r_valid_gap_period": 2 + seed % 3,
            "read_error_addrs": {error_address},
        },
    )
    env.trace_scenario_id = "CR09_AXI_ERROR_FAIL_STOP_RESET"
    env.trace_config.update({"recovery_seed": seed, "core": core,
                             "error_line": line,
                             "error_beat": beat,
                             "expected_axi_response": 2})
    env.trace_operations = [{"kind": "axi_read_error", "core": core,
                             "line": line,
                             "beat": beat, "address": error_address,
                             "seed": seed}]
    for index, word in enumerate(values):
        env.seed_word(line + index * 8, word)

    event_start = len(env.monitor.events)
    reset_epoch = env.monitor.reset_epoch
    pending = asyncio.create_task(env.cpu.access(core, error_address))
    await _wait_until(
        env.dut,
        lambda: bool(int(env.dut.fatal_error.value)),
        "injected AXI RRESP error did not reach integrated fail-stop",
    )
    # The CPU task and passive monitor run in different Toffee scheduling
    # groups. Let the monitor sample the asserted fail-stop before this test
    # raises reset, otherwise reset can hide the one-cycle fatal edge.
    await ClockCycles(env.dut, 1)
    matching = [error for error in env.axi.errors
                if error["channel"] == "R" and
                error["address"] == error_address and
                error["response"] == 2]
    assert matching, f"seed={seed:#x} beat={beat}: injected beat not observed"
    assert not (int(env.dut.cpu_resp_valid.value) & (1 << core)), (
        "DUT returned a successful CPU response for an AXI error"
    )
    env.dut.reset.value = 1
    await ClockCycles(env.dut, 1)
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await env.reset(cycles=2 + seed % 3)
    env.axi.read_error_addrs.clear()
    assert int(env.dut.fatal_error.value) == 0
    result = await env.cpu_access(core, error_address)
    assert result == values[beat]
    assert int(env.dut.protocol_error.value) == 0

    # The system-level error cross is credited only after tying the injected
    # AXI transaction, fail-stop, reset epoch, and successful retry to actual
    # monitor events from this exact pytest testcase.
    events = env.monitor.events[event_start:]
    failed_request = next(event for event in events
                          if event["source"] == "cpu" and
                          event["event_type"] == "request_accept" and
                          event["core"] == core and
                          event["address"] == error_address)
    read_address = next(event for event in events
                        if event["source"] == "axi" and
                        event["event_type"] == "read_address" and
                        (event["address"] & ~0x3F) == line)
    error_beat = next(event for event in events
                      if event["source"] == "axi" and
                      event["event_type"] == "read_beat" and
                      event["address"] == error_address and
                      event["response"] == 2)
    fatal_event = next(event for event in events
                       if event["source"] == "system" and
                       event["event_type"] == "fatal_error" and
                       event["state"] == "asserted")
    reset_event = next(event for event in events
                       if event["source"] == "system" and
                       event["event_type"] == "reset_assert" and
                       event["state"] == "asserted")
    retry_request = next(event for event in events
                         if event["source"] == "cpu" and
                         event["event_type"] == "request_accept" and
                         event["core"] == core and
                         event["address"] == error_address and
                         event["cycle"] > reset_event["cycle"])
    retry_response = next(event for event in events
                          if event["source"] == "cpu" and
                          event["event_type"] == "response_complete" and
                          event["core"] == core and
                          event["address"] == error_address and
                          event["cycle"] > reset_event["cycle"])
    assert read_address["txn_id"] == error_beat["txn_id"]
    assert read_address["address"] & ~0x3F == line
    assert error_beat["beat"] == beat and error_beat["last"] == int(beat == 7)
    assert failed_request["cycle"] <= read_address["cycle"] <= error_beat["cycle"]
    assert error_beat["cycle"] <= fatal_event["cycle"]
    assert reset_event["reset_epoch"] == reset_epoch
    assert env.monitor.reset_epoch == reset_epoch + 1
    assert retry_response["data"] == values[beat]
    assert not any(event["source"] == "cpu" and
                   event["event_type"] == "response_complete" and
                   event["core"] == core and
                   event["address"] == error_address and
                   failed_request["cycle"] <= event["cycle"] < reset_event["cycle"]
                   for event in events), (
        "failed AXI request produced a CPU response before reset"
    )

    refs = [
        event_reference("failed_cpu_request", "fail_stop", failed_request),
        event_reference("axi_read_address", "refill", read_address),
        event_reference("axi_error_beat", "refill", error_beat),
        event_reference("fatal_error", "fail_stop", fatal_event),
        event_reference("reset_assert", "recovery", reset_event),
        event_reference("retry_cpu_request", "recovery", retry_request),
        event_reference("retry_cpu_response", "recovery", retry_response),
    ]
    proof = checked_overlap_proof(
        checker=("AXI RRESP/ID/beat checker + fail-stop/no-response checker + "
                 "reset-epoch and independent CPU/reference-data checker"),
        checker_pass=True,
        role_endpoints={
            "refill": ("axi_read_address", "axi_error_beat"),
            "fail_stop": ("failed_cpu_request", "fatal_error"),
        },
        event_refs=refs,
        transactions=[
            {"role": "faulted_refill", "protocol": "AXI4-R",
             "txn_id": error_beat["txn_id"], "address": error_address,
             "event_ref_ids": ["axi_read_address", "axi_error_beat"]},
            {"role": "failed_cpu_read", "protocol": "CPU",
             "address": error_address,
             "event_ref_ids": ["failed_cpu_request", "fatal_error"]},
            {"role": "post_reset_retry", "protocol": "CPU",
             "txn_id": retry_response["txn_id"], "address": error_address,
             "event_ref_ids": ["retry_cpu_request", "retry_cpu_response"]},
        ],
        state_transitions=[
            {"event_ref_id": "fatal_error", "state": "asserted"},
            {"event_ref_id": "reset_assert", "state": "asserted"},
        ],
    )
    env.coverage.sample_checked_event(
        "FS.STRESS.AXI_R_ERROR_BEAT_INJECTION", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.STRESS_AXI_ERROR_RECOVERY", checked=True, evidence=proof
    )
    env.trace_operations[0]["checker_status"] = "passed"


@pytest.mark.parametrize("seed", _seeds())
@case
async def test_seeded_reset_during_directory_snoop_pending(full_system_env, seed):
    """CR08: cancel a real shared-line upgrade while its Snoop is pending."""
    rng = random.Random(seed ^ 0xC808)
    requester = rng.randrange(2)
    snoop_target = 1 - requester
    line = 0x0080_0000 + (seed & 0x3FF) * 0x40
    address = line + 8 * rng.randrange(8)
    initial = rng.getrandbits(64)
    attempted_store = rng.getrandbits(64)
    env = await full_system_env(seed=seed, axi_options={"latency": 2})
    env.trace_scenario_id = "CR08_RESET_DIRECTORY_SNOOP_PENDING"
    env.trace_config.update({"recovery_seed": seed, "requester": requester,
                             "snoop_target": snoop_target, "line": line,
                             "address": address})
    env.trace_operations = [{"kind": "shared_upgrade_reset", "seed": seed,
                             "requester": requester, "snoop_target": snoop_target,
                             "address": address,
                             "attempted_store": attempted_store}]
    env.seed_word(address, initial)

    # Build the legal S/S precondition through CPU accesses. The following
    # store therefore requires a Directory Upgrade and peer invalidation.
    assert await env.cpu_access(0, address) == initial
    assert await env.cpu_access(1, address) == initial
    assert env.reference.states[line] == ["S", "S"]

    # Drain the last prelude Snoop pulse before opening the trace window; the
    # wrapper exposes a sampled event pin that may remain high until the next
    # clock edge after a CPU response.
    await ClockCycles(env.dut, 2)
    event_start = len(env.monitor.events)
    old_epoch = env.monitor.reset_epoch
    pending = asyncio.create_task(env.cpu.access(
        requester, address, write=True, data=attempted_store, mask=0xFF
    ))
    target_bit = 1 << snoop_target
    try:
        await _wait_until(
            env.dut,
            lambda: bool(int(env.dut.monitor_snoop_accept_valid.value) & target_bit) and
            (((int(env.dut.monitor_snoop_accept_addr.value) >>
               (32 * snoop_target)) & 0xFFFF_FFC0) == line),
            "CR08 did not reach peer Snoop acceptance",
            pending=pending,
        )
        # The Passive Monitor samples on its own scheduler callback. Advance
        # one edge so the just-observed handshake has a trace reference before
        # asserting reset; the protocol FSM still has not completed the Snoop.
        await ClockCycles(env.dut, 1)
        events_before_reset = env.monitor.events[event_start:]
        accepted_snoop = next(
            event for event in events_before_reset
            if event["source"] == "snoop" and
            event["event_type"] == "accept" and
            event["core"] == snoop_target and
            event["address"] & ~0x3F == line
        )
        directory_request = next(
            event for event in events_before_reset
            if event["source"] == "directory" and
            event["event_type"] == "request_accept" and
            event["address"] & ~0x3F == line and
            event["opcode"] == 0b010
        )
        assert accepted_snoop["txn_id"] == directory_request["txn_id"]
        # Reset on the next active edge, before the snoop response or grant
        # can complete the upgrade. The write must remain architecturally
        # uncommitted and must not leak a successful CPU response.
        assert not any(event["source"] == "snoop" and
                       event["event_type"] == "response" and
                       event.get("txn_id") == accepted_snoop["txn_id"]
                       for event in events_before_reset)
        assert not any(event["source"] == "directory" and
                       event["event_type"] == "grant_accept" and
                       event.get("txn_id") == directory_request["txn_id"]
                       for event in events_before_reset)
        assert not (int(env.dut.cpu_resp_valid.value) & (1 << requester))

        env.dut.reset.value = 1
        await ClockCycles(env.dut, 1)
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await env.reset(cycles=2)
        assert env.monitor.reset_epoch == old_epoch + 1
        assert int(env.dut.protocol_error.value) == 0
        assert int(env.dut.fatal_error.value) == 0
        assert await env.cpu.access(requester, address) == env.reference.word(address)

        events = env.monitor.events[event_start:]
        reset_event = next(event for event in events
                           if event["source"] == "system" and
                           event["event_type"] == "reset_assert" and
                           event["state"] == "asserted")
        retry_request = next(event for event in events
                             if event["source"] == "cpu" and
                             event["event_type"] == "request_accept" and
                             event["core"] == requester and
                             event["address"] == address and
                             event["cycle"] > reset_event["cycle"])
        retry_response = next(event for event in events
                              if event["source"] == "cpu" and
                              event["event_type"] == "response_complete" and
                              event["core"] == requester and
                              event["address"] == address and
                              event["cycle"] > reset_event["cycle"])
        assert accepted_snoop["cycle"] < reset_event["cycle"]
        assert retry_response["data"] == initial
        assert not any(event["source"] == "cpu" and
                       event["event_type"] == "response_complete" and
                       event["core"] == requester and
                       event["address"] == address and
                       event["cycle"] < reset_event["cycle"]
                       for event in events)

        refs = [
            event_reference("upgrade_request", "pending_upgrade", directory_request),
            event_reference("snoop_accept", "snoop", accepted_snoop),
            event_reference("reset_assert", "pending_upgrade", reset_event),
            event_reference("snoop_reset_assert", "snoop", reset_event),
            event_reference("retry_request", "recovery", retry_request),
            event_reference("retry_response", "recovery", retry_response),
        ]
        proof = checked_overlap_proof(
            checker=("Directory Upgrade/Snoop transaction-ID matcher + no-grant/no-response "
                     "before reset + reset-epoch and independent data checker"),
            checker_pass=True,
            role_endpoints={
                "pending_upgrade": ("upgrade_request", "reset_assert"),
                "snoop": ("snoop_accept", "snoop_reset_assert"),
            },
            event_refs=refs,
            transactions=[
                {"role": "cancelled_upgrade", "protocol": "MESI-Directory",
                 "txn_id": directory_request["txn_id"], "address": line,
                 "event_ref_ids": ["upgrade_request", "snoop_accept"]},
                {"role": "post_reset_retry", "protocol": "CPU",
                 "txn_id": retry_response["txn_id"], "address": address,
                 "event_ref_ids": ["retry_request", "retry_response"]},
            ],
            state_transitions=[
                {"event_ref_id": "reset_assert", "state": "asserted"},
            ],
        )
        env.coverage.sample_checked_cross(
            "FS.CROSS.STRESS_RESET_DIRECTORY_SNOOP_PENDING",
            checked=True, evidence=proof,
        )
        env.trace_operations[0]["checker_status"] = "passed"
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        env.dut.cpu_req_valid.value = 0
        env.dut.cpu_resp_ready.value = 0
