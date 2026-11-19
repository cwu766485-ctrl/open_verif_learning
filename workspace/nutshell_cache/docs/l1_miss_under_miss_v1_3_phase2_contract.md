# v1.3 Phase 2 — Same-L1 Miss-under-Miss Contract

**Status (2026-11-19): implemented and integrated in the current working-tree snapshot; the first same-core Directory concurrency acceptance test and four-miss resource test pass.**

The measured implementation evidence is in
[`reports/full_system/v13/nonblocking_l1_coverage.json`](../reports/full_system/v13/nonblocking_l1_coverage.json)
and [`docs/dv/v1.3_nonblocking_l1_validation.md`](dv/v1.3_nonblocking_l1_validation.md).
The recorded source base is `b75e94ed4ab42024518707d50a8716b128827e35` plus
the dirty-tree snapshot hash recorded in the JSON. The full AXI wrapper build
completed, six focused tests passed, and the integrated full-system suite
reported 76 passed / 1 skipped. The broader `coherence_verify` target did not
complete because the Benchmark v4 B03 working-set sweep was interrupted; this
is not a full release sign-off.

This document records the implementation contract and its evidence. Historical
baseline descriptions and source audits below refer to the pre-implementation
single-issue design; the 2026-11-19 status and evidence above supersede those
statements.

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
  `cpu_txn_q`, `cpu_state_q`). Its single-entry Snoop FSM is now structurally
  isolated in `MesiL1SnoopEngine`, one instance per L1. Grant, refill,
  metadata-commit, and CPU-response handshakes are still qualified by the
  single active CPU transaction ID. Duplicating the whole controller per MSHR
  would still duplicate Snoop acceptance/state and risks collisions between
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

The first structural step is complete: `MesiL1SnoopEngine` now owns the former
Snoop FSM while preserving the controller's external interface. This prepares a
single shared Snoop path for future per-MSHR CPU contexts; it does not add
same-core concurrent Directory requests or change miss issue behavior.

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
was exercised with distinct live IDs in the two-context and four-miss tests.
The tests do not replace a separate namespace-width proof for every possible
parameterization; no live ID may be silently truncated or reused.

## Required proof points and current evidence

Statuses below refer only to the dirty snapshot and the local runs linked at
the top of this document. `PASS` means the stated checker/testpoint was observed
in that run; `PARTIAL` means a related case passed but not the full stated
cross; `OPEN` remains required work.

| Testpoint | Required observation | Current status and evidence |
|---|---|---|
| Same-core miss-under-miss | Two different-set misses from one core accepted by Directory before first CPU response | **PASS** — seed 1245697; Directory handshakes at cycles 3/7, IDs 0/1; first response cycle 221; lifecycle checkers passed. |
| Four CPU misses | CPU0 A/B and CPU1 C/D live before first response | **PASS** — seed 1246212; four Directory handshakes observed before any CPU response; per-core MSHR peak 2. |
| Resource accounting | Concurrent four-miss window | **PASS** — L1 issued contexts 4, Directory 4, refill MSHR 4, AXI R 4, AXI W 0 (read-only test). |
| Out-of-order refill | AXI read IDs return out of issue order | **PASS** — first two read IDs deliberately reversed; transaction/data association and per-core CPU miss order checked. |
| Full backpressure | Both local entries occupied and further request held | **PASS** — third request remained unaccepted until an entry retired; request stability/release checked by the four-miss test. |
| Same-line conflict | Duplicate line request while first is live | **PASS** — duplicate was not separately issued and re-looked-up after the first transaction. |
| Same-set/victim collision | Two different lines compete for one set/victim | **OPEN** — same-set issue is constrained; dirty victim-way reservation under two live misses needs dedicated checking. |
| Hit-under-miss | Resident read while misses are live | **PARTIAL** — the existing bypass is verified with one live miss. With both MSHR entries occupied, current `hit_under_miss_ready` deliberately deasserts; resident-hit progress in that state is unsupported and untested. |
| Store/refill collision | Secondary Store and refill/metadata activity contend | **PARTIAL** — secondary Store commit, peer owner-data Snoop, and FIFO responses passed; complete byte-mask/refill collision matrix remains open. |
| Snoop/replacement collision | Dirty PutM/replacement overlaps owner-data Snoop | **OPEN** — this run does not close the two-live-miss dirty replacement progress/deadlock case. |
| Reset cancellation | Reset cancels live entries without stale response | **PARTIAL** — reset epoch and cancellation passed with two accepted L1 entries; all phases with two simultaneously issued misses remain to be covered. |

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

The first coding slice described by the original plan is implemented in the
current snapshot: two live miss contexts per L1 are routed by their internal
transaction IDs, while the existing public CPU ports remain unchanged. The
same-core test observes two different-set Directory handshakes before the first
CPU response; the four-miss test observes four Directory contexts, refill
MSHRs and AXI reads outstanding. Refill ownership is held for a complete line,
and metadata/store/refill writes are arbitrated at the L1 array interface.
Replacement remains a single per-core FSM, so not every replacement/Snoop
overlap has been proven for two live misses.

The pre-implementation accepted-entry-only measurements (one controller-owned
and one Directory-issued miss per core) are historical. The current snapshot
has separate primary and secondary miss contexts and records two issued misses
per core in the four-request test. See the machine-readable evidence above for
the current checker results and resource peaks.

The Hit-under-Miss bypass is intentionally narrower than the two-entry miss
capacity: it accepts a resident read only when exactly one MSHR is valid. With
two live entries, the shared lookup/refill arbitration and single hit-response
slot are not proven for bypass, so requests remain backpressured. This is a
known v1.3 limitation, not evidence that Hit-under-Miss works at full MSHR
occupancy.

## Explicit limits for this phase

- No same-line MSHR merge.
- No arbitrary same-core CPU response reordering and no CPU request-ID port.
- No L2 banking, extra SRAM ports, Directory-context increase, or AXI protocol
  change without measured evidence and a separate design review.
- No performance claim until the same Benchmark v4 workload/settings are run
  against a preserved baseline and this implementation.
- No PPA, SRAM macro, STA, or silicon sign-off claim.
