from __future__ import annotations

import hashlib
import json

from dv.coverage.rtl_release_gate import _manifest_errors, init_ledger, validate_point_decision


def point(count: int = 0) -> dict:
    return {
        "point_id": "RCP-LINE-EXAMPLE", "count": count,
        "source_sha256": "rtl-sha", "dataset_fingerprint": "dataset-sha",
    }


def decision(status: str = "PROVEN_UNREACHABLE", **overrides) -> dict:
    return {
        "status": status,
        "source_fingerprint": "source-sha",
        "source_sha256": "rtl-sha",
        "dataset_fingerprint": "dataset-sha",
        "rationale": "A reviewed invariant excludes this state.",
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
    (tmp_path / "proof.txt").write_text("proof result PASS\n")
    assert validate_point_decision(point(), decision(), tmp_path) == []
    (tmp_path / "proof.txt").unlink()
    assert any("missing" in item for item in validate_point_decision(point(), decision(), tmp_path))


def test_source_fingerprint_change_rejects_old_review():
    stale = decision(source_fingerprint="old-source")
    assert any("stale" in item for item in validate_point_decision(point(), stale, current_source_fingerprint="source-sha"))


def test_changed_rtl_source_sha_rejects_old_review():
    assert any("RTL source SHA changed" in item for item in validate_point_decision(point(), decision(source_sha256="old-rtl")))


def test_changed_dataset_fingerprint_rejects_old_review():
    assert any("dataset changed" in item for item in validate_point_decision(point(), decision(dataset_fingerprint="old-data")))


def test_open_required_point_fails():
    open_record = decision("OPEN")
    assert any("OPEN required coverage point" in item for item in validate_point_decision(point(), open_record))


def test_raw_hit_without_human_review_record_fails():
    errors = validate_point_decision(point(count=1), None)
    assert errors == ["RCP-LINE-EXAMPLE: raw hit has no human review record; OPEN"]


def test_covered_requires_nonzero_same_dataset_count_and_checkable_evidence(tmp_path):
    (tmp_path / "test.log").write_text("PASS test_x::checker_y; raw point count=1\n")
    covered = decision(
        "COVERED", evidence_ref="test_x::checker_y", evidence_kind="checker",
        evidence_path="test.log",
        evidence_sha256=hashlib.sha256((tmp_path / "test.log").read_bytes()).hexdigest(),
        reviewed_by="reviewer-a",
    )
    assert any("requires a nonzero count" in item for item in validate_point_decision(point(0), covered))
    assert validate_point_decision(point(1), covered, tmp_path) == []
    stale_evidence = dict(covered, evidence_sha256="stale")
    assert any("checksum" in item for item in validate_point_decision(point(1), stale_evidence, tmp_path))


def test_waiver_requires_independent_approval(tmp_path):
    (tmp_path / "proof.txt").write_text("reviewed waiver support\n")
    waived = decision("REVIEWED_WAIVER", evidence_kind="review", proof_ref="", approval_ref="review-ticket-7",
                      evidence_sha256=hashlib.sha256(b"reviewed waiver support\n").hexdigest(), approved_by="reviewer-a")
    assert any("independent approval" in item for item in validate_point_decision(point(), waived, tmp_path))


def test_ledger_initializer_never_overwrites(tmp_path):
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps({"points": [{"point_id": "existing", "status": "REVIEWED_WAIVER"}]}))
    try:
        init_ledger({"source_fingerprint": "x"}, path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("initializer overwrote manual decisions")
    assert json.loads(path.read_text())["points"][0]["status"] == "REVIEWED_WAIVER"


def test_manifest_head_drift_is_provenance_when_source_and_datasets_match():
    dataset = {
        "raw_sha256": "raw",
        "line_info_sha256": "line-info",
        "compiled_manifest_sha256": "compiled",
        "dataset_fingerprint": "dataset",
        "top": "ExampleTb",
        "filelist": "rtl/files.f",
        "compiled_product_sources": ["rtl/example.sv"],
    }
    saved = {
        "repository_head": "before-report-commit",
        "source_fingerprint": "source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {"example": dict(dataset)},
    }
    current = {
        "repository_head": "commit-containing-report",
        "source_fingerprint": "source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {"example": dict(dataset)},
    }

    assert _manifest_errors(saved, current) == []


def test_manifest_source_change_still_rejects_old_dataset():
    saved = {
        "repository_head": "before-source-change",
        "source_fingerprint": "old-source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {},
    }
    current = {
        "repository_head": "after-source-change",
        "source_fingerprint": "new-source",
        "rtl_manifest": {"sha256": "manifest", "sources": ["rtl/example.sv"]},
        "datasets": {},
    }

    assert any("stale for the current verification source fingerprint" in error
               for error in _manifest_errors(saved, current))
