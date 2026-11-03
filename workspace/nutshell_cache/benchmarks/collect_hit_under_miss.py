"""Combine the checked-in pre-change baseline with the latest P1 measurement."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "benchmarks/results/rtl_opt_p1_hit_under_miss_baseline.json"
MEASURED = ROOT / "reports/rtl_optimization/hit_under_miss_after.json"
OUTPUT = ROOT / "benchmarks/results/rtl_opt_p1_hit_under_miss_ab.json"


def main():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    optimized = json.loads(MEASURED.read_text(encoding="utf-8"))
    if baseline["workload"] != optimized["workload"]:
        raise SystemExit("baseline and optimized workload definitions differ")
    if baseline["memory_response_delay_cycles"] != optimized[
        "memory_response_delay_cycles"
    ]:
        raise SystemExit("baseline and optimized memory delay differs")

    before = baseline["operations_per_cycle"]
    after = optimized["operations_per_cycle"]
    result = {
        "benchmark": "P1 L1 hit-under-miss",
        "measurement": "Verilator cycle-level simulation; synthetic memory latency",
        "baseline": baseline,
        "optimized": optimized,
        "change": {
            "window_cycles": optimized["window_cycles"] - baseline["window_cycles"],
            "window_cycles_percent": (
                100.0 * (optimized["window_cycles"] - baseline["window_cycles"])
                / baseline["window_cycles"]
            ),
            "operations_per_cycle": after - before,
            "operations_per_cycle_percent": 100.0 * (after - before) / before,
            "miss_latency_cycles": (
                optimized["miss_latency_cycles"] - baseline["miss_latency_cycles"]
            ),
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
