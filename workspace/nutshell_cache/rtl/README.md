# Readable RTL layout

This directory is the maintained, human-oriented NutShell Cache RTL. It is a
behavior-preserving Verilog baseline; timing and ready/valid handshakes are
kept stable while generated provenance comments are removed.

Do not delete generated-looking wires merely because their names are ugly:
`_RAND_*` supports simulation initialization and `_T_*`/`_GEN_*` may encode
synchronous-read timing and handshake conditions. The cleanup strategy is to
move generated implementation into `generated/`, then maintain semantic RTL
and small standalone combinational units here, with regression equivalence.

## Ownership

- `rtl/`: maintained Verilog RTL source.
- `src/`, `test/`: Python/Toffee verification environment and tests.

## Layout

- `CacheTop.v`: top-level Cache module.
- `pipeline/`: Stage 1 lookup, Stage 2 hit/miss decision, Stage 3 transaction FSM.
- `array/`: metadata/data arrays and access wrappers.
- `control/`: arbitration and small decision logic.
- `interfaces/`: CPU, downstream-memory, MMIO and coherence interface contracts.
- `bus/`: compatibility placeholder retained for future bus adapter modules.

## Naming policy

New hand-written modules use semantic names such as `AddressDecoder`,
`ByteMaskMerge`, `TagCompareUnit` and `ReplacementSelector`. Existing
generated module names are retained inside the baseline until a full
interface/trace equivalence check is available.

## Stage 3 Phase-2 regions

`pipeline/CacheStage3.v` is intentionally one stateful module. Its internal
regions are request classification, selected-way data/meta, hit path, writeback
path, refill path, MMIO bypass, coherence release, main FSM, array write
arbitration and CPU response. These paths share request registers, beat
counters, array ports and ready/valid state.

Stage 3 remains one module in this first pass because hit, writeback, refill,
MMIO, probe release, counters and ready/valid response control share state.
Splitting those paths will be done only after a passing behavioral baseline.

## Validation rule

Any RTL edit must be compiled with `Cache.files.f` and run against the same
regression before it is considered complete.
