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
  memory writeback interface before the entry is invalidated.

## Current integration boundary

The top supports the blocking request/refill/snoop/grant path, but replacement
is deliberately incomplete. An L1 miss safely stalls if its selected way is
occupied; the L1 Put/PutAck replacement sequencer is not implemented. An L2
victim is reclaimed only when its directory is `DIR_I` with no sharers or
owner. Dirty data for that case is written to memory first. A victim with live
L1 copies raises `memory_adapter_protocol_error` and halts the line engine;
the inclusive back-invalidation sequencer is still needed. The memory write
port treats the accepted final beat as completion and has no separate error
response.

The line ports use 64-byte lines transferred as eight 64-bit beats. Producers
must hold payload stable while stalled; beat indices run 0 through 7 and
`last` is asserted only for beat 7. Reset is shared across the blocks and
clears all protocol metadata and pending streams.

No RTL compilation, simulation, or regression has been run for these integration
blocks yet.
