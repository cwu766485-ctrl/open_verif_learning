"""Dataset-bound attestation for raw hits and review of zero-count RTL points.

Raw hits are machine-attested as code-execution evidence. They are not a
substitute for protocol checkers. Zero-count points remain under individual,
fail-closed human review.
"""

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
VALID_ZERO_DECISIONS = {"OPEN", "BLOCKED", "COVERED", "PROVEN_UNREACHABLE", "REVIEWED_WAIVER"}
VALID_METRICS = set(raw.POINT_TYPES)


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
                    "elaborated_top": dataset["top"],
                    "raw_coverage_sha256": dataset["raw_sha256"],
                    "line_info_sha256": dataset["line_info_sha256"],
                    "verification_contract_sha256": dataset["verification_contract_sha256"],
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
                "elaborated_top": dataset["top"],
                "raw_coverage_sha256": dataset["raw_sha256"],
                "line_info_sha256": dataset["line_info_sha256"],
                "verification_contract_sha256": dataset["verification_contract_sha256"],
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
    """Validate a zero-count point's independent review record.

    Raw hits do not need a human row here; their execution is attested by the
    dataset, source, contract and regression checks in :func:`evaluate`.
    """
    errors: list[str] = []
    point_id = point["point_id"]
    if decision is None:
        if int(point["count"]) > 0:
            return []
        return [f"{point_id}: zero-count point has no review record; OPEN"]
    status = str(decision.get("status", "OPEN")).upper()
    if status not in VALID_ZERO_DECISIONS:
        return [f"{point_id}: invalid decision status {status!r}"]
    if int(point["count"]) > 0:
        return [f"{point_id}: raw-hit point must use machine attestation, not a zero-count review disposition"]
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
        errors.append(f"{point_id}: COVERED is invalid while this exact dataset has raw count zero")
        return errors
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


def _validate_point_identity(point: dict, manifest: dict) -> list[str]:
    errors = []
    dataset_id = point.get("dataset_id", "")
    dataset = manifest.get("datasets", {}).get(dataset_id)
    if dataset is None:
        return [f"{point.get('point_id', '<missing>')}: point references unknown dataset {dataset_id!r}"]
    expected_id = _point_id(dataset_id, point.get("metric", ""), point.get("source", ""), str(point.get("identity", "")))
    if point.get("point_id") != expected_id:
        errors.append(f"{point.get('point_id', '<missing>')}: Point ID does not match dataset/metric/source/identity")
    if point.get("metric") not in VALID_METRICS:
        errors.append(f"{point.get('point_id', '<missing>')}: invalid coverage metric {point.get('metric')!r}")
    if point.get("dataset_fingerprint") != dataset.get("dataset_fingerprint"):
        errors.append(f"{point.get('point_id', '<missing>')}: point dataset fingerprint is stale")
    source_hash = manifest.get("rtl_manifest", {}).get("source_sha256", {}).get(point.get("source"))
    if source_hash is None:
        errors.append(f"{point.get('point_id', '<missing>')}: point source is absent from the Product RTL manifest")
    elif point.get("source_sha256") != source_hash:
        errors.append(f"{point.get('point_id', '<missing>')}: point source SHA does not match the Product RTL manifest")
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
        for key in ("raw_sha256", "line_info_sha256", "compiled_manifest_sha256", "dataset_fingerprint", "top", "filelist", "filelist_sha256", "regression_gate", "verification_contract_sha256"):
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


