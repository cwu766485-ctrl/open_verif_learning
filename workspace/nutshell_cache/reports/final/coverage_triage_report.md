# 剩余 RTL Coverage 分类与实际收敛

结论：不能把所有未命中点强行归为“可补测、无意义、可删除”。本轮逐点分析保留证据不足队列；分类不修改分母、不自动 Waive、不删除防御逻辑。

基线：Phase4 PR `b738ac6`，29,567 Zero Points（907 非 Toggle、28,660 Toggle）。本轮测试源码：`28fa00a331248035226fff48bb210b81f3b90677`。RTL 源码未改。报告提交与测试源码分开。

| 类别 | 有证据的数量 | 本轮处置 |
| --- | ---: | --- |
| 1 可通过定向测试覆盖 | 93 点 | 已实际命中：35 Line、3 Branch、55 Toggle |
| 2 结构固定、无需追求翻转的 Waiver 候选 | 60 点 | 5 个 Directory 行地址信号×6 低位×2 方向；归纳证明通过，待独立审核 |
| 3 已确认可直接删除的死代码 | 0 点 | 未发现充分证据支持删除 |
| 尚不能判定 | 29,414 点 | 逐点 OPEN，继续具体条件分析/测试/证明 |

数字是不同 Top 的独立覆盖义务总数，不是代码行数或可合并覆盖百分比。第1类只统计本轮已验证可测的点，不能理解为其他点不可测。第2类是逐点审核候选，已批准 Waiver 数为0。第3类为0不表示所有剩余代码都可达。

## 1 可测路径与新增测试

Directory Block 新增唯一 Owner 的合法 Upgrade、非 Owner PutS 错误以及三种保留 Snoop Response 编码注入。检查精确错误码、无 metadata/grant/xfer 成功副作用、持续 fail-stop。实际新增18 Line、1 Branch、2 Toggle。

L1 Controller Block 新增本地读命中、M 状态写命中、命中但 MESI_I 的异常 lookup、误收 PutAck，以及缺失 Tag 的 SnoopRead/Invalidate。检查响应地址/操作、无目录请求、异常抑制成功、无伪造数据或 metadata 写入、响应反压稳定性。实际新增17 Line、2 Branch、53 Toggle。

| Dataset | Metric | 基线 | 本轮 |
| --- | --- | ---: | ---: |
| directory_controller | Line | 160/182 | 178/182 |
| directory_controller | Branch | 36/42 | 37/42 |
| directory_controller | Toggle | 258/612 | 260/612 |
| mesi_l1_controller | Line | 107/132 | 124/132 |
| mesi_l1_controller | Branch | 41/46 | 43/46 |
| mesi_l1_controller | Toggle | 688/1804 | 741/1804 |

FSM计数不变；其他Top未获得上述Block命中转记。Raw总命中45,264→45,357，Zero29,567→29,474。分母74,831不变。

## 2 Waiver 候选的依据与范围

DirectoryController的 `line_addr_q` 每次只捕获 `line_align(req_line_addr)`，reset置零。`dir_write_line_addr`、`snoop_req_line_addr`、`line_xfer_addr`、`grant_line_addr` 都直接来自这个对齐寄存器。因此低6位不需要翻转，强行激励也违反结构定义。

本轮在原无接口约束Formal Harness中加入五个信号低6位恒零断言，`coherence_directory_unconstrained.sby` 的 k-induction PASS。初始两拍reset、随后所有端口自由；未加入地址约束。这支持60个Standalone Directory Toggle候选，不支持自动排除Main/AXI实例或其他地址信号。

逐点理由、风险、空审批者见 `triage/waiver_candidates.json`；审批状态PENDING_INDEPENDENT_REVIEW，release_exclusion=false。风险边界：不含内部寄存器位翻转故障模型。现有Release Ledger未添加任何批准记录，Eligible Coverage不计算。

## 3 为什么没有删除所谓死代码

FSM default/error路径属于有意的防御行为。正常reset后的FSM编码不可达证明，只说明当前状态转移不会进入非法编码，不能证明删除错误恢复逻辑在故障模型和维护范围内无风险。共享Block中某路径在Main集成连接下不可达，也不等于模块内全局死代码。

例如SharedLineEngine的ENGINE_GRANT_READ在Block端口反压下可达，而Main的单读端口/engine仲裁限制可能使它无法触发；不能为了Main比例删除共享实现。所有此类项继续OPEN，若要删除应有全实例不可达性、输出无影响或等价证明和明确设计审查。

## 待确认清单与下一步

`triage/baseline_zero_triage.csv.gz` 覆盖全部29,567个基线零点，保留Point ID、Top、源码、Metric、原生身份、分类依据与当前处置。`pending_by_dataset.json`按Dataset/Metric列出29,414个待确认点。

优先继续：DirectoryMshrBank的119个Line缺口中包含合法GetM/Upgrade/Put与不同Context组合，适合扩展Block合法场景；Main/AXI剩余控制缺口需要分别研究集成阻塞及故障传播；Toggle大部分地址/数据/ID/状态位仍缺逐位约束或驱动证据，不能按信号名批量Waive。

## 验证与签核

实际运行 `coherence_directory`、`coherence_l1_controller`、完整独立Block覆盖采集脚本（7个Top）全部PASS；对齐/编码Formal归纳PASS；新分类单元测试2/2，Release Gate单元测试19/19。

本轮未重跑八项目标Full Regression。旧53/53、35/35、280/280属于Phase4源码历史证据，不冒充本轮签核。Release Gate实际运行，make退出2、状态OPEN；当前全部Raw Hit因新测试源码未完成全组回归而暂未自动核验，保留Fail-Closed。

各类Raw Coverage是实际执行增量；不是新的全系统或Full Code Coverage签核。当前结论OPEN。

日志、Raw文件和哈希：`triage/evidence_hashes.json`；Formal：`triage/alignment_proof.log.gz`；Gate退出/日志：`triage/release_gate_status.json`。所有可复现输入都在源码提交，独立审核批准数0。
