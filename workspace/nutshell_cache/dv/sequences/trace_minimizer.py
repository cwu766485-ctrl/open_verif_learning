"""Order-preserving delta debugger for saved full-system operation traces."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


def minimize_operations(
    operations: Sequence[Mapping[str, Any]],
    reproduces: Callable[[list[dict[str, Any]]], bool],
    *,
    required_key: str = "required_prelude",
) -> dict[str, Any]:
    """Remove operations while preserving a required prelude and failure.

    The callback owns replay and failure classification. This helper does not
    alter records, reorder them, or claim that a synthetic trace can be replayed
    unless the caller's callback confirms it. Records marked truthy by
    ``required_key`` are never removed.
    """
    original = [dict(operation) for operation in operations]
    if not reproduces(original):
        raise ValueError("input trace does not reproduce the target failure")

    retained = set(range(len(original)))
    required = {
        index for index, operation in enumerate(original)
        if operation.get(required_key, False)
    }
    removable = [index for index in range(len(original)) if index not in required]
    attempts = 1
    granularity = 2

    while removable:
        granularity = min(granularity, len(removable))
        quotient, remainder = divmod(len(removable), granularity)
        chunks = []
        start = 0
        for chunk_index in range(granularity):
            size = quotient + (1 if chunk_index < remainder else 0)
            chunks.append(removable[start:start + size])
            start += size

        reduced = False
        for chunk in chunks:
            candidate_indices = retained.difference(chunk)
            candidate = [original[index] for index in range(len(original))
                         if index in candidate_indices]
            attempts += 1
            if reproduces(candidate):
                retained = candidate_indices
                removable = [index for index in removable if index in retained]
                granularity = max(granularity - 1, 2)
                reduced = True
                break

        if not reduced:
            if granularity >= len(removable):
                break
            granularity = min(len(removable), granularity * 2)

    result = [original[index] for index in range(len(original))
              if index in retained]
    if not all(original[index].get(required_key, False)
               for index in required if index in retained):
        raise AssertionError("trace minimizer removed a required prelude")
    if not reproduces(result):
        raise AssertionError("trace minimizer lost the reproduced failure")
    return {
        "operations": result,
        "original_count": len(original),
        "minimized_count": len(result),
        "attempts": attempts,
        "required_prelude_count": len(required),
    }
