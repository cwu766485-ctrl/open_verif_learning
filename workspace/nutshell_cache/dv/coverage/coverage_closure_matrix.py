"""Build a source-linked, non-waiving RTL coverage closure matrix.

The matrix combines the selected subsystem run's LCOV source-line gaps with
the native Verilator branch/FSM points.  Classifications are deliberately
conservative: a point is never called unreachable based only on source text.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from dv.coverage import coherence_gap_review as audit
from dv.coverage import coverage_raw_runs as raw_runs


ROOT = audit.ROOT
OUT = ROOT / "reports/coherence/coverage_closure_matrix.csv"
SUMMARY = ROOT / "reports/coherence/coverage_closure_summary.md"
WAIVERS = ROOT / "reports/coherence/coverage_closure_waivers.csv"

FIELDS = [
    "point_id", "raw_dataset", "metric", "raw_status", "rtl_source", "source_line",
    "block", "coverage_point", "feature_spec", "why_unhit",
    "legal_reachability", "protocol_error_protection",
    "unreachable_or_redundant_review", "testcase_checker_formal_evidence",
    "separate_raw_dataset_evidence", "recommended_action", "risk", "review_status",
]
WAIVER_FIELDS = [
    "waiver_id", "raw_dataset", "rtl_source", "source_line", "coverage_point",
    "rationale", "supporting_evidence", "approval",
]

BLOCKS = {
    "rtl/bus/apb/CachePerformanceCsr.sv": "APB Performance CSR",
    "rtl/bus/axi/LineMemoryAxi4Adapter.sv": "AXI4 Line Memory Adapter",
    "rtl/bus/axi/MemoryRefillMshrBank.sv": "Memory Refill MSHR Bank",
    "rtl/cluster/DualL1MesiCluster.sv": "Dual L1 MESI Cluster",
    "rtl/coherence/SharedLineEngine.sv": "Shared Line Engine",
    "rtl/directory/DirectoryController.sv": "Directory Controller",
    "rtl/directory/DirectoryMshrBank.sv": "Directory MSHR Bank",
    "rtl/interconnect/CoherenceRequestArbiter.sv": "Coherence Request Arbiter",
    "rtl/interconnect/CoherenceRequestArbiterCore.sv": "Coherence Arbiter Core",
    "rtl/interconnect/CpuMmioRouter.sv": "CPU/MMIO Router",
    "rtl/interconnect/L2LineWriteArbiter.sv": "L2 Line Write Arbiter",
    "rtl/l1/MesiL1Array.sv": "MESI L1 Array",
    "rtl/l1/MesiL1Controller.sv": "MESI L1 Controller",
    "rtl/l1/MesiL1SnoopArbiter.sv": "MESI L1 Snoop Arbiter",
    "rtl/l2/SharedL2DirectoryArray.sv": "Shared L2 Directory Array",
    "rtl/top/CoherentCacheAxiSubsystem.sv": "AXI Cache Subsystem Top",
    "rtl/top/CoherentCacheSubsystem.sv": "Coherent Cache Subsystem",
}


EVIDENCE = {
    "rtl/directory/DirectoryController.sv": (
        "dv/blocks/directory_controller/tb/DirectoryController_tb.sv; "
        "tests/coherence/test_recovery.py (RCV-01/02/03); "
        "formal/coherence_directory.sby and formal/coherence_directory_progress.sby. "
        "These are distinct runs; current top LCOV does not credit them."
    ),
    "rtl/directory/DirectoryMshrBank.sv": (
        "dv/blocks/directory_mshr_bank/tb/DirectoryMshrBank_tb.sv and "
        "include/xfer_start_backpressure.svh; checker asserts stable payload, "
        "single completion, context routing, and no protocol_error; "
        "formal/coherence_directory_mshr_bank.sby."
    ),
    "rtl/coherence/SharedLineEngine.sv": (
        "CoherentCacheSubsystem_tb directed/stress; Python tests/coherence/test_recovery.py; "
        "RTL mutation cases cover selected owner-data and error mutations. "
        "No standalone SharedLineEngine formal proof is claimed."
    ),
    "rtl/l1/MesiL1Controller.sv": (
        "dv/blocks/mesi_l1_controller/tb/MesiL1Controller_tb.sv and its "
        "snoop/refill/protocol-error includes; subsystem Python Scoreboard. "
        "No standalone controller formal proof is claimed."
    ),
    "rtl/l2/SharedL2DirectoryArray.sv": (
        "dv/blocks/shared_l2_directory_array/tb/SharedL2DirectoryArray_tb.sv; "
        "Dense L2 stress; subsystem Scoreboard checks data and directory outcomes."
    ),
    "rtl/bus/axi/MemoryRefillMshrBank.sv": (
        "AXI subsystem E2E/backpressure regression and formal AXI checks; "
        "review source-specific ID/beat mapping before crediting any guard."
    ),
    "rtl/cluster/DualL1MesiCluster.sv": (
        "dv/blocks/dual_l1_mesi_cluster/tb/DualL1MesiCluster_tb.sv; "
        "subsystem two-core Scoreboard; tests/full_system/test_hit_under_miss_axi.py "
        "checks pending-miss hit response address/data/ID, wrap, stall, snoop and reset. "
        "The Python/Toffee run is separate from raw SV-top RTL coverage."
    ),
    "rtl/interconnect/CpuMmioRouter.sv": (
        "Subsystem MMIO/cache routing scenarios and top monitor; "
        "invalid FSM encoding has no dedicated fault injection."
    ),
}

_POINT_CACHE: dict[str, dict] = {}
_LINE_CACHE: dict[str, dict[str, dict[int, int]]] = {}


def source_text(path: str) -> list[str]:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()


def feature_for(source: str, line: int, point: str = "") -> str:
    if source.endswith("DirectoryController.sv"):
        if 353 <= line <= 365:
            return "Protocol-inconsistent Upgrade presented with DIR_I metadata; the current RTL raises protocol_error but also starts a refill (cache.md stale Upgrade / fail-stop contract)."
        if 467 <= line <= 487:
            return "Owner disappears before Snoop response: retry from authoritative L2 and commit one grant (cache.md snoop/ownership rules)."
        if 374 <= line <= 435:
            return "PutS/PutE/PutM ownership and dirty-data retirement (cache.md Put lifecycle)."
        if 458 <= line <= 510:
            return "Snoop ACK/DATA/INV_ACK response validation and target progression (cache.md snoop rules)."
        if point.startswith("FSM"):
            return "Directory transaction FSM: allocate, transfer/snoop, metadata commit, grant, retirement, reset/error."
        return "Directory request opcode and MESI state transition (cache.md Directory protocol table)."
    if source.endswith("DirectoryMshrBank.sv"):
        return "Four-context selection, same-set serialization, output offer lock and ready/valid stability (cache.md concurrency/backpressure rules)."
    if source.endswith("SharedLineEngine.sv"):
        if 133 <= line <= 143 or 225 <= line <= 255:
            return "Memory response, write response ID/error, and memory protocol fault handling."
        if 268 <= line <= 320:
            return "Inclusive L2 live-victim snoop, dirty owner collection, writeback, directory clear and invalidate."
        if 348 <= line <= 357:
            return "Grant data read waits for L2 line-read acceptance and streams the committed line."
        if 329 <= line <= 341:
            return "PutM eight-beat line transfer into shared L2."
        return "Shared L2 transfer/refill/grant/victim engine lifecycle."
    if source.endswith("MesiL1Controller.sv"):
        if 365 <= line <= 393:
            return "Snoop miss/invalid-line ACK, SnoopRead downgrade and SnoopInvalidate."
        if 305 <= line <= 321 or 431 <= line <= 443:
            return "Eight-beat CPU refill or snoop data beat/last handling."
        if point.startswith("FSM"):
            return "MESI L1 CPU/snoop FSM state and reset/error transitions."
        return "CPU request permission, grant validation, and metadata commit."
    if source.endswith("SharedL2DirectoryArray.sv"):
        return "L2 line write allocation and ordered eight-beat data acceptance."
    if source.endswith("MemoryRefillMshrBank.sv"):
        return "AXI read transaction ID to refill MSHR association and beat routing."
    if source.endswith("DualL1MesiCluster.sv"):
        if 249 <= line <= 276 or 419 <= line <= 428:
            return "Hit-under-Miss: a resident read hit bypasses the pre-refill wait window while preserving the pending miss response and unique transaction IDs."
        return "Replacement victim Put/replay and dual-core array arbitration."
    if source.endswith("CpuMmioRouter.sv"):
        return "Dual-core MMIO/cache request and response routing FSM."
    if point.startswith("FSM"):
        return f"{BLOCKS.get(source, source)} FSM state/transition per RTL implementation."
    return f"{BLOCKS.get(source, source)} behavior described by its block testplan and cache.md interface contract."


def exact_review(source: str, line: int, code: str, point: str) -> tuple[str, str, str, str, str]:
    """Return reachability, protocol-guard, disposition, action, risk.

    This is an explicit source-range review map, not a token/keyword waiver.
    Unmapped points remain unreviewed and are not classified unreachable.
    """
    if source.endswith("DualL1MesiCluster.sv") and (249 <= line <= 276 or 419 <= line <= 428):
        return (
            "Legal but deliberately constrained: only a resident read hit may bypass while the controller is sending a miss or waiting for its grant; writes, misses, active snoops, replacement, and refill cycles remain serialized.",
            "No; this is a legal hit response path. Its transaction ID must remain distinct from the pending miss ID, including wraparound.",
            "Not unreachable or redundant. The instrumented CoherentCacheSubsystem_tb now executes a legal resident-hit-under-pending-miss sequence. This point remains OPEN only when its count is zero in this particular raw dataset; a hit in another elaborated top is recorded separately.",
            "Same-top raw stimulus is in dv/blocks/coherent_cache_subsystem/tb/include/hit_under_miss_coverage.svh and checks a pending cold miss, resident hit data/response, distinct transaction IDs, three-cycle response backpressure, and later miss completion. Full AXI Python tests separately cover ID wrap, remote snoop and reset. Keep each zero-count point OPEN until its exact LCOV/branch/FSM row is hit or independently dispositioned.",
            "High",
        )
    if source.endswith("DirectoryMshrBank.sv") and 339 <= line <= 379:
        return (
            "Legal and directed: valid output can be held while corresponding ready is low.",
            "No; this is ordinary ready/valid flow control.",
            "Not unreachable/redundant. Validate each output channel's payload hold and one-time acceptance.",
            "Add/retain directed write, transfer-start, and grant backpressure tests; collect this block's own raw coverage.",
            "Medium",
        )
    if source.endswith("DirectoryController.sv") and 353 <= line <= 365:
        return (
            "Not a legal MESI request under the current spec: Upgrade requires a valid S copy; DIR_I means the requester has no sharer copy. The stale-but-still-valid DIR_U case is a separate supported recovery path.",
            "Yes. RTL sets protocol_error/code 4, but then proceeds to L2 refill and a data-bearing M grant instead of failing closed as docs/cache.md currently states.",
            "Reachable only through an inconsistent requester/Directory interface condition. This source range exposes a spec/RTL behavior mismatch; it is neither approved legal recovery nor proven unreachable.",
            "Keep OPEN. Resolve the frozen protocol contract and add a block fault-injection test that checks error, no successful grant/metadata commit, and reset recovery. Do not count this as normal functional coverage.",
            "High",
        )
    if source.endswith("DirectoryController.sv") and 467 <= line <= 487:
        return (
            "Legal recovery when a line disappears between Directory lookup and SnoopRead response.",
            "No; ACK/INV_ACK is an allowed no-data response in this race and causes L2 retry.",
            "Not unreachable. This path is part of replacement/Snoop concurrency and must remain covered.",
            "Directed owner PutM/SnoopRead race; independent data, Directory-state, ID and single-grant checker.",
            "High",
        )
    if source.endswith("SharedLineEngine.sv") and 348 <= line <= 355:
        return (
            "Legal; grant and L2 read acceptance may occur on different cycles under L2 port contention.",
            "The hit=false branch is a protocol/invariant error guard; the wait-then-hit branch is legal.",
            "Not unreachable as a whole. Separate the legal waiting arm from the invalid L2-miss guard.",
            "Add a directed grant-read backpressure test; separately inject/force invalid lookup result and check protocol error if interface permits.",
            "High",
        )
    if source.endswith("MesiL1Controller.sv") and 365 <= line <= 368:
        return (
            "Legal; SnoopRead/Invalidate may target an absent or already-invalid L1 line.",
            "No; expected ACK/INV_ACK response, not an error path.",
            "Not unreachable. Verify response opcode, address/transaction ID, no data beats and no metadata mutation.",
            "Run block Snoop miss and invalidate-miss directed cases with response checker.",
            "Medium",
        )
    if source.endswith("SharedL2DirectoryArray.sv") and 313 <= line <= 314:
        return (
            "Reachability not proven; legal Engine sequencing should reclaim/invalidate an inclusive victim before allocating a full set.",
            "Yes; reports a line write to a set with neither hit nor free way.",
            "Not declared unreachable: requires invariant proof or an explicit rejected-write fault test.",
            "Review allocation/reservation handshake; add full-set illegal-write injection and assert protocol_error, or prove the invariant formally.",
            "High",
        )
    if source.endswith("SharedL2DirectoryArray.sv") and 326 <= line <= 327:
        return (
            "Illegal beat order/last combination; legal transfer is beats 0..7 with last only on beat 7.",
            "Yes; protects L2 data-array write protocol.",
            "Not unreachable by assumption. Require directed wrong-index and wrong-last injection with error checker.",
            "Add block Fault Injection for early/late last and skipped/repeated beat; verify no successful commit.",
            "High",
        )
    if source.endswith("SharedLineEngine.sv") and (133 <= line <= 143 or 232 <= line <= 235 or 246 <= line <= 251 or 276 <= line <= 280 or 331 <= line <= 334):
        return (
            "Fault-only or external error path; the exact input combination was not exercised by the measured legal regressions.",
            "Yes; validates response ID/error, beat index/last, or memory protocol consistency.",
            "Do not waive. No unreachability or redundancy proof recorded.",
            "Inject each malformed ID/beat/last/error at the block boundary and check sticky error, no false completion, and reset recovery.",
            "High",
        )
    if source.endswith("MesiL1Controller.sv") and (254 <= line <= 256 or 287 <= line <= 289 or 307 <= line <= 318 or 394 <= line <= 395 or 437 <= line <= 440):
        return (
            "Malformed or inconsistent CPU/grant/refill/snoop interface condition; not exercised by normal legal traffic.",
            "Yes; protects against invalid MESI hit, PUT_ACK as CPU grant, malformed line beats, or unsupported snoop opcode.",
            "Do not waive; no proof that input is impossible at this block boundary.",
            "Use block-level Fault Injection and assert protocol_error/error state plus no CPU success/metadata commit.",
            "High",
        )
    if "default:" in code or "_ERROR" in code or "protocol_error" in code:
        return (
            "Not established from the current stimulus; appears to be an illegal encoding/protocol guard but source inspection alone is insufficient.",
            "Candidate error protection; verify exact branch condition and effect in the corresponding RTL block.",
            "No unreachable/redundant conclusion. No waiver assigned.",
            "Add targeted fault injection where the block interface permits; otherwise provide formal reachability evidence and retain the guard.",
            "Medium",
        )
    return (
        "Not established; no matching transaction was observed in this run.",
        "Unknown until the owning block's condition and neighboring state are reviewed.",
        "Not assessed. No waiver assigned.",
        "Review the exact point in the owning block; add directed stimulus or a bounded/unbounded formal reachability argument.",
        "High",
    )


def has_explicit_source_range_review(source: str, line: int) -> bool:
    """Whether this point falls in one of the hand-authored source reviews.

    A syntax-based candidate (such as a ``default`` arm) is intentionally not
    considered a review. The matrix distinguishes a reviewed condition range
    from a source-mapped point that still needs human inspection.
    """
    return any((
        source.endswith("DirectoryMshrBank.sv") and 339 <= line <= 379,
        source.endswith("DualL1MesiCluster.sv") and (
            249 <= line <= 276 or 419 <= line <= 428
        ),
        source.endswith("DirectoryController.sv") and 353 <= line <= 365,
        source.endswith("DirectoryController.sv") and 467 <= line <= 487,
        source.endswith("SharedLineEngine.sv") and 348 <= line <= 355,
        source.endswith("MesiL1Controller.sv") and 365 <= line <= 368,
        source.endswith("SharedL2DirectoryArray.sv") and 313 <= line <= 314,
        source.endswith("SharedL2DirectoryArray.sv") and 326 <= line <= 327,
        source.endswith("SharedLineEngine.sv") and (
            133 <= line <= 143 or 232 <= line <= 235 or 246 <= line <= 251
            or 276 <= line <= 280 or 331 <= line <= 334
        ),
        source.endswith("MesiL1Controller.sv") and (
            254 <= line <= 256 or 287 <= line <= 289 or 307 <= line <= 318
            or 394 <= line <= 395 or 437 <= line <= 440
        ),
    ))


def block_point(source: str, line: int, state_or_arc: str = "") -> str:
    if state_or_arc:
        return state_or_arc
    src = source_text(source)
    if 0 < line <= len(src):
        return src[line - 1].strip()
    return "source point unavailable"


def fsm_source_line(source: str, point_type: str, outcome: str) -> int:
    """Map extracted FSM names/arcs to the source case label for audit links."""
    src = source_text(source)
    state_name = outcome.rsplit("::", 1)[-1]
    if point_type == "fsm_arc" and "->" in state_name:
        state_name = state_name.split("->", 1)[0]
    pattern = re.compile(rf"^\s*{re.escape(state_name)}\s*:")
    for index, line in enumerate(src, 1):
        if pattern.search(line):
            return index
    return 1


def row(point_id: str, dataset_key: str, metric: str, source: str, line: int,
        point: str, raw_status: str, native_identity: str = "") -> dict[str, str]:
    code = block_point(source, line)
    reach, guard, disposition, action, risk = exact_review(source, line, code, point)
    return {
        "point_id": point_id,
        "raw_dataset": dataset_key,
        "metric": metric,
        "raw_status": raw_status,
        "rtl_source": source,
        "source_line": str(line),
        "block": BLOCKS.get(source, "Unmapped manifest source"),
        "coverage_point": point,
        "feature_spec": feature_for(source, line, metric),
        "why_unhit": "The point has count 0 in the selected raw dataset; this states observation only, not that the behavior is unreachable.",
        "legal_reachability": reach,
        "protocol_error_protection": guard,
        "unreachable_or_redundant_review": disposition,
        "testcase_checker_formal_evidence": EVIDENCE.get(source, "Owning block testplan/testbench plus integrated subsystem regression; no point-specific formal proof recorded."),
        "separate_raw_dataset_evidence": separate_dataset_evidence(
            source, line, metric, native_identity, dataset_key
        ),
        "recommended_action": action,
        "risk": risk,
        "review_status": (
            "source-range behavior reviewed; point-level closure remains open until test/proof evidence is verified"
            if has_explicit_source_range_review(source, line)
            else "source/path mapped only; point-level behavior not individually reviewed; open and not waived"
        ),
    }


def separate_dataset_evidence(source: str, line: int, metric: str,
                              native_identity: str, current_dataset: str) -> str:
    """Cite matching observations from separate runs without summing them."""
    for run_name, (dat, info, _scope) in raw_runs.DATASETS.items():
        if run_name == current_dataset:
            continue
        if not dat.is_file():
            continue
        if metric == "LCOV RTL line":
            if not info.is_file():
                continue
            if run_name not in _LINE_CACHE:
                all_lines: dict[str, dict[int, int]] = defaultdict(dict)
                current_source = ""
                for raw in info.read_text(encoding="utf-8", errors="replace").splitlines():
                    if raw.startswith("SF:"):
                        current_source = audit.canonical_path(raw[3:])
                    elif raw.startswith("DA:") and current_source:
                        try:
                            src_line, hits = raw[3:].split(",", 2)[:2]
                            src_line, hits = int(src_line), int(hits)
                        except ValueError:
                            continue
                        all_lines[current_source][src_line] = max(
                            all_lines[current_source].get(src_line, 0), hits
                        )
                _LINE_CACHE[run_name] = all_lines
            line_hits = _LINE_CACHE[run_name].get(source, {})
            if line in line_hits and line_hits[line] > 0:
                return f"Hit in independent `{run_name}` raw LCOV; this dataset's miss remains separate."
        else:
            point_type = {"Verilator branch": "branch", "FSM state": "fsm_state", "FSM arc": "fsm_arc"}.get(metric)
            if not point_type:
                continue
            if run_name not in _POINT_CACHE:
                _POINT_CACHE[run_name] = raw_runs.read_points(dat)
            run_points = _POINT_CACHE[run_name]
            if run_points.get((source, point_type, native_identity), 0) > 0:
                return f"Hit in independent `{run_name}` native data; this dataset's miss remains separate."
    return "No matching point hit found in other emitted raw datasets; retain as an open per-run miss."


def native_points(path: Path, product: set[str]):
    points: dict[tuple[str, str, str], int] = {}
    metadata_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
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
        if not fields.get("f") or fields.get("t") not in {"branch", "fsm_state", "fsm_arc"}:
            continue
        source = audit.canonical_path(fields["f"])
        if source not in product:
            continue
        identity = "|".join(fields.get(k, "") for k in ("l", "n", "o", "page", "S"))
        key = (source, fields["t"], identity)
        if count >= points.get(key, -1):
            points[key] = count
            metadata_by_key[key] = fields
    return points, metadata_by_key


def build_rows() -> list[dict[str, str]]:
    product = audit.read_manifest()
    rows: list[dict[str, str]] = []
    for dataset_key, (dat, info, _scope) in raw_runs.DATASETS.items():
        if not dat.is_file() or not info.is_file():
            continue
        lines = raw_runs.read_line_info(info)
        for source, source_lines in sorted(lines.items()):
            for line, count in sorted(source_lines.items()):
                if source not in product or count:
                    continue
                point_id = f"{dataset_key}|line:{source}:{line}"
                rows.append(row(point_id, dataset_key, "LCOV RTL line", source,
                                line, block_point(source, line), "miss"))

        points, metadata = native_points(dat, product)
        for key, count in sorted(points.items()):
            if count:
                continue
            source, point_type, identity = key
            fields = metadata[key]
            outcome = fields.get("o", "")
            if point_type == "branch":
                line = int(fields.get("l", "1") or "1")
                point = f"branch ordinal={fields.get('n','?')} outcome={outcome}; body={fields.get('S','N/A')}"
                metric = "Verilator branch"
            else:
                line = fsm_source_line(source, point_type, outcome)
                point = f"{point_type} {outcome}"
                metric = "FSM state" if point_type == "fsm_state" else "FSM arc"
            point_id = f"{dataset_key}|{point_type}:{source}:{identity}"
            rows.append(row(point_id, dataset_key, metric, source, line, point,
                            "count=0", native_identity=identity))
    return rows


def main() -> None:
    rows = build_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with WAIVERS.open("w", newline="", encoding="utf-8") as stream:
        csv.DictWriter(stream, fieldnames=WAIVER_FIELDS, lineterminator="\n").writeheader()

    counts = Counter((row["raw_dataset"], row["metric"]) for row in rows)
    primary_rows = [r for r in rows if r["raw_dataset"] == "Full coherent subsystem regression"]
    risks = Counter(row["risk"] for row in primary_rows)
    open_high = sum(r["risk"] == "High" for r in primary_rows)
    summary = [
        "# RTL Coverage Closure Matrix Summary", "",
        "Generated from each independent raw Verilator dataset listed in `coverage_closure_raw_runs.md`. The matrix includes one record per zero-count Product RTL LCOV line, branch, FSM state, and FSM arc for each run, with a run identity. Repeated source points in different runs are separate observations.",
        "",
        "Zero count means unobserved in that raw dataset. It is not an unreachable-code waiver. Separate Python/Toffee, block, AXI, and subsystem builds are not arithmetically merged.",
        "",
        "| Raw dataset | Metric | Unhit points |", "| --- | --- | ---: |",
    ]
    for (dataset, metric), count in sorted(counts.items()):
        summary.append(f"| {dataset} | {metric} | {count} |")
    summary += ["", "Risk totals below describe only the primary subsystem run; rows across different runs are not pooled.", "", "| Primary dataset risk label | Points |", "| --- | ---: |"]
    for risk in ("High", "Medium", "Low"):
        summary.append(f"| {risk} | {risks[risk]} |")
    explicit_reviewed = sum(
        has_explicit_source_range_review(r["rtl_source"], int(r["source_line"]))
        for r in primary_rows
    )
    unreviewed = sum(
        r["review_status"].startswith("source/path mapped only")
        for r in primary_rows
    )
    summary += [
        "", f"**Open high-risk points:** {open_high} (none are waived by this report).",
        "", f"Primary-run review accounting: {explicit_reviewed} points fall in hand-authored source-range reviews; {unreviewed} are mapped to source/path but not individually reviewed. All remain open until their prescribed test/proof evidence is verified.",
        "", "Waiver inventory: zero approved or automatic waivers. The header-only `coverage_closure_waivers.csv` is retained as the explicit waiver record.",
        "", "The detailed CSV records the raw dataset identity, RTL source line, block, feature/spec relationship, why that dataset missed it, reachability/error-protection assessment, existing evidence, other-run observation, recommended directed test or formal action, and risk.",
        "", "A source-range assessment is not closure. Default/FSM branches are never called unreachable from source keywords alone; no point is waived by this report.",
    ]
    SUMMARY.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} unhit RTL points) and an empty waiver inventory")
    print("; ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
