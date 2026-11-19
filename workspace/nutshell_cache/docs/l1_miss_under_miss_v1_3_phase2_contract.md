# v1.3 Phase 2 — Same-L1 Miss-under-Miss Contract

**Status: design contract for the next RTL increment; not yet implemented.**

This document extends the implemented v1.3 two-entry request tracker. The
current RTL and its passing evidence remain the baseline. Nothing here claims
that two same-L1 misses can already issue concurrently.

## Baseline and target

The current L1 keeps two accepted different-line requests, but routes only the
head request through its single `MesiL1Controller`. The second entry waits for
the first CPU response to retire. The fresh baseline test observed four L1
entries occupied, while Directory contexts, refill MSHRs and AXI read
outstanding each peaked at two. The next target is two independent,
different-line coherence transactions per L1, for four total CPU misses in
flight, provided the shared downstream resources accept them.

For measurement, distinguish these per-entry states: **allocated** means the
CPU request was accepted and the entry is valid; **controller-owned** means
the entry has been selected by the per-core MESI controller; **Directory-issued**
means the controller accepted the Directory request and is in `WAIT_GRANT`,
`REFILL`, `META_WRITE`, `RESP`, or its post-issue `ERROR` state. Directory
Context occupancy, refill MSHR occupancy, and AXI outstanding transactions are
separate counters. The issued state is not inferred from allocation or from
controller ownership alone.

The target is bounded concurrency, not a promise that all four transactions
always progress in the same cycle. Directory set interlocks, the shared
`SharedLineEngine`, single L1 array ports, and downstream backpressure may
serialize particular operations. The test must measure each resource and
demonstrate the required overlap explicitly.

## CPU request and response ordering

- Keep the existing CPU request/response ports. The request side has no tag;
  the response address is observational data and is not a safe substitute for
  an upstream transaction ID when identical or aliased requests exist.
- Preserve same-core miss response order by acceptance order. Each allocated
  MSHR receives a monotonically allocated internal transaction tag, and refill
  or grant events are routed to that MSHR. The tag is internal and does not
  change the LSU interface.
- Preserve the existing eligible resident-read Hit-under-Miss bypass. It may
  respond before an older miss, as it does today. This exception does not
  permit the miss response queue itself to reorder.
- Responses from the two cores remain independent. Refill completion may be
  out of order across MSHR tags, but the per-core CPU response arbiter retires
  misses in acceptance order.
- If implementation analysis proves that the existing response fields and
  internal tags cannot safely maintain this contract, stop before changing the
  public interface and submit a compatibility proposal for review.

## Allocation, dispatch, and retirement

1. Each core may allocate two live MSHRs for distinct cache lines. The request
   handshake captures byte address, operation, write data, byte mask, and a
   local acceptance-order sequence number. This sequence is not a coherence
   transaction ID.
2. Allocate a coherence transaction ID when an MSHR is dispatched for issue,
   then bind that ID to the MSHR until its protocol transaction retires. IDs
   must be unique among live transactions in the namespace used by Directory,
   Grant, Snoop, and refill routing. An entry becomes `issued` only when its
   coherence request is accepted by the Directory interface. Allocation,
   issue, Directory context ownership, refill MSHR allocation, and AXI
   outstanding are separate events and counters.
3. A same-line request is backpressured in this phase; MSHR merging is out of
   scope. A third independent miss is backpressured while both entries are
   live, with valid/payload held stable until accepted.
4. A normal load response may retire only when its refill/data and MESI state
   are committed and the CPU response handshakes. A store retains its payload
   and cannot update data before its required MESI permission and array
   arbitration are granted.
5. Reset cancels every live entry, queued response, and outstanding local
   association under the subsystem reset contract. A stale response from a
   canceled epoch must not be delivered as a new request response.

## Ordering and conflict policy

- **Different sets:** permit independent misses to be allocated and issued
  concurrently. A single refill writer may serialize array writes, but it must
  buffer/associate data per MSHR and must not lose transaction identity.
- **Same set, different lines:** initially serialize issue unless a way is
  explicitly reserved per MSHR and replacement metadata updates are proven
  atomic. Do not let two misses select the same victim way. Same-set banking
  or multiported arrays are not part of this phase.
