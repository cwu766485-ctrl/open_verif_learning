# NutShell Cache v1.1 代码覆盖率报告

**Full RTL Code Coverage Sign-off: OPEN。**
Source Commit：`0e852178ee2fedb5cdf414846cf3920b62a92139`；Source Fingerprint：`5f3c2f4f370989a29608f161504d076d6082523d0302e19ed3baac9ef1bf860a`。

Raw Point总数74831；命中45365；未命中29466。这是独立Top覆盖义务的统计，不是去重后的源码行数或合并覆盖率。

未命中指标：`{'branch': 265, 'fsm_arc': 113, 'fsm_state': 57, 'line': 434, 'toggle': 28597}`。没有改变分母，没有已批准排除；Reviewed Eligible Coverage未计算。

## 各独立数据集 Raw Coverage

| Dataset / Top | Line | Branch | Toggle | FSM State | FSM Arc |
| --- | --- | --- | --- | --- | --- |
| main_subsystem / CoherentCacheSubsystem_tb | 864/992 | 473/556 | 21931/27474 | 30/54 | 13/48 |
| axi_subsystem / CoherentCacheAxiSubsystem_tb | 901/1068 | 509/632 | 15623/32332 | 30/54 | 4/48 |
| directory_controller / DirectoryController_tb | 178/182 | 37/42 | 260/612 | 10/10 | 3/9 |
| directory_mshr_bank / DirectoryMshrBank_tb | 167/286 | 100/128 | 1249/2904 | 31/40 | 11/36 |
| shared_line_engine / SharedLineEngine_tb | 101/104 | 44/52 | 304/648 | 0/0 | 0/0 |
| mesi_l1_controller / MesiL1Controller_tb | 124/132 | 43/46 | 741/1804 | 7/7 | 3/6 |
| shared_l2_directory_array / SharedL2DirectoryArray_tb | 75/79 | 65/74 | 197/1778 | 0/0 | 0/0 |
| bus_blocks / CacheBusBlocks_tb | 67/68 | 70/76 | 1100/2450 | 0/0 | 0/0 |

## Main Top未覆盖代码按模块统计

下表每项为零点数，模块名相同但实例不同的FSM/Branch义务仍保留在CSV中。

| RTL Source | Line | Branch | Toggle | FSM State | FSM Arc |
| --- | ---: | ---: | ---: | ---: | ---: |
| rtl/bus/axi/MemoryRefillMshrBank.sv | 0 | 2 | 293 | 0 | 0 |
| rtl/cluster/DualL1MesiCluster.sv | 3 | 9 | 950 | 0 | 0 |
| rtl/coherence/SharedLineEngine.sv | 31 | 16 | 139 | 0 | 0 |
| rtl/directory/DirectoryController.sv | 57 | 12 | 91 | 22 | 27 |
| rtl/directory/DirectoryMshrBank.sv | 10 | 13 | 1363 | 0 | 0 |
| rtl/interconnect/CoherenceRequestArbiter.sv | 0 | 0 | 64 | 0 | 0 |
| rtl/interconnect/CoherenceRequestArbiterCore.sv | 0 | 0 | 38 | 0 | 0 |
| rtl/interconnect/CpuMmioRouter.sv | 3 | 2 | 264 | 0 | 0 |
| rtl/interconnect/L2LineWriteArbiter.sv | 0 | 0 | 100 | 0 | 0 |
| rtl/l1/MesiL1Array.sv | 0 | 8 | 605 | 0 | 0 |
| rtl/l1/MesiL1Controller.sv | 20 | 14 | 132 | 2 | 8 |
| rtl/l1/MesiL1SnoopArbiter.sv | 0 | 0 | 42 | 0 | 0 |
| rtl/l2/SharedL2DirectoryArray.sv | 4 | 7 | 228 | 0 | 0 |
| rtl/top/CoherentCacheSubsystem.sv | 0 | 0 | 1234 | 0 | 0 |

## 哪些源码行没有执行

以下范围均是LCOV零命中行，仅适用于列出的Dataset。Branch/FSM缺口另有原生Point ID，不能从行覆盖推断关闭。

