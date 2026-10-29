# Dual-L1 MESI Cache Benchmark v4 Results

## Run summary

The Benchmark v4 directed suite completed on 2026-10-29 with 24 workload rows
and 100% operation completion. The Picker/Verilator + Python/Toffee test passed
(1 test, 308.88 seconds); the result collector validated all 24 rows and
generated the checked-in JSON and CSV. The existing v3 Python benchmark also
passed after the shared Driver and monitor changes (1 test, 7.41 seconds).

```bash
source scripts/env.sh
make coherence_benchmark_v4
```

The simulation clock is 10 ns. The CPU side consists of two LSU agents, not a
retiring CPU. All reported latency and throughput values are observed in this
RTL/model setup. They are not CPU IPC/CPI, silicon performance, PPA, or physical
DRAM bandwidth. Memory bandwidth is reported as bytes per simulation cycle;
MiB/s would require an explicitly assumed clock and is intentionally omitted.

## Key observations

- Warm L1 reads completed in 2 cycles with a 100% L1 read hit rate.
- The 4, 16, and 32 KiB working sets remained in L1 after warm-up. At 64 and
  256 KiB, all measured L1 reads missed but all Directory refill lookups hit in
  L2, at 22 cycles. At 512 KiB, both L1 and L2 refill hit rates were 0%, and
  mean latency rose to 42 cycles.
- Nine dirty lines mapped to one L2 set caused one dirty victim writeback and
  one memory write line. The five-line L1 conflict case had an 80% L2 refill
  hit rate.
- The dual-core cold-miss case reached a peak of two simultaneous refill
  MSHRs, versus one for its single-core serial reference. At 2/20/50/100-cycle
  modeled memory delays, total-window speedup was 1.451×/1.594×/1.717×/1.812×.
  This measures two blocking L1s overlapping independent misses; it does not
  demonstrate four CPU misses in flight.
- In the false-sharing A/B, paired stores to different words of one line
  generated 33 snoops and 0.0684 operations/cycle. Stores to separate lines
  generated no snoops and achieved 0.4961 operations/cycle. The operation
  count and setup were matched; this is a simulated protocol-cost comparison.

## Workload results

Rates are fractions of the relevant accepted event class. L2 refill hit rate is
calculated only over accepted Directory refill lookups; `—` means the workload
did not issue such a lookup. Memory bandwidth is aggregate backing-memory bytes
per measured cycle. P95/P99 use nearest-rank samples.

| Workload / case | Ops | Mean / P95 / P99 latency (cycles) | L1 hit rate | L2 refill hit rate | Ops/cycle | Memory B/cycle | Peak refill MSHR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B01 warm L1, Core 0 repeated line | 128 | 2.00 / 2 / 2 | 100.0% | — | 0.2500 | 0.000 | 0 |
| B02 sequential scan, 16 KiB, 8 B stride | 2,048 | 6.12 / 35 / 35 | 87.5% | 0.0% | 0.1231 | 0.985 | 1 |
| B03 working set, 4 KiB | 64 | 2.00 / 2 / 2 | 100.0% | — | 0.2500 | 0.000 | 0 |
| B03 working set, 16 KiB | 256 | 2.00 / 2 / 2 | 100.0% | — | 0.2500 | 0.000 | 0 |
| B03 working set, 32 KiB | 512 | 2.00 / 2 / 2 | 100.0% | — | 0.2500 | 0.000 | 0 |
| B03 working set, 64 KiB | 1,024 | 22.00 / 22 / 22 | 0.0% | 100.0% | 0.0417 | 0.000 | 0 |
| B03 working set, 256 KiB | 4,096 | 22.00 / 22 / 22 | 0.0% | 100.0% | 0.0417 | 0.000 | 0 |
| B03 working set, 512 KiB | 8,192 | 42.00 / 42 / 42 | 0.0% | 0.0% | 0.0227 | 1.455 | 1 |
| B04 L1 same-set, five lines | 5 | 25.80 / 41 / 41 | 0.0% | 80.0% | 0.0360 | 0.460 | 1 |
| B04 L2 same-set, nine dirty lines | 1 | 66.00 / 66 / 66 | 0.0% | 0.0% | 0.0147 | 1.882 | 1 |
| B05 mixed, 100R:0W | 256 | 8.94 / 35 / 35 | 75.8% | 0.0% | 0.0914 | 0.731 | 1 |
| B05 mixed, 80R:20W | 256 | 11.40 / 35 / 35 | 59.0% | 0.0% | 0.0746 | 0.597 | 1 |
| B05 mixed, 50R:50W | 256 | 14.89 / 38 / 38 | 44.5% | 0.0% | 0.0592 | 0.474 | 1 |
| B07 ownership ping-pong, 64 alternating stores | 64 | 25.62 / 26 / 26 | 1.6% | — | 0.0362 | 0.000 | 0 |
| B08 same line, different words | 64 | 14.73 / 27 / 35 | 48.4% | — | 0.0684 | 0.000 | 0 |
| B08 different lines | 64 | 2.03 / 2 / 3 | 100.0% | — | 0.4961 | 0.000 | 0 |