- **Hit while miss is pending:** retain the existing documented hit bypass;
  arbitrate its lookup/read against miss allocation, refill writes, snoop and
  replacement. A hit may not observe partially written refill data.
- **Snoop of a live miss line:** serialize or retry the snoop until the
  transaction reaches a protocol-safe point; preserve Directory ownership and
  data. A snoop to another line should progress when the existing shared
  resources allow it.
- **Replacement:** reserve victim/way ownership before sending Put or
  invalidations. A live miss must not reuse a way being evicted. Preserve
  PutM and owner-data Snoop progress; no shared resource may be held while
  waiting on a response that itself requires that resource.
- **Shared L2/Directory:** do not change their capacities in this increment.
  First prove how many contexts and refill slots can remain active with two
  misses from each core. The shared line engine and data port may remain
  serialized, but waiting contexts must not corrupt or misroute payloads.

## Array and response arbitration requirements

Before RTL implementation, identify every L1 array operation and grant one
owner per physical port each cycle: tag/data lookup, refill data write,
metadata commit, store merge, snoop metadata change, and replacement line
read. Arbitration must define priority and backpressure for each conflict.
While a request is stalled, its payload and MSHR association remain stable.

## RTL ownership audit and implementation boundary

The following boundary is based on the current RTL, not a proposed module
diagram:

- `DualL1MesiCluster` has one `MesiL1Controller` and one replacement FSM per
  core. Its two-entry tracker retains the second request, but only dispatches
  that entry after the current controller transaction and response retire.
- `MesiL1Controller` owns one CPU transaction register set (`cpu_addr_q`,
  `cpu_txn_q`, `cpu_state_q`) and a separate single-entry Snoop FSM. Grant,
  refill, metadata-commit, and CPU-response handshakes are all qualified by
  that single CPU transaction ID. Duplicating the whole controller per MSHR
  would also duplicate Snoop acceptance/state and risks collisions between
  independently reset transaction-ID counters.
- `DualL1MesiCluster` owns one per-core replacement transaction, one serialized
  line-read owner, and the CPU-versus-replacement request selection. The
  replacement victim way is not reserved for two simultaneous replacement
  transactions today.
- `MesiL1Array` has one refill burst collector (`refill_pending_q`, address,
  way, expected beat), one line-read stream, a shared metadata-write port with
  Snoop priority, and a store write path. It cannot accept interleaved refill
  beats for two lines or two simultaneous line reads. Granting two live CPU
  contexts therefore requires explicit ownership/backpressure at these ports;
  it cannot be enabled by only removing the queued-MSHR dispatch condition.
- The shared Directory and refill MSHR bank already track multiple tagged
  requests, but their occupancy is not evidence that the L1 can associate two
  transactions. The shared line engine, same-set interlock, array port, and
  Grant/Transfer routing remain separate limits and must be measured rather
  than assumed away.

### First implementation slice

Keep the public CPU request/response interface unchanged. Use the existing
per-core response transaction ID as the internal coherence tag, but change its
allocator to select an ID that is not live in either local MSHR. Keep local CPU
acceptance sequence separate from this recyclable protocol ID. No incoming CPU
request ID is needed while miss responses remain FIFO per core and the existing
resident-hit bypass remains its explicitly checked exception.

The first functional RTL slice should create two independent miss contexts per
core and let each issue a Directory request with its own live tag. Keep one
shared Snoop engine per L1, route its metadata/data work through the same array
arbiter, and buffer refill beats by the matching MSHR before granting the
single array refill stream to one complete line at a time. Preserve the current
one replacement FSM per core in this slice: a miss that needs a live victim
must wait for victim release before occupying/refilling that way. Do not claim
two overlapping victim replacements.

This slice does not imply that four refills, Directory grants, or AXI reads
will all overlap. Its first acceptance criterion is two distinct Directory
transactions from one L1 live before either CPU miss response, with correct
out-of-order refill association and FIFO CPU miss retirement. Then measure the
shared Directory, refill, line-engine, L1 array, and AXI peaks independently.
If buffering/serialization at the current array or line engine prevents that
criterion, report the concrete limiting resource before considering additional
ports or banking.

