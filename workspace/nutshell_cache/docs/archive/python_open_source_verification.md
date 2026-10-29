# Python/open-source RTL verification platform

> **Archived verification snapshot.** Some migration status, coverage counts,
> and stress limitations below predate the current Python/Toffee regression.
> Use [`dv/README.md`](../../dv/README.md), the current
> [testplan](../testplan_to_coverage_matrix.md), and the
> [final report](../../reports/final/nutshell_cache_verification_report.md)
> for maintained guidance and results.

This project intentionally verifies the maintained Verilog RTL directly. Chisel
is not part of the build or test flow.

```text
rtl/legacy_l1/CacheTop.v + rtl/Cache.files.f
        |
        v
Picker export --sim verilator --lang python
        |
        v
Cache/python/dut.py  (generated DUT binding; disposable)
        |
        v
pytest + Toffee environment
  - SimpleBus master drives CPU requests
  - memory slave models refill/writeback and backpressure
  - MMIO slave checks cache bypass
  - coherence agent checks probe/release
  - reference model checks architectural data, write masks, set/tag/dirty
    history, and probe-hit line retention
```

The active Python environment is under `dv/`, with scenario tests in `tests/`.
`src/` is retained as a legacy migration source. Generated
`Cache/`, waveform, coverage and Python cache files are disposable and removed
by `make clean`.

The coherent subsystem has a separate Python/Toffee path through
`dv/rtl/CoherentCachePythonWrapper.sv`. One `DualCoreCpuDriver` owns both packed
CPU lanes, while `LineMemoryAxiAgent` models the DUT's custom line-memory
boundary (not AXI's five-channel protocol): writable 64-byte lines, IDs,
read/write bursts, and write responses. `CoherenceScoreboard` independently
models byte-accurate data, MESI permissions, L1 ways, and inclusive L2 directory
ownership. `CachePerfMonitor` samples the RTL's accepted L1 and L2 refill events.
Run `make coherence_python_test` for functional checks or
`make coherence_python_verify` for those checks plus Benchmark v2.

The project targets an open simulator/tool flow and does not depend on a
commercial simulator or SystemVerilog UVM. Verification roles are implemented
with Python/Toffee agents, pytest, and Verilator; UVM is not the comparison
target.

## Recommended workflow

```bash
make clean
make gen_dut
make test
make report
```

The DUT is a blocking, single-active-miss cache. It supports an eight-beat
line refill/writeback and ready/valid stalls, but has no MSHR, transaction ID,
multiple outstanding misses or out-of-order response interleaving. Tests should
therefore focus on correctness of the serialized transaction FSM, burst pause/
resume, hit forwarding, dirty eviction, MMIO isolation and probe release.

## Verification layers

1. Interface checks: reset, ready/valid stability and legal one-hot way select.
2. Directed functional tests: read/write hit and miss, masks, MMIO, eviction,
   coherence and cross-line accesses.
3. Constrained-random traffic: seeded mixed reads/writes and replacement.
4. Scoreboard/reference model: compare CPU responses and downstream memory side
   effects, including old data returned by writes.
5. Structural metrics: Verilator line coverage and transaction counters.

## Dual-L1 Python/Toffee verification

The Python subsystem suite currently covers the dual-core owner-transfer path,
paired independent cold misses, byte-masked stores, an L1 replacement that
hits in shared L2, and both dirty-owner and two-sharer live L2 victim reclaim.
A dedicated four-way L1 replacement test compares reference-predicted victim
addresses and Put opcodes with accepted Directory requests. Long stress keeps
20 reproducible seeds × 200 mixed operations, adds ten same-L1-set conflict
lines spread across four L2 sets, and runs a deterministic dirty/shared victim
prologue on seed `0x5eed`. The prologue creates nine same-set L2 pressure
sequentially and checks both an M-owner victim and a two-sharer S victim.
An additional experiment with nine same-L2-set lines mixed into dual-lane
random traffic produced Directory mismatches or response timeouts in 14/20
seeds; that concurrent pattern remains an open stress issue, not a passing
claim of the accepted regression.
Benchmark v3 records
per-core and aggregate L1 hit/miss rates, Directory L2 refill hit/miss rates,
mean/P95 CPU latency, operations per cycle, snoops, writebacks, and backing
memory read/write bytes and bandwidth. JSON and CSV outputs are generated under
`benchmarks/results/`.

These tests complement the SystemVerilog subsystem benches; they do not yet
replace every SV scenario. The Python model follows architectural requests and
responses, and its replacement/directory state is predicted independently of
DUT MESI state outputs. Formal remains a separate SymbiYosys flow.
