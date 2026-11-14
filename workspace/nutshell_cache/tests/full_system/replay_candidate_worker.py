"""One fresh RTL simulation for a replay-closure candidate trace."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from toffee_test import case


@case
async def test_replay_candidate(full_system_env):
    input_path = Path(os.environ["FULL_SYSTEM_REPLAY_WORKER_INPUT"])
    output_path = Path(os.environ["FULL_SYSTEM_REPLAY_WORKER_OUTPUT"])
    seed = int(os.environ["FULL_SYSTEM_REPLAY_CLOSURE_SEED"], 0)
    trace_input = json.loads(input_path.read_text(encoding="utf-8"))
    operations = trace_input["operations"]
    label = trace_input["label"]
    line = 0x0100_0000 + (seed & 0xFF) * 0x40
    address = line + 8 * ((seed >> 8) & 0x7)
    initial = 0x1020_3040_5060_7080 ^ seed
    owner_data = 0xA1B2_C3D4_E5F6_0718 ^ (seed << 1)

    env = await full_system_env(axi_options={"latency": 2}, seed=seed)
    env.trace_scenario_id = "CONTROLLED_CHECKER_FAILURE_REPLAY"
    env.trace_config.update({
        "replay_label": label,
        "checker_fault": "flip_expected_data_bit_0",
    })
    env.trace_operations = [dict(operation) for operation in operations]
    env.seed_word(address, initial)
    env.seed_word(line + 0x1000, initial ^ 0x55AA)
    env.seed_word(line + 0x2000, initial ^ 0xAA55)

    failure = None
    failure_event_ref = None
    for operation in operations:
        if operation["kind"] == "cpu_write":
            await env.cpu_access(
                operation["core"], operation["address"], write=True,
                data=operation["data"], mask=operation["mask"]
            )
            continue

        if operation.get("failure_trigger"):
            owner_state = env.reference.states[line][0]
            assert owner_state == "M", (
                f"legal owner prelude did not reach M: {owner_state}"
            )
            event_start = len(env.monitor.events)
            actual = await env.cpu_access(operation["core"], operation["address"])
            event_index, snoop_event = next((index, event) for index, event in
                enumerate(env.monitor.events[event_start:], start=event_start)
                if event["source"] == "snoop" and
                event["event_type"] == "accept" and
                event.get("core") == 0 and
                (event.get("address", 0) & ~0x3F) == line
            )
            assert actual == owner_data, (
                f"independent model expected {owner_data:#x}, got {actual:#x}"
            )
            faulty_expected = owner_data ^ 1
            try:
                assert actual == faulty_expected, (
                    f"injected checker mismatch: actual={actual:#x} "
                    f"expected={faulty_expected:#x}"
                )
            except AssertionError as error:
                failure = {
                    "kind": "injected_checker_data_mismatch",
                    "message": str(error),
                    "address": operation["address"],
                    "actual": actual,
                    "faulty_expected": faulty_expected,
                    "owner_snoop_cycle": snoop_event["cycle"],
                    "owner_snoop_txn_id": snoop_event.get("txn_id"),
                }
                failure_event_ref = {
                    "event_index": event_index,
                    "source": snoop_event["source"],
                    "event_type": snoop_event["event_type"],
                    "cycle": snoop_event["cycle"],
                    "txn_id": snoop_event.get("txn_id"),
                    "address": snoop_event["address"],
                    "core": snoop_event["core"],
                }
            continue

        await env.cpu_access(operation["core"], operation["address"])

    assert failure is not None, "controlled checker fault was not detected"
    assert failure_event_ref is not None, "owner snoop monitor event was not observed"
    repo_root = Path(__file__).resolve().parents[2]
    source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "source_sha": source_sha,
        "seed": seed,
        "label": label,
        "operation_ids": [operation["id"] for operation in operations],
        "checker_failure_detected": True,
        "failure": failure,
        "failure_event_ref": failure_event_ref,
        "monitor_events": env.trace_records(),
        "worker_test": "test_replay_candidate: passed",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