### B06: serialized versus parallel cold misses

Each row transfers the same 16 cold cache lines. The serial workload sends 16
requests from one blocking L1. The parallel workload sends eight pairs, one
request from each core per pair. Speedup is serial measured-window cycles
divided by parallel measured-window cycles.

| Memory response delay | Serial window cycles | Parallel window cycles | Speedup | Serial / parallel peak MSHR | Serial / parallel ops/cycle |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 cycles | 592 | 408 | 1.451× | 1 / 2 | 0.0270 / 0.0392 |
| 20 cycles | 880 | 552 | 1.594× | 1 / 2 | 0.0182 / 0.0290 |
| 50 cycles | 1,360 | 792 | 1.717× | 1 / 2 | 0.0118 / 0.0202 |
| 100 cycles | 2,160 | 1,192 | 1.812× | 1 / 2 | 0.0074 / 0.0134 |

These cycle totals include protocol and modeled memory waits. They describe
this blocking-L1 subsystem and workload pair; they are not a prediction of CPU
application speedup.

### Read/write detail for B05

| Read:write mix | Read hit rate / mean read latency | Write hit rate / mean write latency | Permission upgrades | Dirty writebacks |
| --- | ---: | ---: | ---: | ---: |
| 100:0 | 75.8% / 8.94 cycles | — | 0 | 0 |
| 80:20 | 67.5% / 10.81 cycles | 24.0% / 13.84 cycles | 11 | 0 |
| 50:50 | 57.3% / 13.82 cycles | 31.2% / 16.02 cycles | 18 | 0 |

Write hit rate excludes permission-upgrade misses; the aggregate L1 hit rate in
the table above uses all accepted requests. Detailed stall, occupancy, memory
read/write, and per-core metrics are in the machine-readable output.

## Reproducibility and artifacts

- [`coherence_benchmark_v4.json`](../benchmarks/results/coherence_benchmark_v4.json)
- [`coherence_benchmark_v4.csv`](../benchmarks/results/coherence_benchmark_v4.csv)
- Run log: `reports/coherence/benchmark_v4.log` (local generated artifact)
- JUnit: `reports/coherence/benchmark_v4.junit.xml` (local generated artifact)
- Method and metric definitions: [`coherence_benchmark_v4_plan.md`](coherence_benchmark_v4_plan.md)

Workloads use fixed seeds, explicit initial Cache states, and the writable
64-byte backing-memory model. Python transactions are checked against the
independent data/coherence model and the RTL event accounting. Results are
simulation evidence only; CPU instruction retirement, real DRAM behavior,
physical frequency, area/power, and PPA are outside this benchmark's scope.
