# Dual-L1 MESI Cache Benchmarking

## Benchmark v4

Benchmark v4 is the Cache-only performance suite. It measures L1 read/write
hit and miss rates, refill L2 rates, CPU request-to-response latency, miss
penalty, per-core/aggregate operations per cycle, backing-memory bytes/cycle,
MSHR and Directory-context occupancy, channel stall cycles, snoop traffic,
and false-sharing behavior. The fixed workload set is B01–B08, including the
4/16/32/64/256/512 KiB working-set sweep, same-set conflict tests, mixed
read/write ratios, four memory-delay points for dual-core misses, ownership
ping-pong, and false-sharing A/B.

The measurements use two LSU agents; no real CPU retires instructions. Thus
Benchmark v4 does not report IPC, CPI, MPKI, CoreMark, or application
performance. Bytes/cycle comes from the simulated backing-memory interface and
is not physical DRAM bandwidth or PPA. See the [v4 metric contract and
workload plan](coherence_benchmark_v4_plan.md) and [measured v4
results](coherence_benchmark_v4_results_2026-10-29.md).

Reproduce the suite with:

```bash
make coherence_benchmark_v4
```

This target validates all workload rows and regenerates
`benchmarks/results/coherence_benchmark_v4.json` and `.csv`.

## Benchmark v3

Benchmark v3 measures the Python/Toffee `CoherentCacheSubsystem` and the
independent AXI-integrated `CoherentCacheAxiSubsystem` testbench. It keeps the
v2 workloads, adds 32 separately checked L2-hit samples, five seeded mixed
dual-core workloads, and five seeded AXI-top runs. JSON and CSV are checked in
under `benchmarks/results/`; baseline and optimized measurements are retained
as separate files for the L2-grant A/B comparison.

## Reproduce

```bash
make COHERENCE_JOBS=2 coherence_benchmark_v3
make COHERENCE_JOBS=2 coherence_axi_e2e
```

`coherence_benchmark_v3` exports the Picker wrapper and drives the RTL through
the shared Python CPU driver, writable line-memory agent, protocol monitors,
and independent MESI/data scoreboard. `coherence_axi_e2e` separately drives
the full AXI subsystem through its five AXI channels and a writable 64-byte
burst memory model, once for each fixed seed. Both suites use a 10 ns
simulation clock. Memory response latency is a controllable model parameter,
not a claim about physical DRAM.

`make coherence_verify` includes the Python benchmark and the AXI top-level
simulation in the full regression. The direct 4-outstanding AXI adapter stress
is a separate test: the integrated dual-L1 CPU workload currently peaks at two
simultaneous read bursts because each L1 controller is blocking.

## Workloads and checks

- 64 warm L1 reads.
- 32 L2 hits after the target line has been evicted from L1 by four
  same-index lines. Each sample checks returned data and verifies zero backing
  memory reads. Samples span 2, 20, 50, and 100 cycle memory response settings.
- Sixteen serialized cold misses versus sixteen cold misses issued as eight
  dual-core pairs, at each memory delay.
- Alternating stores to an M-owned line.
- A dirty inclusive L2 victim that exercises snoops, dirty data recovery, and
  backing-memory write response.
- Five fixed-seed mixed workloads, each containing 48 randomized single-lane
  and dual-core paired reads/writes plus readback of all eight target lines.
  Each seed has a separate architectural scoreboard and address range.
- Five AXI top-level runs, each with 64 CPU requests, a seeded mixed read/write
  workload, burst/accounting checks, forced and periodic AR/AW/W backpressure,
  and an independent writable AXI RAM model. The direct adapter suite checks
  four outstanding IDs and all five channel backpressure paths.

## Metrics

- L1 hit/miss is classified at accepted CPU requests; a store from S is an
  upgrade miss. L2 hit/miss counts accepted Directory refill lookups, rather
  than all metadata probes.
- Mean and nearest-rank P95 CPU latency run from request acceptance to response
  capture. `ops_per_cycle` counts completed operations in the measured window.
- Read, write, and aggregate memory bandwidth count accepted 64-bit data beats
  as eight bytes each and divide by measured simulation cycles. Python reports
  bytes/cycle and MiB/s at 100 MHz; AXI reports bytes/cycle.
- The Python phase counters pair observed same-line Directory/L2/memory
  milestones. The L2 tag lookup is combinational; the L2 hit latency is
  measured end-to-end at the CPU request/response boundary.
- The AXI top-level row includes seed, simulation cycles, operation count,
  mean/P95 latency, operations/cycle, read/write beats, read/write/aggregate
  bandwidth, peak outstanding reads, and AR/AW/W/R/B stall counts.

The detailed v3 results, A/B method, and interpretation are in
[`coherence_benchmark_v3_results_2026-10-25.md`](coherence_benchmark_v3_results_2026-10-25.md).
The historical v2 snapshot remains available in
[`archive/benchmarks/coherence_benchmark_v2_results_2026-10-25.md`](archive/benchmarks/coherence_benchmark_v2_results_2026-10-25.md).
