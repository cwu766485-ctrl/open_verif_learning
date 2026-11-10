# Remaining Freeze Risks

**Functional Candidate OPEN; Full RTL Coverage OPEN.** No architecture expansion is requested.

## Context 2/3

OPEN. Main observed peak2, ctx2/3 cycles0; no integrated upper-bound proof

Minimum closure task: Compose two actual L1 controllers, request arbiter and MSHR; prove capacity or cover slot2/3 including Put bypass; then check retirement

Evidence: coherence_verify.log.gz; coherence_coverage_audit.log.gz; phase4 reachability study

## Grant Read x L2 Busy

PROOF_CANDIDATE_PENDING_CORRESPONDENCE_REVIEW. Actual engine cannot enter state10 in modeled Main read-port composition; runtime accepted grants always see ready

Minimum closure task: Independent review of modeled recurrence/routing vs actual Main/L2 RTL, or full-elaboration proof

Evidence: formal/freeze_read_port_scope.md; final_freeze/formal/freeze_read_port.log.gz

## Dirty Victim BRESP / Producer Safety

ERROR_CASE_PASS_PRODUCER_PROOF_OPEN. B error observed; no CPU success; fatal persists; reset epoch advances; checked recovery read

Minimum closure task: Prove internal refill/snoop/grant and AXI adapter ID/beat/last invariants across all producers; runtime observations are not universal proof

Evidence: final_freeze/bresp_boundary.log.gz; test_full_system_signoff.py; freeze_protocol_observer.svh

## Reset/Fatal/Resource FSM arcs

PARTIAL_OPEN. Seven observed states reset and checked recovery; no stale transaction; Context2/3 source states unobserved

Minimum closure task: Resolve reachability per source state/instance, then reset at those states; prove or independently review tool extraction only where supported

Evidence: risk_reset_states.svh; coherence_verify.log.gz; formal evidence

## Coverage and review boundary

29466 Required zero points remain OPEN, including28597Toggle. No blanket toggle closure required or inferred; no automatic exclusions.60low-bit candidates await independent approval. Legal reachable but unidentified gaps remain unresolved, not waived. Complete per-point control and toggle review is attached.
