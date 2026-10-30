"""Audit source and native Verilator coverage without waiving uncovered RTL."""

from __future__ import annotations

import json
import re
import shlex
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RTL_MANIFEST = ROOT / "rtl/Coherence.files.f"
LCOV = ROOT / "reports/coherence/coverage.info"
NATIVE = ROOT / "reports/coherence/coverage.dat"
VERFILES = ROOT / "reports/coherence/obj_dir/VCoherentCacheSubsystem_tb__verFiles.dat"
PYTHON_MAP = ROOT / "dv/coverage/python_coherence_map.json"
PYTHON_CLOSURE = ROOT / "reports/coherence/python_coverage_closure.json"
AUDIT = ROOT / "docs/coverage_audit_phase1.md"
GAP_REVIEW = ROOT / "docs/coherence_coverage_gap_review.md"


def canonical_path(raw: str) -> str:
    """Normalize Verilator/LCOV paths to project-relative POSIX paths."""
    value = raw.strip().strip('"')
    path = Path(value)
    candidates = [path] if path.is_absolute() else [ROOT / path, ROOT / "rtl" / path]
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            relative = resolved.relative_to(ROOT.resolve())
            return relative.as_posix()
        except (FileNotFoundError, ValueError):
            continue
    # Retain a stable normalized name for generated or unavailable sources.
    if path.is_absolute():
        return path.as_posix()
    for candidate in candidates:
        normalized = Path(__import__("os").path.normpath(str(candidate)))
        try:
            return normalized.relative_to(ROOT).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def read_manifest() -> set[str]:
    if not RTL_MANIFEST.is_file():
        raise FileNotFoundError(RTL_MANIFEST)
    sources: set[str] = set()
    for raw in RTL_MANIFEST.read_text(encoding="utf-8").splitlines():
        item = raw.split("#", 1)[0].strip()
        if not item or item.startswith(("+", "-")):
            continue
        source = canonical_path(item)
        if not source.startswith("rtl/"):
            raise ValueError(f"Manifest entry is outside rtl/: {item} -> {source}")
        if source in sources:
            raise ValueError(f"Duplicate RTL manifest entry: {source}")
        if not (ROOT / source).is_file():
            raise FileNotFoundError(f"Manifest source does not exist: {source}")
        sources.add(source)
    return sources


def classify(source: str, product: set[str]) -> str:
    if source in product:
        return "Product RTL"
    if source.startswith("dv/blocks/") and "/tb/" in source:
        return "Testbench"
    if source.startswith("tests/") and source.endswith((".sv", ".svh", ".v", ".vh")):
        return "Testbench"
    return "Generated/Other"


def read_lcov(product: set[str]):
    if not LCOV.is_file():
        raise FileNotFoundError(f"Run make coherence_regression first: {LCOV}")
    lines: dict[tuple[str, int], int] = {}
    records: set[str] = set()
    source = ""
    for raw in LCOV.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("SF:"):
            source = canonical_path(raw[3:])
            records.add(source)
        elif raw.startswith(("BRDA:", "BRF:", "BRH:")):
            raise ValueError(
                "coverage.info must contain line records only; regenerate it with "
                "verilator_coverage --filter-type line and remove LCOV branch records"
            )
        elif raw.startswith("DA:") and source:
            fields = raw[3:].split(",")
            key = (source, int(fields[0]))
            # Multiple aliases/records for one physical source line count once.
            lines[key] = max(lines.get(key, 0), int(fields[1]))
    unexpected_rtl = sorted(
        path for path in records if path.startswith("rtl/") and path not in product
    )
    if unexpected_rtl:
        raise ValueError("LCOV RTL sources absent from Coherence.files.f: " + ", ".join(unexpected_rtl))
    totals = defaultdict(lambda: [0, 0, 0])  # hit, total, miss
    file_lines: dict[str, dict[int, int]] = defaultdict(dict)
    for (path, line), count in lines.items():
        bucket = classify(path, product)
        totals[bucket][1] += 1
        if count > 0:
            totals[bucket][0] += 1
        else:
            totals[bucket][2] += 1
        file_lines[path][line] = count
    for bucket, (hit, total, miss) in totals.items():
        if hit + miss != total:
            raise AssertionError(f"LCOV reconciliation failed for {bucket}: {hit}+{miss}!={total}")
    return lines, records, file_lines, totals


