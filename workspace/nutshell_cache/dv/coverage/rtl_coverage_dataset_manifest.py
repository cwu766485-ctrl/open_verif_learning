"""Fingerprint independent Verilator RTL coverage datasets for release review.

This module deliberately records datasets independently. It never adds point
counts from different elaborated tops or different test definitions.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

from dv.coverage import coherence_gap_review as audit
from dv.coverage import coverage_raw_runs as raw


ROOT = audit.ROOT
OUTPUT = ROOT / "reports/coherence/rtl_coverage_dataset_manifest.json"
POINT_KINDS = set(raw.POINT_TYPES)

DATASET_META = {
    "Full coherent subsystem regression": {
        "id": "main_subsystem",
        "top": "CoherentCacheSubsystem_tb",
        "filelist": "rtl/Coherence.files.f",
        "tests": ["smoke including risk_closure_patterns", "l2_multisnoop_only", "seeds:00000001,00001234,5EEDC0DE,DEADBEEF,2468ACE0"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/coherent_cache_subsystem/tb/CoherentCacheSubsystem_tb.sv", "markers": ["`include \"include/scenario_sequence.svh\""]},
                {"path": "dv/blocks/coherent_cache_subsystem/tb/include/hit_under_miss_coverage.svh", "markers": ["PASS: raw RTL Hit-under-Miss preserves both checked responses"]},
                {"path": "dv/blocks/coherent_cache_subsystem/tb/include/replacement_and_l2_victims.svh", "markers": ["PASS: L2 live victim back-invalidates an M owner"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/coherent_cache_subsystem/tb/include/reference_protocol_model.svh", "markers": ["task automatic state_model_check_all"]},
                {"path": "dv/blocks/coherent_cache_subsystem/tb/include/transaction_checkers.svh", "markers": ["task automatic expect_word", "task automatic expect_protocol_state"]},
                {"path": "dv/blocks/coherent_cache_subsystem/tb/include/ready_valid_assertions.svh", "markers": ["always_ff @(posedge clock) begin : ready_valid_assertions", "CPU%0d response changed while stalled"]},
            ],
        },
    },
    "AXI cache subsystem E2E (five fixed seeds)": {
        "id": "axi_subsystem",
        "top": "CoherentCacheAxiSubsystem_tb",
        "filelist": "dv/blocks/coherent_cache_axi_subsystem/filelist.f",
        "tests": ["seeds:6699,24301,12648430,195936478,219540062"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/coherent_cache_axi_subsystem/tb/include/benchmark_sequence.svh", "markers": ["PASS: AXI memory-model end-to-end MESI read/write stress"]},
                {"path": "dv/blocks/coherent_cache_axi_subsystem/tb/include/response_backpressure.svh", "markers": ["initial begin : axi_response_backpressure_injection", "AXI R response changed during forced backpressure"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/coherent_cache_axi_subsystem/tb/include/reference_model_and_cpu_tasks.svh", "markers": ["task automatic cpu_access", "returned %016x expected %016x"]},
                {"path": "dv/blocks/coherent_cache_axi_subsystem/tb/include/timeout_guard.svh", "markers": ["$fatal"]},
            ],
        },
    },
    "DirectoryController block": {
        "id": "directory_controller",
        "top": "DirectoryController_tb",
        "filelist": "dv/blocks/directory_controller/filelist.f",
        "tests": ["standalone directed block sequence"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/directory_controller/tb/include/test_sequence.svh", "markers": ["PASS DirectoryController_tb", "PASS: DIR_I Upgrade reports protocol error"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/directory_controller/tb/include/directory_agents.svh", "markers": ["task automatic finish_commit", "task automatic finish_grant", "$fatal"]},
            ],
        },
    },
    "DirectoryMshrBank block": {
        "id": "directory_mshr_bank",
        "top": "DirectoryMshrBank_tb",
        "filelist": "dv/blocks/directory_mshr_bank/filelist.f",
        "tests": ["standalone directed/stress sequence including write, transfer-start and grant stalls"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/directory_mshr_bank/tb/include/xfer_start_backpressure.svh", "markers": ["PASS: refill-start address/ID/context/source remain stable"]},
                {"path": "dv/blocks/directory_mshr_bank/tb/include/context_allocation_and_routing.svh", "markers": ["routes four distinct contexts and out-of-order fills"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/directory_mshr_bank/tb/include/mshr_agents.svh", "markers": ["task automatic complete_xfer", "task automatic accept_directory_writes", "task automatic accept_grants"]},
                {"path": "dv/blocks/directory_mshr_bank/tb/include/xfer_start_backpressure.svh", "markers": ["refill start payload changed during five-cycle backpressure", "complete_xfer(held_context)"]},
            ],
        },
    },
    "SharedLineEngine block": {
        "id": "shared_line_engine",
        "top": "SharedLineEngine_tb",
        "filelist": "dv/blocks/shared_line_engine/filelist.f",
        "tests": ["standalone grant, victim, refill, writeback and fault sequences"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/shared_line_engine/tb/include/engine_grant_cases.svh", "markers": ["test_grant_read_backpressure", "PASS: grant read backpressure"]},
                {"path": "dv/blocks/shared_line_engine/tb/include/engine_xfer_cases.svh", "markers": ["task automatic test_refill_hit_and_cold_miss", "one ordered eight-beat line"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/shared_line_engine/tb/include/engine_xfer_cases.svh", "markers": ["task automatic complete_xfer", "accepted transfer completion did not return engine to idle"]},
                {"path": "dv/blocks/shared_line_engine/tb/include/engine_fault_cases.svh", "markers": ["task automatic expect_engine_protocol_error"]},
            ],
        },
    },
    "MesiL1Controller block": {
        "id": "mesi_l1_controller",
        "top": "MesiL1Controller_tb",
        "filelist": "dv/blocks/mesi_l1_controller/filelist.f",
        "tests": ["standalone refill, snoop, reset and malformed-beat sequences"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/mesi_l1_controller/tb/include/cold_refill_and_local_write.svh", "markers": ["read miss Directory request mismatch", "refill completion did not request metadata update"]},
                {"path": "dv/blocks/mesi_l1_controller/tb/include/snoop_cases.svh", "markers": ["M SnoopInvalidate not accepted", "SnoopData first beat was not held under backpressure"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/mesi_l1_controller/tb/include/reset_and_protocol_error_cases.svh", "markers": ["$fatal", "protocol_error"]},
                {"path": "dv/blocks/mesi_l1_controller/tb/include/remote_owner_and_upgrade.svh", "markers": ["$fatal"]},
            ],
        },
    },
    "SharedL2DirectoryArray block": {
        "id": "shared_l2_directory_array",
        "top": "SharedL2DirectoryArray_tb",
        "filelist": "dv/blocks/shared_l2_directory_array/filelist.f",
        "tests": ["standalone lookup, stream, victim and malformed-write sequences"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/shared_l2_directory_array/tb/SharedL2DirectoryArray_tb.sv", "markers": ["PASS SharedL2DirectoryArray_tb"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/shared_l2_directory_array/tb/SharedL2DirectoryArray_tb.sv", "markers": ["$fatal", "protocol_error"]},
            ],
        },
    },
    "Bus blocks": {
        "id": "bus_blocks",
        "top": "CacheBusBlocks_tb",
        "filelist": "dv/blocks/bus_blocks/filelist.f",
        "tests": ["standalone AXI adapter and APB CSR directed sequences"],
        "regression_gate": "coherence_coverage_audit",
        "verification_contract": {
            "test_sources": [
                {"path": "dv/blocks/bus_blocks/tb/include/invalid_response_cases.svh", "markers": ["PASS: AXI4 burst adapter and APB performance CSR"]},
                {"path": "dv/blocks/bus_blocks/tb/include/outstanding_id_cases.svh", "markers": ["read adapter accepted more than four outstanding requests", "write adapter accepted more than four outstanding requests"]},
            ],
            "checker_sources": [
                {"path": "dv/blocks/bus_blocks/tb/include/bus_agents.svh", "markers": ["task automatic apb_read", "task automatic send_interleaved_r", "$fatal"]},
                {"path": "dv/blocks/bus_blocks/tb/include/invalid_response_cases.svh", "markers": ["adapter_protocol_error"]},
            ],
        },
    },
}

COVERAGE_FLAGS = ["--coverage-line", "--coverage-branch", "--coverage-toggle", "--coverage-fsm"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _source_input_paths() -> list[Path]:
    suffixes = {".sv", ".svh", ".v", ".vh", ".f", ".py", ".sby", ".ys", ".tcl", ".json", ".yml", ".yaml"}
    files: set[Path] = set()
    for dirname in ("rtl", "dv", "tests", "formal", "scripts"):
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if any(part in {"__pycache__", ".pytest_cache", "obj_dir", "build", "generated"} for part in path.parts):
                continue
            # The decision ledger is review evidence, not verification source.
            # Including it would make its source_fingerprint self-referential.
            if path == ROOT / "dv/coverage/rtl_release_decisions.json":
                continue
            files.add(path)
    files.update({ROOT / "Makefile", ROOT / "docs/cache.md", ROOT / "requirements-dv.txt"})
    files.update((ROOT / "dv/blocks").glob("**/README.md"))
    files.update((ROOT / "dv/blocks").glob("**/testplan.md"))
    return sorted(path for path in files if path.is_file())


def source_fingerprint() -> tuple[str, dict[str, str]]:
    source_hashes = {path.relative_to(ROOT).as_posix(): file_sha256(path) for path in _source_input_paths()}
    h = hashlib.sha256()
    for name, digest in source_hashes.items():
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest(), source_hashes


def _git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return result.stdout.strip()


def _tool_version(command: str, args: list[str]) -> str:
    try:
        result = subprocess.run([command, *args], cwd=ROOT, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {exc}"
    return (result.stdout or result.stderr).strip().splitlines()[0]


def _compiled_sources(name: str, dataset_id: str, top: str, filelist: str) -> tuple[list[str], str | None]:
    if dataset_id == "main_subsystem":
        candidate = ROOT / "reports/coherence/obj_dir" / f"V{top}__verFiles.dat"
    elif dataset_id == "axi_subsystem":
        candidate = ROOT / "reports/coherence/block_coverage/coherent_cache_axi_subsystem_obj" / f"V{top}__verFiles.dat"
    else:
        candidate = ROOT / "reports/coherence/block_coverage" / f"{dataset_id}_obj" / f"V{top}__verFiles.dat"
    if not candidate.is_file():
        return [], None
    product = audit.read_manifest()
    sources: set[str] = set()
    for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("S "):
            continue
        try:
            fields = shlex.split(line)
            path = audit.canonical_path(fields[-1])
        except (ValueError, IndexError):
            continue
        if path not in product and f"rtl/{path}" in product:
            path = f"rtl/{path}"
        if path.startswith("rtl/") and path.endswith((".sv", ".v")):
            sources.add(path)
    return sorted(sources), file_sha256(candidate)


def _metric_summary(dat: Path, info: Path) -> dict[str, dict[str, int]]:
    line_info = raw.read_line_info(info)
    points = raw.read_points(dat)
    totals, _ = raw.metric_counts(line_info, points)
    return {kind: {"hit": int(totals[kind][0]), "total": int(totals[kind][1]), "miss": int(totals[kind][1] - totals[kind][0])} for kind in raw.POINT_TYPES}


def _dataset_definition_fingerprint(meta: dict, tool_versions: dict, compiled: list[str], compiled_sha: str | None) -> str:
    contract_sources = {}
    contract = meta["verification_contract"]
    for group in ("test_sources", "checker_sources"):
        for source in contract[group]:
            path = ROOT / source["path"]
            contract_sources[source["path"]] = {
                "sha256": file_sha256(path),
                "markers": source["markers"],
            }
    definition = {
        "top": meta["top"],
        "filelist": meta["filelist"],
        "filelist_sha256": file_sha256(ROOT / meta["filelist"]),
        "compile_options": ["verilator --binary --timing --assert", *COVERAGE_FLAGS, "-CFLAGS -O0", "-Wall -Wno-fatal -Wno-BLKSEQ"],
        "tests": meta["tests"],
        "regression_gate": meta["regression_gate"],
        "verification_contract": contract_sources,
        "tool_versions": tool_versions,
        "compiled_product_sources": compiled,
        "compiled_manifest_sha256": compiled_sha,
    }
    return sha256_bytes(json.dumps(definition, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def build_manifest() -> dict:
    product = audit.read_manifest()
    source_fp, source_hashes = source_fingerprint()
    rtl_hashes = {name: source_hashes[name] for name in sorted(product)}
    rtl_fp = sha256_bytes(json.dumps(rtl_hashes, sort_keys=True, separators=(",", ":")).encode())
    tool_versions = {
        "python": sys.version.split()[0],
        "verilator": _tool_version("verilator", ["--version"]),
        "verilator_coverage": _tool_version("verilator_coverage", ["--version"]),
    }
    datasets = {}
    for label, (dat, info, scope) in raw.DATASETS.items():
        meta = DATASET_META[label]
        if not dat.is_file() or not info.is_file():
            raise FileNotFoundError(f"Missing raw coverage dataset for {label}: {dat} or {info}")
        compiled, compiled_sha = _compiled_sources(label, meta["id"], meta["top"], meta["filelist"])
        omitted = sorted(product - set(compiled)) if compiled else []
        meta_fp = _dataset_definition_fingerprint(meta, tool_versions, compiled, compiled_sha)
        filelist_sha = file_sha256(ROOT / meta["filelist"])
        dataset_fp = sha256_bytes(json.dumps({
            "raw_sha256": file_sha256(dat),
            "line_info_sha256": file_sha256(info),
            "dataset_definition_sha256": meta_fp,
            "filelist_sha256": filelist_sha,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        datasets[meta["id"]] = {
            "label": label,
            "scope": scope,
            "top": meta["top"],
            "filelist": meta["filelist"],
            "filelist_sha256": filelist_sha,
            "compile_options": ["verilator --binary --timing --assert", *COVERAGE_FLAGS, "-CFLAGS -O0", "-Wall -Wno-fatal -Wno-BLKSEQ"],
            "tests": meta["tests"],
            "regression_gate": meta["regression_gate"],
            "verification_contract": meta["verification_contract"],
            "verification_contract_sha256": meta_fp,
            "raw_file": dat.relative_to(ROOT).as_posix(),
            "raw_sha256": file_sha256(dat),
            "line_info_file": info.relative_to(ROOT).as_posix(),
            "line_info_sha256": file_sha256(info),
            "compiled_manifest_sha256": compiled_sha,
            "dataset_fingerprint": dataset_fp,
            "compiled_product_sources": compiled,
            "manifest_product_sources_missing_from_top": omitted,
            "metrics": _metric_summary(dat, info),
        }
    return {
        "schema_version": 1,
        "repository_head": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current"),
        "source_fingerprint": source_fp,
        "product_rtl_fingerprint": rtl_fp,
        "rtl_manifest": {
            "path": "rtl/Coherence.files.f",
            "sha256": file_sha256(ROOT / "rtl/Coherence.files.f"),
            "source_count": len(product),
            "sources": sorted(product),
            "source_sha256": rtl_hashes,
        },
        "source_file_sha256": source_hashes,
        "tool_versions": {
            **tool_versions,
        },
        "datasets": datasets,
    }


def main() -> None:
    manifest = build_manifest()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(manifest['datasets'])} independent datasets)")
    for dataset_id, item in manifest["datasets"].items():
        if item["manifest_product_sources_missing_from_top"]:
            print(f"NOTE {dataset_id}: {len(item['manifest_product_sources_missing_from_top'])} RTL manifest sources are outside this elaborated top")


if __name__ == "__main__":
    main()
