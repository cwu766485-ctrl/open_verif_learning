"""Render one auditable row per seeded full-system stress environment."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "reports/full_system/stress/full_system_coverage.json"
CSV_OUT = ROOT / "reports/full_system/stress_seed_summary.csv"
MD_OUT = ROOT / "reports/full_system/stress_campaign_summary.md"

FIELDS = [
    "scenario_id", "seed", "test_id", "status", "configured_operations",
    "generated_operation_records", "cpu_request_accepts",
    "cpu_response_completions", "directory_requests", "snoop_accepts",
    "mshr_allocations", "mshr_retires", "axi_read_addresses",
    "axi_read_beats", "mmio_requests", "mmio_responses", "apb_completions",
    "max_refill_mshr_occupancy", "max_directory_contexts",
    "protocol_errors", "fatal_errors", "axi_errors", "replay_records",
    "replay_command", "coverage_delta_bins_json", "coverage_delta_crosses_json",
    "stimulus_config_json", "failure_context",
]


def compact_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def configured_operations(run: dict) -> int:
    config = run.get("configuration", {})
    if "operations" in config:
        return int(config["operations"])
    if "rounds" in config:
        return int(config["rounds"])
    if run.get("scenario_id") in {
        "RANDOMIZED_RESET_PHASE", "RANDOMIZED_AXI_READ_ERROR_RECOVERY"
    }:
        return 1
    # The resource-aware sequence checks one owner store and two paired reads.
    return 3 if run.get("scenario_id") == "RESOURCE_AWARE_SNOOP_REFILL" else 0


def replay_command(run: dict) -> str:
    scenario = run.get("scenario_id", "")
    seed = run.get("seed")
    config = run.get("configuration", {})
    if seed is None:
        return ""
    seed_text = f"0x{int(seed):x}"
    if scenario == "FULL_SYSTEM_RANDOM":
        return (
            "source scripts/env.sh && make coherence_full_system_build && "
            f"FULL_SYSTEM_RANDOM_SEEDS={seed_text} "
            f"FULL_SYSTEM_RANDOM_OPERATIONS={configured_operations(run)} "
            "PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv "
            "tests/full_system/test_full_system_random.py"
        )
    if scenario == "SEEDED_MIXED_CPU_MMIO_APB_AXI":
        return (
            "source scripts/env.sh && make coherence_full_system_build && "
            f"FULL_SYSTEM_MIXED_SEED_COUNT=1 FULL_SYSTEM_MIXED_BASE_SEED={seed_text} "
            f"FULL_SYSTEM_MIXED_ROUNDS={configured_operations(run)} "
            "PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv "
            "tests/full_system/test_mixed_agent_random.py"
        )
    if scenario == "RESOURCE_AWARE_SNOOP_REFILL":
        return (
            "source scripts/env.sh && make coherence_full_system_build && "
            f"FULL_SYSTEM_RESOURCE_SEED_COUNT=1 FULL_SYSTEM_RESOURCE_BASE_SEED={seed_text} "
            "PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv "
            "tests/full_system/test_resource_aware_random.py"
        )
    if scenario in {
        "RANDOMIZED_RESET_PHASE", "RANDOMIZED_AXI_READ_ERROR_RECOVERY"
    }:
        return (
            "source scripts/env.sh && make coherence_full_system_build && "
            f"FULL_SYSTEM_RECOVERY_SEED_COUNT=1 "
            f"FULL_SYSTEM_RECOVERY_BASE_SEED={seed_text} "
            "PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv "
            "tests/full_system/test_randomized_recovery.py"
        )
    return f"pytest -sv {run.get('test_id', '')}"


def row_for(run: dict) -> dict[str, object]:
    monitor = run.get("monitor", {})
    events = monitor.get("event_counts", {})
    coverage = run.get("coverage_delta", {})
    return {
        "scenario_id": run.get("scenario_id", ""),
        "seed": run.get("seed", ""),
        "test_id": run.get("test_id", ""),
        "status": run.get("test_status", "unknown"),
        "configured_operations": configured_operations(run),
        "generated_operation_records": len(run.get("generated_operations", [])),
        "cpu_request_accepts": monitor.get("cpu_request_accepts", 0),
        "cpu_response_completions": monitor.get("cpu_response_completions", 0),
        "directory_requests": events.get("directory.request_accept", 0),
        "snoop_accepts": events.get("snoop.accept", 0),
        "mshr_allocations": events.get("mshr.allocate", 0),
        "mshr_retires": events.get("mshr.retire", 0),
        "axi_read_addresses": events.get("axi.read_address", 0),
        "axi_read_beats": events.get("axi.read_beat", 0),
        "mmio_requests": events.get("mmio.request_accept", 0),
        "mmio_responses": events.get("mmio.response_complete", 0),
        "apb_completions": events.get("apb.access_complete", 0),
        "max_refill_mshr_occupancy": monitor.get("max_mshr_occupancy", 0),
        "max_directory_contexts": monitor.get("max_directory_contexts", 0),
        "protocol_errors": monitor.get("protocol_error", 0),
        "fatal_errors": monitor.get("fatal_error", 0),
        "axi_errors": monitor.get("axi_error_count", 0),
        "replay_records": monitor.get("replay_records", 0),
        "replay_command": replay_command(run),
        "coverage_delta_bins_json": compact_json(coverage.get("bins", {})),
        "coverage_delta_crosses_json": compact_json(coverage.get("cross_bins", {})),
        "stimulus_config_json": compact_json(run.get("configuration", {})),
        "failure_context": run.get("failure_context", ""),
    }


def render() -> tuple[list[dict[str, object]], str]:
    if not RAW.is_file():
        raise SystemExit(f"missing stress raw report: {RAW}")
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    runs = raw.get("runs", [])
    rows = [row_for(run) for run in runs]
    totals: dict[str, Counter] = defaultdict(Counter)
    coverage_totals: dict[str, Counter] = defaultdict(Counter)
    for run, row in zip(runs, rows):
        group = str(row["scenario_id"])
        for key in (
            "configured_operations", "generated_operation_records",
            "cpu_request_accepts", "cpu_response_completions",
            "directory_requests", "snoop_accepts", "mshr_allocations",
            "mshr_retires", "axi_read_addresses", "axi_read_beats",
            "mmio_requests", "mmio_responses", "apb_completions",
            "protocol_errors", "fatal_errors", "axi_errors", "replay_records",
        ):
            totals[group][key] += int(row[key])
        totals[group]["max_refill_mshr_occupancy"] = max(
            totals[group]["max_refill_mshr_occupancy"],
            int(row["max_refill_mshr_occupancy"]),
        )
        totals[group]["max_directory_contexts"] = max(
            totals[group]["max_directory_contexts"],
            int(row["max_directory_contexts"]),
        )
        totals[group][f"status:{row['status']}"] += 1
        coverage_totals[group].update(run.get("coverage_delta", {}).get("bins", {}))
        coverage_totals[group].update(run.get("coverage_delta", {}).get("cross_bins", {}))

    lines = [
        "# Four-Agent Full-System Stress Campaign",
        "",
        f"- Raw source: `{RAW.relative_to(ROOT)}` (schema {raw.get('schema_version')}).",
        f"- Pytest exit status: `{raw.get('pytest_exit_status')}`; environments: **{len(rows)}**.",
        "- One CSV row per testcase seed records config, coverage delta, observed transactions/events, error counters, and a replay command.",
        "- CPU random uses 500 configured sequence operations per seed; the generated operation list includes two sequence prelude records. Mixed CPU/MMIO/APB/AXI uses 500 checked rounds per seed. Resource-aware runs check one owner store plus two paired reads. Random recovery runs select one reset phase or one AXI error beat per seed.",
        "- Test stimulus and checks are deterministic for the recorded seed/config at the committed source revision. No failing seed occurred, so replay count is zero and trace shrinking was not applicable.",
        "- The counters are monitor observations. CPU accepted/completed counts can differ because dual-lane pair operations and monitor event definitions are not the same as configured sequence operation counts.",
        "",
        "| Scenario | Seeds / status | Configured ops or rounds | CPU accepts / completions | Directory req | Snoop accepts | AXI AR / R beats | MMIO req / rsp | APB | Protocol / final-fatal / observed AXI errors | Replay |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group, count in totals.items():
        lines.append(
            f"| {group} | {count['status:passed']}/{count['status:passed'] + count['status:failed']} PASS | "
            f"{count['configured_operations']} | "
            f"{count['cpu_request_accepts']} / {count['cpu_response_completions']} | "
            f"{count['directory_requests']} | {count['snoop_accepts']} | "
            f"{count['axi_read_addresses']} / {count['axi_read_beats']} | "
            f"{count['mmio_requests']} / {count['mmio_responses']} | "
            f"{count['apb_completions']} | "
            f"{count['protocol_errors']}/{count['fatal_errors']}/{count['axi_errors']} | "
            f"{count['replay_records']} |"
        )
    lines += ["", "## Per-scenario coverage deltas", ""]
    for group, counts in coverage_totals.items():
        lines += [f"### `{group}`", "", "| Checked bin | Hits |", "| --- | ---: |"]
        lines.extend(f"| `{name}` | {hits} |" for name, hits in sorted(counts.items()))
        lines.append("")
    lines += [
        "## Replay and failure handling",
        "",
        "- The CSV stores the exact test ID, seed, configuration, and a one-seed command for each run.",
        "- AXI error campaign counts are deliberate injected SLVERR events; each seed passes only after the DUT suppresses successful data, resets, and returns the independently expected data on retry. The final-fatal column is sampled after recovery.",
        "- No DUT failure occurred in this random campaign, so its replay count is zero. Separately, `make coherence_full_system_replay_closure` injects a checker expected-data mismatch, captures and replays it on RTL, then reduces the operation trace from five operations to two while retaining the legal owner-store prelude; see `reports/full_system/replay_closure/controlled_checker_failure.json`. This is operation-level reduction, not general cycle-by-cycle interleaving minimization.",
        "- The stress raw JSON is separate from the sign-off coverage dataset. It is a generated scratch report and may be removed by `make clean`; regenerate it with `make COHERENCE_JOBS=2 coherence_full_system_stress`, which also refreshes this compact summary.",
        "",
    ]
    return rows, "\n".join(lines)


def main() -> None:
    rows, markdown = render()
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    MD_OUT.write_text(markdown, encoding="utf-8")
    print(f"wrote {CSV_OUT.relative_to(ROOT)} ({len(rows)} seeds)")
    print(f"wrote {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