def _contract_errors(manifest: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    source_hashes = manifest.get("source_file_sha256", {})
    for dataset_id, dataset in manifest.get("datasets", {}).items():
        contract = dataset.get("verification_contract")
        if not isinstance(contract, dict):
            errors.append(f"{dataset_id}: missing verification contract")
            continue
        for group in ("test_sources", "checker_sources"):
            entries = contract.get(group)
            if not isinstance(entries, list) or not entries:
                errors.append(f"{dataset_id}: verification contract requires non-empty {group}")
                continue
            for entry in entries:
                rel = str(entry.get("path", ""))
                path = (root / rel).resolve()
                try:
                    path.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"{dataset_id}: {group} path escapes repository: {rel}")
                    continue
                if not rel or not path.is_file():
                    errors.append(f"{dataset_id}: {group} source missing: {rel}")
                    continue
                expected = source_hashes.get(rel)
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if not expected or expected != actual:
                    errors.append(f"{dataset_id}: {group} source hash missing/stale: {rel}")
                markers = entry.get("markers")
                if not isinstance(markers, list) or not markers:
                    errors.append(f"{dataset_id}: {group} source has no traceability markers: {rel}")
                else:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    for marker in markers:
                        if not isinstance(marker, str) or not marker or marker not in text:
                            errors.append(f"{dataset_id}: {group} marker missing in {rel}: {marker!r}")
        gate = dataset.get("regression_gate")
        if gate not in REQUIRED_GATES:
            errors.append(f"{dataset_id}: invalid or missing regression_gate {gate!r}")
    return errors


def _regression_errors(source_fp: str, run_data: dict | None = None, root: Path = ROOT) -> list[str]:
    if run_data is None:
        status_path = root / RUN_STATUS.relative_to(ROOT)
        if not status_path.is_file():
            return [f"missing required regression evidence: {status_path.relative_to(root)}"]
        data = _read_json(status_path)
    else:
        data = run_data
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
        resolved_log = (root / str(log_path)).resolve() if log_path else None
        if resolved_log is None or not resolved_log.is_file():
            errors.append(f"{gate}: regression log missing")
        else:
            try:
                resolved_log.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{gate}: regression log path escapes repository")
            else:
                actual_hash = hashlib.sha256(resolved_log.read_bytes()).hexdigest()
                if not record.get("log_sha256") or record.get("log_sha256") != actual_hash:
                    errors.append(f"{gate}: regression log checksum missing or stale")
                if record.get("result") == "PASS" and "PASS" not in resolved_log.read_text(encoding="utf-8", errors="replace") and gate not in {"coherence_full_system_evidence_gate", "coherence_full_system_replay_closure"}:
                    errors.append(f"{gate}: regression log has no PASS evidence marker")
        if record.get("command") != f"make COHERENCE_JOBS=2 {gate}":
            errors.append(f"{gate}: recorded command is not the required reproducible invocation")
    return errors


