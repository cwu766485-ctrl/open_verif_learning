# NutShell Cache v1.1 — Final DV Proof & Release Decision

**Functional Verification Release Candidate: OPEN**  
**Full RTL Code Coverage Sign-off: OPEN**

Baseline `b95d7d9c8548d2f478443b8a15a6c2d147c61f7c`。被测Source SHA：`36303f48fc21f5aae655c6a2701360a13bca5480`；Source Fingerprint：`7f62dfc4c618f229f5745de358a62b2e0387639638f79aee3527da8c01bc6509`；RTL Fingerprint：`15798323c27cd473bf3d70a70b66b7cb39620c5abd2682a39e22512ac6794d6a`。报告SHA为包含此文件的实际Git提交；验证源码与报告提交分开。不改产品RTL、架构、随机规模、Required义务或覆盖分母。

## A — Context2/3

新增`final_context_reachability.sby`实例化实际完整Main，保留两套L1、Replacement Put Bypass、实际Arbiter、DirectoryMshrBank和全部Snoop/Grant路径。没有活动Context≤2假设。Cover实际slot2/3 active位。前端在生产参数L2的循环展开及blocking reset/nonblocking runtime数组赋值处ERROR，未进入Cover求解。**TOOL_LIMITED / OPEN**，没有Witness，也没有不可达结论。探索输入任意，即便未来得到Witness仍须先检查源端合法性，再转Directed Test。本轮没有伪造测试。

最小剩余任务：支持实际阵列的前端或经独立审核的资源控制抽取，保留Put旁路后证明容量上限或取得合法Allocate→Grant→Retire的slot2/3 Witness。历史观测峰值2不是证明。

## B — Grant Read × Busy

新增源码提取器`extract_final_l2_read_control.py --check`：从实际L2保留读接受优先级、hit→busy、beat0、Stall保持、Beat7退休和Reset；校验实际输出/Reset语句，删除只选择数据的Set/Way赋值。hit仍任意。`final_read_port`将此控制切片与实际SharedLineEngine组合，保留Main的Grant Ready、Victim/Grant读仲裁和Stream Ready关系，**k-induction PASS**。

相较旧手写递推，当前控制切片可自动核对Source Hash。它仍不是实际完整Top等价证书：提取非干涉与路由对应需独立审核。**PROOF CANDIDATE / OPEN**，不自动标PROVEN_UNREACHABLE。实际L2前端限制仍保留证据。

## C — Producer Safety

| Harness | 实际RTL / 性质 | 结果 / 边界 |
| --- | --- | --- |
| final_refill_producer | 生产4项MemoryRefillMshrBank；Txn ID匹配、非法ID/Beat/Last检测、分配初始化、Full仅由成功末拍置位、Writer Stall控制保持、Reset清理 | 归纳PASS；唯一环境假设alloc仅在free offered时发生，这是待组合验证的Caller义务；不限制错误响应 |
| final_axi_local | 生产4项AXI Adapter；响应ID关联活跃/已发事务，错误read为终止错误，成功Last=beat7，BRESP错误保持，WLAST对应count7，Reset清slots/输出 | 归纳PASS，无协议假设；未证明完整FIFO记账或端到端正确性 |
| final_axi_producer_bmc | 同一实际Adapter；AR/AW/W与line response反压Valid/Payload保持 | **有界depth8 PASS**；只假设AXI R/B源反压保持；短界不覆盖完整8拍写事务的所有生命周期 |
| final_axi_producer | 更广反压性质的归纳尝试 | TIMEOUT，归纳未成功，保留induction trace；不是可达错误，也不是无界PASS |

既有L1来源/编码/Reset归纳证明和BRESP Error、Owner Retry定向检查由最终回归复用，没有重复实现。

Reset的外部边界已在`docs/cache.md` §6.1和§6.4声明：外存/AXI interconnect共同Reset，取消旧请求/响应，否则须外部drain/epoch wrapper。本轮未新增隐藏假设。局部Reset清理已证明；相同ID重新分配后，接口本身无法分辨违反契约的旧响应。本报告不承诺外部独立复位/不排空场景安全，也不新增epoch架构。

## D — Coverage处置与真实缺口

当前74831原始点；45365命中并全部Raw Attestation核验；29466零点（869非Toggle、28597Toggle）。本轮所有8份Raw与Baseline归档逐字节一致：**新增Line/Branch/FSM/Toggle均0，丢失0**。每Dataset前后值见`proof_release/coverage_comparison.json`。不跨Top转记计数。

Main仍128 Line、83 Branch、24 FSM State、35 FSM Arc，合计270个控制缺口。每点风险、条件、Point ID、Source SHA、Raw/Dataset Hash、Test/Proof范围关联见`proof_release/main_control_risk_disposition.csv`；全部Top控制点见`proof_release/control_point_traceability.json`。`code_coverage_report.md`提供各模块/未执行源码行范围及869控制点和全部Toggle原生身份。

分类边界：历史“结构不可达”只作为未批准候选保留；明确错误处理仍需匹配Fault/Producer范围；合法可达必须同Top测试；本轮新增证明与未命中错误guard的关联只证明所声明性质，不能自动宣布每个guard不可达。Context及其源状态、剩余未决点继续OPEN。当前没有经过独立批准的Unreachable/Waiver排除，没有可直接删除的死代码结论。

60个Directory恒零Toggle逐点重新核验Source/Raw/Dataset与最新Alignment归纳日志，`proof_release/waiver_review_submission.json`：独立审核者null，PENDING，实际排除0。Reviewed Eligible Coverage尚不计算。

## E — 最终回归与发布决定

当前已提交验证源码上八项回归 **8/8 PASS**：Functional53/53、Cross35/35、Stress280/280、Cross Closure21/21、Hit-under-Miss3/3、Replay1/1。`coherence_verify`实际执行包含新三项归纳证明的Formal、既有Mutation/模块/系统检查。独立Evidence Gate核验当前Source SHA。

Release Gate实际 **OPEN**，make退出 **2**，29466 Required零点未处置，45365命中自动核验，未核验0。没有忽略失败退出。

功能发布阻塞仍有：Context2/3集成容量/可达性；读端口控制提取和Main对应独立审核；AXI完整生命周期/反压的无界安全与Refill分配Caller组合保证。上述未全部验证或正式审核处置，故**Functional Candidate OPEN**，不自行批准CONDITIONAL。完整Required代码义务未收敛，故**Full RTL Code Coverage OPEN**。

停止新增DV场景与架构扩展。既有53/35/280回归切片可供审查，但不是冻结批准。最小剩余任务及契约限制见`remaining_risks.md`。

完整证据与哈希：`proof_release/evidence_hashes.json`、`raw_archive.json`、`regression_status.json`、`formal_evidence.json`；源码/CI映射`verification_run_manifest.json`。所有压缩原始日志按解压内容SHA256核验，归档文件另有压缩字节Hash。

被测源码CI两项均success（报告提交CI另查）：

- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42967241446
- https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42967235385

PR：https://github.com/cwu766485-ctrl/open_verif_learning/pull/1 。报告提交CI按实际HEAD另查。未合并、未创建正式Tag。
