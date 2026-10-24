"""Close the dual-L1 MESI functional bins and emit a reproducible regression report."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def lcov_line_summary(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    found = hit = 0
    da_found = da_hit = 0
    for line in path.read_text(errors="replace").splitlines():
        # Verilator emits DA records but omits the aggregate LF/LH records
        # normally written by lcov. Count the line records directly so the
        # native Verilator LCOV output still closes code coverage.
        if line.startswith("DA:"):
            fields = line[3:].split(",", 1)
            if len(fields) == 2:
                da_found += 1
                da_hit += int(fields[1]) > 0
        elif line.startswith("LF:"):
            found += int(line[3:])
        elif line.startswith("LH:"):
            hit += int(line[3:])
    return (hit, found) if found else (da_hit, da_found)


def summarize(map_path: Path, logs: list[Path], lcov: Path | None,
              waiver_path: Path | None, out_json: Path, out_md: Path) -> int:
    spec = json.loads(map_path.read_text())
    contents = {p: p.read_text(errors="replace") for p in logs}
    combined = "\n".join(contents.values())
    bins = []
    misses = []
    for item in spec["bins"]:
        hits = sum(text.count(item["testpoint"]) for text in contents.values())
        row = {**item, "test": spec.get("test", ""),
               "hits": hits, "status": "hit" if hits else "miss"}
        bins.append(row)
        if not hits:
            misses.append(item["id"])

    stall_counts = {}
    cover_lines = re.findall(r"^COVER:.*$", combined, flags=re.MULTILINE)
    for line in cover_lines:
        for key, value in re.findall(r"([a-zA-Z0-9_]+)=(\d+)", line):
            stall_counts[key] = max(stall_counts.get(key, 0), int(value))
    missing_stalls = [key for key in spec.get("required_stall_bins", [])
                      if stall_counts.get(key, 0) <= 0]
    code_hit, code_total = lcov_line_summary(lcov) if lcov else (0, 0)
    bench_match = re.search(r"^BENCH: (.+)$", combined, flags=re.MULTILINE)
    bench = ({key: int(value) for key, value in
              re.findall(r"([a-zA-Z0-9_]+)=(\d+)", bench_match.group(1))}
             if bench_match else {})
    bench["storage_capacity_bytes"] = 2 * 32 * 1024 + 256 * 1024
    bench["storage_capacity_kib"] = bench["storage_capacity_bytes"] // 1024
    if "l1_miss_avg_cycles" in bench and "l1_hit_avg_cycles" in bench:
        bench["l1_miss_penalty_cycles"] = (
            bench["l1_miss_avg_cycles"] - bench["l1_hit_avg_cycles"]
        )

    waivers = []
    if waiver_path and waiver_path.exists():
        payload = json.loads(waiver_path.read_text())
        waivers = payload.get("waivers", payload if isinstance(payload, list) else [])

    pass_markers = sum(len(re.findall(r"^PASS:", text, flags=re.MULTILINE))
                       for text in contents.values())
    result = {
        "schema_version": 1,
        "regression": spec["regression"],
        "status": "PASS" if not misses and not missing_stalls else "FAIL",
        "simulation_logs": [str(p) for p in logs],
        "test_pass_markers": pass_markers,
        "functional_coverage": {
            "hit": len(bins) - len(misses), "total": len(bins),
            "percent": 100.0 * (len(bins) - len(misses)) / max(1, len(bins)),
            "bins": bins, "missing": misses,
        },
        "stall_counts": stall_counts,
        "missing_stall_bins": missing_stalls,
        "performance_proxy": bench,
        "code_coverage": {
            "line_hit": code_hit, "line_total": code_total,
            "percent": 100.0 * code_hit / code_total if code_total else None,
            "lcov": str(lcov) if lcov else None,
        },
        "waivers": {"count": len(waivers), "file": str(waiver_path) if waiver_path else None},
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Dual-L1 MESI Regression Report", "",
        f"- **Status:** {result['status']}",
        f"- **PASS markers:** {pass_markers}",
        f"- **Functional coverage:** {result['functional_coverage']['hit']}/{len(bins)} "
        f"({result['functional_coverage']['percent']:.1f}%)",
        f"- **Code line coverage:** {code_hit}/{code_total} "
        f"({result['code_coverage']['percent']:.1f}%)" if code_total else
        "- **Code line coverage:** unavailable (no LCOV input)",
        f"- **Documented waivers:** {len(waivers)}",
        "", "| Feature | Testpoint | Bin | Test | Hits | Status |",
        "|---|---|---|---|---:|---|",
    ]
    for item in bins:
        lines.append(f"| {item['feature']} | `{item['testpoint']}` | `{item['id']}` | "
                     f"{item['test']} | {item['hits']} | {item['status']} |")
    lines.extend(["", "## Backpressure closure", "",
                  "| Channel | Stalled cycles | Status |", "|---|---:|---|"])
    for key in spec.get("required_stall_bins", []):
        count = stall_counts.get(key, 0)
        lines.append(f"| `{key}` | {count} | {'hit' if count else 'miss'} |")
    lines.extend(["", "Logs:", ""] + [f"- `{p}`" for p in logs] + [""])
    lines.extend(["", "## Performance and storage baseline", "",
                  f"- L1 hit: {bench.get('l1_hit_avg_cycles', 0)} average cycles "
                  f"({bench.get('l1_hit_count', 0)} samples)",
                  f"- L1 miss: {bench.get('l1_miss_avg_cycles', 0)} average cycles "
                  f"({bench.get('l1_miss_count', 0)} samples; "
                  f"{bench.get('l1_miss_penalty_cycles', 0)} cycle penalty vs. hit)",
                  f"- Remote snoop: {bench.get('snoop_avg_cycles', 0)} average cycles "
                  f"({bench.get('snoop_count', 0)} samples)",
                  f"- Configured data capacity: {bench['storage_capacity_kib']} KiB "
                  "(two 32 KiB L1s plus 256 KiB shared L2)",
                  "- These are RTL simulation cycle counts and configured capacity. "
                  "No target standard-cell library, SRAM compiler model, clock constraint, "
                  "or physical-design flow is configured, so this report does not claim "
                  "silicon area or static timing closure.", ""])
    out_md.write_text("\n".join(lines))
    if misses or missing_stalls:
        print(f"coherence coverage closure failed: bins={misses}, stalls={missing_stalls}", file=sys.stderr)
        return 1
    print(f"coherence functional coverage: {len(bins)}/{len(bins)} bins hit; report: {out_md}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", type=Path, default=Path("dv/coverage/coherence_map.json"))
    parser.add_argument("--log", action="append", type=Path, required=True)
    parser.add_argument("--lcov", type=Path)
    parser.add_argument("--waivers", type=Path, default=Path("dv/coverage/coherence_waivers.json"))
    parser.add_argument("--json", type=Path, default=Path("reports/coherence/regression.json"))
    parser.add_argument("--markdown", type=Path, default=Path("reports/coherence/regression.md"))
    args = parser.parse_args(argv)
    absent = [str(path) for path in args.log if not path.is_file()]
    if absent:
        parser.error("missing simulation log(s): " + ", ".join(absent))
    return summarize(args.map, args.log, args.lcov, args.waivers, args.json, args.markdown)


if __name__ == "__main__":
    raise SystemExit(main())
