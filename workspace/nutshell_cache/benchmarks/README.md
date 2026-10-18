# NutShell L1 DCache baseline

Run from `workspace/nutshell_cache` in WSL:

```bash
make benchmark
```

The test uses the maintained cache RTL through the same Verilator/Toffee
environment as the regression. It writes machine-readable results to
`benchmarks/results/dcache_baseline.json`.

## Current result

Measured 2026-10-18 on the local WSL2 x86-64 host, with a 32 KiB, 4-way,
64-byte-line DCache (128 sets):

| Read pattern | Accesses | Hits | Misses | Hit rate | RTL cycles/access |
|---|---:|---:|---:|---:|---:|
| One hot line, 64 reads | 64 | 63 | 1 | 98.4375% | 4.125 |
| 256 lines / 16 KiB, two passes | 512 | 256 | 256 | 50% | 8.000 |
| Five lines mapping to one 4-way set, five sweeps | 25 | 12 | 13 | 48% | 8.160 |

The working-set test begins cold, so its first pass misses and the second pass
hits. The conflict test deliberately exceeds the four ways available in one
set. This makes the counters useful for checking that the hit/miss monitor
sees both reuse and conflict behavior.

## CPU IPC smoke baseline

The full NutShell `inorder` CPU simulator also ran the prebuilt
`ready-to-run/microbench.bin` image to a successful trap. All ten workload
checks passed. DiffTest reported 783,387 retired instructions and 1,512,377
cycles, for **0.517984 IPC**. The captured result is in
`benchmarks/results/cpu_microbench_baseline.json`.

This is a first CPU-level smoke baseline, not a CoreMark result. Its counters
cover reset through the image's good trap, including startup and test harness
work. The run disabled reference-model comparison (`--no-diff`) while keeping
the simulator's trap counters enabled. The CPU simulator build needed a local
Verilator 5.020 waveform-header compatibility shim; no waveform was enabled.

## CoreMark workload baseline

I also built the EEMBC 2K performance workload from the OpenXiangShan
`nexus-am` tree for `riscv64-nutshell`, then ran 100 iterations on the same
`inorder` RTL. It reached a good trap with the expected performance seed and
algorithm CRCs (`e9f5`, `e714`, `1fd7`, `8e3a`). The timed region measured 6,844
CLINT microseconds. NutShell's simulation CLINT advances one microsecond per
10,000 RTL cycles, giving an estimated **1.461133 iterations per million
cycles** for the benchmark region. The CPU reported 0.524310 IPC across the
whole image through the good trap. Details are in
`benchmarks/results/coremark_baseline.json`.

A separate 10-iteration 2K validation-seed run also reached a good trap with
the expected CRCs (`18f2`, `e3c1`, `0747`, `8d84`).

This is a cycle-normalized RTL baseline, not an EEMBC-reportable score. The
100-iteration run is shorter than CoreMark's 10-second minimum, and the port's
built-in floating-point score formatter is unsupported by the bare-metal
printf. The formula-derived per-million-cycle value is retained because it is
useful for comparing revisions under this exact simulation timing model.

## Measurement definition

- An access is one accepted CPU demand read at the cache's Stage2-to-Stage3
  handshake. The counter excludes MMIO and coherence traffic.
- Hit rate is `hits / accepted_reads`; miss rate is `misses / accepted_reads`.
- RTL cycles are sampled rising edges from the first request through the last
  response. Reset and its cache-clear sweep are excluded. Cycles/access is a
  transaction-latency metric for this serial request trace, not CPU IPC.
- The host and UTC run time are stored with each result. RTL cycles are
  independent of host wall-clock speed, but the memory responder and testbench
  configuration still form part of this setup.

## How to present this in an interview

> I found that the cache project had no repeatable performance baseline, so I
> added a small cycle-based benchmark on the maintained RTL. I measured demand
> access events at the cache handshake and checked three patterns: a hot line,
> a working set that fits, and a set-conflict pattern beyond associativity. The
> run records hit/miss rates and RTL cycles per serialized access as JSON. I
> also captured a full-core smoke IPC of 0.518 and ran the CoreMark 2K
> performance and validation seeds to matching CRCs. The CoreMark result is
> only a cycle-normalized RTL baseline because this run did not meet EEMBC's
> 10-second timing rule. I do not present simulator cycles as silicon Fmax.

This gives a concrete discussion of workload design, measurement boundaries,
cache geometry, reproducibility, and what the result does and does not claim.
For a stronger CPU-level performance story, rerun the CoreMark performance
workload long enough to meet EEMBC's timing rule, fix the bare-metal score
formatter, and run the separate validation seeds. A physical maximum clock
frequency still needs a target FPGA board or an ASIC synthesis/place-and-route
timing flow with stated constraints; a Verilator cycle count cannot establish
Fmax.