def evaluate(
    manifest: dict,
    ledger: dict,
    run_data: dict | None,
    root: Path = ROOT,
    manifest_errors: list[str] | None = None,
) -> dict:
    inventory = current_point_inventory(manifest)
    records = ledger.get("points", [])
    decisions = {item.get("point_id"): item for item in records if item.get("point_id")}
    known_ids = {point["point_id"] for point in inventory}
    errors: list[str] = []
    if len(decisions) != len(records):
        errors.append("decision ledger has duplicate or missing Point IDs")
    source_fp = manifest["source_fingerprint"]
    regression_errors = _regression_errors(source_fp, run_data, root)
    contract_errors = _contract_errors(manifest, root)
    errors.extend(regression_errors)
    errors.extend(contract_errors)
    errors.extend(manifest_errors or [])
    identity_errors = {point["point_id"]: _validate_point_identity(point, manifest) for point in inventory}
    for point in inventory:
        errors.extend(identity_errors[point["point_id"]])
        decision = decisions.get(point["point_id"])
        # Human ledger decisions exist only for zero-count points. A hit is
        # represented by the exact raw dataset attestation below.
        if int(point["count"]) == 0:
            if decision is not None:
                for key in ("dataset_id", "metric", "source", "identity"):
                    if decision.get(key) != point.get(key):
                        errors.append(f"{point['point_id']}: ledger {key} does not match stable point identity")
            errors.extend(validate_point_decision(point, decision, root, source_fp))
        elif decision is not None:
            errors.append(f"{point['point_id']}: active human disposition on a raw hit; archive legacy decision and use RAW_COVERED attestation")
    for point_id in sorted(set(decisions) - known_ids):
        errors.append(f"{point_id}: ledger point is absent from current datasets (stale review record)")

    # A point's raw execution attestation is dataset-scoped. It does not imply
    # that the corresponding behavior is functionally correct; protocol
    # correctness remains covered by the separately required evidence gate.
    passed_runs = (run_data or {}).get("runs", {}) if run_data is not None else {}
    if run_data is None and RUN_STATUS.is_file():
        try:
            passed_runs = _read_json(root / RUN_STATUS.relative_to(ROOT)).get("runs", {})
        except ValueError:
            passed_runs = {}
    common_attestation_valid = not (regression_errors or contract_errors or (manifest_errors or []))
    attested_by_dataset: Counter[str] = Counter()
    attested_by_dataset_metric: Counter[tuple[str, str]] = Counter()
    raw_hits_by_dataset: Counter[str] = Counter()
    for point in inventory:
        if int(point["count"]) <= 0:
            point["raw_attestation"] = "ZERO_COUNT_REVIEW_REQUIRED"
            continue
        dataset_id = point["dataset_id"]
        raw_hits_by_dataset[dataset_id] += 1
        gate = manifest["datasets"][dataset_id].get("regression_gate")
        run = passed_runs.get(gate, {}) if isinstance(passed_runs, dict) else {}
        if common_attestation_valid and not identity_errors[point["point_id"]] and run.get("result") == "PASS" and run.get("returncode") == 0 and run.get("source_fingerprint_before") == source_fp and run.get("source_fingerprint_after") == source_fp:
            attested_by_dataset[dataset_id] += 1
            attested_by_dataset_metric[(dataset_id, point["metric"])] += 1
            point["raw_attestation"] = "RAW_COVERED"
        else:
            point["raw_attestation"] = "RAW_HIT_UNATTESTED"

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
                "raw_hit_attested": attested_by_dataset_metric[(dataset_id, metric)],
                "excluded_by_approved_review": excluded_count,
                "eligible_hit": hit,
                "eligible_total": total - excluded_count,
                "eligible_miss": max(0, total - excluded_count - hit),
            }

    stale_history = ledger.get("stale_decisions", [])
    return {
        "status": "PASS" if not errors else "OPEN",
        "source_fingerprint": source_fp,
        "point_count": len(inventory),
        "hit_count_points": sum(int(point["count"]) > 0 for point in inventory),
        "zero_count_points": sum(int(point["count"]) == 0 for point in inventory),
        "raw_hit_attested_points": sum(attested_by_dataset.values()),
        "raw_hit_unattested_points": sum(raw_hits_by_dataset.values()) - sum(attested_by_dataset.values()),
        "zero_open_or_blocked_points": sum(int(point["count"]) == 0 and (decisions.get(point["point_id"], {}).get("status", "OPEN").upper() in {"OPEN", "BLOCKED"}) for point in inventory),
        "stale_decision_history_count": len(stale_history),
        "contract_errors": contract_errors,
        "regression_errors": regression_errors,
        "attested_points_by_dataset": dict(attested_by_dataset),
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
        "policy": "Raw hits are machine-attested per exact dataset; this initializer creates OPEN rows only for zero-count points and never grants waivers.",
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
            for point in inventory if int(point["count"]) == 0
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Initialized {path.relative_to(ROOT)} with {len(ledger['points'])} OPEN point decisions; no point was waived.")


def write_point_matrix(result: dict) -> None:
    fields = ["point_id", "dataset_id", "elaborated_top", "metric", "raw_count", "raw_status", "raw_coverage_sha256", "line_info_sha256", "verification_contract_sha256", "source", "source_line", "identity", "source_sha256", "dataset_fingerprint", "decision_status", "rationale", "risk", "evidence_path", "reviewed_by", "approved_by"]
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
                "elaborated_top": point["elaborated_top"],
                "metric": point["metric"], "raw_count": point["count"],
                "raw_status": point.get("raw_attestation", "ZERO_COUNT_REVIEW_REQUIRED"),
                "raw_coverage_sha256": point["raw_coverage_sha256"],
                "line_info_sha256": point["line_info_sha256"],
                "verification_contract_sha256": point["verification_contract_sha256"],
                "source": point["source"], "source_line": point["source_line"],
                "identity": point["identity"], "source_sha256": point["source_sha256"],
                "dataset_fingerprint": point["dataset_fingerprint"],
                "decision_status": "RAW_COVERED" if point.get("raw_attestation") == "RAW_COVERED" else decision.get("status", "OPEN"),
                "rationale": decision.get("rationale", ""), "risk": decision.get("risk", ""),
                "evidence_path": decision.get("evidence_path", decision.get("evidence_ref", "")),
                "reviewed_by": decision.get("reviewed_by", ""), "approved_by": decision.get("approved_by", ""),
            })


