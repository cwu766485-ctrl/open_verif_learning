# MESI RTL integration blocks

`rtl/Coherence.files.f` contains the new coherence RTL in dependency order. It
does not change the legacy `rtl/Cache.files.f` single-L1 baseline.

## Implemented blocks

- `CoherenceProtocol.sv`: common MESI, directory, request, snoop, grant, and
  line-transfer encodings.
- `MesiL1SnoopArbiter.sv`: same-line CPU/Snoop ownership and retry policy,
  shared by the L1 controller and its focused formal proof.
- `MesiL1Controller.sv`: one blocking LSU request FSM plus an independent
  snoop FSM. Same-line work is serialized, Snoop wins idle-cycle conflicts,
  and unrelated Snoop traffic can progress while the CPU FSM is busy.
- `DirectoryController.sv`: one globally serialized directory transaction;
  it handles GetS/GetM/Upgrade and PutS/PutE/PutM control sequencing.
- `MesiL1Array.sv`: parameterized tag/data/MESI array. The configured geometry
  is 128 sets × 4 ways × 64 bytes = 32 KiB. It has an LSU lookup port, separate
  CPU/snoop metadata writes, byte-masked M-state stores, refill sequencing,
  and a serialized snoop line-read port. `replace_valid` means the selected
  replacement way currently contains a live victim.
- `CoherenceRequestArbiter.sv`: two-input round-robin arbiter. It holds the
  selected request source while the downstream Directory applies backpressure.
- `SharedL2DirectoryArray.sv`: 512 sets × 8 ways × 64 bytes = 256 KiB, with
  directory state, sharers, owner, and an L2 dirty bit. It has full-line
  read/write ports, reports a full-set victim, and will not overwrite that
  victim implicitly. The integration controller must invalidate its L1 copies,
  write back dirty data, then use `entry_invalidate` before allocating the way.
- `DualL1MesiCluster.sv`: instantiates two `MesiL1Controller`s, two configured
  L1 arrays, and the shared request arbiter. CPU read data and masked stores
  connect to the arrays. Directory-facing request/snoop/grant channels and
  owner data streams are exposed for an upper Directory/L2 line adapter.
- `CoherentCacheSubsystem.sv`: composes the dual-L1 cluster, serialized
  Directory controller, and shared L2 array. It routes snoops and owner data,
  refills L2 from an eight-beat backing-memory read interface, and returns L2
  lines to the selected L1. Dirty, unshared L2 victims use an eight-beat
  memory writeback interface and wait for its response before invalidation. NutShell MMIO
  addresses in `[0x3000_0000, 0x8000_0000)` use an independent, serialized
  request/response bypass and never allocate in L1, L2, or the Directory.
  Memory requests and line beats carry the active transaction ID; refill beats
  with a mismatched ID are rejected before reaching the L2 array.

## Focused module regressions

The module-level benches use reduced array geometries but keep the production
RTL indexing, protocol widths, and handshakes. Run each block independently
from the repository root:

```sh
make coherence_l1_array       # refill, lookup, masked store, Snoop metadata,
                              # line-read backpressure, replacement, bad beat
make coherence_l1_controller  # E-to-M, GetS and GetM/refill, Upgrade,
                              # M/S SnoopInvalidate, stalled channels, reset
make coherence_directory      # GetS/GetM/Upgrade, PutS/PutE/PutM,
                              # owner snoops, channel stalls, active reset
make coherence_l2_array       # directory metadata, eight-beat data,
                              # read stall, dirty victim, reclaim, bad beat
make coherence_request_arbiter # round-robin, source lock, payload routing,
                               # reset and backpressure
make coherence_snoop_arbiter   # same/different-line CPU/Snoop arbitration
make coherence_cluster         # two L1 arrays/controllers plus request mux
make coherence_modules         # all seven block/cluster benches
make coherence_multisnoop     # L2 DIR_S victim invalidates both L1 sharers
make coherence_formal         # arbiters plus 16-step Directory/L1 checks
make coherence_verify         # all above plus subsystem directed/random tests
```

## Verification decomposition

