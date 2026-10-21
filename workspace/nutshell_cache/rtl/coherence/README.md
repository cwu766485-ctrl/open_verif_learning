# MESI RTL integration blocks

`rtl/Coherence.files.f` contains the new coherence RTL in dependency order. It
does not change the legacy `rtl/Cache.files.f` single-L1 baseline.

## Implemented blocks

- `CoherenceProtocol.sv`: common MESI, directory, request, snoop, grant, and
  line-transfer encodings.
- `MesiL1Controller.sv`: one blocking LSU request FSM plus an independent
  snoop FSM. It commits local MESI metadata before acknowledging a Grant or
  SnoopData response.
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
  memory writeback interface before the entry is invalidated. NutShell MMIO
  addresses in `[0x3000_0000, 0x8000_0000)` use an independent, serialized
  request/response bypass and never allocate in L1, L2, or the Directory.
  Memory requests and line beats carry the active transaction ID; refill beats
  with a mismatched ID are rejected before reaching the L2 array.

## Current integration boundary

The blocking top now handles all three L1 victim states. It stages the
request, sends PutS/PutE/PutM, transfers all eight beats for PutM, waits for
PutAck and commit, invalidates the old L1 line, then replays the pending miss.
The shared L2 reclaims `DIR_I` victims directly, invalidates every recorded
sharer of a `DIR_S` victim, and invalidates a `DIR_U` owner while recovering
its full line. Dirty data is written to memory before the victim entry is
released. The memory write port treats the accepted final beat as completion
and has no separate error response.

The line ports use 64-byte lines transferred as eight 64-bit beats. Producers
must hold payload stable while stalled; beat indices run 0 through 7 and
`last` is asserted only for beat 7. Reset is shared across the blocks and
clears all protocol metadata and pending streams. External CPU, MMIO, and
backing-memory handshakes are blocked while reset is asserted. The external
memory model must share this reset so requests from before reset are cancelled.

The subsystem regression compiles the integrated RTL with Verilator assertions
enabled. It checks directed protocol and eviction flows, channel backpressure,
reset cancellation, concurrent requests, and a reference-data scoreboard. A
seeded 80-operation phase is part of every run. `coherence_random` repeats the
suite with five recorded seeds. This is a functional regression gate; it does
not establish full RTL lint cleanliness or unbounded whole-subsystem proof.

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
requests and write beats, and the Directory request path; memory refill data
includes valid gaps. Ready/valid payload stability and MESI/directory metadata
invariants are asserted during the run. Reset is injected while a refill
request, a backpressured MMIO response, a backpressured CPU response, an owner
SnoopData stream, and a stalled dirty L2 writeback beat are active. Concurrent
cases submit same-line requests from both cores and
different-line misses together. A scoreboard checks returned read values and
applies byte masks to committed writes. The randomized phase varies addresses,
cores, operation type, and masks under periodic stalls.

The SymbiYosys proof is limited to `CoherenceRequestArbiterCore`: selection
correctness, source retention while stalled, and winner rotation under
continuous two-source contention pass bounded basecase plus induction. It is
not a formal proof of the MESI controllers, Directory, L2 replacement, or the
complete subsystem. The remaining explicit channel gap is backpressure applied
by the L2 receiver to a valid memory refill data beat; current refill coverage
uses inter-beat valid gaps and request-side stalls.

Run the directed/default-seed suite with `make coherence_smoke`, the five-seed
suite with `make coherence_random`, and the arbiter proof with
`make coherence_formal`.
