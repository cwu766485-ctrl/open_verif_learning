#!/usr/bin/env python3
"""Run and record the required v1.1 RTL/DV release regression targets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dv.coverage.rtl_coverage_dataset_manifest import ROOT, source_fingerprint
from dv.coverage.rtl_release_gate import REQUIRED_GATES, RUN_STATUS


def main() -> int:
    jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    if jobs != 2:
        raise SystemExit("The release evidence contract requires COHERENCE_JOBS=2")
    log_dir = ROOT / "reports/closure/release_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "schema_version": 1,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": source_fingerprint()[0],
        "required_gates": REQUIRED_GATES,
        "runs": {},
    }
    RUN_STATUS.parent.mkdir(parents=True, exist_ok=True)
    RUN_STATUS.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    env = os.environ.copy()
    for gate in REQUIRED_GATES:
        command = f"make COHERENCE_JOBS=2 {gate}"
        before = source_fingerprint()[0]
        log = log_dir / f"{gate}.log"
        print(f"=== {command} ===", flush=True)
        with log.open("w", encoding="utf-8") as stream:
            proc = subprocess.run(
                ["bash", "-lc", f"source scripts/env.sh && {command}"],
                cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False,
            )
        after = source_fingerprint()[0]
        results["runs"][gate] = {
            "command": command,
            "returncode": proc.returncode,
            "result": "PASS" if proc.returncode == 0 and before == after else "FAIL",
            "source_fingerprint_before": before,
            "source_fingerprint_after": after,
            "log": log.relative_to(ROOT).as_posix(),
            "completed_utc": datetime.now(timezone.utc).isoformat(),
        }
        results["updated_utc"] = datetime.now(timezone.utc).isoformat()
        RUN_STATUS.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
        print("\n".join(tail), flush=True)
        print(f"{gate}: {results['runs'][gate]['result']} (exit={proc.returncode})", flush=True)
        if proc.returncode != 0 or before != after:
            print(f"Stopped at first failing gate; see {log.relative_to(ROOT)}", file=sys.stderr)
            return proc.returncode or 1
    results["completed_utc"] = datetime.now(timezone.utc).isoformat()
    RUN_STATUS.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