| Layer | RTL block | Dedicated evidence | Remaining boundary |
| --- | --- | --- | --- |
| Protocol | `CoherenceProtocol.sv` | Compiled by every coherence bench; protocol encodings are exercised by the controller and subsystem tests | No separate package-only bench; the package contains enums and small helper functions |
| Request arbitration | `CoherenceRequestArbiter` | Directed simulation for reset priority, round-robin alternation, selected-source retention under backpressure, and payload routing; separate SymbiYosys proof | No multi-request queue; only two request sources are supported |
| Per-L1 CPU/Snoop arbitration | `MesiL1SnoopArbiter` | Directed same-line/different-line cases and independent SymbiYosys properties | Progress is checked under the documented valid/ready contract; no liveness proof without fairness assumptions |
| L1 storage | `MesiL1Array` | Refill, lookup, masked store, Snoop metadata, line-read stalls, replacement, malformed beat | Reduced geometry in the bench; production geometry is checked by elaboration/integration |
| L1 protocol control | `MesiL1Controller` | GetS/GetM/Upgrade, E-to-M, SnoopInvalidate, channel stalls, active reset; 16-step bounded formal checks | Formal harness is controller-level, not a proof of the array/controller composition |
| Directory control | `DirectoryController` | GetS/GetM/Upgrade, PutS/PutE/PutM, owner Snoop, channel stalls, active reset; 16-step bounded formal checks | One globally serialized Directory transaction |
| Shared L2 storage | `SharedL2DirectoryArray` | Tag/directory metadata, full-line transfers, stalls, dirty victim reporting and reclaim, malformed beat | Live-victim recovery is additionally checked at subsystem level |
| Dual-L1 cluster | `DualL1MesiCluster` | Simultaneous independent L1 misses, request-source ordering, transaction routing, two full refills and CPU response-data checks | Snoop ownership between the two L1s and eviction interaction are covered at subsystem level |
| Memory/MMIO adapters | Subsystem memory and MMIO paths | Backpressure, transaction IDs, read/write errors, reset cancellation and bypass are checked at subsystem level | Not split into separate adapter-only benches yet |
| Integrated subsystem | `CoherentCacheSubsystem` | Directed MESI/victim/error/reset/concurrency tests, scoreboard, assertions, multisnoop case, and fixed-seed randomized operations | No unbounded proof of the complete subsystem |

`make coherence_modules` runs six leaf-module benches plus the dual-L1 cluster
bench. `make
coherence_verify` adds the formal gate and integrated subsystem regression. The
legacy single-L1 Python/Toffee verification remains a separate regression path.

The Directory is a two-core, single-requester transaction controller. For any
one request, its protocol can require at most one remote L1 snoop; the
multi-target case is the inclusive L2 `DIR_S` victim path, where the subsystem
must invalidate both recorded sharers before releasing the victim. That case
has a dedicated check in `coherence_multisnoop`.

`coherence_formal` checks local properties for the request and Snoop arbiters,
Directory FSM, and L1 controller with SymbiYosys. The arbiter jobs retain their
inductive/combinational proofs. The Directory/L1 jobs are 16-step bounded
safety checks for output stability under backpressure, transaction routing,
metadata legality, reset cancellation, and Snoop/refill data routing. These
compositional checks do not prove the complete cache subsystem. The focused
simulation tests complement the top-level `coherence_smoke` and five-seed
`coherence_random` regressions.

GitHub Actions runs `make coherence_verify` using the YosysHQ OSS CAD Suite,
which supplies the Slang SystemVerilog frontend needed by the controller
formal harnesses as well as Yosys, SBY, Z3, and Verilator.

## Current integration boundary

The blocking top now handles all three L1 victim states. It stages the
request, sends PutS/PutE/PutM, transfers all eight beats for PutM, waits for
PutAck and commit, invalidates the old L1 line, then replays the pending miss.
The shared L2 reclaims `DIR_I` victims directly, invalidates every recorded
sharer of a `DIR_S` victim, and invalidates a `DIR_U` owner while recovering
its full line. Dirty data is written to memory before the victim entry is
released. The memory write port has a separate transaction-ID tagged response;
a failed response leaves the victim valid and dirty.

