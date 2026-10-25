"""Prove representative Stage3 RTL mutations are detected by formal checks."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_RTL_ROOT = PROJECT_ROOT / "rtl" / "legacy_l1"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "formal" / "mutations"


@dataclass(frozen=True)
class Mutation:
    name: str
    original: str
    replacement: str


MUTATIONS = (
    Mutation(
        "stalled_response_rdata",
        "assign io_out_bits_rdata = hit ? dataRead : inRdataRegDemand;",
        "assign io_out_bits_rdata = hit ? dataRead : io_mem_resp_bits_rdata;",
    ),
    Mutation(
        "byte_lane_mask",
        "wire [7:0] _wordMask_T_12 = io_in_bits_req_wmask[0] ? 8'hff : 8'h0;",
        "wire [7:0] _wordMask_T_12 = io_in_bits_req_wmask[1] ? 8'hff : 8'h0;",
    ),
    Mutation(
        "refill_data_bit",
        "wire [63:0] _dataRefill_T_3 = io_mem_resp_bits_rdata & _dataRefill_T_2;",
        "wire [63:0] _dataRefill_T_3 = (io_mem_resp_bits_rdata ^ 64'h1) & _dataRefill_T_2;",
    ),
    Mutation(
        "writeback_data_bit",
        "assign io_mem_req_bits_wdata = _dataHitWay_T_9 | _dataHitWay_T_7;",
        "assign io_mem_req_bits_wdata = (_dataHitWay_T_9 | _dataHitWay_T_7) ^ 64'h1;",
    ),
)


def _mutate(source: str, mutation: Mutation) -> str:
    count = source.count(mutation.original)
    if count != 1:
        raise RuntimeError(
            f"{mutation.name}: expected exactly one mutation anchor, found {count}"
        )
    return source.replace(mutation.original, mutation.replacement, 1)


def _run_one(mutation: Mutation) -> dict[str, object]:
    rtl_path = LEGACY_RTL_ROOT / "pipeline" / "CacheStage3.v"
    original_source = rtl_path.read_text(encoding="utf-8")
    mutated_source = _mutate(original_source, mutation)
    log_path = OUTPUT_DIR / f"{mutation.name}.log"

    with tempfile.TemporaryDirectory(prefix=f"{mutation.name}_", dir=OUTPUT_DIR) as tmp:
        work = Path(tmp)
        (work / "CacheStage3.v").write_text(mutated_source, encoding="utf-8")
        shutil.copyfile(
            LEGACY_RTL_ROOT / "control" / "MetaWriteArbiter.v",
            work / "MetaWriteArbiter.v",
        )
        shutil.copyfile(
            LEGACY_RTL_ROOT / "control" / "DataWriteArbiter.v",
            work / "DataWriteArbiter.v",
        )
        shutil.copyfile(
            PROJECT_ROOT / "formal" / "cache_stage3_lifecycle_harness.v",
            work / "CacheStage3LifecycleHarness.v",
        )
        script = work / "mutation.ys"
        script.write_text(
            "\n".join(
                (
                    "read_verilog -formal -D FORMAL -D CACHE_STAGE3_FORMAL -DSYNTHESIS "
                    "CacheStage3.v MetaWriteArbiter.v DataWriteArbiter.v "
                    "CacheStage3LifecycleHarness.v",
                    "prep -top CacheStage3LifecycleHarness -flatten",
                    "chformal -cover -remove",
                    "async2sync",
                    "chformal -lower",
                    "sat -prove-asserts -seq 8 -set-assumes -timeout 30 -verify",
                    "",
                )
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["yosys", "-Q", "-l", str(log_path), "-s", str(script)],
            cwd=work,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        combined = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return {
                "mutation": mutation.name,
                "caught": False,
                "result": "mutated design unexpectedly passed",
                "log": str(log_path.relative_to(PROJECT_ROOT)),
            }

        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        proof_failed = bool(
            re.search(
                r"SAT proof finished - model found: FAIL|model found: FAIL|proof failed",
                log_text + combined,
                re.IGNORECASE,
            )
        )
        if not proof_failed:
            raise RuntimeError(
                f"{mutation.name}: Yosys failed without a formal counterexample; "
                f"inspect {log_path}\n{combined[-3000:]}"
            )
        return {
            "mutation": mutation.name,
            "caught": True,
            "result": "formal assertion produced a counterexample",
            "log": str(log_path.relative_to(PROJECT_ROOT)),
        }


def run_all() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = [_run_one(mutation) for mutation in MUTATIONS]
    caught = sum(record["caught"] is True for record in records)
    report = {
        "status": "PASS" if caught == len(MUTATIONS) else "FAIL",
        "caught": caught,
        "total": len(MUTATIONS),
        "mutations": records,
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    if caught != len(MUTATIONS):
        missed = [record["mutation"] for record in records if not record["caught"]]
        raise AssertionError(f"formal check missed RTL mutations: {missed}")
    return report


def main() -> None:
    report = run_all()
    print(f"Formal RTL mutations caught: {report['caught']}/{report['total']}")
    for record in report["mutations"]:
        print(f"  PASS {record['mutation']} -> {record['result']}")


if __name__ == "__main__":
    main()
