#!/usr/bin/env python3
"""Collect deterministic AXI subsystem simulation rows into JSON and CSV."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "reports" / "coherence"
RESULT_DIR = ROOT / "benchmarks" / "results"
PREFIX = "AXI_TOP_BENCH,"


def collect():
    rows = []
    for log_path in sorted(LOG_DIR.glob("axi_e2e_seed_*.log")):
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(PREFIX):
                rows.append(json.loads(line[len(PREFIX):]))
    rows.sort(key=lambda row: row["seed"])
    if len(rows) != 5:
        raise SystemExit(
            f"expected five AXI top-level seed records, found {len(rows)}; "
            f"inspect {LOG_DIR}/axi_e2e_seed_*.log"
        )
    if len({row["seed"] for row in rows}) != len(rows):
        raise SystemExit("AXI top-level benchmark contains duplicate seeds")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "benchmark_version": 3,
        "dut": "CoherentCacheAxiSubsystem with standalone writable AXI RAM model",
        "clock_period_ns": 10,
        "seed_count": len(rows),
        "metric_definitions": {
            "mean_latency_cycles": "Mean accepted CPU request to CPU response latency measured in the SV testbench",
            "p95_latency_cycles": "Nearest-rank P95 of accepted CPU request to CPU response samples",
            "ops_per_cycle": "Completed CPU requests divided by active simulation cycles",
            "memory_bandwidth": "Accepted AXI R/W data beats times 8 bytes divided by simulation cycles",
            "peak_read_outstanding": "Maximum concurrent AXI read bursts observed by the independent top-level memory model",
        },
        "results": rows,
    }
    json_path = RESULT_DIR / "axi_top_benchmark_v3.json"
    csv_path = RESULT_DIR / "axi_top_benchmark_v3.csv"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"AXI top v3: {len(rows)} seeds -> {json_path} and {csv_path}")


if __name__ == "__main__":
    collect()
