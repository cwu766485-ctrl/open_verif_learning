import pytest

from dv.coverage.collector import CacheCoverage
from dv.coverage.functional_closure import check_payload


def _payload(missing=()):
    bins = {goal: 1 for goal in CacheCoverage.GOALS if goal not in missing}
    return {
        "bins": bins,
        "functional_coverage": {
            "covered_goals": len(bins),
            "total_goals": len(CacheCoverage.GOALS),
            "uncovered": list(missing),
        },
    }


def test_functional_closure_accepts_a_complete_plan():
    assert check_payload(_payload()) == (len(CacheCoverage.GOALS), len(CacheCoverage.GOALS))


def test_functional_closure_fails_when_a_planned_cross_is_uncovered():
    goal = "op_result=read/miss"
    with pytest.raises(ValueError, match=goal):
        check_payload(_payload(missing=(goal,)))
