"""Report raw and waiver-adjusted statement coverage for maintained RTL.

Generated Picker/Verilator wrappers remain visible in the full LCOV report but
are intentionally excluded from the maintained-RTL closure metric. Every
waiver must point to an observed zero-count line; newly uncovered lines fail
the closure check instead of silently reducing the adjusted denominator.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


WAIVER_FILE = Path(__file__).with_name("waivers.json")


def _rtl_relative_path(source):
    normalized = source.replace(chr(92), "/")
    marker = "/rtl/"
    if marker not in normalized:
        return None
    return "rtl/" + normalized.rsplit(marker, 1)[1]


def _parse_info(info_path):
    current_source = None
    lines = defaultdict(dict)
    for raw_line in Path(info_path).read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("SF:"):
            current_source = _rtl_relative_path(raw_line[3:])
        elif current_source and raw_line.startswith("DA:"):
            line_text, count_text = raw_line[3:].split(",", 1)
            lines[current_source][int(line_text)] = int(count_text)
    return lines


def summarize(info_path, waiver_path=WAIVER_FILE):
    report = _parse_info(info_path)
    maintained = {source: data for source, data in report.items() if source.startswith("rtl/")}
    if not maintained:
        raise ValueError(f"no maintained rtl/ entries found in {info_path}")

    waiver_data = json.loads(Path(waiver_path).read_text(encoding="utf-8"))
    waivers = {(entry["source"], entry["line"]): entry["reason"]
               for entry in waiver_data["waivers"]}
    raw_points = {(source, line): count
                  for source, source_lines in maintained.items()
                  for line, count in source_lines.items()}
    missing_waiver_targets = set(waivers) - set(raw_points)
    if missing_waiver_targets:
        raise ValueError(f"waiver target(s) absent from coverage data: {sorted(missing_waiver_targets)}")

    hit = sum(count > 0 for count in raw_points.values())
    total = len(raw_points)
    unhit = {point for point, count in raw_points.items() if count == 0}
    waiver_points = set(waivers)
    hit_waivers = {point for point in waiver_points if raw_points[point] > 0}
    if hit_waivers:
        raise ValueError(f"waiver target(s) now hit; review/remove waiver(s): {sorted(hit_waivers)}")
    unexpected = unhit - waiver_points
    if unexpected:
        raise ValueError(f"new unwaived RTL line(s) uncovered: {sorted(unexpected)}")

    adjusted_total = total - len(waiver_points)
    if adjusted_total <= 0:
        raise ValueError("no coverage points remain after waivers")
    adjusted = 100.0 * hit / adjusted_total
    print(f"Maintained RTL raw line coverage: {hit}/{total} ({100.0 * hit / total:.1f}%)")
    print(f"Documented exclusions: {len(waiver_points)} (see dv/coverage/waivers.json)")
    print(f"Waiver-adjusted maintained RTL coverage: {hit}/{adjusted_total} ({adjusted:.1f}%)")
    print("Generated DUT/wrapper sources are excluded from this metric and remain in reports/rtl/.")
    return hit, total, len(waiver_points), adjusted


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m dv.coverage.closure reports/cache.info", file=sys.stderr)
        return 2
    try:
        summarize(argv[0])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"coverage closure error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