The response path needs a per-core ordered completion queue or equivalent
oldest-live-MSHR selection keyed by the local acceptance-order sequence.
Refill/grant responses may target a younger MSHR by its bound coherence ID,
but cannot overtake an older miss at the CPU interface. The hit bypass remains
a separately specified response class. The existing ID width and namespace
must be checked against the maximum number of concurrently live Directory
transactions before implementation; do not silently truncate or reuse a live
ID.

## Required proof points for implementation

All items start **OPEN** until their test and independent checker pass.

| Testpoint | Required observation | Independent check |
|---|---|---|
| Same-core miss-under-miss | Two different-set misses from one core both accepted by Directory before first CPU response | Internal tags, addresses, Directory commits, data and per-core response order |
| Four CPU misses | CPU0 A/B and CPU1 C/D live before first response | L1 MSHR occupancy is 4; each request has a unique live association |
| Resource accounting | Concurrent four-miss window | Separate peaks for issued L1 MSHRs, Directory contexts, refill MSHRs, AXI R outstanding and AXI W outstanding |
| Out-of-order refill | Refill IDs complete out of issue order | Every beat routes to the matching line/tag; CPU miss responses remain FIFO per core |
| Full backpressure | Both local MSHRs occupied and third miss held | No acceptance, payload stable, one acceptance after a slot retires |
| Same-line conflict | Duplicate line request while first is live | No duplicate issue; held request re-looks up after retirement |
| Same-set/victim collision | Two lines compete for one set or victim | No duplicate way, lost dirty data, stale directory entry, or deadlock |
| Hit-under-miss | Resident read while two misses are live | Existing bypass semantics and data preserved |
| Store/refill collision | Store and refill contend for the array | Byte mask and final line value correct; no early store commit |
| Snoop/replacement collision | PutM/replacement and owner-data Snoop overlap | Directory/L1 state and all eight data beats correct; progress under stalls |
| Reset cancellation | Reset with two live misses and responses pending | All old entries canceled; no stale response; post-reset requests work |

The directed four-miss test must use four independent lines and different L2
sets, a fixed seed and sufficient memory latency. It must record cycle-level
handshakes and retain its trace/waveform. L1 allocation count alone is not
proof of downstream issue or four active refills.

## Implementation ownership and first coding slice

The source audit shows why the queued-MSHR dispatch condition cannot simply be
removed:

| Existing owner | Current single-context resource | Required v1.3 owner |
|---|---|---|
| `MesiL1Controller` | One CPU transaction register set and one CPU FSM | Two miss contexts, each with its own request/grant/refill/commit lifecycle; preserve one shared Snoop engine |
| `DualL1MesiCluster` | Two accepted-entry records, one active controller dispatch per core, one replacement FSM | Order/ID allocation, per-context response retention, grant routing by live ID, and request/response reorder control |
| `MesiL1Array` | One refill burst collector, one line-read stream, shared metadata/data write arbitration | Whole-line refill ownership plus safe arbitration for two MSHRs, Snoop, Store, and Replacement |
| `DirectoryMshrBank` / `SharedLineEngine` | Multi-context Directory state but shared L2/line engine resources | Keep existing capacities; expose real downstream stalls and serialize shared streams without losing per-context identity |

The first coding slice is to split the CPU miss transaction state from the
shared Snoop state, then route two live miss contexts by transaction ID while
keeping the existing public CPU ports unchanged. Its first integration target
is the two-same-core case: two different-set cold misses both handshake at the
Directory before either CPU miss response, with distinct live IDs and FIFO CPU
miss retirement. The next slice adds complete-line refill buffering and array
write arbitration; only after that should replacement/Snoop/Reset collisions
be enabled for the two-context path. Each slice must include a directed test
and Checker before proceeding.

Current baseline evidence is only the accepted-entry tracker: each core has
two allocated slots, while controller-owned and Directory-issued miss peaks
are one per core. The present top therefore does **not** satisfy the first
coding-slice criterion. No production RTL change is made by this contract
update.

## Explicit limits for this phase

- No same-line MSHR merge.
- No arbitrary same-core CPU response reordering and no CPU request-ID port.
- No L2 banking, extra SRAM ports, Directory-context increase, or AXI protocol
  change without measured evidence and a separate design review.
- No performance claim until the same Benchmark v4 workload/settings are run
  against a preserved baseline and this implementation.
- No PPA, SRAM macro, STA, or silicon sign-off claim.
