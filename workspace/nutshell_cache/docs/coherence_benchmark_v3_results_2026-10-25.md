# Coherence Benchmark v3 Results — 2026-10-25

## Reproduction and artifacts

Run `make COHERENCE_JOBS=2 coherence_benchmark_v3` and
`make COHERENCE_JOBS=2 coherence_axi_e2e`. The first target runs the full
Python/Toffee cache benchmark; the second rebuilds the AXI-integrated top and
runs its writable burst memory model with five fixed seeds. Both targets are
also part of `make coherence_verify`.

Python JSON/CSV:

- Final RTL: [`coherence_benchmark_v3.json`](../benchmarks/results/coherence_benchmark_v3.json), [`coherence_benchmark_v3.csv`](../benchmarks/results/coherence_benchmark_v3.csv)
- Pre-optimization baseline: [`coherence_benchmark_v3_baseline.json`](../benchmarks/results/coherence_benchmark_v3_baseline.json), [`coherence_benchmark_v3_baseline.csv`](../benchmarks/results/coherence_benchmark_v3_baseline.csv)

AXI top JSON/CSV:

- Final RTL: [`axi_top_benchmark_v3.json`](../benchmarks/results/axi_top_benchmark_v3.json), [`axi_top_benchmark_v3.csv`](../benchmarks/results/axi_top_benchmark_v3.csv)
- Pre-optimization baseline: [`axi_top_benchmark_v3_baseline.json`](../benchmarks/results/axi_top_benchmark_v3_baseline.json), [`axi_top_benchmark_v3_baseline.csv`](../benchmarks/results/axi_top_benchmark_v3_baseline.csv)

The paired runs use the same five seeds, address patterns, memory model,
response-delay settings, and testbench. Each CPU operation's response latency
is captured from request acceptance to response capture. These are simulation
cycle results at 10 ns per cycle, not physical timing or PPA estimates.

## P3 change and A/B results

The original data Grant path accepted a Directory Grant, spent one cycle in
`ENGINE_GRANT_READ`, then issued the shared-L2 line read before streaming the
eight data beats. The optimized path issues that L2 read in the same cycle as
the accepted data Grant and enters the stream state once the array accepts the
read. If the array is not ready, the existing `ENGINE_GRANT_READ` retry path
remains active. A protocol assertion checks that every accepted data Grant
prefetches the matching cache line.

| Workload | Baseline | Optimized | Change |
| --- | ---: | ---: | ---: |
| L2 hit after L1 replacement, 32 samples: mean / P95 | 23 / 23 cycles | 22 / 22 cycles | 1 cycle lower (4.35%) |
| L2-hit operations/cycle | 0.04000 | 0.04167 | 4.17% higher |
| Serialized cold miss, 2-cycle memory: 16 ops | 608 cycles | 592 cycles | 16 cycles lower |
| Paired cold misses, 2-cycle memory: 16 ops | 424 cycles | 408 cycles | 16 cycles lower |
| Dirty L2 victim writeback, 100-cycle memory: response latency | 259 cycles | 258 cycles | 1 cycle lower |
| Warm L1 read latency | 2 cycles | 2 cycles | unchanged |

All 32 L2-hit samples were classified as L1 misses and L2 refill hits, returned
the expected data, and caused zero backing-memory reads. Their memory-response
delay setting does not affect the L2 hit path. The observed
`L2 lookup→Grant acceptance` phase remains three cycles because the optimized
cycle is after that event: the line read now overlaps Grant acceptance. The
CPU request-to-response measurement confirms the end-to-end one-cycle gain.

Across the five 56-operation seeded Python mixed workloads, average response
latency moved from 17.54 to 17.14 cycles; mean throughput moved from 0.04865
to 0.04972 ops/cycle. Aggregate memory traffic moved from 0.4557 to 0.4658
bytes/cycle. Those mixed-workload results are supplementary; the isolated
32-sample L2-hit test is the direct measurement of the chosen optimization.

## AXI-integrated top results

Each of five seeds completed 64 CPU operations. The independent writable RAM
checked 64-byte INCR bursts, IDs, beat counts, write responses, read data, and
architectural readback. All runs observed two concurrent read bursts and
nonzero AR, AW, and W stalls. The full cache top does not naturally stall R
or B responses in this workload; the separate four-outstanding AXI adapter
test exercises backpressure on all five AXI channels.

| Metric, mean across five seeds | Baseline | Optimized |
| --- | ---: | ---: |
| CPU response latency | 29.91 cycles | 29.21 cycles |
| Operations/cycle | 0.03309 | 0.03383 |
| Aggregate memory bandwidth | 0.7377 B/cycle | 0.7541 B/cycle |
| Per-seed P95 latency range | 81–93 cycles | 85–92 cycles |
| Peak outstanding reads | 2 | 2 |

The per-seed P95 range is not uniformly lower, despite the mean latency
improving. Randomized traffic and phase-dependent channel readiness make the
tail sensitive to seed scheduling; the top-level experiment supports the mean
trend but is not evidence of a universal P95 improvement.

## Limits and interpretation

- The performance change removes a registered wait cycle in the simulated
  refill-to-L1 data path. It does not show a higher clock frequency, reduced
  area, RAM inference quality, or physical memory bandwidth.
- The two L1 controllers are blocking, so the integrated CPU top peaks at two
  outstanding read bursts. Four-outstanding capacity is verified separately
  at the line-memory AXI adapter.
- The 32 L2-hit samples are spread across four memory-delay settings and five
  fixed seeds. All hits are warm in L2 and deliberately absent from L1.
- Bounded formal remains component/local evidence; this benchmark does not
  establish unbounded whole-system correctness.
