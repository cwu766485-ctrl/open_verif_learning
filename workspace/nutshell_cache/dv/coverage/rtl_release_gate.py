"""Fail-closed, dataset-bound review gate for raw RTL coverage points."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dv.coverage import coherence_gap_review as audit
from dv.coverage import coverage_raw_runs as raw
from dv.coverage import rtl_coverage_dataset_manifest as manifest_lib


ROOT = audit.ROOT
DATASET_MANIFEST = ROOT / "reports/coherence/rtl_coverage_dataset_manifest.json"
DECISION_LEDGER = ROOT / "dv/coverage/rtl_release_decisions.json"
RUN_STATUS = ROOT / "reports/closure/rtl_release_regression_status.json"
REPORT_JSON = ROOT / "reports/final/rtl_release_gate.json"
REPORT_MD = ROOT / "reports/final/rtl_coverage_signoff.md"
POINT_MATRIX = ROOT / "reports/final/rtl_release_point_matrix.csv"

REQUIRED_GATES = [
    "coherence_verify",
    "coherence_full_system_verify",
    "coherence_hit_under_miss",
    "coherence_full_system_cross_closure",
    "coherence_full_system_stress",
    "coherence_coverage_audit",
    "coherence_full_system_evidence_gate",
    "coherence_full_system_replay_closure",
]
VALID_DECISIONS = {"OPEN", "BLOCKED", "COVERED", "PROVEN_UNREACHABLE", "REVIEWED_WAIVER"}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _point_id(dataset_id: str, metric: str, source: str, identity: str) -> str:
    token = _digest("\0".join((dataset_id, metric, source, identity)))[:20].upper()
    return f"RCP-{metric.upper()}-{token}"


def current_point_inventory(manifest: dict) -> list[dict]:
    product = set(manifest["rtl_manifest"]["sources"])
    inventory: list[dict] = []
    for dataset_id, dataset in manifest["datasets"].items():
        dat = ROOT / dataset["raw_file"]
        info = ROOT / dataset["line_info_file"]
        line_info = raw.read_line_info(info)
        points = raw.read_points(dat)
        seen: set[tuple[str, str]] = set()
        for source, line_map in line_info.items():
            if source not in product:
                continue
            for line, count in line_map.items():
                identity = str(line)
                point_id = _point_id(dataset_id, "line", source, identity)
                seen.add(("line", f"{source}|{identity}"))
                inventory.append({
                    "point_id": point_id, "dataset_id": dataset_id, "metric": "line",
                    "source": source, "identity": identity, "source_line": int(line),
                    "count": int(count), "source_sha256": manifest["rtl_manifest"]["source_sha256"][source],
                    "dataset_fingerprint": dataset["dataset_fingerprint"],
                })
        for (source, metric, identity), count in points.items():
            if source not in product or metric == "line" or metric not in raw.POINT_TYPES:
                continue
            point_key = (metric, f"{source}|{identity}")
            if point_key in seen:
                continue
            seen.add(point_key)
            try:
                source_line = int(identity.split("|", 1)[0])
            except (TypeError, ValueError):
                source_line = ""
            inventory.append({
                "point_id": _point_id(dataset_id, metric, source, identity),
                "dataset_id": dataset_id, "metric": metric, "source": source,
                "identity": identity, "source_line": source_line, "count": int(count),
                "source_sha256": manifest["rtl_manifest"]["source_sha256"][source],
                "dataset_fingerprint": dataset["dataset_fingerprint"],
            })
    return sorted(inventory, key=lambda row: (row["dataset_id"], row["metric"], row["source"], str(row["identity"])))


def _evidence_file(root: Path, decision: dict) -> tuple[Path | None, str | None]:
    rel = str(decision.get("evidence_path", "")).strip()
    if not rel:
        return None, "evidence_path is required"
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None, "evidence_path must stay inside the repository"
    if not path.is_file():
        return None, f"evidence file missing: {rel}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = str(decision.get("evidence_sha256", "")).strip()
    if not expected or expected != actual:
        return None, f"evidence checksum missing or stale: {rel}"
    return path, None


def validate_point_decision(
    point: dict, decision: dict | None, root: Path = ROOT,
    current_source_fingerprint: str | None = None,
) -> list[str]:
    """Validate one raw point against its decision, returning review failures."""
    errors: list[str] = []
    point_id = point["point_id"]
    if decision is None:
        raw_state = "raw hit" if int(point["count"]) > 0 else "zero count"
        return [f"{point_id}: {raw_state} has no human review record; OPEN"]
    status = str(decision.get("status", "OPEN")).upper()
    if status not in VALID_DECISIONS:
        return [f"{point_id}: invalid decision status {status!r}"]
    if current_source_fingerprint is not None and decision.get("source_fingerprint") != current_source_fingerprint:
        errors.append(f"{point_id}: reviewed source fingerprint is stale")
    if decision.get("source_sha256") != point["source_sha256"]:
        errors.append(f"{point_id}: RTL source SHA changed since review")
    if decision.get("dataset_fingerprint") != point["dataset_fingerprint"]:
        errors.append(f"{point_id}: raw coverage dataset changed since review")
    if status in {"OPEN", "BLOCKED"}:
        errors.append(f"{point_id}: {status} required coverage point")
        return errors
    if status == "COVERED":
        if int(point["count"]) <= 0:
            errors.append(f"{point_id}: COVERED requires a nonzero count in this exact dataset")
        for key in ("evidence_ref", "reviewed_by"):
            if not str(decision.get(key, "")).strip():
                errors.append(f"{point_id}: COVERED requires {key}")
        if decision.get("evidence_kind") not in {"test", "checker", "mutation"}:
            errors.append(f"{point_id}: COVERED requires test/checker evidence")
        _, file_error = _evidence_file(root, decision)
        if file_error:
            errors.append(f"{point_id}: {file_error}")
        return errors
    if int(point["count"]) > 0:
        errors.append(f"{point_id}: non-raw disposition used for a point already hit in this dataset")
    for key in ("rationale", "risk", "reviewed_by"):
        if not str(decision.get(key, "")).strip():
            errors.append(f"{point_id}: {key} is required for {status}")
    _, file_error = _evidence_file(root, decision)
    if file_error:
        errors.append(f"{point_id}: {file_error}")
    if status == "PROVEN_UNREACHABLE":
        if decision.get("evidence_kind") not in {"formal", "reachability"}:
            errors.append(f"{point_id}: PROVEN_UNREACHABLE requires formal/reachability evidence")
        if not str(decision.get("proof_ref", "")).strip():
            errors.append(f"{point_id}: PROVEN_UNREACHABLE requires a proof_ref")
        if not str(decision.get("approved_by", "")).strip() or decision.get("approved_by") == decision.get("reviewed_by"):
            errors.append(f"{point_id}: independent approval is required for PROVEN_UNREACHABLE")
    if status == "REVIEWED_WAIVER":
        if not str(decision.get("approval_ref", "")).strip():
            errors.append(f"{point_id}: REVIEWED_WAIVER requires an approval_ref")
        if not str(decision.get("approved_by", "")).strip() or decision.get("approved_by") == decision.get("reviewed_by"):
            errors.append(f"{point_id}: independent approval is required for REVIEWED_WAIVER")
    return errors


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def _manifest_errors(saved: dict, current: dict) -> list[str]:
    errors = []
    if saved.get("source_fingerprint") != current.get("source_fingerprint"):
        errors.append("coverage dataset manifest is stale for the current verification source fingerprint")
    # repository_head is provenance, not a content identity. The coverage
    # manifest is normally generated before its report is committed, so the
    # commit that records it necessarily changes HEAD. Source and dataset
    # fingerprints below provide the actual freshness checks.
    if saved.get("rtl_manifest", {}).get("sha256") != current.get("rtl_manifest", {}).get("sha256"):
        errors.append("RTL Source Manifest changed")
    old_sets, new_sets = saved.get("datasets", {}), current.get("datasets", {})
    if set(old_sets) != set(new_sets):
        errors.append("coverage dataset inventory changed")
    for name in sorted(set(old_sets) & set(new_sets)):
        for key in ("raw_sha256", "line_info_sha256", "compiled_manifest_sha256", "dataset_fingerprint", "top", "filelist"):
            if old_sets[name].get(key) != new_sets[name].get(key):
                errors.append(f"{name}: manifest field {key} is stale")
        # Block/AXI tops intentionally elaborate only their dependency slice.
        # Record omitted manifest sources for scope transparency; do not
        # mistake a smaller valid top for an incomplete compilation.
        compiled = set(old_sets[name].get("compiled_product_sources", []))
        if not compiled:
            errors.append(f"{name}: no Product RTL source was observed in the elaborated top")
        if compiled - set(saved.get("rtl_manifest", {}).get("sources", [])):
            errors.append(f"{name}: elaborated top contains RTL absent from the source manifest")
    return errors


def _regression_errors(source_fp: str) -> list[str]:
    if not RUN_STATUS.is_file():
        return [f"missing required regression evidence: {RUN_STATUS.relative_to(ROOT)}"]
    data = _read_json(RUN_STATUS)
    errors = []
    runs = data.get("runs", {})
    for gate in REQUIRED_GATES:
        record = runs.get(gate)
        if not isinstance(record, dict):
            errors.append(f"required regression not recorded: {gate}")
            continue
        if record.get("result") != "PASS" or record.get("returncode") != 0:
            errors.append(f"required regression did not PASS: {gate}")
        if record.get("source_fingerprint_before") != source_fp or record.get("source_fingerprint_after") != source_fp:
            errors.append(f"{gate}: test run source fingerprint differs from current source")
        log_path = record.get("log", "")
        if not log_path or not (ROOT / log_path).is_file():
            errors.append(f"{gate}: regression log missing")
        if record.get("command") != f"make COHERENCE_JOBS=2 {gate}":
            errors.append(f"{gate}: recorded command is not the required reproducible invocation")
    return errors


def evaluate(manifest: dict, ledger: dict, run_data: dict | None, root: Path = ROOT) -> dict:
    inventory = current_point_inventory(manifest)
    records = ledger.get("points", [])
    decisions = {item.get("point_id"): item for item in records if item.get("point_id")}
    known_ids = {point["point_id"] for point in inventory}
    errors: list[str] = []
    source_fp = manifest["source_fingerprint"]
    for point in inventory:
        decision = decisions.get(point["point_id"])
        errors.extend(validate_point_decision(point, decision, root, source_fp))
    for point_id in sorted(set(decisions) - known_ids):
        errors.append(f"{point_id}: ledger point is absent from current datasets (stale review record)")

    totals: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    excluded: Counter[tuple[str, str]] = Counter()
    for point in inventory:
        pair = totals[point["dataset_id"]][point["metric"]]
        pair[1] += 1
        pair[0] += int(point["count"] > 0)
        decision = decisions.get(point["point_id"], {})
        if decision.get("status") in {"PROVEN_UNREACHABLE", "REVIEWED_WAIVER"} and not validate_point_decision(point, decision, root, source_fp):
            excluded[(point["dataset_id"], point["metric"])] += 1

    eligible = {}
    for dataset_id, metrics in totals.items():
        eligible[dataset_id] = {}
        for metric, (hit, total) in metrics.items():
            excluded_count = excluded[(dataset_id, metric)]
            eligible[dataset_id][metric] = {
                "raw_hit": hit, "raw_total": total, "raw_miss": total - hit,
                "excluded_by_approved_review": excluded_count,
                "eligible_hit": hit,
                "eligible_total": total - excluded_count,
                "eligible_miss": max(0, total - excluded_count - hit),
            }

    if run_data is None:
        errors.extend(_regression_errors(source_fp))
    else:
        runs = run_data.get("runs", {})
        for gate in REQUIRED_GATES:
            record = runs.get(gate)
            if not isinstance(record, dict) or record.get("result") != "PASS" or record.get("returncode") != 0:
                errors.append(f"negative-test fixture missing PASS regression: {gate}")
    return {
        "status": "PASS" if not errors else "OPEN",
        "source_fingerprint": source_fp,
        "point_count": len(inventory),
        "hit_count_points": sum(int(point["count"]) > 0 for point in inventory),
        "zero_count_points": sum(int(point["count"]) == 0 for point in inventory),
        "dataset_metrics": eligible,
        "errors": errors,
        "inventory": inventory,
    }


def init_ledger(manifest: dict, path: Path = DECISION_LEDGER) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing decision ledger: {path}")
    inventory = current_point_inventory(manifest)
    ledger = {
        "schema_version": 1,
        "policy": "Human-reviewed, dataset-bound decisions only. This initializer creates OPEN rows and never grants waivers.",
        "source_fingerprint": manifest["source_fingerprint"],
        "points": [
            {
                "point_id": point["point_id"], "dataset_id": point["dataset_id"],
                "metric": point["metric"], "source": point["source"],
                "source_line": point["source_line"], "identity": point["identity"],
                "source_sha256": point["source_sha256"],
                "dataset_fingerprint": point["dataset_fingerprint"],
                "source_fingerprint": manifest["source_fingerprint"],
                "required": True, "status": "OPEN", "rationale": "Awaiting point-level human review.",
                "risk": "UNASSESSED", "reviewed_by": "", "approved_by": "",
                "evidence_path": "", "evidence_sha256": "", "evidence_ref": "",
            }
            for point in inventory
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Initialized {path.relative_to(ROOT)} with {len(ledger['points'])} OPEN point decisions; no point was waived.")


def write_point_matrix(result: dict) -> None:
    fields = ["point_id", "dataset_id", "metric", "raw_count", "raw_status", "source", "source_line", "identity", "source_sha256", "dataset_fingerprint", "decision_status", "rationale", "risk", "evidence_path", "reviewed_by", "approved_by"]
    ledger = _read_json(DECISION_LEDGER) if DECISION_LEDGER.is_file() else {"points": []}
    decisions = {row.get("point_id"): row for row in ledger.get("points", [])}
    POINT_MATRIX.parent.mkdir(parents=True, exist_ok=True)
    with POINT_MATRIX.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for point in result["inventory"]:
            decision = decisions.get(point["point_id"], {})
            writer.writerow({
                "point_id": point["point_id"], "dataset_id": point["dataset_id"],
                "metric": point["metric"], "raw_count": point["count"],
                "raw_status": "HIT" if point["count"] else "ZERO",
                "source": point["source"], "source_line": point["source_line"],
                "identity": point["identity"], "source_sha256": point["source_sha256"],
                "dataset_fingerprint": point["dataset_fingerprint"],
                "decision_status": decision.get("status", "RAW-HIT-UNREVIEWED" if point["count"] else "OPEN"),
                "rationale": decision.get("rationale", ""), "risk": decision.get("risk", ""),
                "evidence_path": decision.get("evidence_path", decision.get("evidence_ref", "")),
                "reviewed_by": decision.get("reviewed_by", ""), "approved_by": decision.get("approved_by", ""),
            })


def write_report(result: dict, manifest_errors: list[str]) -> None:
    errors = manifest_errors + result["errors"]
    status = "PASS" if not errors else "OPEN"
    report = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_fingerprint": result["source_fingerprint"],
        "repository_head": _read_json(DATASET_MANIFEST).get("repository_head") if DATASET_MANIFEST.is_file() else "unavailable",
        "point_count": result["point_count"],
        "hit_count_points": result["hit_count_points"],
        "zero_count_points": result["zero_count_points"],
        "dataset_metrics": result["dataset_metrics"],
        "manifest_errors": manifest_errors,
        "errors": result["errors"],
        "waiver_count": sum(row.get("status") == "REVIEWED_WAIVER" for row in _read_json(DECISION_LEDGER).get("points", [])) if DECISION_LEDGER.is_file() else 0,
        "required_regression_gates": REQUIRED_GATES,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    point_decisions = _read_json(DECISION_LEDGER).get("points", []) if DECISION_LEDGER.is_file() else []
    decision_counts = Counter(str(row.get("status", "OPEN")).upper() for row in point_decisions)
    decisions_by_id = {row.get("point_id"): row for row in point_decisions}
    hit_unreviewed = sum(1 for point in result["inventory"]
                         if int(point["count"]) > 0 and point["point_id"] not in decisions_by_id)
    zero_unreviewed = sum(1 for point in result["inventory"]
                          if int(point["count"]) == 0 and point["point_id"] not in decisions_by_id)
    findings_by_dataset_metric: Counter[tuple[str, str]] = Counter()
    inventory_by_id = {point["point_id"]: point for point in result["inventory"]}
    for error in errors:
        # Point-level details stay in JSON/CSV. Keep the human report concise.
        matching = inventory_by_id.get(error.split(":", 1)[0])
        if matching:
            findings_by_dataset_metric[(matching["dataset_id"], matching["metric"])] += 1
        else:
            findings_by_dataset_metric[("manifest", "infrastructure")] += 1
    lines = [
        "# RTL Code Coverage Release Gate", "", f"**Decision: {status}**", "",
        f"- Repository HEAD: `{report['repository_head']}`",
        f"- Verification source fingerprint: `{result['source_fingerprint']}`",
        f"- Raw points inventoried: {result['point_count']}; zero-count points: {result['zero_count_points']}",
        f"- Point decisions recorded: {len(point_decisions)} (COVERED={decision_counts['COVERED']}, PROVEN_UNREACHABLE={decision_counts['PROVEN_UNREACHABLE']}, REVIEWED_WAIVER={decision_counts['REVIEWED_WAIVER']}, OPEN={decision_counts['OPEN']}, BLOCKED={decision_counts['BLOCKED']})",
        f"- Unreviewed raw-hit points: {hit_unreviewed}; unreviewed zero-count points: {zero_unreviewed}",
        f"- Reviewed waivers accepted: {report['waiver_count']}",
        "", "Coverage remains separated by elaborated top and metric; these tables are not summed across datasets.",
        "The candidate counts below exclude only approved unreachable/waiver points. They are not a Reviewed Eligible Coverage sign-off while point dispositions remain open.",
        "", "| Dataset | Metric | Raw hit/total | Candidate hit/total after approved exclusions | Candidate misses |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for dataset_id, metrics in sorted(result["dataset_metrics"].items()):
        for metric, item in sorted(metrics.items()):
            lines.append(f"| {dataset_id} | {metric} | {item['raw_hit']}/{item['raw_total']} | {item['eligible_hit']}/{item['eligible_total']} | {item['eligible_miss']} |")
    lines += ["", "## Open gate findings by dataset and metric", ""]
    if not errors:
        lines.append("No gate findings.")
    else:
        lines.extend(f"- {dataset_id} / {metric}: {count} unresolved finding(s)" for (dataset_id, metric), count in sorted(findings_by_dataset_metric.items()))
        lines.append(f"- {len(errors)} total point-level/infrastructure finding(s); see the machine-readable gate JSON and point matrix for stable IDs and details.")
    lines += ["", "A PASS requires a current-source/current-dataset human disposition for every inventoried point. COVERED requires a nonzero count in the same raw dataset plus evidence; unreachable/waiver dispositions require independent review. All required regression commands must also be recorded PASS. Decisions never increase Raw Coverage.", ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    write_point_matrix(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init-ledger", action="store_true", help="create an OPEN-only ledger; refuses to overwrite")
    parser.add_argument("--write-manifest", action="store_true", help="capture current source and raw dataset fingerprints")
    parser.add_argument("--check", action="store_true", help="validate current evidence and emit signoff report")
    args = parser.parse_args()
    try:
        current = manifest_lib.build_manifest()
        if args.write_manifest:
            DATASET_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
            DATASET_MANIFEST.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Wrote {DATASET_MANIFEST.relative_to(ROOT)}")
        if args.init_ledger:
            init_ledger(current)
        if not args.check:
            return 0
        saved = _read_json(DATASET_MANIFEST)
        manifest_errors = _manifest_errors(saved, current)
        ledger = _read_json(DECISION_LEDGER)
        result = evaluate(current, ledger, None)
        write_report(result, manifest_errors)
        print(f"RTL release gate: {('PASS' if not manifest_errors and not result['errors'] else 'OPEN')}; raw zero points={result['zero_count_points']}; findings={len(manifest_errors) + len(result['errors'])}")
        for error in (manifest_errors + result["errors"])[:20]:
            print(f"OPEN: {error}")
        return 0 if not manifest_errors and not result["errors"] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"RTL release gate infrastructure error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
