# Maintained RTL layout

`rtl/` contains the human-oriented NutShell Cache RTL. The legacy single-L1
Verilog baseline keeps its interfaces and timing contracts stable. Do not
remove generated-looking wires from that baseline without checking whether they
carry initialization, synchronous-read timing, or handshake behavior.

## Ownership

- `rtl/`: maintained synthesizable RTL and source filelists.
- `tests/`: Python/Toffee tests and SystemVerilog benches.
- `src/`: retained legacy migration source.

## Functional layout

- `common/`: MESI and line-transfer protocol definitions.
- `l1/`: MESI L1 array, controller, and snoop arbiter.
- `directory/`, `l2/`: directory transaction contexts and shared L2 array.
- `interconnect/`: request arbitration between L1 clients.
- `bus/axi/`, `bus/apb/`: AXI line-memory adapter and APB performance CSR.
- `cluster/`, `top/`: dual-L1 cluster and cache subsystem tops.
- `legacy_l1/`: original CacheTop, pipeline, arrays, and control blocks.

`Cache.files.f` and `Coherence.files.f` are the stable compile lists for the
legacy and MESI designs. SystemVerilog benches are grouped under `tests/` and
built through the focused Make targets.

## Naming policy

New hand-written modules use semantic names such as `AddressDecoder`,
`ByteMaskMerge`, `TagCompareUnit`, and `ReplacementSelector`. Existing generated
module names are retained inside the legacy baseline until interface and trace
equivalence is available.

## Legacy Stage 3 regions

`legacy_l1/pipeline/CacheStage3.v` remains one stateful module. Its internal
regions share request registers, beat counters, array ports, and ready/valid
state, so splitting them requires a passing behavioral baseline first.

## Validation rule

Compile legacy RTL with `Cache.files.f` and the MESI subsystem with
`Coherence.files.f`. Run the corresponding Python regression or focused
SystemVerilog Make target after functional RTL changes.
