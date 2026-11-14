# NutShell Cache v1.1 — Final Proof Closure & Release Review

**Functional Verification Release Decision: OPEN**  
**Full RTL Code Coverage Sign-off Decision: OPEN**

Baseline `837dd8d3639b347fcdc4215b90ec3c41350a6489`。Tested Source SHA `0e852178ee2fedb5cdf414846cf3920b62a92139`（回归与Evidence Gate实际绑定）；Source Fingerprint `5f3c2f4f370989a29608f161504d076d6082523d0302e19ed3baac9ef1bf860a`；RTL Fingerprint `15798323c27cd473bf3d70a70b66b7cb39620c5abd2682a39e22512ac6794d6a`。报告SHA为包含本文件的实际报告提交，独立于Source SHA。产品RTL未改；随机规模、覆盖分母和Required义务未改。

## 三项技术结果

1. **Context2/3：OPEN**。生成实际完整Main/L1控制器/Replacement Put Bypass/Arbiter/Directory MSHR的资源抽取，仅数组输出切点任意化，没有Occupancy≤2假设。前端已成功进入Cover；90秒超时，未获得合法集成Witness或不可达证明。数组切点是过近似，未来抽象Witness必须与真实阵列重放才可称Legal Reachable。当前不制造Directed Test。清单含保留模块与切点Source Hash：`release_review/resource_extraction.json`。
2. **L2 Read Control：作者/工具复核完成，独立审核PENDING**。新增全文件Busy/Beat写点检查，验证只有Reset、接受Read、Beat7 Retire与Stream Increment四类赋值；原有实际Engine+源码控制切片归纳PASS保留。控制依赖检查不是全Top等价证书，也不是独立审批。未将抽象证明点自动标不可达。
3. **AXI/Refill**：实际4项Refill Bank与Main admission条件组合归纳PASS，free-slot assumption已替换为实际alloc_found门控保证；调用状态/地址任意化扩大范围，不假设Context占用。AXI按AR/AW/W/Read/Response五通道拆分，Response稳定性归纳PASS，其余归纳未成功UNKNOWN。原有局部ID/Error/Reset归纳PASS、广义depth8有界PASS保留；FIFO所有权/Beat生命周期无界证明仍OPEN。环境仅AXI R/B源在反压下保持Valid/Payload，不假设合法ID/Last或有限延迟。共享Reset排空契约仍为既有docs/cache.md §6.1。

## 本轮Formal实际状态

- `review_context_resource_cover`：`TIMEOUT 8 2`
- `review_refill_caller`：`PASS 0 3`
- `review_axi_ar`：`UNKNOWN 4 1`
- `review_axi_aw`：`UNKNOWN 4 1`
- `review_axi_w`：`UNKNOWN 4 11`
- `review_axi_read`：`UNKNOWN 4 1`
- `review_axi_response`：`PASS 0 0`

状态字段为SBY原始status及退出码/运行时间，详细日志/轨迹见`release_review/formal/`。UNKNOWN归纳轨迹不是可达Bug；TIMEOUT不是不可达。所有证明范围、Assumption和未证义务见`formal/review_release_scope.md`及既有`formal/final_proof_scope.md`。

## 最终回归及覆盖率

八项完整回归8/8 PASS；Checked Functional53/53、Cross35/35、Stress280/280、Hit-under-Miss3/3、Cross Closure21/21、Replay1/1。当前Source SHA Evidence Gate PASS，相关Formal与既有Mutation保留。被中断的初次旧源码回归不计入本次证据。

Raw总74831，命中45365且全部机器核验，零29466：Line434、Branch265、FSM State57、FSM Arc113、Toggle28597。Main仍128Line、83Branch、24State、35Arc。全部8份Raw与Baseline归档逐字节一致，新增/丢失Raw Hit均0，不跨Top合并。逐Dataset前后值见`release_review/coverage_comparison.json`，未执行代码与逐点CSV见`code_coverage_report.md`。

Release Gate实际OPEN，make退出2；Required零点未全部处置，未忽略失败退出。60个恒零Toggle仅准备当前Hash审核材料，独立审批者null，无批准Waiver/Unreachable排除，不计算Reviewed Eligible Coverage。

精确Source/Raw/Dataset/Point映射：`release_review/control_point_traceability.json`。所有零点保持OPEN；没有删除防御逻辑或批准死代码处置。

## Release Decision

Context2/3集成结论、L2控制提取独立对应审核、AXI FIFO/完整生命周期归纳仍为阻塞项，因此Functional Candidate **OPEN**。可向独立审查者建议按明确政策审查既有53/35功能计划切片，但不自行批准CONDITIONAL。完整Required代码义务未关闭，Full RTL Coverage **OPEN**。

最小后续工作为支持合法阵列约束的资源证明/重放、独立读控制对应审查及AXI队列所有权归纳引理；本轮停止扩展DV，不增加新场景或架构。Remaining Risks见`remaining_risks.md`。

证据索引`release_review/evidence_hashes.json`、Raw归档`raw_archive.json`、回归`regression_status.json`。CI按当前Source SHA与报告提交SHA分别查询：https://github.com/cwu766485-ctrl/open_verif_learning/actions 。PR #1：https://github.com/cwu766485-ctrl/open_verif_learning/pull/1 。不合并、不创建Tag。
