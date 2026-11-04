# DE/DV Next-Phase Baseline

- Repository: `cwu766485-ctrl/open_verif_learning`
- Project: `workspace/nutshell_cache`
- Work branch: `verify/gap-closure`, based on `cache_coherence`
- Local baseline HEAD: `f16b7f14d7478c9148f0e0632e1183f9d71df50f`
- `origin/cache_coherence` at baseline: same SHA; no remote divergence.
- Known GitHub Actions baseline: run `41677618348`, success, at
  `https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/41677618348`.
- RTL manifest: `rtl/Coherence.files.f`, SHA-256
  `06af9024a62bc60b30f2bf33550d1c3d9e0362f231377d964e6a9ce64bfcc667`.
- Toolchain: Verilator `5.053 devel (v5.052-521-g6388139f7)`, Python `3.12.3`,
  pytest `9.1.1`.
- Product RTL changes in this phase: none intended; this phase changes only DV,
  coverage plans, build integration, and reports.

## Starting evidence

At `f16b7f14`, the required local coherence/full-system/H-u-M/stress/coverage
targets had passed in the prior run record. The full-system checked Required
slice was 47/47 feature bins and 23/23 cross bins before adding recovery bins.
The four-agent stress report included 100×500 CPU operations, 100×500 mixed
CPU/MMIO/APB/AXI rounds, and 20 resource-aware seeds.

The raw RTL audit was not a sign-off: the full subsystem dataset recorded 843 /
998 executable lines, 461 / 556 branches, 19,980 / 27,474 toggle points, 30 / 54
FSM states, and 7 / 48 FSM arcs. These are dataset-specific counts, not
combined with other tops. The point-level reviewed/eligible denominator was
not closed, and no waiver was approved.

The prior local Actions-style workflow record is not a substitute for the
current candidate's remote CI. This phase records the new commit and CI status
separately after push.
