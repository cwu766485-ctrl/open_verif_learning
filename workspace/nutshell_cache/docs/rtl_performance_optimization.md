# RTL Performance Optimization: P0 Profile and P1 Hit-under-Miss

## Scope

This change implements the first measured RTL optimization after profiling: a
resident L1 read hit can complete while a different read miss is waiting for a
Directory grant. The cache interface and module ports are unchanged. Stores,
misses, active snoops, replacement, and refill phases remain serialized through
the existing controller.

The result is a cycle-level RTL simulation measurement with a synthetic memory
response delay. It is not a CPU IPC result, physical frequency, area, power, or
silicon bandwidth measurement.

## Design change

`DualL1MesiCluster` recognizes a read hit only while the blocking L1 controller
is in `CPU_SEND_REQ` or `CPU_WAIT_GRANT`. It returns the hit from a one-entry
response register, leaving the in-flight miss and its Directory transaction
untouched. The bypass is disabled when a snoop or replacement is active. The
registered response holds address, data, write attribute, and transaction ID
stable until the CPU accepts it. When occupied, it stalls further bypass hits.
The bypass response ID starts immediately after the active miss response ID;
subsequent bypass hits advance the ID sequence, including across wraparound.
The verification wrapper exposes the existing response transaction ID so the
directed test can check this ordering; no product RTL port was added.

This is intentionally a single-response hit-under-miss path. It does not add an
L1 MSHR, merge same-line misses, allow miss-under-miss, or make L1 stores
non-blocking. Those are separate P2/P3 design changes with broader ordering,
snoop, replacement, reset, and verification implications.

## A/B workload and measurement

The directed workload first warms line B, then issues a cold read miss to line
A with an 80-cycle synthetic backing-memory response delay. While A waits, it
issues 24 reads to resident line B. Every returned address and data word is
checked. A second test holds the bypass hit response under CPU backpressure and
checks that its payload stays stable and the original miss response is not
lost.

| Metric | Before P1 | After P1 | Change |
|---|---:|---:|---:|
| Warm hits accepted before A completes | 0 / 24 | 24 / 24 | All 24 overlap |
| Warm hit responses before A completes | 0 / 24 | 24 / 24 | All 24 overlap |
| Window cycles, 25 total reads | 185 | 113 | −72 cycles (−38.9%) |
| Operations per cycle in this window | 0.1351 | 0.2212 | +63.7% |
| Cold miss latency | 113 cycles | 113 cycles | No change |

The throughput number is completed operations divided by the measured window
from accepting the cold miss through completing all 25 operations. The cold
miss latency is unchanged; the improvement comes from completing independent
warm hits during the miss wait. These figures apply only to this workload and
the stated simulation model.

## Regression evidence

- `make COHERENCE_JOBS=2 coherence_cluster`: PASS.
- `make COHERENCE_JOBS=2 coherence_python_verify`: PASS, 38 passed and 1
  benchmark-v4 case deselected by the existing target filter.
- Python Functional Coverage Closure: 49/49 bins hit.
- Checker fault injection: 9/9 injected faults detected.
- Focused P1 tests: benchmark/data check and response-backpressure check pass.
- `make COHERENCE_JOBS=2 coherence_verify`: PASS after the final RTL and wrapper
  changes. This includes the existing block regressions, formal targets,
  Python functional/stress/mutation and AXI suites, and the 24-row Benchmark v4
  regression.

The Verilator/Python wrapper build emits existing toolchain and C++ format
warnings. No new functional failure was observed. Remote GitHub Actions have
not been run for this P1 commit; local regression results are not a claim of
remote CI sign-off.

## Reproduction

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_hit_under_miss
```

The target writes the latest raw result under ignored `reports/` and refreshes
`benchmarks/results/rtl_opt_p1_hit_under_miss_ab.json`. The pre-change baseline
is retained in `benchmarks/results/rtl_opt_p1_hit_under_miss_baseline.json`.

## Next RTL stages

1. P2: evaluate a two-entry L1 MSHR after specifying same-line merge, set
   conflicts, response IDs, refill/snoop ordering, stores, and reset behavior.
2. P3: profile Directory/L2 serialization and remove only measured shared-port
   bottlenecks, preserving the existing same-set interlock and metadata
   atomicity.
3. P4: measure refill/owner-transfer latency separately before changing beat
   ordering or adding critical-word-first behavior.

Each stage needs its own baseline, directed checks, randomized regression, and
same-workload A/B data before being described as a performance improvement.
