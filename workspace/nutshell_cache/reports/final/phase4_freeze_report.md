# Phase 4 Final Closure Report

**Release Decision: OPEN. Full Code Coverage Sign-off 尚未完成。**

被测/本轮开始时 PR SHA：`69fdfe44f76d332e1e1664ee228d91f5b33886b0`。验证源码最后改动提交：`28fa00a331248035226fff48bb210b81f3b90677`。Source Fingerprint：`4914ae36cc57ff951c606e183ffb0f646b78bad4d94c3b28c3f8c69fe4ef7bb2`。报告 Commit 是包含本文件的实际 Git Commit；报告提交与被测源码区分。RTL 未修改。

## 实际验证增量

相对用户给出的 `461cc1e` Coverage基线（Raw归档标记为`3526950`；后续报告提交保留同一组计数），累计新增 **225 Raw Hit Point：60 Line、11 Branch、154 Toggle**；FSM State/Arc 无增量。所有 Point ID 均保留，无丢失命中，无跨 Top 计数。分类补测阶段单独新增93点（35 Line、3 Branch、55 Toggle）。

| Dataset | Line 前→后 | Branch 前→后 | Toggle 前→后 | FSM State 前→后 | FSM Arc 前→后 |
| --- | --- | --- | --- | --- | --- |
| axi_subsystem | 901/1068 → 901/1068 | 509/632 → 509/632 | 15623/32332 → 15623/32332 | 30/54 → 30/54 | 4/48 → 4/48 |
| bus_blocks | 67/68 → 67/68 | 70/76 → 70/76 | 1100/2450 → 1100/2450 | 0/0 → 0/0 | 0/0 → 0/0 |
| directory_controller | 149/182 → 178/182 | 33/42 → 37/42 | 255/612 → 260/612 | 10/10 → 10/10 | 3/9 → 3/9 |
| directory_mshr_bank | 167/286 → 167/286 | 100/128 → 100/128 | 1189/2904 → 1249/2904 | 31/40 → 31/40 | 11/36 → 11/36 |
| main_subsystem | 850/992 → 864/992 | 468/556 → 473/556 | 21887/27474 → 21923/27474 | 30/54 → 30/54 | 13/48 → 13/48 |
| mesi_l1_controller | 107/132 → 124/132 | 41/46 → 43/46 | 688/1804 → 741/1804 | 7/7 → 7/7 | 3/6 → 3/6 |
| shared_l2_directory_array | 75/79 → 75/79 | 65/74 → 65/74 | 197/1778 → 197/1778 | 0/0 → 0/0 | 0/0 → 0/0 |
| shared_line_engine | 101/104 → 101/104 | 44/52 → 44/52 | 304/648 → 304/648 | 0/0 → 0/0 | 0/0 → 0/0 |

Raw点74831，命中45132→45357，Zero29699→29474；非Toggle940→869，Toggle28759→28605。分母不变。45357个命中全部RAW_COVERED机器核验，未核验0，Manifest错误0。Raw Attestation只证明执行，不能替代功能Checker。

精确差异：`freeze/phase4_baseline_point_diff.csv.gz` 和 `freeze/triage_baseline_point_diff.csv.gz`。8个Top的原始文件/哈希：`freeze/raw_archive.json`、`freeze/dataset_manifest.json`。

## 剩余代码分类与处置

| 类别 | 有证据的数量 | 处置 |
| --- | ---: | --- |
| 可用定向测试覆盖 | 93 | 本轮已实际命中；不代表其余点不可测 |
| 结构固定的Waiver候选 | 60 | 独立Directory Top的5个地址信号低6位、两个方向；归纳恒零证明，待独立审核 |
| 确认可删除的死代码 | 0 | 未有全实例可达性/等价证据，不删防御逻辑 |
| 证据不足，继续分析 | 29414 | 逐点OPEN，不强行归入前三类 |

当前29474个零点=60个待审核候选+29414个证据不足点。批准Waiver/Unreachable排除均为0，审核主体为空；Reviewed Eligible Coverage未计算。低活动度不能当作Constant。FSM default正常不可达也不能据此删除防御逻辑。