def parse_native(product: set[str]):
    if not NATIVE.is_file():
        raise FileNotFoundError(f"Run make coherence_regression first: {NATIVE}")
    points: dict[tuple[str, str, str], int] = {}
    for raw in NATIVE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.startswith("C ") or "'" not in raw:
            continue
        try:
            metadata = raw.split("'", 2)[1]
            count = int(raw.rsplit(" ", 1)[1])
        except (IndexError, ValueError):
            continue
        fields: dict[str, str] = {}
        for component in metadata.split("\x01"):
            if "\x02" in component:
                key, value = component.split("\x02", 1)
                fields[key] = value
        if not fields.get("f") or not fields.get("t"):
            continue
        source = canonical_path(fields["f"])
        point_type = fields["t"]
        # Include source line, point ordinal, branch/outcome, instance and ranges
        # so points from distinct elaborated instances remain distinct.
        identity = "|".join(fields.get(k, "") for k in ("l", "n", "o", "page", "S"))
        key = (source, point_type, identity)
        points[key] = max(points.get(key, 0), count)
    summary = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (source, point_type, _), count in points.items():
        bucket = classify(source, product)
        values = summary[bucket][point_type]
        values[1] += 1
        values[0] += int(count > 0)
    per_source = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (source, point_type, _), count in points.items():
        values = per_source[source][point_type]
        values[1] += 1
        values[0] += int(count > 0)
    return summary, per_source


def compiled_rtl_sources() -> set[str]:
    if not VERFILES.is_file():
        raise FileNotFoundError(f"Missing Verilator source manifest: {VERFILES}")
    sources: set[str] = set()
    for raw in VERFILES.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.startswith("S "):
            continue
        try:
            fields = shlex.split(raw)
            path = canonical_path(fields[-1])
        except (ValueError, IndexError):
            continue
        if path.startswith("rtl/") and path.endswith((".sv", ".v")):
            sources.add(path)
    return sources


def ranges(lines: list[int]) -> str:
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


def missed_category(source_line: str, context: str) -> str:
    code = source_line.lower()
    text = context.lower()
    if re.search(r"\bdefault\s*:", code):
        return "FSM/default 防御分支（不可达候选，未证明）"
    error_markers = (
        "protocol_error", "protocol error", "engine_error", "cpu_error",
        "snp_error", "dir_error", "memory_adapter_error", "_error",
    )
    if any(token in code for token in error_markers):
        return "非法协议检测 / 错误处理"
    if any(token in text for token in ("recover an invalid upgrade", "retry from l2", "recovery", "retry")):
        return "合法恢复 / 重试路径未命中"

    # Attribute a condition/else arm to error handling only when its own
    # immediate body takes an explicit error action. Do not let a nearby
    # sibling case contaminate legal-path classifications.
    source_window = " ".join(context.splitlines())
    if (re.search(r"\b(if|else if)\b", code) or code.startswith("end else begin")) and any(
        token in source_window for token in error_markers
    ):
        return "非法协议检测 / 错误处理"
    if any(token in code for token in ("_bad", "_mismatch", " != ")):
        return "非法协议检测 / 错误处理"
    if any(token in code for token in ("reset", "rst", "recovery", "retry")):
        return "防御 / 复位 / 恢复路径"
    return "合法路径未命中"


def validate_functional_closure() -> tuple[str, list[dict], list[dict]]:
    spec = json.loads(PYTHON_MAP.read_text(encoding="utf-8"))
    closure = json.loads(PYTHON_CLOSURE.read_text(encoding="utf-8"))
    spec_bins = spec.get("bins", [])
    spec_cross = spec.get("cross_bins", [])
    actual_bins = closure.get("functional_coverage", {}).get("bins", [])
    actual_cross = closure.get("cross_coverage", {}).get("bins", [])
    ids = lambda items: [item.get("id") for item in items]
    if len(spec_bins) != 49 or len(spec_cross) != 19:
        raise AssertionError(f"Functional map changed: expected 49/19; got {len(spec_bins)}/{len(spec_cross)}")
    if ids(spec_bins) != ids(actual_bins) or ids(spec_cross) != ids(actual_cross):
        raise AssertionError("Functional/Cross closure IDs do not exactly match the preserved map")
    if closure.get("status") != "PASS" or closure.get("functional_coverage", {}).get("hit") != 49 or closure.get("cross_coverage", {}).get("hit") != 19:
        raise AssertionError("Functional/Cross closure is not PASS 49/49 and 19/19")
    if any(not item.get("checker", "").strip() for item in spec_bins):
        raise AssertionError("A functional bin is missing its checker mapping")
    if any(not item.get("checker", "").strip() for item in spec_cross):
        raise AssertionError("A cross bin is missing its checker mapping")
    return closure["status"], spec_bins, spec_cross


