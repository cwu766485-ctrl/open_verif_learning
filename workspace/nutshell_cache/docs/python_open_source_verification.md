# Python/open-source RTL verification platform

This project intentionally verifies the maintained Verilog RTL directly. Chisel
is not part of the build or test flow.

```text
rtl/CacheTop.v + rtl/Cache.files.f
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
    history, and probe invalidation
```

The active Python environment is under `dv/`, with scenario tests in `tests/`.
`src/` and `test/` are retained as legacy migration sources. Generated
`Cache/`, waveform, coverage and Python cache files are disposable and removed
by `make clean`.

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
