# Remaining Risks

Functional Candidate OPEN; Full RTL Coverage OPEN.

- Context2/3: actual control with symbolic array cutpoints cover TIMEOUT. No legal witness or unreachable proof. Require real array-compatible legal constraints plus trace concretization, or inductive upper bound without occupancy assumption.
- Read slice: global busy/beat write audit and actual engine composition PASS retained; independent extraction/routing review PENDING. No automatic point waiver.
- AXI: response stability inductive PASS; AR/AW/W/read stability UNKNOWN induction. FIFO queue ownership and complete ID/Beat/Last lifetime proof remain OPEN. Prior local guarantees and bounded checks do not substitute.
- Refill: caller free-slot premise discharged for source-checked admission logic; independent integration correspondence review and other end-to-end data/ownership properties separate.
- Reset requires existing common external reset/drain contract; no new epoch feature or implicit assumption.
- 29466 Required zero points remain OPEN;60toggle candidates PENDING independent approval; no exclusions.

Current source/evidence and exact point mapping: final_verification_report.md and release_review/. Stop expanding DV after this bounded review.
