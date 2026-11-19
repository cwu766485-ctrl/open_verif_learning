# NutShell Cache v1.3 — Two-Entry L1 MSHR and Miss-under-Miss

**Document state:** implementation contract for the v1.3 incremental change.
This supplements the frozen v1.1 cache specification; it does not replace that
baseline or describe silicon/PPA sign-off. The accepted two-entry tracker is
the current implementation baseline. The true Miss-under-Miss requirements
below are the next RTL increment and remain **OPEN** until implemented and
checked on the integrated subsystem.

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

## Next increment: true same-L1 Miss-under-Miss (OPEN)

The current v1.3 implementation is a two-entry acceptance tracker with one
issued miss per L1. The proposed next increment is defined separately in
[`l1_miss_under_miss_v1_3_phase2_contract.md`](l1_miss_under_miss_v1_3_phase2_contract.md).
That contract keeps the CPU interface unchanged, retains FIFO ordering among
miss responses from the same core, and requires separate local order sequence
and live coherence transaction ID association. It also requires explicit
single-port L1 array arbitration and per-resource concurrency evidence. Until
the directed tests in that contract pass on the modified RTL, same-L1
Miss-under-Miss and four simultaneous downstream requests remain unsupported.

### Required behavior for this increment

1. Each L1 has two independently live coherence-miss contexts. Two different
   cache-line misses from the same core must each complete a Directory request
   handshake before either miss response is returned. CPU0 and CPU1 may each
   reach this condition, for up to four live L1 miss contexts in total.
2. CPU request/response ports remain source-compatible: no incoming CPU
   Request ID is added. Miss responses from one core retire in CPU request
   acceptance order. A later miss may finish internally first, but its result
   waits in its MSHR until older miss responses retire. Existing resident-read
   Hit-under-Miss bypass remains its documented exception and is checked as a
   separate response class. The two cores have no cross-core response ordering
   requirement.
3. Every live miss has a coherence transaction ID unique among transactions
   from the same request source. The allocator must not reuse an ID until its
   grant/refill/commit lifecycle and response association are retired. Local
   CPU acceptance sequence is stored separately from the recyclable protocol
   ID. The configured ID width and wrap behavior are checked at the maximum
   live occupancy. An upstream request tag is needed only if the CPU interface
   later promises arbitrary same-core response reordering.
4. An MSHR is allocated only on an accepted CPU request that needs coherence
   service; it stores the full request payload, line address, set, local order,
   protocol ID, selected way when reserved, and lifecycle state. It retires
   only after its checked CPU response handshakes, or is canceled by the
   specified reset contract. A store miss applies its byte mask/data only
   after ownership and refill data are valid.
5. A repeated request to a line with a live MSHR is not merged in this
   increment. It is backpressured and re-looked-up after the earlier line
   retires. Two misses mapping to the same L1 set may be accepted into tracking
   only if way allocation and replacement ownership are unambiguous; otherwise
   the later request remains held until the first fill/replacement releases
   the set. The initial four-miss proof uses four distinct lines and distinct
   L1/L2 sets.
6. Each L1 retains one shared Snoop engine and one replacement controller.
   Snoop, PutM victim streaming, refill, store, and metadata commits use an
   explicit per-L1 array arbiter. A snoop matching a line with an uncommitted
   refill must make forward progress without observing partial data, losing
   ownership, or deadlocking the refill/Directory context. A second live miss
   may wait for the single replacement engine; concurrent victim replacement
   is not implied by two MSHRs.
7. Refill data is associated by the live coherence ID. The L1 may buffer each
   transaction's beats or hold a complete stream at the source, but the single
   array refill writer must never interleave two lines. Grant commit occurs
   only after all eight beats are accepted into the correct line and metadata
   state is ready. Directory contexts, refill MSHRs, shared L2/line-engine
   ownership, and AXI outstanding requests are independently backpressured and
   reported; four L1 MSHRs do not promise four concurrent AXI reads.
8. When both local MSHRs are full, a third coherence miss is not accepted and
   its request payload remains stable. A response stall retains completed
   entries and cannot change response address/data/order. Reset cancels all
   live local contexts under the existing coordinated reset; no pre-reset
   response may be accepted after reset, and post-reset traffic must recover.
9. The change must preserve MESI state transitions, clean/dirty L1 replacement,
   owner-data Snoop, same-line conflict handling, MMIO bypass, APB CSR
   behavior, AXI ID/response semantics, and the existing Hit-under-Miss
   contract. L2 banking, extra SRAM ports, changed Directory capacity, and
   changed AXI interfaces are out of scope unless separate measurements and
   design review establish they are necessary.

### Acceptance evidence

The minimum system test sends A/B from CPU0 and C/D from CPU1, with each pair
using distinct lines and sets. Before the first miss response, independent
monitoring must show two Directory-accepted live miss IDs per L1 (four total).
The test separately records per-cycle L1 MSHR occupancy, Directory contexts,
refill MSHRs, shared line-engine ownership, AXI R outstanding and AXI W
outstanding. It checks ID-to-line association, all eight refill beats, final
CPU data, FIFO miss response order per core, and no duplicate/lost transaction.
The same-source refills must be deliberately completed in reverse order where
the shared line-engine protocol permits it; otherwise the concrete serialization
point and its effect on the test are reported. Waveform/handshake trace, fixed
seed, checker result, and the exact source/tool fingerprint are retained.

Full MUM closure also requires separate directed checks for MSHR-full
backpressure, same-line conflict, same-set way conflict, replacement PutM vs
owner-data Snoop, Store/refill contention, CPU response backpressure, reset
cancellation with two active contexts, and transaction-ID wrap. A performance
gain is claimed only after the same Benchmark v4 workloads and settings run
against the preserved blocking baseline and the new RTL; occupancy alone is
not a throughput result.
