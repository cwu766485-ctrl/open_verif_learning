"""Replay one saved full-system CPU transaction trace on request."""

import os

import pytest
from toffee_test import case

from dv.sequences.full_system_replay import load_trace, replay_cpu_transactions


@case
async def test_replay_saved_full_system_trace(full_system_env):
    trace_path = os.environ.get("FULL_SYSTEM_REPLAY_TRACE")
    if not trace_path:
        pytest.skip("set FULL_SYSTEM_REPLAY_TRACE to replay a saved trace")
    run, events = load_trace(
        trace_path, test_id=os.environ.get("FULL_SYSTEM_REPLAY_TEST_ID") or None
    )
    if run.get("test_status") != "passed":
        raise AssertionError(
            f"selected trace source did not pass: {run.get('test_status')} "
            f"({run.get('test_id')})"
        )
    agents = run.get("configuration", {}).get("agents", {})
    env = await full_system_env(
        seed=run.get("seed"),
        axi_options=agents.get("axi"), mmio_options=agents.get("mmio")
    )
    env.trace_scenario_id = "TRACE_REPLAY"
    env.trace_config = {"source_trace": str(trace_path),
                        "source_test_id": run.get("test_id"),
                        "source_seed": run.get("seed")}
    replayed = await replay_cpu_transactions(env, run, events)
    expected = sum(event.get("source") == "cpu_driver" and
                   event.get("event_type") == "transaction" for event in events)
    assert replayed == expected
