# Phase 1 Coverage Infrastructure Audit and Baseline Freeze

Generated from the full regression artifacts on 2026-10-30 22:58 +08.

## Scope and source accounting

No RTL behavior, interface, testcase sequence, Functional Coverage Bin ID, or waiver was changed. Product RTL classification uses exact normalized path membership in rtl/Coherence.files.f.

- RTL Source Manifest: **18 files**; Verilator __verFiles.dat RTL source set: **18 files**; exact match: **PASS**.
- LCOV source records: **30**; product RTL manifest files with executable line points: **14**; files with no line points in this selected top/run: **4**.
- A manifest source with no executable LCOV line points is reported as N/A, not as 0% coverage. Such files can still be parsed/compiled but may be packages, unelaborated top wrappers, or blocks outside this simulation top.

### LCOV line reconciliation

Each normalized (source, line) record is counted once. Hit + missed must equal total in every category and globally.

| Category | Hit | Total | Missed | Reconciliation |
| --- | ---: | ---: | ---: | --- |
| Product RTL | 858 | 1006 | 148 | 858 + 148 = 1006 |
| Testbench | 738 | 748 | 10 | 738 + 10 = 748 |
| Generated/Other | 0 | 0 | 0 | 0 + 0 = 0 |
| **All source records** | **1596** | **1754** | **158** | **1596 + 158 = 1754** |

## Native Verilator coverage by source category

Native point totals are parsed from merged coverage.dat by point type; point hit means count > 0. These are independent of LCOV DA line totals.

| Category | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |
| --- | ---: | ---: | ---: | ---: |
| Product RTL | 450/536 | 19916/26978 | 30/54 | 7/48 |
| Testbench | 235/266 | 4060/6628 | N/A (0 points) | N/A (0 points) |
| Generated/Other | N/A (0 points) | N/A (0 points) | N/A (0 points) | N/A (0 points) |

## Product RTL module raw coverage

Line columns use unique LCOV source-line records. Native columns use point records from coverage.dat. N/A means this build/run emitted no points of that type for the source.

