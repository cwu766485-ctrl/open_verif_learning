from __future__ import annotations

import hashlib
import json

from dv.coverage import rtl_release_gate as gate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_manifest(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "rtl").mkdir()
    (tmp_path / "tests/test.svh").write_text("TEST_CASE: legal_read\n")
    (tmp_path / "tests/checker.svh").write_text("CHECKER_PASS: returned_data_matches\n")
    (tmp_path / "rtl/example.sv").write_text("module example; endmodule\n")
    src_hash = sha(tmp_path / "rtl/example.sv")
    test_hash = sha(tmp_path / "tests/test.svh")
    checker_hash = sha(tmp_path / "tests/checker.svh")
    return {
        "source_fingerprint": "source-sha",
        "source_file_sha256": {
            "tests/test.svh": test_hash,
            "tests/checker.svh": checker_hash,
        },
        "rtl_manifest": {
            "sources": ["rtl/example.sv"],
            "source_sha256": {"rtl/example.sv": src_hash},
        },
        "datasets": {
            "main": {
                "dataset_fingerprint": "dataset-sha",
                "top": "ExampleTb",
                "regression_gate": "coherence_coverage_audit",
                "verification_contract": {
                    "test_sources": [{"path": "tests/test.svh", "markers": ["TEST_CASE: legal_read"]}],
                    "checker_sources": [{"path": "tests/checker.svh", "markers": ["CHECKER_PASS: returned_data_matches"]}],
                },
            },
        },
    }


def make_point(count=0, dataset_id="main"):
    source = "rtl/example.sv"
    identity = "12"
    return {
        "point_id": gate._point_id(dataset_id, "line", source, identity),
        "dataset_id": dataset_id,
        "metric": "line",
        "source": source,
        "identity": identity,
        "source_line": 12,
        "count": count,
        "source_sha256": "" ,
        "dataset_fingerprint": "dataset-sha",
    }


def make_runs(tmp_path):
    runs = {}
    for required in gate.REQUIRED_GATES:
        log = tmp_path / "logs" / f"{required}.log"
        log.parent.mkdir(exist_ok=True)
        log.write_text(f"{required}: PASS\n")
        runs[required] = {
            "result": "PASS",
            "returncode": 0,
            "source_fingerprint_before": "source-sha",
            "source_fingerprint_after": "source-sha",
            "command": f"make COHERENCE_JOBS=2 {required}",
            "log": log.relative_to(tmp_path).as_posix(),
            "log_sha256": sha(log),
        }
    return {"runs": runs}


def test_raw_hit_is_machine_attested_without_human_ledger(monkeypatch, tmp_path):
    manifest = make_manifest(tmp_path)
    point = make_point(count=1)
    point["source_sha256"] = manifest["rtl_manifest"]["source_sha256"][point["source"]]
    monkeypatch.setattr(gate, "current_point_inventory", lambda _: [point])

    result = gate.evaluate(manifest, {"points": []}, make_runs(tmp_path), tmp_path)

    assert result["status"] == "PASS"
    assert result["raw_hit_attested_points"] == 1
    assert result["raw_hit_unattested_points"] == 0
    assert point["raw_attestation"] == "RAW_COVERED"


