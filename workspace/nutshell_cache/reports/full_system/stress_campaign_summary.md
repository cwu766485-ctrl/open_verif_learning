# Four-Agent Full-System Stress Campaign

- Raw source: `reports/full_system/stress/full_system_coverage.json` (schema 1).
- Pytest exit status: `0`; environments: **260**.
- One CSV row per testcase seed records config, coverage delta, observed transactions/events, error counters, and a replay command.
- CPU random uses 500 configured sequence operations per seed; the generated operation list includes two sequence prelude records. Mixed CPU/MMIO/APB/AXI uses 500 checked rounds per seed. Resource-aware runs check one owner store plus two paired reads. Random recovery runs select one reset phase or one AXI error beat per seed.
- Test stimulus and checks are deterministic for the recorded seed/config at the committed source revision. No failing seed occurred, so replay count is zero and trace shrinking was not applicable.
- The counters are monitor observations. CPU accepted/completed counts can differ because dual-lane pair operations and monitor event definitions are not the same as configured sequence operation counts.

| Scenario | Seeds / status | Configured ops or rounds | CPU accepts / completions | Directory req | Snoop accepts | AXI AR / R beats | MMIO req / rsp | APB | Protocol / final-fatal / observed AXI errors | Replay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FULL_SYSTEM_RANDOM | 100/100 PASS | 50000 | 58475 / 58958 | 28114 | 26714 | 1400 / 11200 | 0 / 0 | 200 | 0/0/0 | 0 |
| SEEDED_MIXED_CPU_MMIO_APB_AXI | 100/100 PASS | 50000 | 100300 / 100300 | 50430 | 100 | 50200 / 401600 | 50000 / 50000 | 50200 | 0/0/0 | 0 |
| RESOURCE_AWARE_SNOOP_REFILL | 20/20 PASS | 60 | 20 / 60 | 60 | 20 | 40 / 320 | 0 / 0 | 0 | 0/0/0 | 0 |
| RANDOMIZED_RESET_PHASE | 20/20 PASS | 20 | 40 / 20 | 30 | 0 | 25 / 160 | 5 / 5 | 0 | 0/0/0 | 0 |
| RANDOMIZED_AXI_READ_ERROR_RECOVERY | 20/20 PASS | 20 | 40 / 20 | 40 | 0 | 40 / 265 | 0 / 0 | 0 | 0/0/20 | 0 |

## Per-scenario coverage deltas

### `FULL_SYSTEM_RANDOM`

| Checked bin | Hits |
| --- | ---: |
| `FS.AXI.READ_OUT_OF_ORDER` | 100 |
| `FS.CPU.READ.CORE0` | 17771 |
| `FS.CPU.READ.CORE1` | 17823 |
| `FS.CPU.WRITE.CORE0` | 11662 |
| `FS.CPU.WRITE.CORE1` | 11702 |
| `FS.CROSS.CORE0.READ` | 17771 |
| `FS.CROSS.CORE0.WRITE` | 11662 |
| `FS.CROSS.CORE1.READ` | 17823 |
| `FS.CROSS.CORE1.WRITE` | 11702 |
| `FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET` | 100 |
| `FS.CROSS.SNOOP_REFILL_DISTINCT_L2_SET` | 100 |
| `FS.MESI.E_TO_I` | 266 |
| `FS.MESI.E_TO_M` | 273 |
| `FS.MESI.E_TO_S` | 361 |
| `FS.MESI.I_TO_E` | 1000 |
| `FS.MESI.I_TO_M` | 7164 |
| `FS.MESI.I_TO_S` | 10297 |
| `FS.MESI.M_TO_I` | 6498 |
| `FS.MESI.M_TO_S` | 9936 |
| `FS.MESI.S_TO_I` | 9653 |
| `FS.MESI.S_TO_M` | 9653 |
| `FS.MSHR.OCCUPANCY_2` | 100 |
| `FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET` | 100 |
| `FS.XAGENT.OWNER_TRANSFER_REFILL_APB` | 100 |

### `SEEDED_MIXED_CPU_MMIO_APB_AXI`

| Checked bin | Hits |
| --- | ---: |
| `FS.APB.READ_DURING_AXI` | 50000 |
| `FS.CPU.READ.CORE0` | 24948 |
| `FS.CPU.READ.CORE1` | 25126 |
| `FS.CPU.WRITE.CORE0` | 25200 |
| `FS.CPU.WRITE.CORE1` | 25026 |
| `FS.CROSS.APB_WITH_AXI_TRAFFIC` | 50000 |
| `FS.CROSS.CORE0.READ` | 24948 |
| `FS.CROSS.CORE0.WRITE` | 25200 |
| `FS.CROSS.CORE1.READ` | 25126 |
| `FS.CROSS.CORE1.WRITE` | 25026 |
| `FS.CROSS.MIXED_CPU_MMIO_APB_AXI` | 50000 |
| `FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET` | 100 |
| `FS.CROSS.SNOOP_REFILL_DISTINCT_L2_SET` | 100 |
| `FS.MESI.I_TO_E` | 25098 |
| `FS.MESI.I_TO_M` | 25102 |
| `FS.MESI.I_TO_S` | 100 |
| `FS.MESI.M_TO_S` | 100 |
| `FS.RESOURCE.SNOOP_REFILL_DISTINCT_L2_SET` | 100 |
| `FS.STRESS.MIXED_CPU_MMIO_APB_AXI` | 50000 |
| `FS.XAGENT.OWNER_TRANSFER_REFILL_APB` | 100 |

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
- `conftest.py` captures generated operations, failure context, and cycle/event data; the replay target accepts a saved trace/test ID. `dv.sequences.trace_minimizer` provides an order-preserving delta-debugging primitive that requires a caller-supplied replay predicate and retains marked legal preludes. It is not yet wired to automatic simulator replay; no failing seed occurred in this campaign, so no real DUT failure trace was minimized.
- The stress raw JSON is separate from the sign-off coverage dataset. It is a generated scratch report and may be removed by `make clean`; regenerate it with `make COHERENCE_JOBS=2 coherence_full_system_stress`, which also refreshes this compact summary.
