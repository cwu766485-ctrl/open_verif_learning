# Four-Agent Full-System Stress Campaign

- Raw source: `reports/full_system/full_system_coverage.json` (schema 1).
- Pytest exit status: `0`; environments: **260**.
- One CSV row per testcase seed records config, coverage delta, observed transactions/events, error counters, and a replay command.
- CPU random uses 500 configured sequence operations per seed; the generated operation list includes two sequence prelude records. Mixed CPU/MMIO/APB/AXI uses 500 checked rounds per seed. Resource-aware runs check one owner store plus two paired reads. Random recovery runs select one reset phase or one AXI error beat per seed.
- Test stimulus and checks are deterministic for the recorded seed/config at the committed source revision. No failing seed occurred, so replay count is zero and trace shrinking was not applicable.
- The counters are monitor observations. CPU accepted/completed counts can differ because dual-lane pair operations and monitor event definitions are not the same as configured sequence operation counts.

| Scenario | Seeds / status | Configured ops or rounds | CPU accepts / completions | Directory req | Snoop accepts | AXI AR / R beats | MMIO req / rsp | APB | Protocol / final-fatal / observed AXI errors | Replay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FULL_SYSTEM_RANDOM | 100/100 PASS | 50000 | 28188 / 58665 | 27811 | 26611 | 1200 / 9600 | 0 / 0 | 0 | 0/0/0 | 0 |
| SEEDED_MIXED_CPU_MMIO_APB_AXI | 100/100 PASS | 50000 | 100000 / 100000 | 50000 | 0 | 50000 / 400000 | 50000 / 50000 | 50000 | 0/0/0 | 0 |
| RESOURCE_AWARE_SNOOP_REFILL | 20/20 PASS | 60 | 20 / 60 | 60 | 20 | 40 / 320 | 0 / 0 | 0 | 0/0/0 | 0 |
| RANDOMIZED_RESET_PHASE | 20/20 PASS | 20 | 40 / 20 | 30 | 0 | 25 / 160 | 5 / 5 | 0 | 0/0/0 | 0 |
| RANDOMIZED_AXI_READ_ERROR_RECOVERY | 20/20 PASS | 20 | 40 / 20 | 40 | 0 | 40 / 265 | 0 / 0 | 0 | 0/0/20 | 0 |

## Per-scenario coverage deltas

### `FULL_SYSTEM_RANDOM`

| Checked bin | Hits |
| --- | ---: |
| `FS.AXI.READ_OUT_OF_ORDER` | 100 |
| `FS.CPU.READ.CORE0` | 17681 |
| `FS.CPU.READ.CORE1` | 17729 |
| `FS.CPU.WRITE.CORE0` | 11612 |
| `FS.CPU.WRITE.CORE1` | 11643 |
| `FS.CROSS.CORE0.READ` | 17681 |
| `FS.CROSS.CORE0.WRITE` | 11612 |
| `FS.CROSS.CORE1.READ` | 17729 |
| `FS.CROSS.CORE1.WRITE` | 11643 |
| `FS.MESI.E_TO_I` | 263 |
| `FS.MESI.E_TO_M` | 271 |
| `FS.MESI.E_TO_S` | 358 |
| `FS.MESI.I_TO_E` | 892 |
| `FS.MESI.I_TO_M` | 7038 |
| `FS.MESI.I_TO_S` | 10212 |
| `FS.MESI.M_TO_I` | 6467 |
| `FS.MESI.M_TO_S` | 9854 |
| `FS.MESI.S_TO_I` | 9669 |
| `FS.MESI.S_TO_M` | 9669 |
| `FS.MSHR.OCCUPANCY_2` | 100 |

### `SEEDED_MIXED_CPU_MMIO_APB_AXI`