def test_raw_hit_is_not_attested_without_checker_contract(monkeypatch, tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["datasets"]["main"]["verification_contract"]["checker_sources"] = []
    point = make_point(count=1)
    point["source_sha256"] = manifest["rtl_manifest"]["source_sha256"][point["source"]]
    monkeypatch.setattr(gate, "current_point_inventory", lambda _: [point])

    result = gate.evaluate(manifest, {"points": []}, make_runs(tmp_path), tmp_path)

    assert result["status"] == "OPEN"
    assert result["raw_hit_attested_points"] == 0
    assert result["raw_hit_unattested_points"] == 1
    assert any("checker_sources" in error for error in result["contract_errors"])


def test_missing_zero_review_stays_open(monkeypatch, tmp_path):
    manifest = make_manifest(tmp_path)
    point = make_point(count=0)
    point["source_sha256"] = manifest["rtl_manifest"]["source_sha256"][point["source"]]
    monkeypatch.setattr(gate, "current_point_inventory", lambda _: [point])

    result = gate.evaluate(manifest, {"points": []}, make_runs(tmp_path), tmp_path)

    assert result["status"] == "OPEN"
    assert result["zero_open_or_blocked_points"] == 1
    assert any("zero-count point has no review record" in error for error in result["errors"])


def test_point_id_is_bound_to_dataset_identity(monkeypatch, tmp_path):
    manifest = make_manifest(tmp_path)
    point = make_point(count=1)
    point["source_sha256"] = manifest["rtl_manifest"]["source_sha256"][point["source"]]
    point["identity"] = "13"
    monkeypatch.setattr(gate, "current_point_inventory", lambda _: [point])

    result = gate.evaluate(manifest, {"points": []}, make_runs(tmp_path), tmp_path)
    assert any("Point ID does not match" in error for error in result["errors"])
    assert gate._point_id("main", "line", point["source"], "12") != gate._point_id("other", "line", point["source"], "12")


def test_active_legacy_decision_cannot_override_raw_hit(monkeypatch, tmp_path):
    manifest = make_manifest(tmp_path)
    point = make_point(count=1)
    point["source_sha256"] = manifest["rtl_manifest"]["source_sha256"][point["source"]]
    monkeypatch.setattr(gate, "current_point_inventory", lambda _: [point])
    old = {
        "point_id": point["point_id"], "status": "COVERED",
        "source_fingerprint": "source-sha", "source_sha256": point["source_sha256"],
        "dataset_fingerprint": "dataset-sha",
    }

    result = gate.evaluate(manifest, {"points": [old]}, make_runs(tmp_path), tmp_path)
    assert any("active human disposition on a raw hit" in error for error in result["errors"])


def test_stale_regression_log_hash_invalidates_attestation(tmp_path):
    runs = make_runs(tmp_path)
    runs["runs"]["coherence_coverage_audit"]["log_sha256"] = "stale"
    errors = gate._regression_errors("source-sha", runs, tmp_path)
    assert any("log checksum missing or stale" in error for error in errors)


def decision(status="PROVEN_UNREACHABLE", **overrides):
    return {
        "status": status,
        "source_fingerprint": "source-sha",
        "source_sha256": "rtl-sha",
        "dataset_fingerprint": "dataset-sha",
        "dataset_id": "main",
        "metric": "line",
        "source": "rtl/example.sv",
        "identity": "12",
        "rationale": "An independently reviewed invariant excludes this state.",
        "risk": "Low after proof review.",
        "reviewed_by": "reviewer-a",
        "approved_by": "reviewer-b",
        "evidence_kind": "formal",
        "proof_ref": "property p_state_unreachable",
        "evidence_path": "proof.txt",
        "evidence_sha256": hashlib.sha256(b"proof result PASS\n").hexdigest(),
        **overrides,
    }


def test_unreachable_requires_existing_matching_proof(tmp_path):
    p = make_point(0)
    p["source_sha256"] = "rtl-sha"
    (tmp_path / "proof.txt").write_text("proof result PASS\n")
    assert gate.validate_point_decision(p, decision(), tmp_path) == []
    (tmp_path / "proof.txt").unlink()
    assert any("missing" in item for item in gate.validate_point_decision(p, decision(), tmp_path))


def test_review_rejects_stale_source_and_dataset():
    p = make_point(0)
    p["source_sha256"] = "rtl-sha"
    stale = decision(source_fingerprint="old-source", dataset_fingerprint="old-dataset")
    errors = gate.validate_point_decision(p, stale, current_source_fingerprint="source-sha")
    assert any("source fingerprint is stale" in item for item in errors)
    assert any("dataset changed" in item for item in errors)


def test_zero_count_cannot_be_reviewed_as_covered(tmp_path):
    p = make_point(0)
    p["source_sha256"] = "rtl-sha"
    covered = decision("COVERED", evidence_kind="checker", evidence_ref="test::checker")
    (tmp_path / "proof.txt").write_text("proof result PASS\n")
    errors = gate.validate_point_decision(p, covered, tmp_path)
    assert any("raw count zero" in item for item in errors)


def test_waiver_requires_independent_approval(tmp_path):
    p = make_point(0)
    p["source_sha256"] = "rtl-sha"
    (tmp_path / "proof.txt").write_text("reviewed waiver support\n")
    waived = decision("REVIEWED_WAIVER", evidence_kind="review", proof_ref="", approval_ref="review-ticket-7",
                      evidence_sha256=hashlib.sha256(b"reviewed waiver support\n").hexdigest(), approved_by="reviewer-a")
    assert any("independent approval" in item for item in gate.validate_point_decision(p, waived, tmp_path))


def test_ledger_initializer_never_overwrites(tmp_path):
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps({"points": [{"point_id": "existing", "status": "REVIEWED_WAIVER"}]}))
    try:
        gate.init_ledger({}, path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("initializer overwrote manual decisions")
    assert json.loads(path.read_text())["points"][0]["status"] == "REVIEWED_WAIVER"


def test_manifest_head_drift_is_provenance_when_scope_hashes_match():
    dataset = {
        "raw_sha256": "raw", "line_info_sha256": "line-info",
        "compiled_manifest_sha256": "compiled", "dataset_fingerprint": "dataset",
        "top": "ExampleTb", "filelist": "rtl/files.f", "filelist_sha256": "fl",
        "regression_gate": "coherence_coverage_audit", "verification_contract_sha256": "contract",
        "compiled_product_sources": ["rtl/example.sv"],
    }
    saved = {
        "repository_head": "before-report-commit", "source_fingerprint": "source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {"example": dict(dataset)},
    }
    current = {
        "repository_head": "commit-containing-report", "source_fingerprint": "source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {"example": dict(dataset)},
    }
    assert gate._manifest_errors(saved, current) == []


def test_manifest_source_change_still_rejects_old_dataset():
    saved = {
        "repository_head": "before-source-change", "source_fingerprint": "old-source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]}, "datasets": {},
    }
    current = {
        "repository_head": "after-source-change", "source_fingerprint": "new-source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]}, "datasets": {},
    }
    assert any("stale for the current verification source fingerprint" in error
               for error in gate._manifest_errors(saved, current))
