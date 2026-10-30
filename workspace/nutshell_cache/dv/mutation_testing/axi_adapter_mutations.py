"""Mutate real AXI adapter RTL and require its independent bus block TB to fail."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl/bus/axi/LineMemoryAxi4Adapter.sv"
TB_DIR = ROOT / "dv/blocks/bus_blocks/tb"
TB = TB_DIR / "CacheBusBlocks_tb.sv"
OUT = ROOT / "reports/coherence/mutations"
NAME = "axi_adapter_must_surface_read_error"
ANCHOR = "assign line_rd_data_error = line_rd_data_valid && rd_r_error;"
MUTANT = "assign line_rd_data_error = 1'b0;"
EXPECTED = "AXI read error was not surfaced as a terminal line error"


def run() -> dict[str, object]:
    source = RTL.read_text(encoding="utf-8")
    if source.count(ANCHOR) != 1:
        raise RuntimeError(f"{NAME}: expected one RTL anchor, found {source.count(ANCHOR)}")
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{NAME}_", dir=OUT) as tmp:
        work = Path(tmp)
        mutant_rtl = work / "LineMemoryAxi4Adapter_mutant.sv"
        mutant_rtl.write_text(source.replace(ANCHOR, MUTANT, 1), encoding="utf-8")
        obj = work / "obj"
        command = [
            "verilator", "--binary", "--timing", "--assert", "-j", "2",
            "-Wall", "-Wno-fatal", "-Wno-BLKSEQ", f"-I{TB_DIR}",
            "--top-module", "CacheBusBlocks_tb", "--Mdir", str(obj),
            str(ROOT / "rtl/common/CoherenceProtocol.sv"), str(mutant_rtl),
            str(ROOT / "rtl/bus/apb/CachePerformanceCsr.sv"), str(TB),
        ]
        build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               timeout=240, check=False)
        build_log = build.stdout + "\n" + build.stderr
        (OUT / f"{NAME}.build.log").write_text(build_log, encoding="utf-8")
        if build.returncode:
            raise RuntimeError(f"{NAME}: mutant did not compile; see reports/coherence/mutations/{NAME}.build.log\n{build_log[-3000:]}")

        sim = subprocess.run([str(obj / "VCacheBusBlocks_tb")], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, check=False)
        sim_log = sim.stdout + "\n" + sim.stderr
        (OUT / f"{NAME}.sim.log").write_text(sim_log, encoding="utf-8")
        caught = sim.returncode != 0 and EXPECTED in sim_log
        result = {
            "mutation": NAME,
            "caught": caught,
            "return_code": sim.returncode,
            "expected_checker_failure": EXPECTED,
            "observed": sim_log.strip().splitlines()[-1:] or ["no simulator output"],
            "build_log": f"reports/coherence/mutations/{NAME}.build.log",
            "simulation_log": f"reports/coherence/mutations/{NAME}.sim.log",
        }
        (OUT / f"{NAME}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if not caught:
            raise AssertionError(f"{NAME}: bus block checker did not catch RTL mutation: {result}")
        return result


def main() -> None:
    if shutil.which("verilator") is None:
        raise RuntimeError("verilator is required; source scripts/env.sh first")
    result = run()
    print(f"PASS {result['mutation']} -> checker rejected RTL fault")


if __name__ == "__main__":
    main()
