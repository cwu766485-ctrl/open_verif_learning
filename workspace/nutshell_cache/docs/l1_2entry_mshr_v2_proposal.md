# L1 Two-Entry MSHR — v2 Architecture Proposal

**Status:** design proposal only. No product RTL changes are part of the v1.1
Hit-under-Miss closure work.

## 1. Goal and boundary

Add two miss-status entries per L1 so a core can retain two independent cache
misses while the existing MESI directory, four Directory contexts, four refill
MSHRs, and AXI interface continue to arbitrate downstream work. This enables
Miss-under-Miss. It does not promise four simultaneous CPU misses or remove
shared Directory/L2 serialization.

The two-entry L1 MSHR is a CPU-request tracker. The four existing refill MSHRs
are memory-line burst trackers. They are separate resources and must be
correlated explicitly.

## 2. Candidate interface contract

- CPU request acceptance requires an available MSHR for a miss, or an existing
  line hit path that can accept the request without violating same-set access
  rules.
- Each entry retains line address, original byte/word offset, operation,
  write data/mask, request tag, replay state, and downstream Directory/refill
  context ID.
- Identical-line misses merge only when operation ordering and byte masks can
  be preserved; otherwise the second request is queued behind the first.
- Two different misses may progress concurrently when they do not conflict on
  L1 array ports, replacement way, coherence ownership, Directory same-set
  interlock, or shared L2 write path.
- A hit to a resident, unrelated line can respond while an MSHR is pending,
  preserving the already-verified Hit-under-Miss behavior.
- Response ordering must follow a frozen LSU contract. Until the interface has
  request IDs or an explicit in-order completion rule, arbitrary CPU response
  reordering is prohibited.

## 3. Required ordering and conflict rules

1. **Same line:** serialize or merge requests; never issue duplicate coherence
   ownership transitions for one line.
2. **Same L1 set:** serialize tag/data writes that contend for the same array
   port or replacement metadata. A refill cannot silently evict a line whose
   snoop/update is still active.
3. **Store to pending line:** retain the store and apply its mask after refill
   data is installed, before the dependent CPU response.
4. **Snoop to pending/resident line:** invalidate, downgrade, or forward data
   according to MESI; mark/replay a colliding MSHR and ensure no stale refill
   resurrects a line after a later invalidation.
5. **Replacement:** reserve the victim and way before issuing Put; do not
   overwrite metadata until PutAck and any competing Snoop are resolved.
6. **Reset/error:** cancel all live entries and downstream context mappings;
   discard stale responses by epoch or by guaranteed non-reused transaction
   IDs until cancellation drains.
7. **Response association:** map each completion to its original request tag;
   if the LSU remains in-order, retire in acceptance order even when refills
   return out of order.

## 4. State and resource sketch

Each MSHR entry uses explicit valid/state fields rather than a monolithic shared
controller state:

`FREE → LOOKUP/ALLOC → DIR_WAIT → REFILL_WAIT → INSTALL → RESPONSE_WAIT → FREE`

Side flags record store merge, replay-needed, snoop-seen, victim reserved, and
error. A separate small allocator provides same-line merge lookup, free-entry
selection, and oldest-completable ordering. Downstream Directory/AXI IDs are
stored per entry and may be returned out of order; CPU responses obey the
frozen LSU ordering contract.

## 5. Verification required before RTL implementation

- Two distinct misses, reversed R response order, correct line and CPU response
  association.
- Same-line read/read merge, read/write serialization, and byte-mask store
  merge behavior.
- Same-set conflict against a resident hit and a selected replacement victim.
- SnoopRead/SnoopInvalidate during each MSHR phase, including post-refill replay
  and stale-refill suppression.
- MSHR full backpressure, entry reuse, Directory backpressure, AXI backpressure,
  and starvation/fairness bounds.
- Reset at every lifecycle phase and late response after reset.
- Error on any refill beat and correct cancellation/error response per request.
- Independent request-tag scoreboard, MESI/directory invariants, assertions for
  one-owner-per-line and no duplicate context allocation, and formal safety of
  allocation/retire/reset invariants.
- Benchmark paired against the blocking baseline with identical seeds,
  memory-latency configurations, and workload streams. Report miss latency,
  operations/cycle, overlap occupancy, and per-core fairness.

## 6. Open decisions before coding

- Does the LSU expose request IDs, or must the cache return responses in
  acceptance order?
- Are same-line misses merged, or serialized in v2.0?
- Which L1 array ports support concurrent lookup, refill write, and snoop?
- Is the replacement victim reserved at miss acceptance or only after lookup?
- How does a downstream Directory retry map back to a retained L1 entry?
- What is the architectural CPU error response for refill failures?

These decisions are interface/spec work. Do not infer them from the current
Hit-under-Miss bypass test or from the existence of downstream MSHRs.
