# NutShell Cache v1.3 — Two-Entry L1 Miss Tracking

**Document state:** implementation contract for the v1.3 incremental change.
This supplements the frozen v1.1 cache specification; it does not replace that
baseline or describe silicon/PPA sign-off.

## Functional requirements

1. Each of the two L1s shall track up to two accepted, outstanding,
   different-line CPU requests that require MESI service.
2. The first request is serviced by the existing per-core MESI controller.
   The second is retained in a queued MSHR and dispatched after the first
   response handshakes and the controller is idle. This enables four accepted
   L1 miss requests subsystem-wide, not four simultaneous Directory or memory
   transactions.
3. The CPU interface remains unchanged. It has no incoming request ID. Misses
   from a given core dispatch and complete in acceptance order. Existing
   Hit-under-Miss resident-read bypass remains and can complete ahead of a
   pending miss. Responses from the two cores may complete in either order.
4. Same-line requests are backpressured, not merged. The held request is
   re-looked up after the earlier MSHR retires.
5. Queue allocation captures full address, operation, write data and byte
   mask. It does not reserve an L1 way or perform an array write. Queued work
   performs a fresh lookup/replacement check at dispatch.
6. A queued store is applied only after its normal MESI/refill path. A snoop
   that occurs before queued dispatch is reflected by the fresh lookup.
7. A third independent miss receives backpressure while both local MSHRs are
   valid. Request payload must remain stable until `ready` accepts it.
8. Reset cancels all valid/queued L1 MSHRs under the existing subsystem reset
   contract. Fail-stop protocol errors remain fail-stop until reset.
9. Do not alter Directory Context, refill MSHR, AXI, MMIO, APB, shared L2
   capacity, or their interfaces in this change.

## Resource reporting

Verification reports four independent maxima: L1 MSHR entries, Directory
contexts, refill MSHRs, and AXI outstanding reads/writes. They are different
resources and must never be conflated. The design permits L1 occupancy four;
the single per-core controller still limits active miss issue to at most one
per core.

## Interface compatibility and ordering

The existing response address and internally generated transaction ID remain
unchanged. Since there is no request-ID input, adding one would break the CPU
interface and is not required for the current per-core FIFO miss-dispatch
contract. If future RTL allows multiple same-core downstream requests, that
revision must either preserve FIFO completion or add an explicit upstream
request tag with a compatibility wrapper and LSU update.

## Verification status

Implementation and directed test results are recorded in
[`dv/v1.3_nonblocking_l1_validation.md`](dv/v1.3_nonblocking_l1_validation.md).
This document does not claim four-entry concurrency until a run observes all
four L1 valid bits before any response completion and passes the independent
address/data/order checker.

Architecture details and lifecycle rules are in
[`l1_2entry_mshr_v2_proposal.md`](l1_2entry_mshr_v2_proposal.md).
