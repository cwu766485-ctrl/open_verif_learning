"""Seeded reset and AXI error recovery scenarios for the integrated top."""

import asyncio
import os
import random

import pytest
from toffee import ClockCycles
from toffee_test import case


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
    env.trace_scenario_id = "RANDOMIZED_AXI_READ_ERROR_RECOVERY"
    env.trace_config.update({"recovery_seed": seed, "error_line": line,
                             "error_beat": beat,
                             "expected_axi_response": 2})
    env.trace_operations = [{"kind": "axi_read_error", "line": line,
                             "beat": beat, "address": error_address,
                             "seed": seed}]
    for index, word in enumerate(values):
        env.seed_word(line + index * 8, word)

    pending = asyncio.create_task(env.cpu.access(0, error_address))
    await _wait_until(
        env.dut,
        lambda: bool(int(env.dut.fatal_error.value)),
        "injected AXI RRESP error did not reach integrated fail-stop",
    )
    matching = [error for error in env.axi.errors
                if error["channel"] == "R" and
                error["address"] == error_address and
                error["response"] == 2]
    assert matching, f"seed={seed:#x} beat={beat}: injected beat not observed"
    assert not (int(env.dut.cpu_resp_valid.value) & CORE0), (
        "DUT returned a successful CPU response for an AXI error"
    )
    env.dut.reset.value = 1
    await ClockCycles(env.dut, 1)
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await env.reset(cycles=2 + seed % 3)
    env.axi.read_error_addrs.clear()
    assert int(env.dut.fatal_error.value) == 0
    result = await env.cpu_access(0, error_address)
    assert result == values[beat]
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event(
        "FS.STRESS.AXI_R_ERROR_BEAT_INJECTION", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.STRESS_AXI_ERROR_RECOVERY", checked=True
    )
    env.trace_operations[0]["checker_status"] = "passed"