| RTL Source | Line hit/total | Line missed | Branch hit/total | Toggle hit/total | FSM state hit/total | FSM arc hit/total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `rtl/bus/apb/CachePerformanceCsr.sv` | N/A | N/A | N/A | N/A | N/A | N/A |
| `rtl/bus/axi/LineMemoryAxi4Adapter.sv` | N/A | N/A | N/A | N/A | N/A | N/A |
| `rtl/bus/axi/MemoryRefillMshrBank.sv` | 37/37 | 0 | 32/34 | 429/738 | N/A | N/A |
| `rtl/cluster/DualL1MesiCluster.sv` | 59/62 | 3 | 54/62 | 5066/6300 | N/A | N/A |
| `rtl/coherence/SharedLineEngine.sv` | 73/104 | 31 | 36/52 | 468/648 | N/A | N/A |
| `rtl/common/CoherenceProtocol.sv` | N/A | N/A | N/A | N/A | N/A | N/A |
| `rtl/directory/DirectoryController.sv` | 114/188 | 74 | 29/42 | 497/612 | 18/40 | 4/36 |
| `rtl/directory/DirectoryMshrBank.sv` | 94/104 | 10 | 71/86 | 863/2292 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiter.sv` | 5/5 | 0 | N/A | 276/414 | N/A | N/A |
| `rtl/interconnect/CoherenceRequestArbiterCore.sv` | 22/22 | 0 | 4/4 | 183/260 | N/A | N/A |
| `rtl/interconnect/CpuMmioRouter.sv` | 31/34 | 3 | 18/20 | 1517/1872 | N/A | N/A |
| `rtl/interconnect/L2LineWriteArbiter.sv` | 50/50 | 0 | 4/4 | 1215/1374 | N/A | N/A |
| `rtl/l1/MesiL1Array.sv` | 67/67 | 0 | 54/62 | 1314/2054 | N/A | N/A |
| `rtl/l1/MesiL1Controller.sv` | 103/126 | 23 | 31/46 | 1291/1532 | 12/14 | 3/12 |
| `rtl/l1/MesiL1SnoopArbiter.sv` | 6/6 | 0 | N/A | 195/272 | N/A | N/A |
| `rtl/l2/SharedL2DirectoryArray.sv` | 75/79 | 4 | 67/74 | 992/1324 | N/A | N/A |
| `rtl/top/CoherentCacheAxiSubsystem.sv` | N/A | N/A | N/A | N/A | N/A | N/A |
| `rtl/top/CoherentCacheSubsystem.sv` | 122/122 | 0 | 50/50 | 5610/7286 | N/A | N/A |

## Every uncovered Product RTL line (148 lines)

Each missed executable source line is linked to its original RTL path and line. Categories are source-context review labels: the default/FSM label is only an unreachability candidate, never a proof; error labels identify checks/actions, and legal/recovery labels identify paths for which directed stimulus is appropriate. No category automatically waives a line.

| Review category | Lines |
| --- | ---: |
| FSM/default 防御分支（不可达候选，未证明） | 10 |
| 合法恢复 / 重试路径未命中 | 13 |
| 合法路径未命中 | 29 |
| 非法协议检测 / 错误处理 | 96 |

| Source line | Review category | Source text |
| --- | --- | --- |
| [`rtl/cluster/DualL1MesiCluster.sv:407`](../rtl/cluster/DualL1MesiCluster.sv#L407) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/cluster/DualL1MesiCluster.sv:408`](../rtl/cluster/DualL1MesiCluster.sv#L408) | 非法协议检测 / 错误处理 | `replace_protocol_error_q <= 1'b1;` |
| [`rtl/cluster/DualL1MesiCluster.sv:409`](../rtl/cluster/DualL1MesiCluster.sv#L409) | 非法协议检测 / 错误处理 | `replace_state_q <= REPLACE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:133`](../rtl/coherence/SharedLineEngine.sv#L133) | 非法协议检测 / 错误处理 | `if (mem_r_protocol_bad) begin` |
| [`rtl/coherence/SharedLineEngine.sv:134`](../rtl/coherence/SharedLineEngine.sv#L134) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:135`](../rtl/coherence/SharedLineEngine.sv#L135) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:141`](../rtl/coherence/SharedLineEngine.sv#L141) | 非法协议检测 / 错误处理 | `(engine_state_q != ENGINE_VICTIM_WRITE_WAIT_RSP)) begin` |
| [`rtl/coherence/SharedLineEngine.sv:142`](../rtl/coherence/SharedLineEngine.sv#L142) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:143`](../rtl/coherence/SharedLineEngine.sv#L143) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:182`](../rtl/coherence/SharedLineEngine.sv#L182) | 非法协议检测 / 错误处理 | `end else begin` |
| [`rtl/coherence/SharedLineEngine.sv:183`](../rtl/coherence/SharedLineEngine.sv#L183) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:184`](../rtl/coherence/SharedLineEngine.sv#L184) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:191`](../rtl/coherence/SharedLineEngine.sv#L191) | 非法协议检测 / 错误处理 | `end else begin` |
| [`rtl/coherence/SharedLineEngine.sv:192`](../rtl/coherence/SharedLineEngine.sv#L192) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:193`](../rtl/coherence/SharedLineEngine.sv#L193) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:232`](../rtl/coherence/SharedLineEngine.sv#L232) | 非法协议检测 / 错误处理 | `if ((mem_wr_data_beat_idx != victim_expected_beat_q) \|\|` |
| [`rtl/coherence/SharedLineEngine.sv:233`](../rtl/coherence/SharedLineEngine.sv#L233) | 非法协议检测 / 错误处理 | `(mem_wr_data_last != (mem_wr_data_beat_idx == 3'd7))) begin` |
| [`rtl/coherence/SharedLineEngine.sv:234`](../rtl/coherence/SharedLineEngine.sv#L234) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:235`](../rtl/coherence/SharedLineEngine.sv#L235) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:246`](../rtl/coherence/SharedLineEngine.sv#L246) | 非法协议检测 / 错误处理 | `if (mem_wr_rsp_txn_id != engine_txn_q) begin` |
| [`rtl/coherence/SharedLineEngine.sv:247`](../rtl/coherence/SharedLineEngine.sv#L247) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:248`](../rtl/coherence/SharedLineEngine.sv#L248) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:276`](../rtl/coherence/SharedLineEngine.sv#L276) | 非法协议检测 / 错误处理 | `if ((l2_line_wr_beat_idx != mem_expected_beat_q) \|\|` |
| [`rtl/coherence/SharedLineEngine.sv:278`](../rtl/coherence/SharedLineEngine.sv#L278) | 非法协议检测 / 错误处理 | `(snoop_data_txn_id_core[victim_snoop_target_q] != engine_txn_q)) begin` |
| [`rtl/coherence/SharedLineEngine.sv:279`](../rtl/coherence/SharedLineEngine.sv#L279) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:280`](../rtl/coherence/SharedLineEngine.sv#L280) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:331`](../rtl/coherence/SharedLineEngine.sv#L331) | 非法协议检测 / 错误处理 | `if ((l2_line_wr_beat_idx != mem_expected_beat_q) \|\|` |
| [`rtl/coherence/SharedLineEngine.sv:332`](../rtl/coherence/SharedLineEngine.sv#L332) | 非法协议检测 / 错误处理 | `(l2_line_wr_last != (l2_line_wr_beat_idx == 3'd7))) begin` |
| [`rtl/coherence/SharedLineEngine.sv:333`](../rtl/coherence/SharedLineEngine.sv#L333) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:334`](../rtl/coherence/SharedLineEngine.sv#L334) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/coherence/SharedLineEngine.sv:348`](../rtl/coherence/SharedLineEngine.sv#L348) | 合法路径未命中 | `ENGINE_GRANT_READ: begin` |
| [`rtl/coherence/SharedLineEngine.sv:366`](../rtl/coherence/SharedLineEngine.sv#L366) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/coherence/SharedLineEngine.sv:367`](../rtl/coherence/SharedLineEngine.sv#L367) | 非法协议检测 / 错误处理 | `memory_adapter_protocol_error <= 1'b1;` |
| [`rtl/coherence/SharedLineEngine.sv:368`](../rtl/coherence/SharedLineEngine.sv#L368) | 非法协议检测 / 错误处理 | `engine_state_q <= ENGINE_ERROR;` |
| [`rtl/directory/DirectoryController.sv:238`](../rtl/directory/DirectoryController.sv#L238) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/directory/DirectoryController.sv:239`](../rtl/directory/DirectoryController.sv#L239) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:240`](../rtl/directory/DirectoryController.sv#L240) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd2;` |
| [`rtl/directory/DirectoryController.sv:241`](../rtl/directory/DirectoryController.sv#L241) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:299`](../rtl/directory/DirectoryController.sv#L299) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/directory/DirectoryController.sv:300`](../rtl/directory/DirectoryController.sv#L300) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:301`](../rtl/directory/DirectoryController.sv#L301) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd2;` |
| [`rtl/directory/DirectoryController.sv:302`](../rtl/directory/DirectoryController.sv#L302) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:353`](../rtl/directory/DirectoryController.sv#L353) | 合法恢复 / 重试路径未命中 | `DIR_I: begin` |
| [`rtl/directory/DirectoryController.sv:356`](../rtl/directory/DirectoryController.sv#L356) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:357`](../rtl/directory/DirectoryController.sv#L357) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd4;` |
| [`rtl/directory/DirectoryController.sv:358`](../rtl/directory/DirectoryController.sv#L358) | 合法恢复 / 重试路径未命中 | `grant_opcode_q <= GRANT_DATA_M;` |
| [`rtl/directory/DirectoryController.sv:359`](../rtl/directory/DirectoryController.sv#L359) | 合法恢复 / 重试路径未命中 | `grant_has_data_q <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:360`](../rtl/directory/DirectoryController.sv#L360) | 合法恢复 / 重试路径未命中 | `next_dir_state_q <= DIR_U;` |
| [`rtl/directory/DirectoryController.sv:361`](../rtl/directory/DirectoryController.sv#L361) | 合法恢复 / 重试路径未命中 | `next_sharers_q <= 2'b00;` |
| [`rtl/directory/DirectoryController.sv:362`](../rtl/directory/DirectoryController.sv#L362) | 合法恢复 / 重试路径未命中 | `next_owner_q <= req_src_id;` |
| [`rtl/directory/DirectoryController.sv:363`](../rtl/directory/DirectoryController.sv#L363) | 合法恢复 / 重试路径未命中 | `line_xfer_kind_q <= XFER_L2_REFILL;` |
| [`rtl/directory/DirectoryController.sv:364`](../rtl/directory/DirectoryController.sv#L364) | 合法路径未命中 | `state_q <= DIR_START_XFER;` |
| [`rtl/directory/DirectoryController.sv:366`](../rtl/directory/DirectoryController.sv#L366) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/directory/DirectoryController.sv:367`](../rtl/directory/DirectoryController.sv#L367) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:368`](../rtl/directory/DirectoryController.sv#L368) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd2;` |
| [`rtl/directory/DirectoryController.sv:369`](../rtl/directory/DirectoryController.sv#L369) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:388`](../rtl/directory/DirectoryController.sv#L388) | 非法协议检测 / 错误处理 | `end else if ((lookup_dir_state == DIR_U) &&` |
| [`rtl/directory/DirectoryController.sv:389`](../rtl/directory/DirectoryController.sv#L389) | 合法路径未命中 | `(lookup_owner_id == req_src_id)) begin` |
| [`rtl/directory/DirectoryController.sv:392`](../rtl/directory/DirectoryController.sv#L392) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:393`](../rtl/directory/DirectoryController.sv#L393) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd5;` |
| [`rtl/directory/DirectoryController.sv:394`](../rtl/directory/DirectoryController.sv#L394) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:395`](../rtl/directory/DirectoryController.sv#L395) | 合法路径未命中 | `grant_opcode_q <= GRANT_PUT_ACK;` |
| [`rtl/directory/DirectoryController.sv:396`](../rtl/directory/DirectoryController.sv#L396) | 非法协议检测 / 错误处理 | `end else if (lookup_dir_state != DIR_I) begin` |
| [`rtl/directory/DirectoryController.sv:397`](../rtl/directory/DirectoryController.sv#L397) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:398`](../rtl/directory/DirectoryController.sv#L398) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd5;` |
| [`rtl/directory/DirectoryController.sv:399`](../rtl/directory/DirectoryController.sv#L399) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:400`](../rtl/directory/DirectoryController.sv#L400) | 非法协议检测 / 错误处理 | `end else begin` |
| [`rtl/directory/DirectoryController.sv:401`](../rtl/directory/DirectoryController.sv#L401) | 合法路径未命中 | `state_q <= DIR_COMMIT;` |
| [`rtl/directory/DirectoryController.sv:413`](../rtl/directory/DirectoryController.sv#L413) | 非法协议检测 / 错误处理 | `end else if (lookup_dir_state == DIR_I) begin` |
| [`rtl/directory/DirectoryController.sv:414`](../rtl/directory/DirectoryController.sv#L414) | 合法路径未命中 | `state_q <= DIR_COMMIT;` |
| [`rtl/directory/DirectoryController.sv:415`](../rtl/directory/DirectoryController.sv#L415) | 非法协议检测 / 错误处理 | `end else begin` |
| [`rtl/directory/DirectoryController.sv:416`](../rtl/directory/DirectoryController.sv#L416) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:417`](../rtl/directory/DirectoryController.sv#L417) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd6;` |
| [`rtl/directory/DirectoryController.sv:418`](../rtl/directory/DirectoryController.sv#L418) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:438`](../rtl/directory/DirectoryController.sv#L438) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/directory/DirectoryController.sv:439`](../rtl/directory/DirectoryController.sv#L439) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:440`](../rtl/directory/DirectoryController.sv#L440) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd2;` |
| [`rtl/directory/DirectoryController.sv:441`](../rtl/directory/DirectoryController.sv#L441) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:467`](../rtl/directory/DirectoryController.sv#L467) | 合法恢复 / 重试路径未命中 | `if (((snoop_rsp_opcode == SNOOP_RSP_INV_ACK) \|\|` |
| [`rtl/directory/DirectoryController.sv:470`](../rtl/directory/DirectoryController.sv#L470) | 合法恢复 / 重试路径未命中 | `snoop_response_must_be_data_q)) begin` |
| [`rtl/directory/DirectoryController.sv:475`](../rtl/directory/DirectoryController.sv#L475) | 合法恢复 / 重试路径未命中 | `next_dir_state_q <= DIR_U;` |
| [`rtl/directory/DirectoryController.sv:476`](../rtl/directory/DirectoryController.sv#L476) | 合法恢复 / 重试路径未命中 | `next_sharers_q <= 2'b00;` |
| [`rtl/directory/DirectoryController.sv:477`](../rtl/directory/DirectoryController.sv#L477) | 合法恢复 / 重试路径未命中 | `next_owner_q <= src_id_q;` |
| [`rtl/directory/DirectoryController.sv:478`](../rtl/directory/DirectoryController.sv#L478) | 合法恢复 / 重试路径未命中 | `grant_has_data_q <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:483`](../rtl/directory/DirectoryController.sv#L483) | 合法路径未命中 | `line_xfer_kind_q <= XFER_L2_REFILL;` |
| [`rtl/directory/DirectoryController.sv:484`](../rtl/directory/DirectoryController.sv#L484) | 合法路径未命中 | `snoop_response_must_be_data_q <= 1'b0;` |
| [`rtl/directory/DirectoryController.sv:485`](../rtl/directory/DirectoryController.sv#L485) | 合法路径未命中 | `snoop_resume_q <= DIR_COMMIT;` |
| [`rtl/directory/DirectoryController.sv:486`](../rtl/directory/DirectoryController.sv#L486) | 合法路径未命中 | `pending_targets_q <= 2'b00;` |
| [`rtl/directory/DirectoryController.sv:487`](../rtl/directory/DirectoryController.sv#L487) | 合法路径未命中 | `state_q <= DIR_START_XFER;` |
| [`rtl/directory/DirectoryController.sv:488`](../rtl/directory/DirectoryController.sv#L488) | 非法协议检测 / 错误处理 | `end else if ((snoop_opcode_q == SNOOP_READ) &&` |
| [`rtl/directory/DirectoryController.sv:489`](../rtl/directory/DirectoryController.sv#L489) | 非法协议检测 / 错误处理 | `(snoop_rsp_opcode != SNOOP_RSP_DATA)) begin` |
| [`rtl/directory/DirectoryController.sv:490`](../rtl/directory/DirectoryController.sv#L490) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:491`](../rtl/directory/DirectoryController.sv#L491) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd8;` |
| [`rtl/directory/DirectoryController.sv:492`](../rtl/directory/DirectoryController.sv#L492) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:493`](../rtl/directory/DirectoryController.sv#L493) | 非法协议检测 / 错误处理 | `end else if ((snoop_opcode_q == SNOOP_INVALIDATE) &&` |
| [`rtl/directory/DirectoryController.sv:495`](../rtl/directory/DirectoryController.sv#L495) | 非法协议检测 / 错误处理 | `(snoop_rsp_opcode != SNOOP_RSP_DATA)) begin` |
| [`rtl/directory/DirectoryController.sv:496`](../rtl/directory/DirectoryController.sv#L496) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:497`](../rtl/directory/DirectoryController.sv#L497) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd10;` |
| [`rtl/directory/DirectoryController.sv:498`](../rtl/directory/DirectoryController.sv#L498) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:501`](../rtl/directory/DirectoryController.sv#L501) | 非法协议检测 / 错误处理 | `(snoop_rsp_opcode != SNOOP_RSP_INV_ACK)) begin` |
| [`rtl/directory/DirectoryController.sv:502`](../rtl/directory/DirectoryController.sv#L502) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:503`](../rtl/directory/DirectoryController.sv#L503) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd11;` |
| [`rtl/directory/DirectoryController.sv:504`](../rtl/directory/DirectoryController.sv#L504) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:529`](../rtl/directory/DirectoryController.sv#L529) | 非法协议检测 / 错误处理 | `DIR_ERROR: state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryController.sv:531`](../rtl/directory/DirectoryController.sv#L531) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/directory/DirectoryController.sv:532`](../rtl/directory/DirectoryController.sv#L532) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/directory/DirectoryController.sv:533`](../rtl/directory/DirectoryController.sv#L533) | 非法协议检测 / 错误处理 | `protocol_error_code <= 4'd9;` |
| [`rtl/directory/DirectoryController.sv:534`](../rtl/directory/DirectoryController.sv#L534) | 非法协议检测 / 错误处理 | `state_q <= DIR_ERROR;` |
| [`rtl/directory/DirectoryMshrBank.sv:339`](../rtl/directory/DirectoryMshrBank.sv#L339) | 合法路径未命中 | `if (dir_write_valid && !dir_write_ready && !write_offer_lock_q) begin` |
| [`rtl/directory/DirectoryMshrBank.sv:340`](../rtl/directory/DirectoryMshrBank.sv#L340) | 合法路径未命中 | `write_offer_lock_q <= 1'b1;` |
| [`rtl/directory/DirectoryMshrBank.sv:341`](../rtl/directory/DirectoryMshrBank.sv#L341) | 合法路径未命中 | `write_offer_idx_q <= write_sel;` |
| [`rtl/directory/DirectoryMshrBank.sv:362`](../rtl/directory/DirectoryMshrBank.sv#L362) | 合法路径未命中 | `if (line_xfer_start_valid && !line_xfer_start_ready &&` |
| [`rtl/directory/DirectoryMshrBank.sv:363`](../rtl/directory/DirectoryMshrBank.sv#L363) | 合法路径未命中 | `!xfer_offer_lock_q) begin` |
| [`rtl/directory/DirectoryMshrBank.sv:364`](../rtl/directory/DirectoryMshrBank.sv#L364) | 合法路径未命中 | `xfer_offer_lock_q <= 1'b1;` |
| [`rtl/directory/DirectoryMshrBank.sv:365`](../rtl/directory/DirectoryMshrBank.sv#L365) | 合法路径未命中 | `xfer_offer_idx_q <= xfer_sel;` |
| [`rtl/directory/DirectoryMshrBank.sv:372`](../rtl/directory/DirectoryMshrBank.sv#L372) | 合法路径未命中 | `if (grant_valid && !grant_ready && !grant_offer_lock_q) begin` |
| [`rtl/directory/DirectoryMshrBank.sv:373`](../rtl/directory/DirectoryMshrBank.sv#L373) | 合法路径未命中 | `grant_offer_lock_q <= 1'b1;` |
| [`rtl/directory/DirectoryMshrBank.sv:374`](../rtl/directory/DirectoryMshrBank.sv#L374) | 合法路径未命中 | `grant_offer_idx_q <= grant_sel;` |
| [`rtl/interconnect/CpuMmioRouter.sv:162`](../rtl/interconnect/CpuMmioRouter.sv#L162) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/interconnect/CpuMmioRouter.sv:163`](../rtl/interconnect/CpuMmioRouter.sv#L163) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/interconnect/CpuMmioRouter.sv:164`](../rtl/interconnect/CpuMmioRouter.sv#L164) | 合法路径未命中 | `mmio_state_q <= MMIO_IDLE;` |
| [`rtl/l1/MesiL1Controller.sv:254`](../rtl/l1/MesiL1Controller.sv#L254) | 非法协议检测 / 错误处理 | `if (cpu_req_hit && (cpu_req_line_state == MESI_I)) begin` |
| [`rtl/l1/MesiL1Controller.sv:255`](../rtl/l1/MesiL1Controller.sv#L255) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l1/MesiL1Controller.sv:256`](../rtl/l1/MesiL1Controller.sv#L256) | 非法协议检测 / 错误处理 | `cpu_state_q <= CPU_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:287`](../rtl/l1/MesiL1Controller.sv#L287) | 非法协议检测 / 错误处理 | `if (grant_opcode == GRANT_PUT_ACK) begin` |
| [`rtl/l1/MesiL1Controller.sv:288`](../rtl/l1/MesiL1Controller.sv#L288) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l1/MesiL1Controller.sv:289`](../rtl/l1/MesiL1Controller.sv#L289) | 非法协议检测 / 错误处理 | `cpu_state_q <= CPU_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:317`](../rtl/l1/MesiL1Controller.sv#L317) | 合法路径未命中 | `(grant_data_beat_idx == 3'd7)) begin` |
| [`rtl/l1/MesiL1Controller.sv:318`](../rtl/l1/MesiL1Controller.sv#L318) | 非法协议检测 / 错误处理 | `cpu_state_q <= CPU_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:345`](../rtl/l1/MesiL1Controller.sv#L345) | 非法协议检测 / 错误处理 | `CPU_ERROR: cpu_state_q <= CPU_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:347`](../rtl/l1/MesiL1Controller.sv#L347) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/l1/MesiL1Controller.sv:348`](../rtl/l1/MesiL1Controller.sv#L348) | 合法路径未命中 | `cpu_state_q <= CPU_IDLE;` |
| [`rtl/l1/MesiL1Controller.sv:349`](../rtl/l1/MesiL1Controller.sv#L349) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l1/MesiL1Controller.sv:365`](../rtl/l1/MesiL1Controller.sv#L365) | 合法路径未命中 | `if (!snoop_tag_hit \|\| (snoop_line_state == MESI_I)) begin` |
| [`rtl/l1/MesiL1Controller.sv:366`](../rtl/l1/MesiL1Controller.sv#L366) | 合法路径未命中 | `snoop_rsp_opcode_q <= (snoop_opcode == SNOOP_INVALIDATE) ?` |
| [`rtl/l1/MesiL1Controller.sv:368`](../rtl/l1/MesiL1Controller.sv#L368) | 合法路径未命中 | `snoop_state_q <= SNP_SEND_RSP;` |
| [`rtl/l1/MesiL1Controller.sv:394`](../rtl/l1/MesiL1Controller.sv#L394) | 非法协议检测 / 错误处理 | `end else begin` |
| [`rtl/l1/MesiL1Controller.sv:395`](../rtl/l1/MesiL1Controller.sv#L395) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l1/MesiL1Controller.sv:439`](../rtl/l1/MesiL1Controller.sv#L439) | 合法路径未命中 | `(snoop_array_beat_idx == 3'd7)) begin` |
| [`rtl/l1/MesiL1Controller.sv:440`](../rtl/l1/MesiL1Controller.sv#L440) | 非法协议检测 / 错误处理 | `snoop_state_q <= SNP_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:454`](../rtl/l1/MesiL1Controller.sv#L454) | 非法协议检测 / 错误处理 | `SNP_ERROR: snoop_state_q <= SNP_ERROR;` |
| [`rtl/l1/MesiL1Controller.sv:456`](../rtl/l1/MesiL1Controller.sv#L456) | FSM/default 防御分支（不可达候选，未证明） | `default: begin` |
| [`rtl/l1/MesiL1Controller.sv:457`](../rtl/l1/MesiL1Controller.sv#L457) | 合法路径未命中 | `snoop_state_q <= SNP_IDLE;` |
| [`rtl/l1/MesiL1Controller.sv:458`](../rtl/l1/MesiL1Controller.sv#L458) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l2/SharedL2DirectoryArray.sv:313`](../rtl/l2/SharedL2DirectoryArray.sv#L313) | 非法协议检测 / 错误处理 | `if (!line_wr_hit && !line_wr_free_found)` |
| [`rtl/l2/SharedL2DirectoryArray.sv:314`](../rtl/l2/SharedL2DirectoryArray.sv#L314) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |
| [`rtl/l2/SharedL2DirectoryArray.sv:326`](../rtl/l2/SharedL2DirectoryArray.sv#L326) | 非法协议检测 / 错误处理 | `(line_wr_beat_idx != line_wr_expected_beat_q)) begin` |
| [`rtl/l2/SharedL2DirectoryArray.sv:327`](../rtl/l2/SharedL2DirectoryArray.sv#L327) | 非法协议检测 / 错误处理 | `protocol_error <= 1'b1;` |

## Uncovered-line review and suggested testpoints

| RTL module | Raw gap | Suggested Testpoint / checker |
| --- | ---: | --- |
| `rtl/cluster/DualL1MesiCluster.sv` | 3 (407–409) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/coherence/SharedLineEngine.sv` | 31 (133–135, 141–143, 182–184, 191–193, 232–235, 246–248, 276, 278–280, 331–334, 348, 366–368) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/directory/DirectoryController.sv` | 74 (238–241, 299–302, 353, 356–364, 366–369, 388–389, 392–401, 413–418, 438–441, 467, 470, 475–478, 483–493, 495–498, 501–504, 529, 531–534) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/directory/DirectoryMshrBank.sv` | 10 (339–341, 362–365, 372–374) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/interconnect/CpuMmioRouter.sv` | 3 (162–164) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/l1/MesiL1Controller.sv` | 23 (254–256, 287–289, 317–318, 345, 347–349, 365–366, 368, 394–395, 439–440, 454, 456–458) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |
| `rtl/l2/SharedL2DirectoryArray.sv` | 4 (313–314, 326–327) | Target unhit defensive/error paths with a source-specific checker; classify results before considering any waiver. |

## Functional Coverage map and checker closure

- Python Functional Coverage: **49/49 PASS**; Cross Coverage: **19/19 PASS**; closure status: **PASS**.
- The IDs below are compared in order against the generated closure artifact. Every mapped bin retains a non-empty checker description. No Bin ID or closure logic was edited.
- Closure logic counts sampled feature/cross counters and fails on missing bins. Checker descriptions are audited as map metadata; the current closure script does not machine-prove that each checker ran for each bin. The full regression passed its existing Scoreboard/Monitor checks, but per-bin checker invocation remains an infrastructure gap.

| Bin ID | Feature / Cross | Testpoint | Checker |
| --- | --- | --- | --- |
| `mesi.cold_read` | `cold_read` | Independent cold GetS data check | CoherenceScoreboard response/data model |
| `mesi.cold_write` | `cold_write` | Cold GetM stores to the dual-core set-pressure sequence | CoherenceScoreboard byte-accurate data and MESI invariants |
| `mesi.remote_read_e` | `remote_read_from_E` | Core1 reads Core0 E line | Independent MESI state transition and returned data |
| `mesi.remote_read_m` | `remote_read_from_M` | Remote read observes latest M-owner data | Independent MESI state transition and returned data |
| `mesi.shared_upgrade` | `shared_upgrade` | Core0 byte-masked S-to-M store | Byte-merge data comparison and MESI transition |
| `l1.replacement` | `l1_eviction` | Five same-index lines exceed one L1 set capacity | Independent 4-way L1 replacement model |
| `l1.replacement_put_match` | `l1_replacement_put_match` | Predicted L1 victim line/state matches the accepted Put opcode and address | Independent round-robin replacement scoreboard compared with Directory Put handshakes |
| `l2.refill_hit` | `l2_refill_hit` | Re-read L1-evicted line retained in shared L2 | DUT L2 event and no backing-memory read |
| `l2.refill_miss` | `l2_refill_miss` | Cold line refill absent from shared L2 | DUT L2 event and backing-memory read |
| `l2.live_victim` | `l2_live_eviction` | Ninth same-set line evicts a line still owned by the other L1 | Directory/L1 reference state plus snoop, owner data, and L2 victim model |
| `l2.live_victim_dirty_owner` | `l2_live_victim_dirty_owner` | Dirty M owner is back-invalidated, written back, and reloaded with the same data | Independent Directory/MESI model, accepted Snoop, eight-beat memory writeback, and reload data |
| `l2.live_victim_shared` | `l2_live_victim_shared` | Shared L2 victim with two live S copies is invalidated at both L1s | Independent Directory/L1 model compared with both accepted snoops and any required memory writeback data |
| `cpu.dual_miss_overlap` | `parallel_cold_miss_pair` | Both CPU lanes present independent cold misses together | Single packed DualCoreCpuDriver handshakes and matches each response |
| `cpu.byte_mask` | `byte_mask_write` | Masked store followed by remote read | Architectural byte-lane merge comparison |
| `cpu.byte_mask_m_hit` | `byte_mask_m_hit` | Second byte-masked store hits a Modified line | Independent byte-merge model and local/remote data checks |
| `memory.dirty_writeback` | `dirty_writeback` | Dirty inclusive L2 victim writes all eight beats | Writable memory contents, beat count, and later victim reload |
| `memory.write_response` | `write_response` | CPU transaction completes after memory write response | ID-matched write response handshake count |
| `reset.active_refill` | `reset_during_refill` | Reset cancels a memory-accepted refill without a stale CPU response; the same line works after recovery | CPU response monitor, reset-aware line memory and post-reset data scoreboard |
| `backpressure.cpu_response` | `cpu_response_backpressure` | CPU response payload remains stable while ready is held low | Packed-lane driver checks address, operation and data through the stall |
| `backpressure.memory_read_request` | `memory_read_request_backpressure` | Cold refill request holds through deterministic memory-ready stalls | Accepted line-request queue and ready/valid stall counter |
| `backpressure.memory_write_request` | `memory_write_request_backpressure` | Dirty victim write request holds through deterministic memory-ready stalls | Accepted write-request queue and ready/valid stall counter |
| `backpressure.memory_write_data` | `memory_write_data_backpressure` | All eight dirty-victim beats survive deterministic write-data stalls | Beat-index checker, writable memory model and ready/valid stall counter |
| `memory.read_response_gaps` | `memory_read_response_gaps` | Read refill beats complete with deterministic response-valid gaps | ID/beat-aware memory queue and returned architectural data |
| `directory.lookup_race_regression` | `directory_lookup_race_regression` | Different-address owner transfer and cold grant contend for the L2 lookup | Blocked-lookup monitor plus independent data, snoop-beat, and Directory scoreboard checks |
| `directory.lookup_conflict_transfer` | `directory_lookup_conflict_transfer` | A waiting request is held while an active owner-transfer lookup uses the shared port | Accepted transfer address remains distinct from blocked incoming request |
| `directory.lookup_conflict_grant` | `directory_lookup_conflict_grant` | A waiting request is held while an active grant lookup uses the shared port | Accepted grant address remains distinct from blocked incoming request |
| `directory.snoop_ack_l2_retry` | `snoop_ack_l2_retry` | A same-set Put removes the snapshotted E/M owner before SnoopRead response in either core direction; Directory retries from retained L2 data | Accepted ACK/Snoop transaction ID, PutE/PutM-to-PutAck and GetS-to-DATA_E ID matching, post-ACK L2 hit, no owner beats or DRAM read, data integrity, and independent MESI/Directory commit |
| `directory.mshr_dual_context_backpressure` | `directory_mshr_dual_context_backpressure` | Two distinct-set cold misses hold independent Directory contexts and refill MSHRs during memory request/response stalls | Dual-core driver response matching, unique memory IDs, peak MSHR/Directory occupancy, independent data and Directory model, and protocol-error check |
| `directory.replacement_replay_s_core0` | `replacement_replay_s_core0` | Core0 replacement PutS races a Core1 same-line GetM and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, REPLACE_REPLAY state sample, final data and Directory model |
| `directory.replacement_replay_s_core1` | `replacement_replay_s_core1` | Core1 replacement PutS races a Core0 same-line GetM and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, REPLACE_REPLAY state sample, final data and Directory model |
| `directory.replacement_replay_e_core0` | `replacement_replay_e_core0` | Core0 replacement PutE races a Core1 same-line GetS and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, REPLACE_REPLAY state sample, final data and Directory model |
| `directory.replacement_replay_e_core1` | `replacement_replay_e_core1` | Core1 replacement PutE races a Core0 same-line GetS and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, REPLACE_REPLAY state sample, final data and Directory model |
| `directory.replacement_replay_m_core0` | `replacement_replay_m_core0` | Core0 dirty replacement PutM races a Core1 same-line GetS and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, dirty data comparison, REPLACE_REPLAY sample, and final Directory model |
| `directory.replacement_replay_m_core1` | `replacement_replay_m_core1` | Core1 dirty replacement PutM races a Core0 same-line GetS and replays the miss | Independent replacement predictor, accepted Put/Snoop/Grant monitors, dirty data comparison, REPLACE_REPLAY sample, and final Directory model |
| `directory.snoop_ack_retry_e_owner_core0` | `snoop_ack_l2_retry_e_owner_core0` | Core0's E line is replaced before its SnoopRead ACK; Core1 retries from L2 | Accepted PutE/PutAck and GetS/DATA_E transaction matching, L2 hit, no DRAM/owner stream, and independent data/Directory model |
| `directory.snoop_ack_retry_e_owner_core1` | `snoop_ack_l2_retry_e_owner_core1` | Core1's E line is replaced before its SnoopRead ACK; Core0 retries from L2 | Accepted PutE/PutAck and GetS/DATA_E transaction matching, L2 hit, no DRAM/owner stream, and independent data/Directory model |
| `directory.snoop_ack_retry_m_owner_core0` | `snoop_ack_l2_retry_m_owner_core0` | Core0's M line is replaced before its SnoopRead ACK; Core1 retries dirty data from L2 | Accepted PutM/PutAck and GetS/DATA_E transaction matching, L2 hit, no DRAM/owner stream, and independent dirty-data/Directory model |
| `directory.snoop_ack_retry_m_owner_core1` | `snoop_ack_l2_retry_m_owner_core1` | Core1's M line is replaced before its SnoopRead ACK; Core0 retries dirty data from L2 | Accepted PutM/PutAck and GetS/DATA_E transaction matching, L2 hit, no DRAM/owner stream, and independent dirty-data/Directory model |
| `cpu.same_line_dual_lane` | `same_line_dual_lane` | Both CPU lanes read then write disjoint bytes of one line concurrently | Independent byte-accurate scoreboard and final readback |
| `litmus.message_passing` | `litmus_message_passing` | Core0 completes DATA then READY stores; Core1 observes READY and the latest DATA on distinct lines | Independent byte-accurate MESI/data scoreboard and accepted Directory metadata monitor |
| `false_sharing.same_line` | `false_sharing_same_line` | Two cores repeatedly write different words in one 64-byte line | Independent data scoreboard, snoop/request monitor, and final word readback |
| `false_sharing.separate_lines` | `false_sharing_separate_lines` | Matched two-core write workload on distinct 64-byte lines | Independent data scoreboard and final word readback |
| `false_sharing.final_data` | `false_sharing_data_checked` | A/B cases preserve both final word values | Independent architectural data scoreboard |
| `litmus.generation_100` | `litmus_generation_counter_100` | 100 distinct DATA/READY/ACK generations complete without skip, duplicate consumption, or stale data | Independent scoreboard, generation sequence checker, and Directory monitor |
| `litmus.generation_backpressure` | `litmus_generation_backpressure` | Generation handshake remains correct with memory request/response gaps and CPU response stalls | Ready/valid driver checks, memory agent stall counters, and scoreboard |
| `cpu.seeded_random` | `randomized_seeded_regression` | Four reproducible mixed read/write seeds pass the independent model | Seeded Python sequence, byte-accurate MESI/data scoreboard and protocol error output |
| `cpu.random_dual_lane` | `random_dual_lane_pairs` | Seeded regression issues independent requests on both packed CPU lanes | Single dual-core driver and per-core response matching |
| `coherence.dirty_owner_fill_port` | `dirty_owner_snoop_during_l2_fill` | Both core directions transfer an M-owner line while an unrelated L2 refill is active | Eight-beat owner-data scoreboard, independent Directory model, and shared L2 write-port collision monitor |
| `directory.stale_upgrade_recovery` | `stale_upgrade_recovery` | A queued shared-copy Upgrade is invalidated by the winning peer Upgrade, then recovers ownership | Independent byte-accurate MESI model, accepted request/grant order, owner-data beats, and Directory commit monitor |
| `cross.cold_read_from_memory` | Cross: `I:from_I:read:core0:source_memory:l2_miss:snoop_none:beats_8` | Invalid L1 cold GetS from memory after an L2 miss, with no snoop and an eight-beat line transfer | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.remote_m_owner_read` | Cross: `I:from_M:read:core0:source_remote_owner:l2_hit:snoop_core1:beats_8` | Core0 GetS while Core1 owns M, sourced from the remote owner with an eight-beat transfer | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.remote_m_owner_read_core1` | Cross: `I:from_M:read:core1:source_remote_owner:l2_hit:snoop_core0:beats_8` | Core1 GetS while Core0 owns M, including an overlapping independent Directory context | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.shared_upgrade_snoop` | Cross: `S:from_S:write:core1:source_l1:l2_none:snoop_core0:beats_0` | Core1 S-to-M upgrade snoops Core0 without a line-data transfer | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.modified_hit_masked_store` | Cross: `M:from_I:write:core0:source_l1:l2_none:snoop_none:beats_0` | Core0 byte-masked M-hit store updates only selected byte lanes | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.l2_hit_after_l1_eviction` | Cross: `I:from_I:read:core0:source_shared_l2:l2_hit:snoop_none:beats_8` | L1-evicted line refills from shared L2 without a snoop | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.lookup_conflict_during_transfer` | Cross: `interleaving:active_transfer_distinct_address_ready_stall` | Another line request is blocked during an owner-transfer lookup while randomized memory ready stalls are active | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.lookup_conflict_during_grant` | Cross: `interleaving:active_grant_distinct_address_ready_stall` | Another line request is blocked during a grant lookup while randomized memory ready stalls are active | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.dirty_owner_waits_for_fill_port` | Cross: `interleaving:dirty_owner_waits_for_l2_fill_port` | Dirty owner writeback waits until the refill releases the shared L2 array port | CoherenceScoreboard MESI/data/Directory checks plus accepted request, snoop-beat, and Directory-commit monitor checks |
| `cross.message_passing` | Cross: `interleaving:message_passing_distinct_lines` | Ordered producer DATA/READY stores are observed by the consumer on separate lines | CoherenceScoreboard byte-accurate data/MESI checks, plus test-specific READY/ACK, address separation, and accepted transaction checks |
| `cross.false_sharing` | Cross: `interleaving:false_sharing_same_line_ping_pong` | Same-line different-word stores create ownership traffic absent from matched separate-line stores | CoherenceScoreboard byte-accurate data/MESI checks, plus test-specific READY/ACK, address separation, and accepted transaction checks |
| `cross.generation_counter` | Cross: `interleaving:data_ready_ack_100_generations` | 100 monotonic generations cross producer/consumer with legal backpressure | CoherenceScoreboard byte-accurate data/MESI checks, plus test-specific READY/ACK, address separation, and accepted transaction checks |
| `cross.mshr_two_context_memory_backpressure` | Cross: `interleaving:distinct_set_contexts_read_stalled` | Two different-set contexts remain allocated while memory request and response channels are stalled | Directory MSHR bank checker for context lifecycle, request/response ID routing, stable payloads, and progress under the stated fairness assumptions |
| `cross.replacement_put_s_snoop_core0` | Cross: `interleaving:put_s_snoop_core0` | Core0 PutS overlaps Core1 same-line GetM and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |
| `cross.replacement_put_s_snoop_core1` | Cross: `interleaving:put_s_snoop_core1` | Core1 PutS overlaps Core0 same-line GetM and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |
| `cross.replacement_put_e_snoop_core0` | Cross: `interleaving:put_e_snoop_core0` | Core0 PutE overlaps Core1 same-line GetS and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |
| `cross.replacement_put_e_snoop_core1` | Cross: `interleaving:put_e_snoop_core1` | Core1 PutE overlaps Core0 same-line GetS and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |
| `cross.replacement_put_m_snoop_core0` | Cross: `interleaving:put_m_snoop_core0` | Core0 dirty PutM overlaps Core1 same-line GetS and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |
| `cross.replacement_put_m_snoop_core1` | Cross: `interleaving:put_m_snoop_core1` | Core1 dirty PutM overlaps Core0 same-line GetS and reaches the replacement replay path | Independent replacement victim model, accepted Put/Snoop transaction monitor, and final MESI/data/Directory checks |

## Tool support and limits

- This run uses the workspace OSS CAD Suite Verilator 5.053 development build. The build requests line, branch, toggle, and FSM instrumentation; the merged native report is generated by verilator_coverage summary/hier.
- Branch points are reported only where Verilator elaborates a branch point. FSM extraction is experimental and conservative: 0 extracted state/arc points means N/A for this design/run, not 0% design FSM coverage.
- Verilator emitted a COVERIGN warning for one TB FSM whose state variable is assigned multiple times in a reset branch; that machine was not extracted. FSM percentages therefore cover only machines Verilator extracted, not every RTL/TB state variable.
- Toggle points may be absent for signals filtered by Verilator defaults (including underscore-prefixed signals unless coverage-underscore is enabled), unsupported/generated constructs, or signals optimized away. Report emitted points only; no denominator is inferred from RTL declarations.
- Hierarchy summaries collapse some hierarchy paths and are not precise per-instance results. The source/module table uses native point identity grouped by original source path.
- Product sources outside the selected simulation top or without executable coverage points are N/A. The AXI top, CSR and some uninstantiated wrappers require their own elaborated block run for meaningful runtime coverage.
- Branch/toggle/FSM instrumentation changes only measurement. Existing test commands, transaction sequences, and expected behavior are unchanged.

## Baseline interpretation

This report freezes the corrected counting boundary. Product RTL is exactly the set in Coherence.files.f, so source folders such as coherence/, interconnect/, common/, and bus/ cannot silently fall into Other. Testbench and Generated/Other records remain separate. Missed lines are reviewed individually and are not automatically waived.

PPA, physical SRAM mapping, timing signoff, and full-system CPU memory ordering are outside this coverage audit.
