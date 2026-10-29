#!/usr/bin/env python3
"""Validate and export Benchmark v4 pytest records as JSON and CSV."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "reports" / "coherence" / "benchmark_v4.log"
RESULTS = ROOT / "benchmarks" / "results"
PREFIX = "COHERENCE_BENCHMARK_V4,"
EXPECTED_WORKLOADS = {
    "B01_warm_l1": 1,
    "B02_sequential_scan": 1,
    "B03_working_set_sweep": 6,
    "B04_set_conflict": 2,
    "B05_mixed_read_write": 3,
    "B06_dual_core_parallel_miss": 4,
    "B06_serial_cold_miss": 4,
    "B07_ownership_ping_pong": 1,
    "B08_false_sharing": 2,
}


def collect():
    if not LOG.is_file():
        raise SystemExit(f"missing Benchmark v4 log: {LOG}")
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        marker = line.find(PREFIX)
        if marker >= 0:
            rows.append(json.loads(line[marker + len(PREFIX):]))
    expected_rows = sum(EXPECTED_WORKLOADS.values())
    if len(rows) != expected_rows:
        raise SystemExit(
            f"expected {expected_rows} Benchmark v4 rows, "
            f"found {len(rows)}; inspect {LOG}"
        )
    counts = {}
    for row in rows:
        counts[row["workload"]] = counts.get(row["workload"], 0) + 1
        if row["completed_ops"] != row["requested_ops"]:
            raise SystemExit(f"incomplete workload row: {row}")
        if row["window_cycles"] <= 0:
            raise SystemExit(f"invalid cycle window: {row}")
    if counts != EXPECTED_WORKLOADS:
        raise SystemExit(f"workload row counts differ: {counts}")

    by_key = {(row["workload"], row["case"]): row for row in rows}
    warm = by_key[("B01_warm_l1", "core0_repeated_line")]
    if warm["l1_read_hit_rate"] != 1.0 or warm["l1_read_misses"] != 0:
        raise SystemExit(f"B01 should be a 100% L1 read-hit workload: {warm}")
    scan = by_key[("B02_sequential_scan", "16KiB_8B_stride")]
    if not scan["l1_read_hits"] or not scan["l1_read_misses"]:
        raise SystemExit(f"B02 must show both line misses and spatial hits: {scan}")
    conflict = by_key[("B04_set_conflict", "L2_same_set_nine_dirty_lines")]
    if not conflict["dirty_writebacks"] or not conflict["memory_write_lines"]:
        raise SystemExit(f"B04 L2 victim did not produce a dirty writeback: {conflict}")
    parallel = [row for row in rows
                if row["workload"] == "B06_dual_core_parallel_miss"]
    serial = [row for row in rows
              if row["workload"] == "B06_serial_cold_miss"]
    if {row["memory_response_latency_cycles"] for row in parallel} != {2, 20, 50, 100}:
        raise SystemExit("B06 memory latency sweep is incomplete")
    if {row["memory_response_latency_cycles"] for row in serial} != {2, 20, 50, 100}:
        raise SystemExit("B06 serial reference sweep is incomplete")
    if any(row["mshr_peak_occupancy"] < 2 for row in parallel):
        raise SystemExit(f"B06 did not demonstrate two overlapping refills: {parallel}")
    if any(row["mshr_peak_occupancy"] != 1 for row in serial):
        raise SystemExit(f"B06 serial reference should peak at one refill: {serial}")
    serial_by_delay = {row["memory_response_latency_cycles"]: row for row in serial}
    for row in parallel:
        serial_row = serial_by_delay[row["memory_response_latency_cycles"]]
        row["parallel_speedup_vs_serial"] = (
            serial_row["window_cycles"] / row["window_cycles"]
        )
    for row in serial:
        row["parallel_speedup_vs_serial"] = None
    ping = by_key[("B07_ownership_ping_pong", "64_alternating_stores")]
    if ping["snoops"] <= 0:
        raise SystemExit(f"B07 did not observe ownership snoops: {ping}")
    same = by_key[("B08_false_sharing", "same_line_different_words")]
    separate = by_key[("B08_false_sharing", "different_lines")]
    if same["snoops"] <= separate["snoops"]:
        raise SystemExit("B08 same-line case must produce more snoops than separate lines")

    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "benchmark_version": 4,
        "dut": "CoherentCacheSubsystem via Picker/Verilator and Python/Toffee",
        "clock_period_ns": 10,
        "cpu_model": "dual LSU agents; not a retired-instruction CPU model",
        "memory_model": "writable 64-byte line model; response delay is configurable",
        "result_interpretation": (
            "RTL simulation cycles and modeled memory traffic; not silicon PPA, "
            "real CPU IPC/CPI, or physical DRAM bandwidth"
        ),
        "metric_definitions": {
            "l1_hit_miss": "accepted CPU requests classified by L1 event pins; write hits exclude S-to-M permission upgrades",
            "l2_refill_hit_miss": "accepted Directory refill lookup events, not all L2 tag probes",
            "amat": "mean accepted CPU request-to-response cycles, by read/write and L1 hit/miss class",
            "miss_penalty": "mean L1-miss response latency minus mean L1-hit response latency",
            "throughput": "completed CPU requests divided by measured window cycles, per core and aggregate",
            "parallel_speedup": "same 16 cold cache lines and memory delay: single-core serial cycles divided by dual-core paired cycles",
            "bandwidth": "accepted 64-bit line-memory beats times eight bytes divided by measured window cycles",
            "mshr_occupancy": "per-cycle popcount of exported refill-MSHR valid bits; Directory context occupancy is reported separately",
            "stall_cycles": "cycles of VALID without READY, reported by channel and core; categories may overlap",
            "fairness": "Jain index over per-core completion counts during the window",
        },
        "workload_counts": counts,
        "workloads": rows,
    }
    json_path = RESULTS / "coherence_benchmark_v4.json"
    csv_path = RESULTS / "coherence_benchmark_v4.csv"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    fieldnames = list(dict.fromkeys(
        key for row in rows for key in row
    ))
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            })
    print(f"Benchmark v4: {len(rows)} rows validated -> {json_path}, {csv_path}")


if __name__ == "__main__":
    collect()
