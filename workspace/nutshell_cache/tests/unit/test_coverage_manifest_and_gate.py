from __future__ import annotations

from dv.coverage import coherence_gap_review as audit
from dv.coverage.rtl_release_gate import _manifest_errors


def test_all_manifest_sources_are_classified_as_product_rtl():
    product = audit.read_manifest()
    assert len(product) == 18
    assert any(path.startswith("rtl/coherence/") for path in product)
    assert any(path.startswith("rtl/interconnect/") for path in product)
    assert all(audit.classify(path, product) == "Product RTL" for path in product)


def test_independent_top_dependency_slice_is_not_a_manifest_failure():
    saved = {
        "source_fingerprint": "source",
        "repository_head": "head",
        "rtl_manifest": {"sha256": "rtl", "sources": ["rtl/a.sv", "rtl/b.sv"]},
        "datasets": {
            "block": {
                "raw_sha256": "raw", "line_info_sha256": "info",
                "compiled_manifest_sha256": "compiled", "dataset_fingerprint": "data",
                "top": "BlockTb", "filelist": "block.f",
                "compiled_product_sources": ["rtl/a.sv"],
                "manifest_product_sources_missing_from_top": ["rtl/b.sv"],
            }
        },
    }
    assert _manifest_errors(saved, saved) == []


def test_unmanifested_compiled_source_is_rejected():
    saved = {
        "source_fingerprint": "source",
        "repository_head": "head",
        "rtl_manifest": {"sha256": "rtl", "sources": ["rtl/a.sv"]},
        "datasets": {
            "block": {
                "raw_sha256": "raw", "line_info_sha256": "info",
                "compiled_manifest_sha256": "compiled", "dataset_fingerprint": "data",
                "top": "BlockTb", "filelist": "block.f",
                "compiled_product_sources": ["rtl/not_in_manifest.sv"],
                "manifest_product_sources_missing_from_top": [],
            }
        },
    }
    assert any("absent from the source manifest" in error for error in _manifest_errors(saved, saved))


def test_known_uncovered_points_use_explicit_source_reviews():
    assert audit.reviewed_missed_category(
        "rtl/directory/DirectoryController.sv", 358,
        "grant_opcode_q <= GRANT_DATA_M;", "recover an invalid Upgrade"
    ) == "DIR_I 上收到 Upgrade：非法状态组合，fail-stop 错误路径"
    assert audit.reviewed_missed_category(
        "rtl/directory/DirectoryController.sv", 362,
        "default: begin", "invalid state encoding"
    ) == "Directory 状态编码 default：防御性 fail-stop，未证明不可达"
    assert audit.reviewed_missed_category(
        "rtl/l1/MesiL1Controller.sv", 317,
        "(grant_data_beat_idx == 3'd7)) begin", "CPU_ERROR"
    ) == "Refill beat/last 异常：CPU fail-stop 错误路径"
    assert audit.reviewed_missed_category(
        "rtl/l1/MesiL1Controller.sv", 439,
        "snoop_array_last", "SNP_ERROR"
    ) == "Snoop beat/last 异常：Snoop fail-stop 错误路径"
    assert audit.reviewed_missed_category(
        "rtl/interconnect/CpuMmioRouter.sv", 164,
        "mmio_state_q <= MMIO_IDLE;", "default"
    ) == "MMIO FSM 非法编码 default：防御性复位，未证明不可达"
    assert audit.reviewed_missed_category(
        "rtl/coherence/SharedLineEngine.sv", 348,
        "ENGINE_GRANT_READ: begin", "L2 line read handshake"
    ) == "合法 Grant Read / L2 Hit 等待路径（独立 Block 有命中）"
    assert audit.reviewed_missed_category(
        "rtl/coherence/SharedLineEngine.sv", 352,
        "memory_adapter_protocol_error <= 1'b1;", "L2 miss"
    ) == "Grant Read 后 L2 Miss：错误保护路径"
    assert audit.reviewed_missed_category(
        "rtl/directory/DirectoryMshrBank.sv", 362,
        "if (line_xfer_start_valid && !line_xfer_start_ready)", "ready"
    ) == "合法 ready/valid Offer Lock（独立 Block 有命中）"
    assert audit.reviewed_missed_category(
        "rtl/directory/DirectoryMshrBank.sv", 350,
        "if (snoop_req_valid && !snoop_req_ready)", "ready"
    ) != "合法 ready/valid Offer Lock（独立 Block 有命中）"