| Checked bin | Hits |
| --- | ---: |
| `FS.APB.READ_DURING_AXI` | 50000 |
| `FS.CPU.READ.CORE0` | 24848 |
| `FS.CPU.READ.CORE1` | 25026 |
| `FS.CPU.WRITE.CORE0` | 25152 |
| `FS.CPU.WRITE.CORE1` | 24974 |
| `FS.CROSS.APB_WITH_AXI_TRAFFIC` | 50000 |
| `FS.CROSS.CORE0.READ` | 24848 |
| `FS.CROSS.CORE0.WRITE` | 25152 |
| `FS.CROSS.CORE1.READ` | 25026 |
| `FS.CROSS.CORE1.WRITE` | 24974 |
| `FS.CROSS.MIXED_CPU_MMIO_APB_AXI` | 50000 |
| `FS.MESI.I_TO_E` | 24998 |
| `FS.MESI.I_TO_M` | 25002 |
| `FS.STRESS.MIXED_CPU_MMIO_APB_AXI` | 50000 |

### `RESOURCE_AWARE_SNOOP_REFILL`

| Checked bin | Hits |
| --- | ---: |
| `FS.CPU.READ.CORE0` | 20 |
| `FS.CPU.READ.CORE1` | 20 |
| `FS.CPU.WRITE.CORE0` | 10 |
| `FS.CPU.WRITE.CORE1` | 10 |
| `FS.CROSS.CORE0.READ` | 20 |
| `FS.CROSS.CORE0.WRITE` | 10 |
| `FS.CROSS.CORE1.READ` | 20 |
| `FS.CROSS.CORE1.WRITE` | 10 |
| `FS.CROSS.SNOOP_REFILL_DISTINCT_L2_SET` | 10 |
| `FS.CROSS.SNOOP_REFILL_SAME_L2_SET` | 10 |
| `FS.MESI.I_TO_E` | 20 |
| `FS.MESI.I_TO_M` | 20 |
| `FS.MESI.I_TO_S` | 20 |
| `FS.MESI.M_TO_S` | 20 |
| `FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET` | 10 |
| `FS.RESOURCE.SNOOP_REFILL_SAME_L2_SET` | 10 |

### `RANDOMIZED_RESET_PHASE`

| Checked bin | Hits |
| --- | ---: |
| `FS.CPU.READ.CORE0` | 15 |
| `FS.CROSS.CORE0.READ` | 15 |
| `FS.CROSS.STRESS_RESET_AR_STALL` | 5 |
| `FS.CROSS.STRESS_RESET_CPU_RESPONSE_STALL` | 5 |
| `FS.CROSS.STRESS_RESET_MMIO_REQUEST_STALL` | 5 |
| `FS.CROSS.STRESS_RESET_R_GAP` | 5 |
| `FS.MESI.I_TO_E` | 15 |
| `FS.STRESS.RESET_AR_STALL` | 5 |
| `FS.STRESS.RESET_CPU_RESPONSE_STALL` | 5 |
| `FS.STRESS.RESET_MMIO_REQUEST_STALL` | 5 |
| `FS.STRESS.RESET_R_GAP` | 5 |

### `RANDOMIZED_AXI_READ_ERROR_RECOVERY`

| Checked bin | Hits |
| --- | ---: |
| `FS.CPU.READ.CORE0` | 20 |
| `FS.CROSS.CORE0.READ` | 20 |
| `FS.CROSS.STRESS_AXI_ERROR_RECOVERY` | 20 |
| `FS.MESI.I_TO_E` | 20 |
| `FS.STRESS.AXI_R_ERROR_BEAT_INJECTION` | 20 |

## Replay and failure handling

- The CSV stores the exact test ID, seed, configuration, and a one-seed command for each run.
- AXI error campaign counts are deliberate injected SLVERR events; each seed passes only after the DUT suppresses successful data, resets, and returns the independently expected data on retry. The final-fatal column is sampled after recovery.
- For future failures, `conftest.py` captures the generated operation prefix and failure context in `full_system_coverage.json` and cycle/event data in `full_system_trace.jsonl`; the replay target accepts a saved trace/test ID. No trace minimizer is implemented yet.
- The raw JSON is a generated scratch report and may be removed by `make clean`; regenerate it with `make COHERENCE_JOBS=2 coherence_full_system_stress`, which also refreshes this compact summary.
