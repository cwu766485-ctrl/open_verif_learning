"""System-level checker-failure capture, replay, and RTL trace reduction."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dv.sequences.trace_minimizer import minimize_operations


def _scenario(seed: int):
    line = 0x0100_0000 + (seed & 0xFF) * 0x40
    address = line + 8 * ((seed >> 8) & 0x7)
    initial = 0x1020_3040_5060_7080 ^ seed
    owner_data = 0xA1B2_C3D4_E5F6_0718 ^ (seed << 1)
    noise_data = 0x8877_6655_4433_2211 ^ seed
    operations = [
        {"id": "owner_store", "kind": "cpu_write", "core": 0,
         "address": address, "data": owner_data, "mask": 0xFF,
         "required_prelude": True},
        {"id": "independent_read", "kind": "cpu_read", "core": 1,
         "address": line + 0x1000},
        {"id": "remote_owner_read", "kind": "cpu_read", "core": 1,
         "address": address, "failure_trigger": True},
        {"id": "independent_write", "kind": "cpu_write", "core": 0,
         "address": line + 0x2000, "data": noise_data, "mask": 0xFF},
        {"id": "independent_read_after", "kind": "cpu_read", "core": 0,
         "address": line + 0x1000},
    ]
    return line, address, initial, owner_data, operations


def _signature(payload: dict) -> dict:
    failure = payload["failure"]
    return {key: failure[key] for key in
            ("kind", "address", "actual", "faulty_expected")}


def _run_candidate(operations, *, seed, label, work_dir, index,
                   expected_signature=None):
    ids = [operation["id"] for operation in operations]
    if "owner_store" not in ids or "remote_owner_read" not in ids:
        return {"accepted": False, "reason": "required prelude/trigger absent",
                "operation_ids": ids}

    candidate_path = work_dir / f"candidate_{index}.json"
    output_path = work_dir / f"result_{index}.json"
    coverage_path = work_dir / f"coverage_{index}.json"
    trace_path = work_dir / f"trace_{index}.jsonl"
    candidate_path.write_text(json.dumps({"operations": operations,
                                         "label": label}), encoding="utf-8")
    child_env = os.environ.copy()
    child_env.update({
        "FULL_SYSTEM_REPLAY_WORKER_INPUT": str(candidate_path),
        "FULL_SYSTEM_REPLAY_WORKER_OUTPUT": str(output_path),
        "FULL_SYSTEM_REPLAY_CLOSURE_SEED": str(seed),
        "FULL_SYSTEM_COVERAGE_OUTPUT": str(coverage_path),
        "FULL_SYSTEM_TRACE_OUTPUT": str(trace_path),
    })
    worker = Path(__file__).with_name("replay_candidate_worker.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         f"{worker}::test_replay_candidate"],
        cwd=Path(__file__).resolve().parents[2], env=child_env,
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0 or not output_path.is_file():
        raise AssertionError(
            f"RTL replay candidate {label!r} failed to complete\n"
            f"exit={result.returncode}\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if not payload.get("checker_failure_detected"):
        raise AssertionError(f"candidate {label!r} did not reproduce injected failure")
    signature = _signature(payload)
    if expected_signature is not None and signature != expected_signature:
        raise AssertionError(
            f"candidate {label!r} changed failure signature: {signature} != "
            f"{expected_signature}"
        )
    return {
        "accepted": True,
        "label": label,
        "operation_ids": ids,
        "failure_signature": signature,
        "failure_event_ref": payload["failure_event_ref"],
        "worker_test": payload["worker_test"],
        "payload": payload,
    }


def test_controlled_failure_replay_and_legal_prelude_minimization():
    seed = int(os.environ.get("FULL_SYSTEM_REPLAY_CLOSURE_SEED", "0xF1A1"), 0)
    _line, _address, _initial, _owner_data, operations = _scenario(seed)
    repo_root = Path(__file__).resolve().parents[2]
    attempts = []

    with tempfile.TemporaryDirectory(prefix="cache-replay-closure-") as temp:
        work_dir = Path(temp)
        original = _run_candidate(
            operations, seed=seed, label="initial_failure", work_dir=work_dir,
            index=0,
        )
        baseline_signature = original["failure_signature"]
        attempts.append(original)

        replay = _run_candidate(
            operations, seed=seed, label="same_seed_replay", work_dir=work_dir,
            index=1, expected_signature=baseline_signature,
        )
        if replay["failure_event_ref"]["cycle"] != \
                original["failure_event_ref"]["cycle"]:
            raise AssertionError("same-seed replay changed the failure event cycle")
        attempts.append(replay)

        def reproduces(candidate):
            attempt = _run_candidate(
                candidate, seed=seed, label=f"minimize_{len(attempts)}",
                work_dir=work_dir, index=len(attempts),
                expected_signature=baseline_signature,
            )
            attempts.append(attempt)
            return attempt["accepted"]

        minimized = minimize_operations(operations, reproduces)
        minimized_ids = [operation["id"]
                         for operation in minimized["operations"]]
        if minimized_ids != ["owner_store", "remote_owner_read"]:
            raise AssertionError(f"unexpected minimized trace: {minimized_ids}")
        if minimized["required_prelude_count"] != 1:
            raise AssertionError("minimizer did not retain the legal owner prelude")
        minimized_replay = attempts[-1]

        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        output = Path(os.environ.get(
            "FULL_SYSTEM_REPLAY_CLOSURE_OUTPUT",
            "reports/full_system/replay_closure/controlled_checker_failure.json",
        ))
        if not output.is_absolute():
            output = repo_root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 2,
            "source_sha": head,
            "scenario": "M Owner remote read with injected checker expected-data bit flip",
            "seed": seed,
            "failure_is_product_rtl_bug": False,
            "failure_signature": baseline_signature,
            "same_seed_replay_matches": True,
            "same_seed_failure_cycle_matches": True,
            "minimization": {
                "original_count": minimized["original_count"],
                "minimized_count": minimized["minimized_count"],
                "attempts": minimized["attempts"],
                "required_prelude_count": minimized["required_prelude_count"],
                "retained_operation_ids": minimized_ids,
                "candidate_replays_use_rtl": True,
                "final_minimized_trace_replayed_on_rtl": True,
            },
            "operations": operations,
            "minimized_operations": minimized["operations"],
            "initial_failure_event_ref": original["failure_event_ref"],
            "same_seed_replay_event_ref": replay["failure_event_ref"],
            "minimized_failure_event_ref":
                minimized_replay["failure_event_ref"],
            "original_trace_monitor_events":
                original["payload"]["monitor_events"],
            "minimized_trace_monitor_events":
                minimized_replay["payload"]["monitor_events"],
            "candidate_replay_summary": [
                {key: attempt[key] for key in
                 ("accepted", "label", "operation_ids", "reason",
                  "failure_signature", "failure_event_ref", "worker_test")
                 if key in attempt}
                for attempt in attempts
            ],
            "limitations": [
                "The expected-data bit flip is injected in the checker; DUT data, reference model, and monitors are not modified.",
                "Every dependency-valid delta candidate is replayed on a fresh RTL simulation; candidates lacking the required legal prelude or failure trigger are rejected before simulator launch.",
                "The reduction preserves transaction order and the legal M-owner prelude; it does not constrain unrelated simulator cycle interleavings.",
            ],
        }
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"RTL checker failure replay/minimization evidence: {output}")
