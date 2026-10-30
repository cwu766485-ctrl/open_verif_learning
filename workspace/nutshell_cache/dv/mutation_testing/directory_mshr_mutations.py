"""Mutate the real Directory MSHR arbitration RTL and require its block TB to fail."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RTL = PROJECT_ROOT / "rtl/directory/DirectoryMshrBank.sv"
TB_DIR = PROJECT_ROOT / "dv/blocks/directory_mshr_bank/tb"
TB = TB_DIR / "DirectoryMshrBank_tb.sv"
OUT = PROJECT_ROOT / "reports/coherence/mutations"
ANCHOR = "if (snoop_valid_ctx[i] && !snoop_ready_ctx[i] &&"
MUTATION = "directory_mshr_stalled_snoop_put_must_bypass"
EXPECTED_FAILURE = "stalled-snoop target Put did not bypass the blocking L1"


def run() -> dict[str, object]:
    source = RTL.read_text(encoding="utf-8")
    if source.count(ANCHOR) != 1:
        raise RuntimeError(f"{MUTATION}: expected one RTL anchor, found {source.count(ANCHOR)}")
    mutant = source.replace(ANCHOR, "if (snoop_valid_ctx[i] && snoop_ready_ctx[i] &&", 1)
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{MUTATION}_", dir=OUT) as tmp:
        work = Path(tmp)
        mutant_rtl = work / "DirectoryMshrBank_mutant.sv"
        mutant_rtl.write_text(mutant, encoding="utf-8")
        obj = work / "obj"
        compile_cmd = [
            "verilator", "--binary", "--timing", "--assert", "-j", "2",
            "-Wall", "-Wno-fatal", "-Wno-BLKSEQ", f"-I{TB_DIR}",
            "--top-module", "DirectoryMshrBank_tb", "--Mdir", str(obj),
            str(PROJECT_ROOT / "rtl/common/CoherenceProtocol.sv"),
            str(PROJECT_ROOT / "rtl/directory/DirectoryController.sv"),
            str(mutant_rtl), str(TB),
        ]
        compiled = subprocess.run(compile_cmd, cwd=PROJECT_ROOT, capture_output=True,
                                  text=True, timeout=240, check=False)
        build_log = compiled.stdout + "\n" + compiled.stderr
        (OUT / f"{MUTATION}.build.log").write_text(build_log, encoding="utf-8")
        if compiled.returncode:
            raise RuntimeError(f"{MUTATION}: mutant did not compile; see reports/coherence/mutations/{MUTATION}.build.log\n{build_log[-3000:]}")

        sim = subprocess.run([str(obj / "VDirectoryMshrBank_tb")], cwd=PROJECT_ROOT,
                             capture_output=True, text=True, timeout=60, check=False)
        sim_log = sim.stdout + "\n" + sim.stderr
        (OUT / f"{MUTATION}.sim.log").write_text(sim_log, encoding="utf-8")
        caught = sim.returncode != 0 and EXPECTED_FAILURE in sim_log
        report = {
            "mutation": MUTATION,
            "caught": caught,
            "return_code": sim.returncode,
            "expected_checker_failure": EXPECTED_FAILURE,
            "observed": sim_log.strip().splitlines()[-1:] or ["no simulator output"],
            "build_log": f"reports/coherence/mutations/{MUTATION}.build.log",
            "simulation_log": f"reports/coherence/mutations/{MUTATION}.sim.log",
        }
        (OUT / f"{MUTATION}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if not caught:
            raise AssertionError(f"{MUTATION}: block checker did not catch RTL mutation: {report}")
        return report


def main() -> None:
    if shutil.which("verilator") is None:
        raise RuntimeError("verilator is required; source scripts/env.sh first")
    result = run()
    print(f"PASS {result['mutation']} -> checker rejected RTL fault")


if __name__ == "__main__":
    main()