def render() -> tuple[str, str]:
    product = read_manifest()
    lines, lcov_sources, file_lines, totals = read_lcov(product)
    native_summary, native_by_source = parse_native(product)
    compiled = compiled_rtl_sources()
    missing_compile = sorted(product - compiled)
    extra_compile = sorted(compiled - product)
    if missing_compile or extra_compile:
        raise AssertionError(
            "Compiled RTL manifest mismatch; missing=" + repr(missing_compile) + "; extra=" + repr(extra_compile)
        )
    closure_status, mapped_bins, mapped_cross = validate_functional_closure()

    categories = ("Product RTL", "Testbench", "Generated/Other")
    total_all = sum(values[1] for values in totals.values())
    hit_all = sum(values[0] for values in totals.values())
    miss_all = sum(values[2] for values in totals.values())
    if hit_all + miss_all != total_all:
        raise AssertionError(f"Global LCOV reconciliation failed: {hit_all}+{miss_all}!={total_all}")

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    rows = [
        "# Phase 1 Coverage Infrastructure Audit and Baseline Freeze", "",
        f"Generated from the full regression artifacts on {stamp}.", "",
        "## Scope and source accounting", "",
        "No RTL behavior, interface, testcase sequence, Functional Coverage Bin ID, or waiver was changed. Product RTL classification uses exact normalized path membership in rtl/Coherence.files.f.", "",
        f"- RTL Source Manifest: **{len(product)} files**; Verilator __verFiles.dat RTL source set: **{len(compiled)} files**; exact match: **PASS**.",
        f"- LCOV source records: **{len(lcov_sources)}**; product RTL manifest files with executable line points: **{sum(1 for path in product if path in file_lines)}**; files with no line points in this selected top/run: **{sum(1 for path in product if path not in file_lines)}**.",
        "- A manifest source with no executable LCOV line points is reported as N/A, not as 0% coverage. Such files can still be parsed/compiled but may be packages, unelaborated top wrappers, or blocks outside this simulation top.", "",
        "### LCOV line reconciliation", "",
        "Each normalized (source, line) record is counted once. Hit + missed must equal total in every category and globally.", "",
        "| Category | Hit | Total | Missed | Reconciliation |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for category in categories:
        hit, total, miss = totals[category]
        rows.append(f"| {category} | {hit} | {total} | {miss} | {hit} + {miss} = {total} |")
    rows.append(f"| **All source records** | **{hit_all}** | **{total_all}** | **{miss_all}** | **{hit_all} + {miss_all} = {total_all}** |")

    native_types = ("branch", "toggle", "fsm_state", "fsm_arc")
    rows += ["", "## Native Verilator coverage by source category", "",
             "Native point totals are parsed from merged coverage.dat by point type; point hit means count > 0. These are independent of LCOV DA line totals.", "",
             "| Category | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for category in categories:
        values = [native_summary[category][kind] for kind in native_types]
        fmt = [f"{hit}/{total}" if total else "N/A (0 points)" for hit, total in values]
        rows.append(f"| {category} | " + " | ".join(fmt) + " |")
    rows += ["", "## Product RTL module raw coverage", "",
             "Line columns use unique LCOV source-line records. Native columns use point records from coverage.dat. N/A means this build/run emitted no points of that type for the source.", "",
             "| RTL Source | Line hit/total | Line missed | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for source in sorted(product):
        source_lines = file_lines.get(source, {})
        total = len(source_lines)
        hit = sum(count > 0 for count in source_lines.values())
        line_value = f"{hit}/{total}" if total else "N/A"
        missed = str(total - hit) if total else "N/A"
        native = native_by_source[source]
        cells = []
        for kind in native_types:
            p_hit, p_total = native[kind]
            cells.append(f"{p_hit}/{p_total}" if p_total else "N/A")
        rows.append(f"| `{source}` | {line_value} | {missed} | " + " | ".join(cells) + " |")

    uncovered = []
    for (source, line), count in sorted(lines.items()):
        if source in product and count == 0:
            source_lines = (ROOT / source).read_text(encoding="utf-8", errors="replace").splitlines()
            code = source_lines[line - 1].strip() if 0 < line <= len(source_lines) else "<source line unavailable>"
            # Keep a small surrounding source window so a recovery comment or
            # a multi-line guard can be associated with its own branch.
            lo, hi = max(0, line - 10), min(len(source_lines), line + 10)
            context = " ".join(source_lines[lo:hi])
            category = missed_category(code, context)
            uncovered.append((source, line, category, code))
    review_counts: dict[str, int] = defaultdict(int)
    for _, _, category, _ in uncovered:
        review_counts[category] += 1
    rows += ["", f"## Every uncovered Product RTL line ({len(uncovered)} lines)", "",
             "Each missed executable source line is linked to its original RTL path and line. Categories are source-context review labels: the default/FSM label is only an unreachability candidate, never a proof; error labels identify checks/actions, and legal/recovery labels identify paths for which directed stimulus is appropriate. No category automatically waives a line.", "",
             "| Review category | Lines |", "| --- | ---: |"]
    for category in sorted(review_counts):
        rows.append(f"| {category} | {review_counts[category]} |")
    rows += ["", "| Source line | Review category | Source text |",
             "| --- | --- | --- |"]
    for source, line, category, code in uncovered:
        safe = code.replace("|", "\\|").replace("`", "\\`")
        rows.append(f"| [`{source}:{line}`](../{source}#L{line}) | {category} | `{safe}` |")

    rows += ["", "## Uncovered-line review and suggested testpoints", "",
             "| RTL module | Raw gap | Suggested Testpoint / checker |",
             "| --- | ---: | --- |"]
    module_testpoints = {
        "coherence/SharedLineEngine.sv": "RCV-03/05: Snoop ACK with no data, retry from authoritative L2; check single completion and returned line data.",
        "directory/DirectoryController.sv": "RCV-01/02/03: owner-self GetM, stale Upgrade, invalid metadata/opcode and retry outcomes; independent Directory/MESI checker.",
        "directory/DirectoryMshrBank.sv": "RCV-04: context allocation/retirement, same-set lock, Put bypass and Grant/Snoop/Transfer backpressure; context lifecycle checker.",
        "l1/MesiL1Controller.sv": "L1 Snoop/metadata removal race and invalid command handling; check accepted handshake and retained line data.",
        "l1/MesiL1Array.sv": "Replacement and metadata removal race; compare valid/tag/data after simultaneous legal Snoop and CPU activity.",
        "cluster/DualL1MesiCluster.sv": "Same-cycle two-core request/response routing and reset cancellation; per-core transaction ID/address checker.",
        "interconnect/CpuMmioRouter.sv": "MMIO/cache simultaneous requests and response routing under backpressure; per-lane request/response checker.",
        "l2/SharedL2DirectoryArray.sv": "L2 read/write collision, replacement and directory metadata consistency; array transaction checker.",
    }
    gaps_by_source = defaultdict(list)
    for source, line, category, code in uncovered:
        gaps_by_source[source].append(line)
    for source in sorted(product):
        if gaps_by_source[source]:
            rows.append(f"| `{source}` | {len(gaps_by_source[source])} ({ranges(gaps_by_source[source])}) | {module_testpoints.get(source, 'Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver.')} |")

    rows += ["", "## Functional Coverage map and checker closure", "",
             f"- Python Functional Coverage: **49/49 PASS**; Cross Coverage: **19/19 PASS**; closure status: **{closure_status}**.",
             "- The IDs below are compared in order against the generated closure artifact. Every mapped bin retains a non-empty checker description. No Bin ID or closure logic was edited.",
             "- Closure logic counts sampled feature/cross counters and fails on missing bins. Checker descriptions are audited as map metadata; the current closure script does not machine-prove that each checker ran for each bin. The full regression passed its existing Scoreboard/Monitor checks, but per-bin checker invocation remains an infrastructure gap.", "",
             "| Bin ID | Feature / Cross | Testpoint | Checker |",
             "| --- | --- | --- | --- |"]
    for item in mapped_bins:
        rows.append(f"| `{item['id']}` | `{item['feature']}` | {item['testpoint']} | {item['checker']} |")
    for item in mapped_cross:
        rows.append(f"| `{item['id']}` | Cross: `{item.get('key', '')}` | {item['testpoint']} | {item['checker']} |")

    rows += ["", "## Tool support and limits", "",
             "- This run uses the workspace OSS CAD Suite Verilator 5.053 development build. The build requests line, branch, toggle, and FSM instrumentation; the merged native report is generated by verilator_coverage summary/hier.",
             "- Branch points are reported only where Verilator elaborates a branch point. FSM extraction is experimental and conservative: 0 extracted state/arc points means N/A for this design/run, not 0% design FSM coverage.",
             "- Verilator emitted a COVERIGN warning for one TB FSM whose state variable is assigned multiple times in a reset branch; that machine was not extracted. FSM percentages therefore cover only machines Verilator extracted, not every RTL/TB state variable.",
             "- Toggle points may be absent for signals filtered by Verilator defaults (including underscore-prefixed signals unless coverage-underscore is enabled), unsupported/generated constructs, or signals optimized away. Report emitted points only; no denominator is inferred from RTL declarations.",
             "- Hierarchy summaries collapse some hierarchy paths and are not precise per-instance results. The source/module table uses native point identity grouped by original source path.",
             "- Product sources outside the selected simulation top or without executable coverage points are N/A. The AXI top, CSR and some uninstantiated wrappers require their own elaborated block run for meaningful runtime coverage.",
             "- Branch/toggle/FSM instrumentation changes only measurement. Existing test commands, transaction sequences, and expected behavior are unchanged.", "",
             "## Baseline interpretation", "",
             "This report freezes the corrected counting boundary. Product RTL is exactly the set in Coherence.files.f, so source folders such as coherence/, interconnect/, common/, and bus/ cannot silently fall into Other. Testbench and Generated/Other records remain separate. Missed lines are reviewed individually and are not automatically waived.", "",
             "PPA, physical SRAM mapping, timing signoff, and full-system CPU memory ordering are outside this coverage audit.", ""]

    gap_rows = [
        "# Coherence RTL Coverage Gap Review", "",
        f"Generated from the Phase 1 source audit on {stamp}.", "",
        f"- Product RTL: **{totals['Product RTL'][0]}/{totals['Product RTL'][1]}** hit; **{totals['Product RTL'][2]}** missed.",
        f"- Testbench: **{totals['Testbench'][0]}/{totals['Testbench'][1]}** hit; **{totals['Testbench'][2]}** missed.",
        f"- Generated/Other: **{totals['Generated/Other'][0]}/{totals['Generated/Other'][1]}** hit; **{totals['Generated/Other'][2]}** missed.",
        f"- All LCOV records: **{hit_all}/{total_all}** hit; **{miss_all}** missed; reconciliation: **PASS**.",
        f"- RTL manifest / compiler source reconciliation: **{len(product)}/{len(compiled)} files; PASS**.",
        "", "The detailed audit lists every uncovered Product RTL source line, review category, module-level raw coverage, native Verilator point coverage, checker mapping and remaining testpoints.",
        "", "See [Phase 1 Coverage Infrastructure Audit](coverage_audit_phase1.md). No uncovered line was automatically waived.", "",
    ]
    return "\n".join(rows), "\n".join(gap_rows)


def main() -> None:
    audit, gap = render()
    AUDIT.write_text(audit, encoding="utf-8")
    GAP_REVIEW.write_text(gap, encoding="utf-8")
    print("\n".join(gap.splitlines()[2:9]))
    print(f"Wrote {AUDIT.relative_to(ROOT)} and {GAP_REVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
