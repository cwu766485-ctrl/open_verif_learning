"""Run and summarize targeted RTL mutation checks across the MESI datapath."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .axi_adapter_mutations import run as run_axi
from .coherence_rtl_mutations import run_all as run_l1
from .directory_mshr_mutations import run as run_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports/coherence/mutations"


def run_all() -> dict[str, object]:
    l1 = run_l1()
    directory = run_directory()
    axi = run_axi()
    mutations = [*l1["mutations"], directory, axi]
    caught = sum(record.get("caught") is True for record in mutations)
    report: dict[str, object] = {
        "status": "PASS" if caught == len(mutations) else "FAIL",
        "caught": caught,
        "total": len(mutations),
        "scope": [
            "rtl/l1/MesiL1Controller.sv",
            "rtl/directory/DirectoryMshrBank.sv",
            "rtl/bus/axi/LineMemoryAxi4Adapter.sv",
        ],
        "mutations": mutations,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rtl_mutation_campaign_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if caught != len(mutations):
        missed = [record["mutation"] for record in mutations
                  if record.get("caught") is not True]
        raise AssertionError(f"RTL mutation campaign missed: {missed}")
    return report


def main() -> None:
    if shutil.which("verilator") is None:
        raise RuntimeError("verilator is required; source scripts/env.sh first")
    result = run_all()
    print(f"RTL mutation campaign caught: {result['caught']}/{result['total']}")
    for item in result["mutations"]:
        print(f"  PASS {item['mutation']}")


if __name__ == "__main__":
    main()
