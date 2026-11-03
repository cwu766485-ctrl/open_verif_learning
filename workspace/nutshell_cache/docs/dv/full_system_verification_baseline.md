# Full-System Python/Toffee Verification — Baseline Freeze

Snapshot: 2026-11-01 (Asia/Singapore)
Repository: `cwu766485-ctrl/open_verif_learning`, branch `cache_coherence`
Project: `workspace/nutshell_cache`
Baseline HEAD: `f897109` (`docs: freeze full-system DV baseline`)
Remote relation at freeze: 9 local commits ahead of `origin/cache_coherence`; no remote-only commits or local source edits were present.

This baseline is for the proposed Python/Toffee UVM-style full-system verification work. It is not a product RTL sign-off. The intended system DUT is `rtl/top/CoherentCacheAxiSubsystem.sv`.

## Existing verification components

| Responsibility | Existing source of truth | Baseline capability / boundary |
| --- | --- | --- |
| Dual CPU lanes | `dv/agents/coherent_cpu_agent.py` | One packed-port owner; paired and single blocking CPU accesses, request and response stalls, per-core observed latency. It is not a queueing multi-outstanding CPU agent. |
| CPU sequences | `dv/sequences/coherence_sequences.py`, `dv/sequences/cpu_sequences.py` | Reusable CPU access helpers and dual-lane sequences used by subsystem tests. |
| Coherence memory | `dv/agents/line_memory_axi_agent.py` | Drives the line-oriented memory port of the Python coherence wrapper, with delay/backpressure and snoop-data integration. It is not an AXI five-channel agent. |
| AXI memory | `dv/agents/axi4_memory_agent.py` | Five-channel slave model for the standalone line-to-AXI adapter wrapper; it checks ID routing, interleaved R beats, out-of-order completion, burst shape, stalls, errors, reset and ID reuse. Its data pattern/model is adapter-test oriented. |
| MMIO | `dv/agents/mmio_agent.py`, `dv/models/mmio_register_model.py` | Existing SimpleBus-style role/model utilities; no unified full-system MMIO request/response agent bound to the top-level MMIO interface. |
| Environment | `dv/env/coherence_env.py`, `tests/coherence/conftest.py` | Owns the packed CPU driver, line-memory driver, perf and snoop-data monitors, and fresh scoreboard factory for `CoherentCacheSubsystem`. |
| Reference model / scoreboard | `dv/scoreboard/coherence_scoreboard.py`, `dv/models/cache_reference_model.py`, `dv/models/backing_memory_model.py` | Independent CPU-visible data/MESI/Directory model and replacement bookkeeping for the current Python subsystem regression. |
| Protocol and transaction checkers | `dv/checkers/`, `dv/monitors/snoop_data_monitor.py` | Ready/valid, cache protocol, transaction lifecycle and snoop/data/Directory checks for existing wrappers and tests. |
| Performance monitor | `dv/monitors/cache_perf_monitor.py` | Samples current subsystem performance and protocol-stage taps. |
| Functional coverage | `dv/coverage/coherence_coverage.py`, `dv/coverage/python_closure.py`, `dv/coverage/coherence_map.json`, `dv/coverage/python_coherence_map.json` | Existing checked functional/cross closure; the latest recorded required results are 49/49 functional and 19/19 cross. This is not yet full-system four-agent coverage. |
| Fault injection / mutation / formal | `dv/fault_injection/`, `dv/mutation_testing/`, `formal/` | Existing checker-level fault injection, selected RTL mutations, and bounded/component SymbiYosys jobs. |

## Existing test inventory and DUT tops

