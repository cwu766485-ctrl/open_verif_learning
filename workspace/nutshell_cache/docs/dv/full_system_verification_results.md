# Python/Toffee Full-System Verification Results

**Current execution record:** [`closure_phase2_execution_2026-11-06.md`](closure_phase2_execution_2026-11-06.md). This report is the canonical source for the current SHA, six local regression results, coverage scope, CR01–CR10 status, and final OPEN decision.

## Current snapshot

- Tested RTL/DV source SHA: `14542f52bef5a42560cc615a5db104e3122dbd33`.
- All six Phase 2 regression gates passed locally; full-system stress passed 260/260 seeded environments.
- Integrated functional/cross closure: 53/53 required bins and 29/29 required crosses. The separate Python coherence closure is 49/49 and 19/19.
- CR01 and CR07 have checked system-level overlap evidence. CR02–CR06 and CR08–CR10 remain OPEN.
- Primary raw RTL coverage and all dataset-specific gaps are detailed in `reports/final/rtl_coverage_signoff.md` and `reports/final/coverage_closure_matrix.csv`. No waivers are approved and reviewed/eligible coverage is not computed.
- The remote Actions run on base SHA `9b281f3` passed, but it is not CI for the local candidate. Candidate CI is pending publication.

## Verification architecture

The Python/Toffee environment targets `CoherentCacheAxiSubsystem` through a verification-only wrapper. It coordinates dual CPU lanes, AXI4 backing memory, MMIO and APB agents; observes internal protocol events passively; checks data and coherence with independent models; records checked functional/cross coverage; and supports seeded traffic and JSONL replay. This is a Python UVM-style organization, not SystemVerilog UVM. Product RTL behavior and interfaces were not changed in this DV closure phase.

## Reproduction

Run from `workspace/nutshell_cache`:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_full_system_verify
make COHERENCE_JOBS=2 coherence_hit_under_miss
make COHERENCE_JOBS=2 coherence_full_system_cross_closure
make COHERENCE_JOBS=2 coherence_full_system_stress
make COHERENCE_JOBS=2 coherence_coverage_audit
```

The regression result is not a full sign-off. Integrated four-CPU-miss traffic, receiver-side AXI R/B backpressure, APB wait states, arbitrary CPU response ordering, and MMIO error responses are outside current interface support. PPA, STA, physical SRAM macros, chip integration, and unbounded system formal proof are excluded.
