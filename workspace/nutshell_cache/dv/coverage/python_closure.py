"""Close mapped Python/Toffee MESI bins against sampled feature counters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def close(map_path: Path, coverage_path: Path, json_path: Path,
          markdown_path: Path) -> int:
    spec = json.loads(map_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    features = coverage.get("features", {})
    bins = []
    for item in spec["bins"]:
        count = int(features.get(item["feature"], 0))
        bins.append({**item, "test": spec["test"], "hits": count,
                     "status": "hit" if count else "miss"})
    missing = [item["id"] for item in bins if item["hits"] == 0]
    result = {
        "schema_version": 1,
        "regression": spec["regression"],
        "status": "FAIL" if missing else "PASS",
        "functional_coverage": {
            "hit": len(bins) - len(missing), "total": len(bins),
            "percent": 100.0 * (len(bins) - len(missing)) / max(1, len(bins)),
            "missing": missing, "bins": bins,
        },
        "sampled_features": features,
        "cross_state_opcode_core_source": coverage.get(
            "cross_state_opcode_core_source", {}),
        "l1_evictions": coverage.get("l1_evictions", 0),
        "l2_live_evictions": coverage.get("l2_live_evictions", 0),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    lines = [
        "# Python/Toffee Coherence Functional Coverage", "",
        f"- Status: **{result['status']}**",
        f"- Mapped bins: **{len(bins) - len(missing)}/{len(bins)}**",
        f"- L1 evictions: {result['l1_evictions']}",
        f"- Live inclusive L2 evictions: {result['l2_live_evictions']}",
        "", "| Feature | Testpoint | Checker | Hits | Status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for item in bins:
        lines.append(f"| `{item['feature']}` | {item['testpoint']} | "
                     f"{item['checker']} | {item['hits']} | {item['status']} |")
    if missing:
        lines.extend(["", "Missing bins: " + ", ".join(f"`{x}`" for x in missing)])
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if missing:
        print("Python coherence coverage closure failed: " + ", ".join(missing),
              file=sys.stderr)
        return 1
    print(f"Python coherence coverage: {len(bins)}/{len(bins)} bins hit")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", type=Path,
                        default=Path("dv/coverage/python_coherence_map.json"))
    parser.add_argument("--coverage", type=Path,
                        default=Path("benchmarks/results/coherence_python_functional_coverage.json"))
    parser.add_argument("--json", type=Path,
                        default=Path("reports/coherence/python_coverage_closure.json"))
    parser.add_argument("--markdown", type=Path,
                        default=Path("reports/coherence/python_coverage_closure.md"))
    args = parser.parse_args(argv)
    if not args.map.is_file() or not args.coverage.is_file():
        parser.error("coverage map and sampled feature JSON must both exist")
    return close(args.map, args.coverage, args.json, args.markdown)


if __name__ == "__main__":
    raise SystemExit(main())
