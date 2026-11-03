# Final RTL Coverage Closure — Baseline Freeze

**Snapshot date:** 2026-10-31 (Asia/Singapore)  
**Working branch:** `cache_coherence`  
**Baseline commit:** `08030fd364e4a94a5099d5cd2e71926f2af592a8`  
**Remote base:** `8f10574643b5e81eae5f1a5651eb6266d61a290c`

## Git state and preservation

The working tree was clean at the start of this closure task. The local branch is three commits ahead of `origin/cache_coherence`; those commits are preserved and are not rebased, reset, or force-pushed. They are:

| Commit | Purpose |
| --- | --- |
| `f73d92c` | Add DMB and SharedLineEngine directed block coverage |
| `a7c0264` | Add raw coverage inventory and source-linked gap matrix |
| `08030fd` | Record current functional RTL/DV signoff boundary |

The remote branch still points at `8f105746`. A direct push attempt failed because this shell has no GitHub credentials. Thus the baseline and all results here are local until a normal authenticated push and remote Actions run succeed. No history was rewritten.

## Scope and toolchain

The Product RTL manifest is `rtl/Coherence.files.f`: **18 source files**. The frozen source tree and raw run products are those at the baseline commit. The full locally available EDA/DV environment, after `source scripts/env.sh`, reports:

- `rtl/Coherence.files.f` SHA-256: `06af9024a62bc60b30f2bf33550d1c3d9e0362f231377d964e6a9ce64bfcc667`
- DV inventory at baseline: 45 Python test files and SV block benches under `tests/` and `dv/blocks/`; 16 `.sby` task files are present, of which 7 are invoked by `coherence_formal`.

| Tool | Version |
| --- | --- |
| Verilator | 5.053 devel, `v5.052-521-g6388139f7` |
| Python | 3.12.3 |
| pytest | 9.1.1 |
| SymbiYosys | 0.70 |
| Yosys | 0.70+186, `3718f7f13` |
| GNU Make | 4.3 |

The system tools outside `scripts/env.sh` are older and are not the baseline toolchain.

## Baseline validation and workload inventory

The exact full-regression invocation completed locally with exit status 0 on 2026-10-31:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
```

The target includes standalone L1 array/controller, L2 array, Directory, Directory MSHR, SharedLineEngine, coherence arbiters and cluster tests; bus-block tests; AXI lint, five AXI E2E seeds and R/B/RB backpressure; seven configured SBY tasks; integrated subsystem regression; Python/Toffee functional and AXI adapter tests; standard and dense-set stress; RTL mutation; and Benchmark v4.

| Baseline item | Result / exact scope |
| --- | --- |
| Python functional bins | 49/49 PASS |
| Python required cross bins | 19/19 PASS |
| Integrated SV structured bins | 38/38 PASS |
| Formal | 7 configured tasks PASS |
| AXI E2E | 5 fixed seeds; 64 operations per seed |
| AXI response backpressure | R, B, and combined R/B stall modes PASS |
| Standard random stress | 20 seeds × 200 operations = 4,000 operations |
| Dense L2 set stress | 20 seeds × 200 operations = 4,000 operations |
| RTL mutation | 4/4 selected mutations detected; targeted scope only |
| Checker fault injection | 9/9 checker-level injected faults caught; not exhaustive DUT error-path injection |
| Benchmark v4 | 24 workload rows validated |

## Frozen raw coverage

Primary subsystem LCOV is independently reconciled in `reports/coherence/coverage.info`:

| Category | Hit | Total | Miss |
| --- | ---: | ---: | ---: |
| Product RTL executable lines | 858 | 1,006 | 148 |
| Testbench executable lines | 738 | 748 | 10 |
| Generated/Other | 0 | 0 | 0 |
| Total | 1,596 | 1,754 | 158 |

Primary Product RTL native Verilator points are separately reported in `reports/coherence/coverage.dat`:

| Metric | Hit | Total | Miss |
| --- | ---: | ---: | ---: |
| Branch | 450 | 536 | 86 |
| Toggle | 19,916 | 26,978 | 7,062 |
| FSM state | 30 | 54 | 24 |
| FSM arc | 7 | 48 | 41 |

Independent AXI and block coverage datasets are listed in `reports/coherence/coverage_closure_raw_runs.md`. Their raw denominators are not added. Python/Toffee functional evidence is kept distinct from Verilator source coverage.

## Known baseline limitation

The prior source-linked matrix records 299 zero-count primary-subsystem observations (148 lines, 86 branches, 24 FSM states, 41 FSM arcs). It labels 85 points as falling within manually reviewed source ranges and 214 as source-mapped only; all are still open in that matrix. The waiver inventory is empty. Therefore this is a frozen **passing regression baseline**, not a completed RTL code coverage sign-off.

## Reproduction and source identity

```bash
cd workspace/nutshell_cache
source scripts/env.sh
git rev-parse HEAD
sha256sum rtl/Coherence.files.f
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_coverage_audit
```

The manifest path and complete SHA are recorded by the closure run; raw coverage files are snapshots from the baseline commit and must be regenerated after source, stimulus, or toolchain changes.
