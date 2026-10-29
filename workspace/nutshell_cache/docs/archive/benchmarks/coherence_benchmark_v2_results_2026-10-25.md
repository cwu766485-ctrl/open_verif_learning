# Coherence Benchmark v2 Results (2026-10-25)

> **Historical snapshot.** Benchmark v3 is the current result. See the
> [method and reproduction guide](../../coherence_benchmark.md) and
> [v3 results](../../coherence_benchmark_v3_results_2026-10-25.md).

Run with `make coherence_python_verify` against the Picker/Verilator
`CoherentCacheSubsystem` wrapper. The five main workloads ran with memory
response delays of 2, 20, 50, and 100 cycles; an isolated dirty L2 victim
writeback ran at 100 cycles (fixed seed 0, 10 ns clock). Detailed
per-row counters are in
[`coherence_benchmark_v2.json`](../../../benchmarks/results/coherence_benchmark_v2.json)
and CSV form.

The latest rerun also records per-phase transaction counts, mean, and P95 in
the schema-v3 JSON/CSV. This is monitor-based RTL-cycle attribution; an empty
phase means that workload did not exercise that stage.

## Per-level cache behavior

| Workload | L1 result | L2 refill result | Other |
| --- | --- | --- | --- |
| Warm L1 reads | 64/64 hits (100%) | no refill lookup | 2 cycles/request; 0.250 ops/cycle |
| L2 hit after L1 replacement | 1 miss (0% hit) | 1 hit (100%) | 0 memory reads; response latency 23 cycles |
| Serialized cold misses | 16 misses (0% hit) | 16 misses (0% hit) | 16 memory line reads |
| Paired dual-L1 cold misses | 16 misses (0% hit) | 16 misses (0% hit) | 16 memory line reads; paired requests overlap |
| Ownership write ping-pong | 1 hit, 15 misses (6.25% hit) | no refill lookup | 15 snoops |
| Dirty L2 victim writeback | 1 miss (0% hit) | 1 miss (0% hit) | 1 snoop, 1 dirty writeback, 64B read + 64B write |

The denominator is the accepted CPU requests for L1 and accepted Directory
refill lookups for L2. “No refill lookup” is reported as N/A in the machine
results, not as a zero hit rate.

## Cold-miss throughput and memory bandwidth

Bandwidth includes accepted read and write data beats at the line-memory
interface. These cold-read workloads issue reads only, so read and total
bandwidth match and write bandwidth is zero.

| Memory delay | Serialized cycles | Paired cycles | Paired speedup | Paired mean / P95 latency | Paired ops/cycle | Paired BW (B/cycle) | Paired BW (MiB/s at 100 MHz) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 608 | 424 | 1.434x | 46.00 / 51 cycles | 0.03774 | 2.4151 | 230.32 |
| 20 | 902 | 563 | 1.602x | 63.38 / 69 cycles | 0.02842 | 1.8188 | 173.46 |
| 50 | 1424 | 768 | 1.854x | 89.00 / 94 cycles | 0.02083 | 1.3333 | 127.16 |
| 100 | 2224 | 1168 | 1.904x | 139.00 / 144 cycles | 0.01370 | 0.8767 | 83.61 |

The paired workload lets the two blocking L1 controllers overlap misses to
different lines. It demonstrates two-core overlap, not simultaneous use of all
four Directory contexts or four refill MSHRs.

## Pipeline phase attribution

Observed mean cycles from the schema-v3 run (empty phases are not applicable):

| Workload / memory delay | L1 miss → Directory accept | Directory accept → L2 lookup | L2 hit lookup → grant | L2 miss lookup → memory request | Memory read request → last beat | Memory write request → response |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 hit after L1 replacement / 2 | 8 | 1 | 3 | — | — | — |
| Serialized cold misses / 2 | 2 | 1 | — | 1 | 9 | — |
| Paired cold misses / 2 | 3 | 1 | — | 1 | 14.5 | — |
| Serialized cold misses / 20 | 2.375 | 1 | — | 1 | 27 | — |
| Paired cold misses / 20 | 3.375 | 1 | — | 1 | 31.8125 | — |
| Serialized cold misses / 50 | 5 | 1 | — | 1 | 57 | — |
| Paired cold misses / 50 | 6 | 1 | — | 1 | 57 | — |
| Serialized cold misses / 100 | 5 | 1 | — | 1 | 107 | — |
| Paired cold misses / 100 | 6 | 1 | — | 1 | 107 | — |
| Dirty L2 victim / 100 | 2 | 1 | — | 126 | 107 | 108 |

Directory-to-L2 measures the accepted refill request to the refill lookup
boundary; it does not imply a one-cycle physical SRAM access. The dirty-victim
L2-miss-to-memory interval includes victim back-invalidation and writeback
work, so it is not directly comparable to a cold refill.

The dirty-victim workload runs last to keep its intentional backing-memory
write and resident dirty state from changing the initial conditions of the
read-throughput measurements. At 100-cycle memory response delay, the measured
victim transaction took 259 cycles, moved 64B in and 64B out, and achieved
0.2452 B/cycle each of read and write traffic (0.4904 B/cycle aggregate,
46.77 MiB/s at 100 MHz). The write channel alone measured 23.39 MiB/s.

## Measured RTL change

The previous warm-read baseline was 3 cycles/request and 0.200 op/cycle. A hit
or cold miss with a free way now skips the replacement-check state and enters a
registered replay; requests with a live victim retain the eviction FSM. The
rerun measured 2 cycles/request and 0.250 op/cycle: 33.3% lower request
latency and 25% higher measured warm-read throughput, without reintroducing a
combinational request-ready loop.

Python/Toffee and the full coherence verification passed on the final RTL.
Formal results are bounded proofs; the directory and MSHR properties are not
unbounded proofs of the entire cache subsystem.
