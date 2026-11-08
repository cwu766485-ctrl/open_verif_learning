"""Summarize independent Verilator coverage datasets without cross-run addition."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from dv.coverage import coherence_gap_review as audit


ROOT = audit.ROOT
OUT = ROOT / "reports/coherence/coverage_closure_raw_runs.md"
PRODUCT = audit.read_manifest()

DATASETS = {
    "Full coherent subsystem regression": (
        ROOT / "reports/coherence/coverage.dat",
        ROOT / "reports/coherence/coverage.info",
        "Main subsystem smoke, multisnoop and five seeded regressions, all from one common subsystem elaboration and coverage definition. The standalone Directory MSHR regression is a separate dataset and is not included here.",
    ),
    "AXI cache subsystem E2E (five fixed seeds)": (
        ROOT / "reports/coherence/block_coverage/coherent_cache_axi_subsystem.dat",
        ROOT / "reports/coherence/block_coverage/coherent_cache_axi_subsystem_line.info",
        "Five official AXI E2E seeds merged only within this identical top/build/test definition.",
    ),
    "DirectoryController block": (
        ROOT / "reports/coherence/block_coverage/directory_controller.dat",
        ROOT / "reports/coherence/block_coverage/directory_controller_line.info",
        "Standalone DirectoryController directed TB.",
    ),
    "DirectoryMshrBank block": (
        ROOT / "reports/coherence/block_coverage/directory_mshr_bank.dat",
        ROOT / "reports/coherence/block_coverage/directory_mshr_bank_line.info",
        "Standalone four-context MSHR directed/stress TB, including transfer-start backpressure.",
    ),
    "SharedLineEngine block": (
        ROOT / "reports/coherence/block_coverage/shared_line_engine.dat",
        ROOT / "reports/coherence/block_coverage/shared_line_engine_line.info",
        "Standalone immediate/delayed grant read, refill, PutM, multi-sharer clean victim, dirty-owner writeback, backpressure and selected protocol fault cases.",
    ),
    "MesiL1Controller block": (
        ROOT / "reports/coherence/block_coverage/mesi_l1_controller.dat",
        ROOT / "reports/coherence/block_coverage/mesi_l1_controller_line.info",
        "Standalone controller refill, snoop, reset and malformed-beat tests.",
    ),
    "SharedL2DirectoryArray block": (
        ROOT / "reports/coherence/block_coverage/shared_l2_directory_array.dat",
        ROOT / "reports/coherence/block_coverage/shared_l2_directory_array_line.info",
        "Standalone L2 array lookup, stream, victim and malformed-write tests.",
    ),
    "Bus blocks": (
        ROOT / "reports/coherence/block_coverage/bus_blocks.dat",
        ROOT / "reports/coherence/block_coverage/bus_blocks_line.info",
        "Standalone AXI line adapter and APB CSR tests, including malformed response and outstanding-ID cases.",
    ),
}

POINT_TYPES = ("line", "branch", "toggle", "fsm_state", "fsm_arc")


def read_line_info(path: Path) -> dict[str, dict[int, int]]:
    if not path.is_file():
        return {}
    result: dict[str, dict[int, int]] = defaultdict(dict)
    source = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("SF:"):
            source = audit.canonical_path(raw[3:])
        elif raw.startswith("DA:") and source in PRODUCT:
            line, count = raw[3:].split(",", 2)[:2]
            number, hits = int(line), int(count)
            result[source][number] = max(result[source].get(number, 0), hits)
    return result


def read_points(path: Path):
    points: dict[tuple[str, str, str], int] = {}
    if not path.is_file():
        return points
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.startswith("C ") or "'" not in raw:
            continue
        try:
            fields: dict[str, str] = {}
            for component in raw.split("'", 2)[1].split("\x01"):
                if "\x02" in component:
                    key, value = component.split("\x02", 1)
                    fields[key] = value
            count = int(raw.rsplit(" ", 1)[1])
        except (IndexError, ValueError):
            continue
        source, point_type = fields.get("f", ""), fields.get("t", "")
        source = audit.canonical_path(source) if source else ""
        if source not in PRODUCT or point_type not in POINT_TYPES:
            continue
        identity = "|".join(fields.get(key, "") for key in ("l", "n", "o", "page", "S"))
        key = (source, point_type, identity)
        points[key] = max(points.get(key, 0), count)
    return points


def metric_counts(line_info, points, source_filter=None):
    selected = PRODUCT if source_filter is None else set(source_filter)
    totals = {name: [0, 0] for name in POINT_TYPES}
    per_source = defaultdict(lambda: {name: [0, 0] for name in POINT_TYPES})
    for source, lines in line_info.items():
        if source not in selected:
            continue
        for hits in lines.values():
            totals["line"][1] += 1
            totals["line"][0] += int(hits > 0)
            per_source[source]["line"][1] += 1
            per_source[source]["line"][0] += int(hits > 0)
    for (source, kind, _identity), hits in points.items():
        if source not in selected or kind == "line":
            continue
        totals[kind][1] += 1
        totals[kind][0] += int(hits > 0)
        per_source[source][kind][1] += 1
        per_source[source][kind][0] += int(hits > 0)
    return totals, per_source


def fmt(pair):
    return f"{pair[0]}/{pair[1]}" if pair[1] else "N/A"


def render() -> str:
    rows = [
        "# Final Code Coverage Closure: Raw Run Inventory",
        "",
        "Each row below is an independent Verilator elaboration/test definition. Values are never summed across the rows. The five-seed AXI top is merged only across those five runs because they share the same build, instrumentation, top and testcase definition.",
        "",
        "Coverage ratios are raw observations, not signoff closure by themselves. Functional coverage and Python/Toffee observations are not merged into RTL LCOV or native point counts.",
        "",
    ]
    for name, (dat, info, scope) in DATASETS.items():
        if not dat.is_file():
            rows += [f"## {name}", "", f"**Not run / data missing:** `{dat.relative_to(ROOT)}`", ""]
            continue
        line_info = read_line_info(info)
        points = read_points(dat)
        totals, by_source = metric_counts(line_info, points)
        rows += [f"## {name}", "", scope, "",
                 "| Metric | Hit / total | Miss |", "| --- | ---: | ---: |"]
        for kind in POINT_TYPES:
            hit, total = totals[kind]
            rows.append(f"| {kind} | {fmt((hit, total))} | {total-hit if total else 'N/A'} |")
        rows += ["", "| Product RTL source | Line | Branch | Toggle | FSM state | FSM arc |",
                 "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for source in sorted(PRODUCT):
            metrics = by_source[source]
            if not any(metrics[name][1] for name in POINT_TYPES):
                continue
            rows.append("| `" + source + "` | " + " | ".join(fmt(metrics[name]) for name in POINT_TYPES) + " |")
        no_points = [source for source in sorted(PRODUCT)
                     if not any(by_source[source][name][1] for name in POINT_TYPES)]
        if no_points:
            rows += ["", "No Product RTL points emitted in this run:", ""]
            rows.extend(f"- `{source}`" for source in no_points)
        rows.append("")
    rows += [
        "## Interpretation limits",
        "",
        "- Verilator line, branch, toggle and FSM metrics have separate denominators. FSM metrics include only state machines extracted by this Verilator build; a zero denominator means no extracted machine, not zero design FSM coverage.",
        "- Toggle totals are affected by Verilator instrumentation filters, optimization and elaboration. They are point totals for emitted signals, not all declared RTL bits.",
        "- Python/Toffee uses a different simulator wrapper and does not emit compatible Verilator coverage points. Its passing tests are cited as separate functional evidence; its coverage is not added to RTL reports.",
        "- Source lines absent from an LCOV file have no executable line point in that elaboration. Package-only files can legitimately emit no runtime point; wrapper files may still emit points in the AXI top even when absent in the selected non-AXI subsystem run.",
        "- Block and subsystem coverage are separately reported. They must not be arithmetically combined because parameterization, elaborated hierarchy and stimulus differ.",
        "",
    ]
    return "\n".join(rows)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
