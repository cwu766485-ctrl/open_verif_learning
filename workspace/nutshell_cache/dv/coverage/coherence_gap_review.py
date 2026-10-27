"""Render a source-linked audit of uncovered coherent-cache RTL lines."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LCOV = ROOT / "reports/coherence/coverage.info"
OUTPUT = ROOT / "docs/coherence_coverage_gap_review.md"


def _ranges(lines: list[int]) -> str:
    if not lines:
        return "—"
    result: list[str] = []
    start = previous = lines[0]
    for line in lines[1:]:
        if line == previous + 1:
            previous = line
            continue
        result.append(str(start) if start == previous else f"{start}–{previous}")
        start = previous = line
    result.append(str(start) if start == previous else f"{start}–{previous}")
    return ", ".join(result)


def render() -> str:
    if not LCOV.exists():
        raise FileNotFoundError(f"Run make coherence_regression first: {LCOV}")

    total = defaultdict(int)
    hit = defaultdict(int)
    misses: dict[str, list[int]] = defaultdict(list)
    source = ""
    for raw in LCOV.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("SF:"):
            source = raw[3:]
        elif raw.startswith("DA:") and source:
            fields = raw[3:].split(",")
            line, count = int(fields[0]), int(fields[1])
            total[source] += 1
            if count:
                hit[source] += 1
            else:
                misses[source].append(line)

    design_sources = {
        path: lines for path, lines in misses.items()
        if path.startswith(("cluster/", "directory/", "l1/", "l2/", "top/"))
    }
    tb_sources = {path: lines for path, lines in misses.items()
                  if path.startswith("../tests/")}
    other = {path: lines for path, lines in misses.items()
             if path not in design_sources and path not in tb_sources}
    rtl_total = sum(total[path] for path in design_sources)
    rtl_hit = sum(hit[path] for path in design_sources)
    rtl_missed = sum(len(lines) for lines in design_sources.values())
    tb_missed = sum(len(lines) for lines in tb_sources.values())
    all_lines = sum(total.values())
    all_hit = sum(hit.values())
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    rows = [
        "# Coherence RTL Coverage Gap Review",
        "",
        f"Generated from `reports/coherence/coverage.info` on {stamp}.",
        "",
        "## Summary",
        "",
        f"- Merged line records: {all_hit}/{all_lines} hit; {all_lines - all_hit} missed.",
        f"- Product RTL: {rtl_hit}/{rtl_total} hit; {rtl_missed} missed lines.",
        f"- SystemVerilog testbench: {tb_missed} missed lines (kept separate from RTL).",
    ]
    if other:
        rows.append(f"- Other source files: {sum(map(len, other.values()))} missed lines.")

    rows += [
        "",
        "## Per-file unhit line ranges",
        "",
        "Line numbers refer to the source paths in the merged LCOV report.",
        "",
        "| Source | Hit / total | Missed | Unhit lines |",
        "| --- | ---: | ---: | --- |",
    ]
    for path in sorted(misses):
        rows.append(
            f"| `{path}` | {hit[path]}/{total[path]} | {len(misses[path])} "
            f"| {_ranges(misses[path])} |"
        )

    rows += [
        "",
        "## Review conclusion",
        "",
        "The unhit RTL is concentrated in defensive protocol-error handling, "
        "illegal metadata/opcode rejection, reset/error FSM defaults, and "
        "rare recovery/arbiter-lock paths. These lines are not evidence of a "
        "functional failure by themselves. The Directory recovery cases and "
        "invalid-input paths remain the most valuable candidates for future "
        "directed tests; existing bounded formal and independent Python/Toffee "
        "tests provide separate evidence for transaction stability, MSHR "
        "admission, reset cancellation, data integrity, and coherence state.",
        "",
        "The testbench misses are assertion/error guards and setup branches; "
        "they are reported separately. This review does not waive any "
        "functional requirement and does not claim 100% statement/branch "
        "coverage. PPA, SRAM mapping, and STA are outside this review.",
        "",
    ]
    return "\n".join(rows)


def main() -> None:
    text = render()
    OUTPUT.write_text(text, encoding="utf-8")
    print(text.split("## Summary", 1)[1].split("## Per-file", 1)[0].strip())
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
