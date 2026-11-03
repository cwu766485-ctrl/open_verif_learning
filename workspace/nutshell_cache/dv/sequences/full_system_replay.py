"""Replay completed CPU transactions from the normalized full-system trace."""

import json
from collections import defaultdict
from pathlib import Path

from dv.agents.coherent_cpu_agent import CpuRequest


def load_trace(path, *, test_id=None):
    """Load one run header and its events from a full-system JSONL trace."""
    path = Path(path)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    runs = [record for record in records if record.get("record_type") == "run"]
    if test_id is not None:
        runs = [record for record in runs if record.get("test_id") == test_id]
    if not runs:
        raise ValueError(f"no run record found in trace {path}")
    run = runs[0]
    events = [record for record in records
              if record.get("record_type") == "event" and
              record.get("test_id") == run.get("test_id")]
    return run, events


async def replay_cpu_transactions(env, run, events):
    """Replay saved CPU request groups and check every original response.

    This replays request contents and grouping. It preserves configured memory
    and MMIO latency plus CPU response stalls, but simulator cycle scheduling
    is naturally re-evaluated by the current build.
    """
    for address, value in run.get("initial_backing_memory", {}).items():
        env.seed_word(int(address, 0), int(value, 0))

    transactions = [event for event in events
                    if event.get("source") == "cpu_driver" and
                    event.get("event_type") == "transaction"]
    if not transactions:
        raise ValueError("trace contains no completed CPU driver transactions")
    groups = defaultdict(list)
    for transaction in transactions:
        groups[transaction["request_group"]].append(transaction)

    replayed = 0
    for group_id in sorted(groups):
        group = sorted(groups[group_id], key=lambda item: item["core"])
        if len(group) > 2 or len({item["core"] for item in group}) != len(group):
            raise ValueError(f"invalid CPU request group {group_id}")
        reqs = [None, None]
        for item in group:
            payload = item["payload"]
            reqs[item["core"]] = CpuRequest(
                addr=item["address"], write=bool(payload["write"]),
                data=payload["write_data"], mask=payload["write_mask"]
            )

        if len(group) == 1:
            item = group[0]
            request = reqs[item["core"]]
            stall = item["payload"].get("response_stall_cycles", 0)
            if request.addr < 0x3000_0000:
                result = await env.cpu_access(
                    item["core"], request.addr, write=request.write,
                    data=request.data, mask=request.mask,
                    response_stall_cycles=stall
                )
            else:
                result = await env.cpu.access(
                    item["core"], request.addr, write=request.write,
                    data=request.data, mask=request.mask,
                    response_stall_cycles=stall
                )
            if result != item["payload"]["response_data"]:
                raise AssertionError(
                    f"replay response mismatch in group {group_id}: "
                    f"actual={result:#x}, trace={item['payload']['response_data']:#x}"
                )
            replayed += 1
            continue

        if all(request.addr < 0x3000_0000 for request in reqs if request):
            if reqs[0] and reqs[1] and \
                    (reqs[0].addr & ~0x3F) == (reqs[1].addr & ~0x3F):
                raise ValueError(
                    f"same-line dual request group {group_id} needs an explicit "
                    "serialization scenario to replay its expected ordering"
                )
            delays = {item["core"]: item["payload"].get(
                "request_delay_cycles", 0) for item in group}
            stall = max(item["payload"].get("response_stall_cycles", 0)
                        for item in group)
            results = await env.cpu_access_pair(
                reqs[0], reqs[1], request_delay_cycles=delays,
                response_stall_cycles=stall
            )
        else:
            transition_start = len(env.reference.transitions)
            event_start = len(env.monitor.events)
            expected_cache = {}
            for item in group:
                request = reqs[item["core"]]
                if request.addr < 0x3000_0000:
                    expected_cache[item["core"]] = env.reference.predict(
                        item["core"], request.addr, write=request.write,
                        write_data=request.data, write_mask=request.mask
                    )[0]
            results = await env.cpu.access_pair(
                reqs[0], reqs[1],
                request_delay_cycles={item["core"]: item["payload"].get(
                    "request_delay_cycles", 0) for item in group},
                response_stall_cycles=max(
                    item["payload"].get("response_stall_cycles", 0)
                    for item in group
                )
            )
            # The mixed cache/MMIO path has no shared architectural state.
            # Cacheable reads/writes are still checked against the independent
            # model; the MMIO agent checks its own device model and response.
            for item in group:
                core = item["core"]
                request = reqs[core]
                result = results[core]
                if request.addr < 0x3000_0000:
                    if not request.write and result != expected_cache[core]:
                        raise AssertionError(
                            f"replay cache response mismatch at {request.addr:#x}: "
                            f"actual={result:#x}, "
                            f"expected={expected_cache[core]:#x}"
                        )
                    env.reference.observe(
                        core, request.addr, write=request.write,
                        write_data=request.data, write_mask=request.mask,
                        response_data=result
                    )
                    observed = env._check_observed_commits(
                        request.addr & ~0x3F, event_start
                    )
                    txn = next(txn for txn in reversed(env.cpu.transactions)
                               if txn["request_group"] ==
                               env.cpu.request_group - 1 and txn["core"] == core)
                    env._credit_cpu(core, request.write, request.addr,
                                    txn["accepted_cycle"], txn["response_cycle"],
                                    transition_start, observed)
                if result != item["payload"]["response_data"]:
                    raise AssertionError(
                        f"replay response mismatch in group {group_id}, core{core}: "
                        f"actual={result:#x}, trace="
                        f"{item['payload']['response_data']:#x}"
                    )
                replayed += 1
            continue

        for item in group:
            core = item["core"]
            result = results[core]
            if result != item["payload"]["response_data"]:
                raise AssertionError(
                    f"replay response mismatch in group {group_id}, core{core}: "
                    f"actual={result:#x}, trace="
                    f"{item['payload']['response_data']:#x}"
                )
            replayed += 1
    return replayed
