# MESI RTL module ownership

The subsystem top is a structural composition point. It retains the external
CPU, MMIO, backing-memory, monitor, and error interfaces, and connects the L1
cluster, Directory bank, shared L2 array, and line engine. Stateful protocol
behavior is assigned to the module that owns it.

## Extracted from `CoherentCacheSubsystem`

| Module | Responsibility | Preserved behavior |
| --- | --- | --- |
| `rtl/interconnect/CpuMmioRouter.sv` | Selects cacheable requests for the dual-L1 cluster, routes responses, and serializes the uncached MMIO bypass. | Same MMIO address window, round-robin preference, single-outstanding request state, and fatal/reset gating. |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | Tracks memory refill IDs, collects eight response beats, schedules L2 fill streams, and retires completed Directory contexts. | Same slot selection, ID matching, beat/error checks, fill and completion round-robin order, and reset behavior. |
| `rtl/interconnect/L2LineWriteArbiter.sv` | Selects the owner of the shared L2 line-write port among PutM, victim snoop data, refill data, and Directory owner data. | Same source priority and ready routing; the selected stream retains ownership through its existing beat handshakes. |
| `rtl/coherence/SharedLineEngine.sv` | Runs the shared line FSM for refill, inclusive victim recovery, dirty writeback, PutM, grant, and snoop flows. | Original 16 state encodings, reset values, transition priorities, and handshake conditions. This is a structural extraction, not a protocol redesign. |

The top keeps aliases such as `engine_state_q`, `mem_mshr_full_q`, and
`l2_line_wr_*` for existing testbench diagnostics and monitor wiring. These are
observations of the extracted modules' signals and do not add duplicate state.

## Remaining top-level responsibilities

`CoherentCacheSubsystem` still owns the connections among the four extracted
blocks, `DualL1MesiCluster`, `DirectoryMshrBank`, and
`SharedL2DirectoryArray`. Shared lookup ownership, Directory handshakes,
snoop routing, memory channel wiring, performance event wiring, and top-level
assertions remain visible there because they span module boundaries.

`DirectoryController`, `DirectoryMshrBank`, `MesiL1Controller`,
`MesiL1Array`, `LineMemoryAxi4Adapter`, `CachePerformanceCsr`,
`DualL1MesiCluster`, and `CoherentCacheAxiSubsystem` were not split in this
refactor. In particular, the victim/PutM/refill/grant sequencing remains in a
single `SharedLineEngine`; extracting smaller engines would change shared state
ownership and needs a separate design review.

## Source lists

`rtl/Coherence.files.f` lists the shared line engine, MMIO router, L2 write
arbiter, and refill MSHR bank along with the existing MESI modules. The legacy
single-L1 list `rtl/Cache.files.f` is unchanged.

This document describes RTL ownership and compile organization. It does not
claim new functional coverage, formal proof, synthesis, or PPA results.