def write_report(result: dict, manifest_errors: list[str]) -> None:
    errors = result["errors"]
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
        "raw_hit_attested_points": result["raw_hit_attested_points"],
        "raw_hit_unattested_points": result["raw_hit_unattested_points"],
        "zero_open_or_blocked_points": result["zero_open_or_blocked_points"],
        "stale_decision_history_count": result["stale_decision_history_count"],
        "attested_points_by_dataset": result["attested_points_by_dataset"],
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
        f"- Raw points inventoried: {result['point_count']}; zero-count points requiring review: {result['zero_count_points']}",
        f"- Raw-hit execution attestations: {result['raw_hit_attested_points']}/{result['hit_count_points']}; unattested hits: {result['raw_hit_unattested_points']}",
        f"- Zero-point decisions recorded: {len(point_decisions)} (COVERED={decision_counts['COVERED']}, PROVEN_UNREACHABLE={decision_counts['PROVEN_UNREACHABLE']}, REVIEWED_WAIVER={decision_counts['REVIEWED_WAIVER']}, OPEN={decision_counts['OPEN']}, BLOCKED={decision_counts['BLOCKED']}); zero OPEN/BLOCKED: {result['zero_open_or_blocked_points']}",
        f"- Archived stale historical decisions: {result['stale_decision_history_count']}; unreviewed zero-count rows: {zero_unreviewed}",
        f"- Reviewed waivers accepted: {report['waiver_count']}",
        "", "Coverage remains separated by elaborated top and metric; these tables are not summed across datasets.",
        "RAW_COVERED means only that a nonzero point was observed in the exact hashed dataset under the recorded Top/source/tool/test/checker contract and required regression. It does not establish functional correctness; key protocol behavior requires the independent Functional-System Evidence Gate. Candidate counts exclude only independently reviewed unreachable/waiver points.",
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
    lines += ["", "A PASS requires current source and dataset fingerprints, hashed regression logs for all required gates, valid Test/Checker source contracts, and an individual accepted disposition for every zero-count point. A zero-count point cannot be marked COVERED; it must first be observed in this exact dataset. PROVEN_UNREACHABLE and REVIEWED_WAIVER require evidence and independent approval. Raw hits are never transferred across elaborated Tops, and no disposition changes Raw Coverage.", ""]
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
        result = evaluate(current, ledger, None, manifest_errors=manifest_errors)
        write_report(result, manifest_errors)
        print(f"RTL release gate: {('PASS' if not result['errors'] else 'OPEN')}; raw zero points={result['zero_count_points']}; findings={len(result['errors'])}")
        for error in result["errors"][:20]:
            print(f"OPEN: {error}")
        return 0 if not result["errors"] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"RTL release gate infrastructure error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
