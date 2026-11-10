# NutShell Cache v1.1 Final Verification Freeze

**Functional Verification Release Candidate: OPEN**  
**Full RTL Code Coverage Sign-off: OPEN**

被测 Source / PR SHA：`b383383abea773decff022c149b7e767fb2df827`；Source Fingerprint：`819b8656e469947612ac43bbe740800ce09b1014cb9529e82eddb14c1ff2ae47`；Product RTL Fingerprint：`15798323c27cd473bf3d70a70b66b7cb39620c5abd2682a39e22512ac6794d6a`。报告 SHA 为包含本文件的实际提交。RTL未改，微架构与Required义务冻结。

## 五类风险结果

| 风险 | 本轮证据 | 结论 |
| --- | --- | --- |
| Main Context2/3 | 双向替换/请求时间扫描，峰值2，slot2/3未活动；Block四Context Cover独立保留 | OPEN：未得到集成上限证明或合法反例 |
| Grant Read × L2 Busy | 实际Engine+L2控制递推组合，k-induction PASS；实际Main连续读端口检查通过 | 结构不可达候选；连线对应待独立审查，不自动排除 |
| Dirty Victim AXI BRESP Error | 错误、8拍fail-stop、Reset无旧响应、Core1恢复读PASS；写回ID/Beat/Last连续检查 | 错误场景PASS，完整Producer归纳安全仍OPEN |
| Owner-missing Retry方向/Timing | 两个owner方向×offset0..9；每方向观察2次Retry，数据与MESI检查PASS | 固定扫描范围PASS |
| Reset/Fatal/Resource Arc | 增加FINISH Reset，七种实际暂态Reset及恢复PASS；错误恢复与冲突回归PASS | 部分完成；未达实例/状态Arc OPEN |

逐点映射：`final_freeze/boundary_point_mapping.csv.gz`；合法行为后续清单：`final_freeze/legal_behavior_followup.json`。

完整 `RTL Condition → Stimulus/Proof → DUT Event → Independent Checker → Coverage Point → Evidence` 链及最小后续任务：`final_freeze/five_boundary_evidence.json`。未将运行时安全观察写为无界证明，未将组合式归纳写成全Top协议证明。

## Raw Coverage变化

| Dataset | Line 前→后 | Branch 前→后 | Toggle 前→后 | FSM State 前→后 | FSM Arc 前→后 |
| --- | --- | --- | --- | --- | --- |
| main_subsystem | 864/992 → 864/992 | 473/556 → 473/556 | 21923/27474 → 21931/27474 | 30/54 → 30/54 | 13/48 → 13/48 |
| axi_subsystem | 901/1068 → 901/1068 | 509/632 → 509/632 | 15623/32332 → 15623/32332 | 30/54 → 30/54 | 4/48 → 4/48 |
| directory_controller | 178/182 → 178/182 | 37/42 → 37/42 | 260/612 → 260/612 | 10/10 → 10/10 | 3/9 → 3/9 |
| directory_mshr_bank | 167/286 → 167/286 | 100/128 → 100/128 | 1249/2904 → 1249/2904 | 31/40 → 31/40 | 11/36 → 11/36 |
| shared_line_engine | 101/104 → 101/104 | 44/52 → 44/52 | 304/648 → 304/648 | 0/0 → 0/0 | 0/0 → 0/0 |
| mesi_l1_controller | 124/132 → 124/132 | 43/46 → 43/46 | 741/1804 → 741/1804 | 7/7 → 7/7 | 3/6 → 3/6 |
| shared_l2_directory_array | 75/79 → 75/79 | 65/74 → 65/74 | 197/1778 → 197/1778 | 0/0 → 0/0 | 0/0 → 0/0 |
| bus_blocks | 67/68 → 67/68 | 70/76 → 70/76 | 1100/2450 → 1100/2450 | 0/0 → 0/0 | 0/0 → 0/0 |

本轮相对200d268归档：新增8个Main Toggle，Line/Branch/FSM均0增量，0丢失命中，Point总数74831不变。Raw Hit 45365，全部自动核验45365，未核验0。Zero 29466（非Toggle869，Toggle28597）。

Main仍128 Line、83 Branch、24 FSM State、35 FSM Arc。合法控制路径无新增Line/Branch的原因：双向Retry与FINISH Reset执行的是已有源码路径；Context2/3无真实分配；GrantRead得到组合式结构证明而不是刺激命中；内部错误guard未由合法Producer触发，完整不变量尚缺。独立Top已有命中不转记Main。

当前逐点复核：`final_freeze/review_matrix.csv.gz`，97个结构不可达候选、123个明确错误处理点、29246个仍未充分判定点；全部OPEN。Main控制270点中13个证明候选、47个错误处理点、210个未决。分类保守：未因信号名/未命中推断Constant；未决中可能包含合法可达行为，不能当作无风险。完整差异`final_freeze/freeze_baseline_point_diff.csv.gz`；原始档案与哈希`raw_archive.json`。

Tool/Instrumentation Limited：不同Top及原生FSM提取范围分开保留。新增Reset执行未增加原生Arc不能单独证明工具错误；相关Arc继续OPEN。未新增无证据的Tool Waiver。

## Formal与独立审查

新Read-Port组合式k-induction PASS；编码/对齐归纳PASS；Directory事务depth24和MSHR depth12有界PASS；既有可选事务归纳UNKNOWN保留。假设/保证边界见`formal/freeze_read_port_scope.md`及`final_freeze/formal_evidence.json`。初轮独立Beat抽象反例保留；它是Harness抽象错误，不宣称RTL缺陷。

60个Standalone Directory低6位Toggle候选已逐点核对Source Hash、Point身份、当前Raw/Dataset Hash和最新Formal PASS：`final_freeze/waiver_review_submission.json`。以PR仓库附件提交审查，审批者null，PENDING_INDEPENDENT_REVIEW。批准Waiver/Unreachable排除0，不改分母；Reviewed Eligible Coverage不计算。没有冒充独立审核。

## 最终回归与冻结决定

八项目标实际8/8 PASS；Functional53/53、Cross35/35、Stress280/280（41分17秒）；Cross Closure21/21，Hit-under-Miss3/3，Replay1/1。Full-System Verify70passed/1skipped；skip不计PASS。Formal、Mutation及现有Checker Infrastructure保留。

Release Gate实际OPEN，make退出2（程序退出1），29466条发现均为Required零点未处置；Manifest错误0，没有忽略非零退出。Gate单元测试19/19。当前标准签核报告已刷新8/8回归状态；代码签核仍OPEN。

**停止扩展测试/架构，提交冻结审查包，暂不宣布冻结候选通过。** Context2/3边界、完整内部Producer Safety和未达FSM源状态仍需最小证明/合法测试任务，见`remaining_risks.md`。现有53/35功能计划的回归切片通过可供审核，但不能代表全部高风险合法行为已验证。

被测SHA的CI均success：

- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42844588610
- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42844268091

PR #1：https://github.com/cwu766485-ctrl/open_verif_learning/pull/1。报告提交CI需按新HEAD另查，不借用被测源码CI。未合并、未创建Tag。Evidence Hash：`final_freeze/evidence_hashes.json`；Source/Dataset身份：`dataset_manifest.json`；完整回归日志哈希：`regression_status.json`。
