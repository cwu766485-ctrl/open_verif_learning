# Remaining Freeze Risks

**Functional Candidate OPEN; Full RTL Coverage OPEN.** No architecture expansion is requested.

## Context 2/3

OPEN. Main observed peak2, ctx2/3 cycles0; no integrated upper-bound proof

Minimum closure task: Compose two actual L1 controllers, request arbiter and MSHR; prove capacity or cover slot2/3 including Put bypass; then check retirement

Evidence: coherence_verify.log.gz; coherence_coverage_audit.log.gz; phase4 reachability study

## Grant Read x L2 Busy

PROOF_CANDIDATE_PENDING_CORRESPONDENCE_REVIEW. Actual engine cannot enter state10 in modeled Main read-port composition; runtime accepted grants always see ready

Actual L2+Engine attempt: TOOL ERROR due to Slang mixed array assignments; no unreachable conclusion.

Minimum closure task: Independent review of modeled recurrence/routing vs actual Main/L2 RTL, or full-elaboration proof

Evidence: formal/freeze_read_port_scope.md; final_freeze/formal/freeze_read_port.log.gz

## Dirty Victim BRESP / Producer Safety

ERROR_CASE_PASS_PRODUCER_PROOF_OPEN. B error observed; no CPU success; fatal persists; reset epoch advances; checked recovery read

New proof: actual L1 Controller + Snoop Arbiter accepted-request ID provenance, encoding and reset cleanup inductive PASS with no protocol assumptions; beat/last only forwards array inputs.

Minimum closure task: Prove remaining array/refill and AXI adapter ID/beat/last legality across all producers; runtime observations and L1 ID proof are not universal protocol proof

Evidence: final_freeze/bresp_boundary.log.gz; test_full_system_signoff.py; freeze_protocol_observer.svh

## Reset/Fatal/Resource FSM arcs

PARTIAL_OPEN. Seven observed states reset and checked recovery; no stale transaction; Context2/3 source states unobserved

Minimum closure task: Resolve reachability per source state/instance, then reset at those states; prove or independently review tool extraction only where supported

Evidence: risk_reset_states.svh; coherence_verify.log.gz; formal evidence

## Coverage and review boundary

29466 Required zero points remain OPEN, including28597Toggle. No blanket toggle closure required or inferred; no automatic exclusions.60low-bit candidates await independent approval. Legal reachable but unidentified gaps remain unresolved, not waived. Complete per-point control and toggle review is attached.

Current tested source: `e0b087c44e9131d2eb9ca7cbf0193e82bb18a22c`. Current raw inventory and precise source-line gaps: [code_coverage_report.md](code_coverage_report.md). Eight current regression gates PASS; release make exit2/OPEN. Latest proof/evidence hashes: `continued_freeze/`. No approved waivers or deletion candidates.
