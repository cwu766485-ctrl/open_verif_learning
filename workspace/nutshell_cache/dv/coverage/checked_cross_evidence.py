"""Helpers for serializing event-backed checked cross evidence.

This module does not run or infer checkers. Callers may build a proof only
after their independent data/protocol checks have passed; the evidence gate
then binds every referenced event and interval endpoint to the saved trace.
"""


_TRACE_FIELDS = (
    "source", "event_type", "cycle", "reset_epoch", "core", "address",
    "write", "data", "txn_id", "source_id", "opcode", "beat", "last",
    "response", "length", "destination", "old_state", "new_state",
    "old_sharers", "old_owner", "state", "sharers", "owner", "cause",
    "is_snoop", "payload", "outcome",
)


def event_reference(ref_id, role, event):
    """Copy the identifying fields from a real FullSystemMonitor event."""
    if not ref_id or not role or not isinstance(event, dict):
        raise ValueError("event reference requires an ID, role, and event")
    if not {"source", "event_type", "cycle"} <= set(event):
        raise ValueError("monitor event is missing source/type/cycle")
    reference = {key: event[key] for key in _TRACE_FIELDS if key in event}
    reference.update(ref_id=ref_id, role=role)
    return reference


def checked_overlap_proof(*, checker, checker_pass, role_endpoints,
                          event_refs, transactions, state_transitions):
    """Build an exact intersection proof with event-bound role endpoints.

    ``role_endpoints`` maps a role to ``(start_ref_id, end_ref_id)``. The
    helper rejects empty or non-overlapping windows and dangling endpoints;
    the repository evidence gate independently repeats those checks against
    the serialized monitor trace.
    """
    if checker_pass is not True or not checker:
        raise AssertionError("checked overlap evidence requires a passing checker")
    refs = {item["ref_id"]: item for item in event_refs}
    if len(refs) != len(event_refs):
        raise ValueError("event reference IDs must be unique")
    if len(role_endpoints) < 2 or not transactions or not state_transitions:
        raise ValueError("overlap proof requires roles, transactions, and transitions")

    roles = {}
    for name, (start_id, end_id) in role_endpoints.items():
        start_ref, end_ref = refs.get(start_id), refs.get(end_id)
        if not start_ref or not end_ref:
            raise ValueError(f"role {name} references a missing event")
        if start_ref["role"] != name or end_ref["role"] != name:
            raise ValueError(f"role {name} endpoint ownership mismatch")
        roles[name] = {
            "start_cycle": int(start_ref["cycle"]),
            "end_cycle": int(end_ref["cycle"]),
            "start_event_ref": start_id,
            "end_event_ref": end_id,
        }
    start = max(role["start_cycle"] for role in roles.values())
    end = min(role["end_cycle"] for role in roles.values())
    if start > end:
        raise AssertionError(f"roles do not overlap: {start}>{end}")
    return {
        "checker": checker,
        "checker_pass": True,
        "overlap": {"start_cycle": start, "end_cycle": end, "roles": roles},
        "transactions": transactions,
        "state_transitions": state_transitions,
        "event_refs": event_refs,
    }
