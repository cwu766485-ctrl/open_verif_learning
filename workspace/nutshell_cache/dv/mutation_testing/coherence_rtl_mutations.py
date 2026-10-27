"""Mutate real MESI controller RTL and require its directed checker to fail.

This complements ``dv.fault_injection`` which mutates checker expectations. The
campaign changes isolated RTL expressions, rebuilds the actual controller with
its existing module-level SystemVerilog testbench, and passes only when that
testbench rejects the defective implementation for the expected reason.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RTL = PROJECT_ROOT / "rtl" / "l1" / "MesiL1Controller.sv"
OUT = PROJECT_ROOT / "reports" / "coherence" / "mutations"
TB = PROJECT_ROOT / "tests" / "l1" / "rtl" / "MesiL1Controller_tb.sv"


@dataclass(frozen=True)
class Mutation:
    name: str
    anchor: str
    replacement: str
    expected_checker_failure: str


MUTATIONS = (
    Mutation(
        "remote_read_must_downgrade_m_owner",
        "snoop_meta_state_q <= MESI_S;",
        "snoop_meta_state_q <= MESI_M;",
        "M-to-S Snoop metadata update missing",
    ),
    Mutation(
        "owner_data_response_must_mark_data_present",
        "snoop_rsp_has_data_q <= 1'b1;\n                snoop_meta_state_q <= MESI_S;",
        "snoop_rsp_has_data_q <= 1'b0;\n                snoop_meta_state_q <= MESI_S;",
        "Snoop response header mismatch",
    ),
)


def _run_one(mutation: Mutation) -> dict[str, object]:
    original = RTL.read_text(encoding="utf-8")
    count = original.count(mutation.anchor)
    if count != 1:
        raise RuntimeError(
            f"{mutation.name}: expected one RTL anchor, found {count}"
        )
    mutated = original.replace(mutation.anchor, mutation.replacement, 1)
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{mutation.name}_", dir=OUT) as tmp:
        work = Path(tmp)
        mutant_rtl = work / "MesiL1Controller_mutant.sv"
        mutant_rtl.write_text(mutated, encoding="utf-8")
        obj = work / "obj"
        compile_cmd = [
            "verilator", "--binary", "--timing", "--assert", "-j", "2",
            "-Wall", "-Wno-fatal", "-Wno-BLKSEQ",
            "--top-module", "MesiL1Controller_tb", "--Mdir", str(obj),
            str(PROJECT_ROOT / "rtl/common/CoherenceProtocol.sv"),
            str(PROJECT_ROOT / "rtl/l1/MesiL1SnoopArbiter.sv"),
            str(mutant_rtl), str(TB),
        ]
        compiled = subprocess.run(
            compile_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
            timeout=240, check=False,
        )
        compile_log = compiled.stdout + "\n" + compiled.stderr
        (OUT / f"{mutation.name}.build.log").write_text(
            compile_log, encoding="utf-8"
        )
        if compiled.returncode != 0:
            raise RuntimeError(
                f"{mutation.name}: mutated RTL failed to compile, not a caught bug; "
                f"see reports/coherence/mutations/{mutation.name}.build.log\n"
                f"{compile_log[-3000:]}"
            )

        sim = subprocess.run(
            [str(obj / "VMesiL1Controller_tb")], cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=60, check=False,
        )
        sim_log = sim.stdout + "\n" + sim.stderr
        (OUT / f"{mutation.name}.sim.log").write_text(
            sim_log, encoding="utf-8"
        )
        caught = (
            sim.returncode != 0
            and mutation.expected_checker_failure in sim_log
        )
        return {
            "mutation": mutation.name,
            "caught": caught,
            "return_code": sim.returncode,
            "expected_checker_failure": mutation.expected_checker_failure,
            "observed": sim_log.strip().splitlines()[-1:] or ["no simulator output"],
            "build_log": f"reports/coherence/mutations/{mutation.name}.build.log",
            "simulation_log": f"reports/coherence/mutations/{mutation.name}.sim.log",
        }


def run_all() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    records = [_run_one(mutation) for mutation in MUTATIONS]
    caught = sum(record["caught"] is True for record in records)
    report = {
        "status": "PASS" if caught == len(MUTATIONS) else "FAIL",
        "caught": caught,
        "total": len(MUTATIONS),
        "scope": "real MesiL1Controller.sv; existing MesiL1Controller_tb.sv",
        "mutations": records,
    }
    (OUT / "rtl_mutation_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if caught != len(MUTATIONS):
        missed = [record["mutation"] for record in records
                  if record["caught"] is not True]
        raise AssertionError(f"MESI RTL checker missed mutations: {missed}")
    return report


def main() -> None:
    if shutil.which("verilator") is None:
        raise RuntimeError("verilator is required; source scripts/env.sh first")
    result = run_all()
    print(f"MESI RTL mutations caught: {result['caught']}/{result['total']}")
    for mutation in result["mutations"]:
        print(f"  PASS {mutation['mutation']} -> checker rejected RTL fault")


if __name__ == "__main__":
    main()
