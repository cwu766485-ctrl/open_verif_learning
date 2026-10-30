# Coherence RTL Coverage Gap Review

Generated from `reports/coherence/coverage.info` on 2026-10-30 17:47 +08.

## Summary

- Merged line records: 2799/3088 hit; 289 missed.
- Product RTL: 1034/1224 hit; 190 missed lines.
- SystemVerilog testbench: 45 missed lines (kept separate from RTL).
- Other source files: 54 missed lines.

## Per-file unhit line ranges

Line numbers refer to the source paths in the merged LCOV report.

| Source | Hit / total | Missed | Unhit lines |
| --- | ---: | ---: | --- |
| `../dv/blocks/coherent_cache_subsystem/tb/include/backpressure_cases.svh` | 20/27 | 7 | 10, 38, 57–60, 69 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/cpu_drivers.svh` | 153/177 | 24 | 30–31, 36–38, 40–42, 65, 69–70, 109–112, 142, 146–147, 210, 215–216, 220–221, 255 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/error_and_summary_cases.svh` | 21/23 | 2 | 15, 52 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/memory_model.svh` | 152/156 | 4 | 20, 133–135 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/mesi_and_concurrency_cases.svh` | 28/31 | 3 | 15, 23, 145 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/random_and_reset_cases.svh` | 66/68 | 2 | 149, 193 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/reference_data_model.svh` | 155/157 | 2 | 125–126 |
| `../dv/blocks/coherent_cache_subsystem/tb/include/reference_protocol_model.svh` | 124/125 | 1 | 29 |
| `cluster/DualL1MesiCluster.sv` | 126/134 | 8 | 407–409, 412–413, 443–445 |
| `coherence/SharedLineEngine.sv` | 141/190 | 49 | 133–135, 141–143, 182–184, 191–193, 203–205, 207–208, 218–220, 232–235, 246–248, 276, 278–280, 298–300, 320, 331–334, 348–354, 366–368 |
| `directory/DirectoryController.sv` | 218/323 | 105 | 198–201, 238–241, 277–286, 299–302, 313–315, 331–334, 353, 356–364, 366–369, 378–380, 388–389, 392–401, 413–418, 431–434, 438–441, 467, 470, 475–480, 482–493, 495–498, 501–504, 529, 531–534 |
| `directory/DirectoryMshrBank.sv` | 169/186 | 17 | 146–147, 156, 158, 160, 178, 287, 339–341, 362–365, 372–374 |
| `interconnect/CpuMmioRouter.sv` | 68/73 | 5 | 82, 138, 162–164 |
| `l1/MesiL1Array.sv` | 146/159 | 13 | 260–262, 269–270, 290–291, 300–301, 309–310, 326, 341 |
| `l1/MesiL1Controller.sv` | 188/225 | 37 | 254–256, 287–289, 309, 317–318, 345, 347–349, 365–368, 377–379, 394–395, 409, 415–420, 429, 436, 439–440, 454, 456–458 |
| `l2/SharedL2DirectoryArray.sv` | 187/197 | 10 | 274–275, 288–289, 305, 313–314, 326–327, 340 |

## Review conclusion

The unhit RTL is concentrated in defensive protocol-error handling, illegal metadata/opcode rejection, reset/error FSM defaults, and rare recovery/arbiter-lock paths. These lines are not evidence of a functional failure by themselves. The Directory recovery cases and invalid-input paths remain the most valuable candidates for future directed tests; existing bounded formal and independent Python/Toffee tests provide separate evidence for transaction stability, MSHR admission, reset cancellation, data integrity, and coherence state.

The testbench misses are assertion/error guards and setup branches; they are reported separately. This review does not waive any functional requirement and does not claim 100% statement/branch coverage. PPA, SRAM mapping, and STA are outside this review.