| Dataset | RTL Source | 未覆盖源码行 |
| --- | --- | --- |
| axi_subsystem | rtl/bus/apb/CachePerformanceCsr.sv | 68, 75-77 |
| axi_subsystem | rtl/bus/axi/LineMemoryAxi4Adapter.sv | 312 |
| axi_subsystem | rtl/cluster/DualL1MesiCluster.sv | 419-422, 425-427, 472-474 |
| axi_subsystem | rtl/coherence/SharedLineEngine.sv | 133-139, 141-143, 182-184, 191-193, 232-235, 246-248, 250-251, 276, 278-280, 331-334, 348, 364, 366-368 |
| axi_subsystem | rtl/directory/DirectoryController.sv | 238-241, 299-302, 329, 353, 358-360, 362-365, 384-385, 388-397, 409-414, 434-437, 463, 466, 471-474, 479-489, 491-494, 497-500, 525, 527-530 |
| axi_subsystem | rtl/directory/DirectoryMshrBank.sv | 339-341, 348-350, 362-365, 372-374 |
| axi_subsystem | rtl/interconnect/CpuMmioRouter.sv | 152, 156, 162-164 |
| axi_subsystem | rtl/l1/MesiL1Controller.sv | 254-256, 287-289, 317-318, 345, 347-349, 365-366, 368, 394-395, 439-440, 454, 456-458 |
| axi_subsystem | rtl/l2/SharedL2DirectoryArray.sv | 313-314, 326-327 |
| bus_blocks | rtl/bus/apb/CachePerformanceCsr.sv | 77 |
| directory_controller | rtl/directory/DirectoryController.sv | 527-530 |
| directory_mshr_bank | rtl/directory/DirectoryController.sv | 215-221, 238-241, 246-255, 257-267, 270, 299-302, 307-311, 329, 353, 358-360, 362-365, 370-372, 384-385, 388-397, 401-414, 418-419, 434-437, 463, 466, 471-474, 479-489, 491-495, 497-503, 527-530 |
| main_subsystem | rtl/cluster/DualL1MesiCluster.sv | 472-474 |
| main_subsystem | rtl/coherence/SharedLineEngine.sv | 133-135, 141-143, 182-184, 191-193, 232-235, 246-248, 276, 278-280, 331-334, 348, 366-368 |
| main_subsystem | rtl/directory/DirectoryController.sv | 238-241, 299-302, 353, 358-360, 362-365, 384-385, 388-397, 409-414, 434-437, 484-489, 491-494, 497-500, 525, 527-530 |
| main_subsystem | rtl/directory/DirectoryMshrBank.sv | 339-341, 362-365, 372-374 |
| main_subsystem | rtl/interconnect/CpuMmioRouter.sv | 162-164 |
| main_subsystem | rtl/l1/MesiL1Controller.sv | 254-256, 287-289, 317-318, 345, 347-349, 394-395, 439-440, 454, 456-458 |
| main_subsystem | rtl/l2/SharedL2DirectoryArray.sv | 313-314, 326-327 |
| mesi_l1_controller | rtl/l1/MesiL1Controller.sv | 347-349, 394-395, 456-458 |
| shared_l2_directory_array | rtl/l2/SharedL2DirectoryArray.sv | 214-215, 313-314 |
| shared_line_engine | rtl/coherence/SharedLineEngine.sv | 366-368 |

## 处置边界

- Legal Reachable：必须由实际同Top刺激、DUT事件与独立Checker证明；未决点不自动归为不可测。
- Illegal Protocol/Defensive：明确错误赋值已单列，仍需逐路径Fault Injection或Producer Safety；不能删除防御逻辑。
- Structurally Unreachable：L1 ID/编码/Reset和读端口组合证明的具体边界见final_verification_report.md；证明候选与审批分开，不自动减分母。
- Tool Limited：实际L2+Engine Formal因数组混合赋值前端限制无法展开，保留配置及失败日志；不等于不可达。
- Unresolved：Context2/3、剩余Producer与FSM源状态保持OPEN；Toggle不要求无依据地全部翻转。

60个Directory低位候选的当前哈希及独立审批状态见`../final_freeze/waiver_review_submission.json`；未批准。

## 逐点文件与证据

- `code_coverage/main_uncovered_control_points.csv`：Main每个Line/Branch/FSM缺口，包含源码条件、原生身份、Point ID与哈希。
- `code_coverage/uncovered_control_points.csv`：全部8个Dataset的非Toggle零点。
- `code_coverage/uncovered_points.csv.gz`：全部零点，包含Toggle原生实例/信号/位/方向身份。
- `code_coverage/module_summary.json`：每Dataset×Source×Metric的分子、分母和零点数。
- `code_coverage/dataset_manifest.json`：Source/Top/Dataset/Raw Hash与验证契约。
- `final_verification_report.md`及`remaining_risks.md`：当前签核、五类边界证据和最小剩余任务。

本报告只统计当前Raw事实和待办，不冒充独立审查批准。Raw Hit核验和回归状态以当前Release Gate证据为准。