| Entry point | DUT top / wrapper | Main scope |
| --- | --- | --- |
| `make coherence_verify` | Multiple SV block tops, `CoherentCacheSubsystem`, `CoherentCacheAxiSubsystem`, Python wrappers | Existing block, bus, AXI E2E/backpressure, formal, integrated SV, Python/Toffee, stress, mutation and benchmark suites. |
| `tests/coherence/*` via `make coherence_python_verify` | `dv/rtl/CoherentCachePythonWrapper.sv` wrapping `CoherentCacheSubsystem` | MESI data/Directory behavior, owner transfers, replacement, stalls, reset, concurrency, fault checks and functional coverage. Backing memory attaches to line-level memory pins; this is not the AXI-integrated top. |
| `tests/axi/test_axi4_adapter_python.py` via `make coherence_axi_python_test` | `dv/rtl/LineMemoryAxi4PythonWrapper.sv` wrapping `LineMemoryAxi4Adapter` | Five-channel AXI adapter: four outstanding IDs, interleaving/order, R/B errors, reset and stalls. It does not include the cache subsystem. |
| `rtl/coherence/tb/CoherentCacheAxiSubsystem_tb.sv` through `coherence_axi_e2e` | `CoherentCacheAxiSubsystem` | Full RTL AXI integration with fixed-seed end-to-end memory traffic and response/backpressure checks; not Python Agent-based. |
| `dv/blocks/<block>/` and corresponding Make targets | Individual RTL block tops | Directed block interface, protocol, error and coverage checks. |
| `tests/l1/*` | Legacy `CacheTop` Python/Toffee wrapper | Original single-L1 DCache regression; keep separate from MESI L1 tests. |

Current full-system gaps: there is no Python/Toffee wrapper/fixture for the AXI-integrated product top; no unified four-agent `FullSystemEnv`; no APB master or top-bound MMIO slave; no full-top internal passive probe bundle; no full-system independent event-driven coverage plan, trace recorder/replay or coverage-guided scenario scheduler. Existing standalone tests remain useful and are not to be replaced by empty framework scaffolding.

## Frozen coverage and verification evidence

The prior RTL coverage audit at this unchanged RTL baseline records the following primary subsystem raw results; separate AXI and block scopes must remain separate:

| Metric | Hit / total | Miss |
| --- | ---: | ---: |
| Product RTL line | 858 / 1006 | 148 |
| Branch | 450 / 536 | 86 |
| Toggle | 19916 / 26978 | 7062 |
| FSM state | 30 / 54 | 24 |
| FSM arc | 7 / 48 | 41 |
| Python functional bins | 49 / 49 | 0 |
| Python required cross bins | 19 / 19 | 0 |

Raw RTL gaps remain open; the 49/49 and 19/19 functional results are not code coverage. Prior status and detailed scope are in `reports/final/rtl_coverage_signoff.md`, `reports/final/verification_signoff.md`, and `reports/final/coverage_closure_matrix.csv`.

## Baseline regression rerun

Command requested by this plan:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
```

The rerun completed successfully with exit status 0 on the frozen baseline SHA above. The full command reached the final Benchmark v4 pytest target, which reported `1 passed in 167.86s`; the log also records the existing subsystem directed/random suites (20 cases per invocation), AXI Python adapter tests (3 cases), and four mutation checks as passing. Formal and RTL/block regressions were part of the same `coherence_verify` target and the target returned success. The complete local log and machine-readable status are `reports/full_system/baseline_coherence_verify.log` and `reports/full_system/baseline_coherence_verify.status`; generated logs are ignored by Git, while this summary is the durable baseline record.

## Baseline-to-implementation note

The additive integrated Python/Toffee slice was implemented at `9b1d89e`.
Its exact regression results and remaining scope are recorded in
[`full_system_verification_results.md`](full_system_verification_results.md).

## Planned additive files / changes

The plan proposes, subject to interface audit and incremental validation:

- Verification-only packed wrapper and Picker build target for `CoherentCacheAxiSubsystem`; no Product RTL interface changes.
- `dv/env/full_system_env.py`; full-top CPU, AXI memory, MMIO and APB roles reusing the current dual-lane CPU and AXI infrastructure where contracts match.
- Passive full-top probes/monitors, independent system scoreboard extensions, checked functional coverage plan, deterministic scenario generation, JSONL trace/replay, pytest entry points and Make targets.
- Architecture, interface/transaction, scenario, observability and traceability documents plus full-system reports.

Existing `CoherenceEnv`, legacy L1 tests, block benches, formal jobs, coverage Bin IDs and current regression targets remain intact. The full-system environment must only claim tests/features that are actually driven and checked.

## Toolchain snapshot

Pinned/local tool versions recorded by the existing baseline report `reports/closure/baseline.md`: Verilator 5.053 development (`v5.052-521-g6388139f7`), Python 3.12.3, pytest 9.1.1, SymbiYosys 0.70, Yosys 0.70+186, GNU Make 4.3. Reconfirm `make doctor` if the environment changes.
