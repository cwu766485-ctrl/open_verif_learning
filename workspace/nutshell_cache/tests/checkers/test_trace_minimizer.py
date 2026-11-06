"""Tests for order-preserving failure-trace reduction."""

import pytest

from dv.sequences.trace_minimizer import minimize_operations


def test_minimizer_keeps_required_prelude_and_failing_operation_ordered():
    trace = [
        {"id": "setup", "required_prelude": True},
        {"id": "noise_a"},
        {"id": "trigger"},
        {"id": "noise_b"},
        {"id": "noise_c"},
    ]

    def reproduces(candidate):
        ids = [item["id"] for item in candidate]
        return "setup" in ids and "trigger" in ids and \
            ids.index("setup") < ids.index("trigger")

    result = minimize_operations(trace, reproduces)
    ids = [item["id"] for item in result["operations"]]
    assert ids == ["setup", "trigger"]
    assert result["original_count"] == 5
    assert result["minimized_count"] == 2
    assert result["attempts"] > 1
    assert result["required_prelude_count"] == 1


def test_minimizer_rejects_trace_that_does_not_reproduce():
    with pytest.raises(ValueError, match="does not reproduce"):
        minimize_operations([{"id": "op"}], lambda _trace: False)
