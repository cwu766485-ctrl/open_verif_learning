"""First Python/Toffee end-to-end MESI smoke test for the dual-L1 subsystem."""

import csv

import asyncio

import json

import os

import math

import random

from pathlib import Path

import pytest

from toffee import ClockCycles, Executor, start_clock

from dv.agents.coherent_cpu_agent import CpuRequest, DualCoreCpuDriver

from dv.agents.line_memory_axi_agent import LineMemoryAxiAgent

from dv.coverage.coherence_coverage import CoherenceCoverage

from dv.monitors.cache_perf_monitor import CachePerfMonitor

from dv.monitors.snoop_data_monitor import SnoopDataMonitor

from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard
from dv.sequences.coherence_sequences import CpuAccess

PYTHON_COVERAGE = CoherenceCoverage()

COVERAGE_PATH = Path(os.environ.get(
    "COHERENCE_COVERAGE_PATH",
    str(Path(__file__).resolve().parents[2] / "benchmarks" / "results" /
        "coherence_python_functional_coverage.json"),
))

def _randomized_seeds():
    count = int(os.environ.get("COHERENCE_STRESS_SEED_COUNT", "0"))
    if count <= 0:
        return (0x1A2B, 0x5EED, 0xC0FFEE, 0xD15EA5E)
    if not 1 <= count <= 50:
        raise ValueError("COHERENCE_STRESS_SEED_COUNT must be in [1, 50]")
    # Keep the minimized Directory lookup race replay first, then add stable,
    # independent seeds so a failing case can be replayed from its pytest ID.
    return (0x5EED,) + tuple(0xA0000000 + index * 0x9E3779B9
                             for index in range(count - 1))

def _record_model(model):
    PYTHON_COVERAGE.observe_model(model)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.write_text(json.dumps(PYTHON_COVERAGE.to_dict(), indent=2) + "\n",
                             encoding="utf-8")

_PUT_OPCODES = {0b011, 0b100, 0b101}

_PUT_OPCODE_BY_STATE = {"S": 0b011, "E": 0b100, "M": 0b101}

def _assert_replacement_put_trace(model, memory, *, model_cursor=0,
                                  request_cursor=0):
    """Compare independently predicted L1 victims with accepted Put traffic."""
    expected = [
        (item["core"], item["line"], _PUT_OPCODE_BY_STATE[item["state"]])
        for item in model.l1_evictions[model_cursor:]
        if item.get("state") in _PUT_OPCODE_BY_STATE
    ]
    actual = [
        (item["core"], item["line"], item["opcode"])
        for item in memory.snoop_data.directory_requests[request_cursor:]
        if item["opcode"] in _PUT_OPCODES
    ]
    assert actual == expected, (
        "L1 replacement victim/Put mismatch: "
        f"accepted={actual}, independently predicted={expected}"
    )
    return actual

async def _model_access(cpu, model, snoop_data, core, addr, *, write=False,
                        data=0, mask=0xFF, response_stall_cycles=0):
    """Execute one CPU operation and update only from accepted protocol traffic."""
    put_cursor = len(snoop_data.directory_requests)
    result = await cpu.access(core, addr, write=write, data=data, mask=mask,
                              response_stall_cycles=response_stall_cycles)
    for event in snoop_data.directory_requests[put_cursor:]:
        if event["opcode"] in _PUT_OPCODES:
            model.observe_l1_put(event["core"], event["line"], event["opcode"])
    if write:
        model.observe(core, addr, write=True, write_data=data, write_mask=mask)
    else:
        model.observe(core, addr, response_data=result)
    return result

def _p95(samples):
    if not samples:
        return None
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]

def _rate(numerator, denominator):
    return numerator / denominator if denominator else None

def _phase_samples(starts, ends, start_key="addr", end_key="addr"):
    """Pair ordered same-line milestones and return non-negative cycle deltas."""
    pending = {}
    for item in sorted(starts, key=lambda event: event["cycle"]):
        pending.setdefault(item[start_key], []).append(item["cycle"])
    samples = []
    for item in sorted(ends, key=lambda event: event["cycle"]):
        queue = pending.get(item[end_key], [])
        if queue and queue[0] <= item["cycle"]:
            samples.append(item["cycle"] - queue.pop(0))
    return samples

def _phase_stats(samples):
    return {
        "transactions": len(samples),
        "mean_cycles": (sum(samples) / len(samples) if samples else None),
        "p95_cycles": _p95(samples),
    }

def _v4_percentile(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]

def _v4_counter_delta(after, before):
    return {key: after.get(key, 0) - before.get(key, 0)
            for key in set(after) | set(before)}

from toffee_test import case

__all__ = [name for name in globals() if not name.startswith("__")]