Toggle工作队列：`{'UNCLASSIFIED': 3280, 'ADDRESS_TAG': 20601, 'DATA': 3717, 'TRANSACTION_CONTEXT_ID': 732, 'BYTE_MASK': 176, 'FSM_ENCODING': 99}`；仅按信号用途安排工作，不代表不可达或豁免。Top/Instance/Signal/Bit/Direction及控制条件逐点保留于`freeze/zero_point_review.csv.gz`。

## 控制路径与仍OPEN风险

- Main新增脏Owner替换与对端GetS时序交叠，实际观察Owner-missing Retry、Snoop Tag Miss，检查脏数据/整行和最终MESI。无内部Force。
- Directory新增唯一Owner Upgrade、非Owner PutS、三种保留SnoopResponse注入，检查精确错误码及fail-stop；L1新增本地命中、无Tag Snoop、意外PutAck和异常metadata，检查响应、反压稳定和无成功副作用。
- MSHR独立Top增加Context1/2/3与Context0的Offer Lock竞争；不能代替Main Context2/3义务。
- Main Context2/3须3/4个同时存活请求；两路阻塞L1通常仅两个所有权请求，额外Put bypass交叠尚缺集成可达性证明。
- ENGINE_GRANT_READ须接受Grant时L2读端口不Ready；Main Engine占用与L2 busy区间可能互斥，Block虽可达，Main结构不变量仍待证明。
- 仍缺部分合法Directory Put/Upgrade/recovery组合、L1 metadata/replacement/snoop竞态、集成错误生产者不变量、Reset/FSM arcs及逐位Toggle证据。

Reachability条件研究：`freeze/reachability_study.md`。所有未解决项OPEN；源码分析不是独立批准。

## Formal边界

- Directory FSM编码及5个地址低6位恒零：Inductive Proof PASS，初始两拍Reset后接口输入任意，无地址/协议输入约束。只支持所列性质。
- Directory事务记账、coherent metadata、Reset取消：Bounded Safety PASS depth24。
- MSHR Allocate/Retire及Reset一致性：Bounded Safety PASS depth12，保留合法opcode/metadata前提；不能覆盖任意非法环境。
- 可选Directory事务归纳探索：UNKNOWN，basecase通过而归纳未完成，不能宣称unbounded协议证明。

当前Formal日志、配置哈希及Assumption/Guarantee边界：`freeze/formal_evidence.json`；历史可选探索：`phase4/formal_exploration.json`。性质到Point候选映射：`freeze/formal_point_mapping.csv.gz`；60个精确恒零Point映射及空审批记录：`freeze/triage_waiver_candidates.json`。没有因此自动排除任何点。

## 回归与发布范围

八项目标实际全部PASS：coherence_verify、coherence_full_system_verify、coherence_hit_under_miss、coherence_full_system_cross_closure、coherence_full_system_stress、coherence_coverage_audit、coherence_full_system_evidence_gate、coherence_full_system_replay_closure。Functional53/53、Cross35/35、Stress280/280、Cross Closure21/21、Hit-under-Miss3/3、Replay1/1。Full-System Verify70 passed/1 skipped；skip未算作通过。

`coherence_release_gate`实际OPEN，make退出2（gate程序退出1），29474条发现全部是Required零点尚未处置；无额外hash/identity/regression问题。最终Gate单元测试19/19。日志/退出码：`reports/closure/rtl_release_gate_status.json`、`.log.gz`；逐目标指纹/日志SHA：`verification_run_manifest.json`、`freeze/regression_status.json`。当前verification_signoff已统一为8/8回归PASS，代码签核单独OPEN。

**Functional Verification Release Candidate：仅提出供独立审核**，范围为现有RTL v1.1双核CPU/MMIO/APB/AXI四Agent平台及53/35已声明Checked Plan、280Seed回归、明确有界Formal。不能宣称全部RTL路径或Toggle收敛、Main Context2/3可达或协议全局归纳安全。Reviewed RTL Code Coverage尚未完成，Full Code Coverage Sign-off OPEN。

PR：https://github.com/cwu766485-ctrl/open_verif_learning/pull/1 。被测SHA `69fdfe44f76d332e1e1664ee228d91f5b33886b0` 的两项Actions均success：

- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42794686673
- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42794679720

上述CI属于被测SHA；报告提交的新CI以PR当前HEAD单独核对。未合并、未创建Release Tag。
