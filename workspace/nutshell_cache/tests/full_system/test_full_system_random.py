"""Seed-reproducible legal full-system random regression."""

import os

import pytest
from toffee_test import case

from dv.sequences.full_system_sequences import (
    FullSystemRandomSequence,
    RandomConfig,
)


def _seeds():
    explicit = os.environ.get("FULL_SYSTEM_RANDOM_SEEDS")
    if explicit:
        return [int(token.strip(), 0) for token in explicit.split(",")
                if token.strip()]
    count = int(os.environ.get("FULL_SYSTEM_RANDOM_SEED_COUNT", "10"))
    base = int(os.environ.get("FULL_SYSTEM_RANDOM_BASE_SEED", "0xA11CE"), 0)
    if not 1 <= count <= 500:
        raise ValueError("FULL_SYSTEM_RANDOM_SEED_COUNT must be in [1, 500]")
    return [base + index * 0x9E3779B9 for index in range(count)]


@pytest.mark.parametrize("seed", _seeds())
@case
async def test_seeded_full_system_coherence(full_system_env, seed):
    operations = int(os.environ.get("FULL_SYSTEM_RANDOM_OPERATIONS", "100"))
    if not 1 <= operations <= 2000:
        raise ValueError("FULL_SYSTEM_RANDOM_OPERATIONS must be in [1, 2000]")
    address_count = int(os.environ.get("FULL_SYSTEM_RANDOM_ADDRESS_COUNT", "12"))
    env = await full_system_env(
        seed=seed,
        axi_options={"latency": 2 + seed % 9,
                     "read_reorder_window": 6 + seed % 5},
        mmio_options={"response_delay": seed % 4},
    )
    env.trace_scenario_id = "FULL_SYSTEM_RANDOM"
    sequence = FullSystemRandomSequence(RandomConfig(
        seed=seed, operations=operations, address_count=address_count,
        write_probability=0.4, pair_probability=0.15,
        response_stall_max=2,
    ))
    env.trace_config = {
        "agents": {
            "axi": {"latency": 2 + seed % 9,
                    "read_reorder_window": 6 + seed % 5},
            "mmio": {"response_delay": seed % 4},
        },
        "operations": operations,
        "address_count": address_count,
        "write_probability": sequence.config.write_probability,
        "pair_probability": sequence.config.pair_probability,
        "response_stall_max": sequence.config.response_stall_max,
        "axi_latency": 2 + seed % 9,
        "axi_read_reorder_window": 6 + seed % 5,
        "mmio_response_delay": seed % 4,
    }
    try:
        await sequence.run(env)
    finally:
        env.trace_operations = list(sequence.history)
    for core in (0, 1):
        assert env.coverage.bins[f"FS.CPU.READ.CORE{core}"] > 0
        assert env.coverage.bins[f"FS.CPU.WRITE.CORE{core}"] > 0
    for transition in ("I_TO_E", "I_TO_S", "I_TO_M", "E_TO_M", "E_TO_S",
                       "E_TO_I", "S_TO_M", "S_TO_I", "M_TO_S", "M_TO_I"):
        assert env.coverage.bins[f"FS.MESI.{transition}"] > 0
    assert int(env.dut.protocol_error.value) == 0