The frozen memory contract is documented in `docs/cache.md` §6.1: synchronous
shared reset cancels transactions; reads return eight beats or one terminal
beat-0 error; writes return an explicit response after beat 7; malformed and
failed transactions latch `fatal_error` and suppress success responses. The
response cannot arrive in the same cycle as its request/final-beat handshake.
All line ports use 64-byte lines transferred as eight 64-bit beats. Producers
must hold payload stable while stalled; beat indices run 0 through 7 and
`last` is asserted only for beat 7. See §6.2 for Snoop progress and §6.3 for the
frozen logical SRAM bank/port mapping.

The subsystem regression compiles the integrated RTL with Verilator assertions
enabled. It checks directed protocol and eviction flows, channel backpressure,
reset cancellation, concurrent requests, and a reference-data scoreboard. A
seeded 80-operation phase is part of every run. `coherence_random` repeats the
suite with five recorded seeds. Directed cases also exercise terminal memory
read errors and failed write responses while checking that the dirty victim is
retained. This is a functional regression gate; it does not establish full RTL
lint cleanliness or unbounded whole-subsystem proof.

The integrated bench also maintains an independent two-core MESI shadow model.
It updates the model from completed CPU transactions, accepted snoops, and Put
requests, then compares every modeled line against both physical L1 copies,
all eight data beats, and the corresponding L2 directory metadata. The data
reference table separately checks every CPU read and masked write. Functional
bins are defined in `dv/coverage/coherence_map.json` as Feature → Testpoint →
Bin → Test; `make coherence_regression` fails if any planned bin or required
ready/valid stall is absent. It retains per-seed logs, merged Verilator line and
branch coverage, and `reports/coherence/regression.md` / `.json`.

The regression report includes cycle-based L1 hit, miss, and remote-snoop
latencies plus configured cache capacity. Those are RTL simulation results.
There is no target standard-cell library, SRAM compiler model, clock
constraint, or physical-design flow in this repository, so area and timing
figures are not silicon PPA or static timing signoff.

## Directed subsystem smoke test

`tb/CoherentCacheSubsystem_tb.sv` exercises the integrated dual-L1 path with a
small deterministic memory model. From the project root, run:

```sh
make coherence_smoke
```

The test covers MMIO bypass reads/writes, backing-memory refill, silent E-to-M
writes, sharing, S-to-M
upgrade, remote GetS/GetM interventions from both M and E owners, and byte-
masked writes. It checks every beat of lines transferred during owner
intervention, L1 PutS/PutE/PutM replacement, and live L2 `DIR_U` and `DIR_S`
victims. It also checks dirty owner recovery, invalidation of all recorded
sharers, memory writeback, and clear protocol-error outputs.
It also stalls CPU responses, MMIO request/responses, backing-memory read/write
requests and write beats, a valid refill beat at the L2 receiver, and the
Directory request path; memory refill data includes valid gaps. Ready/valid
payload stability and MESI/directory metadata invariants are asserted during
the run. Reset is injected while a refill
request, a backpressured MMIO response, a backpressured CPU response, an owner
SnoopData stream, and a stalled dirty L2 writeback beat are active. Concurrent
cases submit same-line requests from both cores and
different-line misses together. Dedicated cases check concurrent upgrades,
same-line Snoop waiting behind E-to-M store commit, and different-line Snoop
progress during a stalled CPU response. A scoreboard checks returned read
values and applies byte masks to committed writes. The randomized phase varies
addresses, cores, operation type, and masks under periodic stalls.

The SymbiYosys checks cover `CoherenceRequestArbiterCore` selection/source
retention, the combinational per-L1 same-line CPU/Snoop arbitration rules, and
bounded Directory/L1 controller safety properties. They do not prove L2
replacement or the complete subsystem. The integrated directed test forces
the L2 refill receiver to stall a valid memory beat and checks payload
stability; memory read/write error paths and local CPU/Snoop progress have
dedicated directed cases.

Run the directed/default-seed suite with `make coherence_smoke`, the five-seed
suite with `make coherence_random`, and the local formal checks with
`make coherence_formal`.
