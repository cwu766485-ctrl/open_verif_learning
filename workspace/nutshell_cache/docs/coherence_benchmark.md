# Dual-L1 MESI Benchmark v2

Benchmark v2 runs as a Python/Toffee test against the packed
`CoherentCacheSubsystem` wrapper. It does not patch a SystemVerilog testbench.
The single dual-core driver owns the packed request/response pins, and the
writable 64-byte memory model preserves data across dirty writebacks.

## Run

```bash
make coherence_benchmark_v2
```

The target exports the wrapper with Picker, compiles it with Verilator, and
runs the deterministic tests at memory response delays of 2, 20, 50, and 100
cycles. Results are written to
[`../benchmarks/results/coherence_benchmark_v2.json`](../benchmarks/results/coherence_benchmark_v2.json)
and the matching CSV. To run the Python functional suite and benchmark in one
clean export, use `make coherence_python_verify`.
The checked-in run summary and limitations are in
[`coherence_benchmark_v2_results_2026-10-25.md`](coherence_benchmark_v2_results_2026-10-25.md).

## Workloads

- 64 warm L1 reads.
- An L1 replacement followed by a shared-L2 refill hit. The test checks that
  no backing-memory line read occurs in the measured access.
- Sixteen serialized cold misses versus sixteen cold misses sent as eight
  two-core request pairs.
- Alternating stores to one M-owned line to measure ownership-transfer snoops.
- Eight M-owned lines kept live across both L1s, followed by a ninth same-set
  line to measure back-invalidation, dirty owner data, and memory writeback.
- The functional suite separately checks byte-masked stores, independent cold
  misses, dirty inclusive-L2 eviction, all eight writeback beats, and the write
  response before the evicted line is read again.

Each workload declares its initial cache state. Fixed addresses and seed zero
make the runs repeatable. The benchmark uses a configurable response delay,
not a claim about real DRAM timing. The RTL simulation clock period is 10 ns.

## Metrics

- L1 hit/miss counts and rates are sampled on accepted CPU requests. A store
  from S is an upgrade miss; E/M stores are hits.
- L2 hit/miss counts describe accepted Directory refill lookups against the
  shared L2 data array. They do not count every Directory metadata probe.
- Mean and nearest-rank P95 latency span CPU request acceptance through response
  capture by the driver. `ops_per_cycle` is completed CPU operations divided by
  the measured window.
- Memory bandwidth counts accepted 64-bit R/W data beats, converts them to
  bytes, and divides by window cycles. Read, write, and aggregate BW are reported
  in bytes/cycle and MiB/s at the 100 MHz simulation clock. These are
  line-memory interface measurements, not physical DRAM bandwidth.

The current two-L1 RTL can overlap at most two CPU-originated misses because
each L1 controller is blocking. The benchmark therefore measures dual-core
overlap; it does not establish utilization of all four Directory contexts or
four refill MSHRs. The AXI adapter's independent 4-outstanding stress test is
kept separate from this two-core CPU workload.
