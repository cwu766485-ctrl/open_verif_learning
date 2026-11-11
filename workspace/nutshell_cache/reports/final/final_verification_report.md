# NutShell Cache v1.1 Final Verification Freeze

**Functional Verification Release Candidate: OPEN**  
**Full RTL Code Coverage Sign-off: OPEN**

被测 Source SHA：`e0b087c44e9131d2eb9ca7cbf0193e82bb18a22c`；Source Fingerprint：`a732ce942f791cc7ad3c2270ad31309d520b021e9997937ead656f2e9359776e`；RTL Fingerprint：`15798323c27cd473bf3d70a70b66b7cb39620c5abd2682a39e22512ac6794d6a`。报告 SHA 为包含本文件的实际 Git 提交，与被测源码提交区分。未修改 RTL、架构、Required 义务或覆盖率分母。

## 最终回归

八项完整回归 8/8 PASS。Functional 53/53、Cross 35/35、Stress 280/280（25分22秒）；Cross Closure 21/21、Hit-under-Miss 3/3、Replay 1/1。Evidence Gate 核验当前 Source SHA。`coherence_verify` 包含既有 Formal、Mutation 与模块/系统验证，新 L1 属性已纳入必需 Formal。

Release Gate 实际 **OPEN**，make 退出 **2**，程序退出1；Gate单元测试19/19。45365个原始命中全部核验，未核验0；29466个Required零点仍OPEN。未忽略失败退出，未计算未经审核的Eligible Coverage。

## 五类风险的实际结论

| 风险 | Stimulus / Proof → DUT / Checker | 结论与最小剩余任务 |
| --- | --- | --- |
| Directory Context2/3集成 | 既有双向Owner替换与时序扫描，实际MSHR峰值2，slot2/3未活动；Block四Context Cover独立保留 | OPEN：需要组合实际L1/仲裁器/MSHR证明集成上限，或合法slot2/3分配及Retire反例 |
| GrantRead × L2 Busy | 实际Engine+模型化L2控制递推k-induction PASS；Main运行时Grant Ready检查PASS | 候选不可达，待连线/模型对应独立审核；新增实际L2+Engine证明被Slang数组混合赋值限制阻塞，TOOL ERROR，不是证明 |
| Dirty Victim Error / Producer | 既有真实BRESP错误→8拍fail-stop→reset→core1独立数据/MESI恢复检查PASS；新增实际L1 Controller+Snoop Arbiter归纳PASS | L1已接受CPU/Snoop事务ID来源、输出关联、编码和Reset清理已证明；Snoop Beat/Last仅证明转发输入，未证明输入合法。其余Array/AXI/Refill Producer不变量OPEN |
| Owner-missing Retry方向/Timing | 两方向×offset0..9，实际每方向2次Retry，独立数据/MESI检查PASS | 有限扫描范围PASS，不扩展随机场景 |
| Reset/Fatal/Resource Arc | 既有七种实际暂态Reset及FINISH Reset、恢复读检查PASS；新增L1编码/Reset归纳PASS | 未达Context/实例源状态及FSM Arc仍OPEN，需逐状态可达性判定 |

完整既有Stimulus/Event/Checker链见`final_freeze/five_boundary_evidence.json`、逐点映射`final_freeze/boundary_point_mapping.csv.gz`。这些历史刺激在本次当前源码回归中重新执行；新增L1逐点范围关联见`continued_freeze/l1_property_point_scope_mapping.json`（仅范围关联，零点均OPEN，不声称逐点不可达）。新增证明边界见`formal/freeze_l1_producer_scope.md`。不将ID证明推广为全协议安全、活性或全系统签核。

## 代码覆盖率与未覆盖代码

详见 [代码覆盖率报告](code_coverage_report.md)：各Dataset、Main各模块、零命中源码行范围。逐点CSV保留Top、Source、条件、实例/位/方向、Point ID和Source/Dataset/Raw Hash。

| 范围 | Line | Branch | Toggle | FSM State | FSM Arc |
| --- | --- | --- | --- | --- | --- |
| Main 本次前→后 | 864/992→864/992 | 473/556→473/556 | 21931/27474→21931/27474 | 30/54→30/54 | 13/48→13/48 |
| Main 零点 | 128 | 83 | 5543 | 24 | 35 |
| 全部8个独立Dataset零点 | 434 | 265 | 28597 | 57 | 113 |

总74831点，Raw Hit45365，Zero29466（非Toggle869）。本次新增Raw Hit **0**，丢失 **0**，全部8份原始文件与前一轮逐字节相同；每Dataset前后比较见`continued_freeze/coverage_comparison.json`。相对最初200d268归档的前一轮实际新增8个Main Toggle独立保留，不能重复计作本次增量。

Line/Branch/FSM没有增加的原因：已有Retry/Reset测试重复走已执行源码；Context2/3尚未集成分配；GrantRead Busy是结构证明研究而非命中；内部错误guard需要完整Producer不变量。Block命中未转记Main。

处置分类保持保守：合法可达缺口必须补同Top检查测试；明确错误赋值单列Illegal/Defensive；其余不足以判定的点标UNRESOLVED，不能根据低活动度批准Waiver或删除代码。现有分类候选见`final_freeze/review_matrix.csv.gz`（97结构候选、123错误处理、29246未决，均未排除）；当前逐点源码/哈希见`code_coverage/uncovered_points.csv.gz`。**没有已证明可直接删除的死代码，没有批准Waiver。**

## Formal与审核

- 新`freeze_l1_producer`：实际未修改L1 RTL，初始两拍Reset，随后任意输入及任意后续Reset，无协议假设；独立已接受请求ID模型及断言式归纳引理，k-induction PASS。范围不含输入Beat合法性、AXI匹配或Context容量。
- `freeze_read_port`：实际Engine与模型化L2递推组合归纳PASS，对应关系仍待审核。
- `freeze_actual_l2_read_port`：实际生产参数L2数组因前端拒绝blocking reset/nonblocking runtime混用而TOOL ERROR；保留配置及失败日志，不改RTL绕过问题。
- Directory编码/低位对齐归纳PASS；Directory事务depth24、MSHR depth12为有界安全PASS；历史可选事务归纳UNKNOWN仍UNKNOWN。

60个Standalone Directory低位Toggle候选已重新核对逐点身份、源码Hash、当前Dataset/Raw Hash及新Formal日志：`continued_freeze/waiver_review_submission.json`。独立审批者null，PENDING，实际排除0。不将候选当作已批准Unreachable。

## 冻结决定与交付

Context2/3集成边界、其余Producer安全及未达FSM源状态仍需最小证明/合法测试，因此功能候选与完整代码签核均 **OPEN**。停止新增随机场景和架构扩展；现有53/35功能计划回归切片已通过，可供有限范围审核，但本报告不宣布冻结批准。

当前证据：`continued_freeze/dataset_manifest.json`、`raw_archive.json`、`formal_evidence.json`、`regression_status.json`、`evidence_hashes.json`；`verification_run_manifest.json`。日志与原始数据压缩归档，SHA256按解压内容核验。报告提交只包含证据，不改变被测源码。

被测源码CI均success：

- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42943297869
- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42943288219

PR：https://github.com/cwu766485-ctrl/open_verif_learning/pull/1 。报告提交CI另查其实际HEAD，不能借用源码CI。未合并、未创建正式Tag。
