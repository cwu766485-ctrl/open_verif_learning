"""Fail regression closure if any planned functional coverage goal is missed."""

import json
import sys
from pathlib import Path

from dv.coverage.collector import CacheCoverage


def check_payload(payload):
    summary = payload.get("functional_coverage", {})
    bins = payload.get("bins", {})
    goals = CacheCoverage.GOALS
    uncovered = [goal for goal in goals if not bins.get(goal, 0)]
    declared_uncovered = summary.get("uncovered")

    if summary.get("total_goals") != len(goals):
        raise ValueError(
            f"coverage report declares {summary.get('total_goals')} goals; "
            f"current plan has {len(goals)}"
        )
    if declared_uncovered != uncovered:
        raise ValueError(
            "coverage report summary does not match its bins: "
            f"declared={declared_uncovered!r}, computed={uncovered!r}"
        )
    if uncovered:
        raise ValueError("uncovered functional goal(s): " + ", ".join(uncovered))

    covered = summary.get("covered_goals")
    if covered != len(goals):
        raise ValueError(f"coverage report declares only {covered}/{len(goals)} goals hit")
    return covered, len(goals)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m dv.coverage.functional_closure reports/functional_coverage.json", file=sys.stderr)
        return 2
    try:
        payload = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        covered, total = check_payload(payload)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"functional coverage closure error: {exc}", file=sys.stderr)
        return 1
    print(f"Functional coverage goals hit: {covered}/{total} (100.0%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
