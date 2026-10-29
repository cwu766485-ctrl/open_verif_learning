# Dual-L1 MESI Cache Benchmark v4 Plan

## Scope

Benchmark v4 measures the Cache subsystem through two LSU agents and the
Python/Toffee DUT wrapper. It does not model retired CPU instructions, so IPC,
CPI, MPKI, CoreMark, and application-level performance are out of scope. The
results are RTL simulation cycles and modeled memory traffic, not silicon
frequency, physical DRAM bandwidth, area, power, or PPA.

The DUT uses two private 32 KiB, four-way L1 caches and an inclusive 256 KiB,
eight-way shared L2/Directory. Refill MSHRs and Directory contexts are counted
as distinct resources. L1 controllers remain blocking, and the L2 fill and
coherence data paths have shared resources; reported concurrency is the
measured behavior of this RTL and agent pair.

## Metric contract

- **L1 hit/miss:** one event for each accepted cached CPU request, classified
  from the RTL L1 event pins. Read and write events are reported separately.
  An S-to-M permission upgrade is an L1 write miss but is also broken out as a
  permission upgrade; it is not counted as a data miss.
- **L2 refill hit/miss:** accepted Directory refill lookup events. These are
  not all tag probes and are not a ratio over all CPU operations.
- **Latency / AMAT:** the shared CPU Driver records request acceptance and
  response capture. Mean, nearest-rank P95/P99, read/write means, and hit/miss
  means are calculated over completed operations in that workload window.
  Miss penalty is mean L1-miss latency minus mean L1-hit latency when both
  classes occur.
- **Throughput:** completed CPU operations divided by cycles elapsed in the
  measured workload window; reported per core and aggregate. It includes
  protocol and memory wait cycles. It is not an instruction throughput or
  unconstrained peak issue rate.
- **Parallel speedup:** for B06, cycles for the same 16 cold lines on one
  blocking core divided by cycles for eight paired dual-core requests, at the
  same modeled memory response delay.
- **Memory bandwidth:** accepted 64-bit backing-memory beats × 8 bytes divided
  by measured simulation cycles, reported as read, write, and aggregate
  bytes/cycle. MiB/s is meaningful only after choosing an assumed clock.
- **Traffic amplification:** backing-memory read/write bytes divided by
  logical CPU bytes (8 bytes per read and the asserted byte-mask population
  for writes). It is reported only as a model-relative ratio.
- **MSHR / Directory occupancy:** cycle-sampled population counts of the
  exported valid bits, with mean, peak, histogram, and full cycles. Refill
  MSHRs and Directory contexts are not combined.
- **Stalls:** CPU request/response waits use the shared Python Driver's
  handshake observations. Memory, Directory, transfer, and snoop channel
  stalls use their valid/ready observations. Different channels may stall in
  the same cycle, so category totals can overlap.
- **Fairness:** Jain index over the two per-core completion counts. A single
  active core therefore reports 0.5; interpret it only for dual-core cases.

Each run starts from a stated cache state. Setup traffic is excluded from the
workload window, while the cache and backing-memory contents resulting from
setup are explicitly described in each result row. Seeds, response delay,
operation counts, and measured cycles are retained in JSON and CSV.

## Workloads

| ID | Workload | Setup and measured traffic | Primary question |
| --- | --- | --- | --- |
| B01 | Warm L1 | Repeated reads to a line preloaded in Core 0; 128 measured reads | L1 hit rate and hit latency |
| B02 | Sequential scan | Cold 16 KiB read scan with 8-byte stride | Compulsory line misses and spatial reuse |
| B03 | Working-set sweep | 4, 16, 32, 64, 256, and 512 KiB; populate, then repeat a full line-stride pass | L1/L2 capacity behavior and miss penalty |
| B04 | Set conflict | Five lines mapping to one L1 set; then nine dirty lines mapping to one L2 set | Conflict replacement and dirty live-victim recovery |
| B05 | Mixed read/write | 256 seeded operations each at 100:0, 80:20, and 50:50; final data readback | AMAT, hit/miss, write traffic, and backpressure |
| B06 | Parallel cold miss | Eight dual-core request pairs and a 16-request single-core serial baseline at 2, 20, 50, and 100-cycle memory delay | Refill overlap, MSHR occupancy, fairness, latency scaling, and parallel speedup |
| B07 | Ownership ping-pong | 64 alternating stores to one line | Snoop and ownership-transfer cost |
| B08 | False sharing | Matched paired stores to different words in one line versus separate lines | Extra coherence traffic and throughput cost |

The workload generator uses fixed seeds and explicit operation counts. Data is
checked against the writable line-memory model and independent architectural
scoreboard where applicable. A row is rejected if the Driver's completed
request count differs from the requested count, if L1 event accounting does
not reconcile, or if workload-specific coherence/data checks fail.

## Reproduce and outputs

```bash
source scripts/env.sh
make coherence_benchmark_v4
```

The command exports/builds the Picker/Verilator wrapper if needed, runs the
directed B01–B08 workloads, validates the emitted rows, and writes:

- `reports/coherence/benchmark_v4.log`
- `reports/coherence/benchmark_v4.junit.xml`
- `benchmarks/results/coherence_benchmark_v4.json`
- `benchmarks/results/coherence_benchmark_v4.csv`

The JSON includes the metric definitions, environment boundary, workload
metadata, and all rows. The CSV contains one row per case; nested histograms
and stall breakdowns are JSON-encoded cells. This is a Cache-only microbenchmark
and is not a substitute for a real CPU-integrated application benchmark.
