# Update Log

所有记录按时间倒序，简要说明变更、发现的问题和修复思路。

## 2026-11-19

- **为 v1.3 双事务上下文改造拆出单一 Snoop 控制器。** 将原 `MesiL1Controller` 内的 Snoop FSM 原样迁入每 L1 一个的 `MesiL1SnoopEngine`，外部接口和 MESI 事务行为保持不变；同步更新 RTL/Filelist、Block 文档、Formal 源列表和 Mutation 目标。拆分是为后续保留共享 Snoop owner、避免复制每个 miss context 的 snoop 状态与 ID 分配器；它本身没有增加同核并行 Directory 请求。代码检查还发现 `extract_release_resource_control.py` 的 retained manifest 缩进曾使函数返回结构错误，已修正并通过 `py_compile`。
- **对结构拆分执行定向回归与 Formal。** `make COHERENCE_JOBS=2 coherence_l1_controller coherence_cluster coherence_rtl_mutation coherence_nonblocking_l1_mshr coherence_hit_under_miss` 退出码 0：Controller/Cluster Block PASS，RTL Mutation 4/4 被捕获，MSHR 定向测试 5/5、Hit-under-Miss Python 2/2、AXI Top 3/3 PASS。另有 14/14 个 `coherence_formal` SymbiYosys 子目标 PASS，包含 L1 Controller、Directory/MSHR 与仲裁性质。覆盖证据刷新后 `coherence_nonblocking_l1_mshr` 再次 5/5 PASS，数据集明确记录源码 dirty diff hash；四个本地 L1 entry 仍只对应最多每核一个 controller-owned / Directory-issued miss，Directory Context、Refill MSHR、AXI R outstanding 峰值各为 2，本轮没有达成四笔下游 outstanding。
- **完成完整基线回归并固定当前 v1.3 结论。** `make COHERENCE_JOBS=2 coherence_verify` 在源码 SHA `75104a7e` 加记录的 dirty-tree diff `77a64bdc…` 上退出码为 0；Block、AXI、Formal、RTL/Python 回归、两组压力测试、Mutation 和 Benchmark v4 均通过。Python Coverage 为 Functional 49/49、Cross 19/19，9/9 Checker Fault Injection 被捕获。Benchmark v4 校验 24 个 workload 行，是重测基线，不是优化收益。集成 LCOV 1715/1855 包含 TB，不能当作产品 RTL 覆盖率。远端 CI 尚未核验。
- **完成 v1.3 基线回归复核并审计 Miss-under-Miss RTL 边界。** 当前 `coherence_nonblocking_l1_mshr` 5/5 PASS；`coherence_hit_under_miss` 的 Python 子系统 2/2、AXI Top 3/3 PASS。最新资源证据仍是每核 2 个已分配槽、每核最多 1 个 controller-owned/Directory-issued miss；Directory Context、Refill MSHR、AXI R outstanding 峰值分别为 2/2/2。因此已验证的是 tracking 与跨核并行，不是同核 miss 并行。
- **补充 v1.3 Phase 2 的 RTL 所有权审计和实现边界。** 源码确认每核只有一个 MESI CPU 事务上下文、一个替换 FSM；L1 阵列只有单 refill burst collector 和单 line-read stream。简单复制完整控制器会复制 Snoop FSM 并引入事务 ID 冲突风险；仅解除 queued-MSHR 派发限制则会争用 refill、metadata、line-read 和 victim-way 资源。契约现明确要求两笔独立 tagged miss context、单一共享 Snoop、refill/array 仲裁、活跃 ID 分配与按接受序号 FIFO 响应。保持 LSU 接口，不改产品 RTL 功能/接口，不声称 four-issued-miss 完成。
- **修正文档证据状态。** 记录了 `coherence_hit_under_miss` 本轮完整重建后通过 5 项测试；先前 status 143 的中断构建不再是最终结果。Benchmark 数字仅描述既有 Hit-under-Miss bypass 的合成延迟工作负载，不作为 v1.3 MSHR 性能提升。

## 2026-11-18

- **校准 L1 MSHR 并发监控口径。** 复查发现 `valid`（已分配）被重复当作 active，而 controller ownership 又被直接当作 Directory-issued。现已拆分 Allocated、Controller-owned、Directory-issued 的逐核直方图和峰值；issued 只统计 Directory 握手后 `WAIT_GRANT/REFILL/META_WRITE/RESP/ERROR` 阶段。四冷读证据分别为 L1 分配 4（每核 2）、controller-owned 每核 1、Directory-issued 每核 1、Directory Context 2、Refill MSHR 2、AXI R outstanding 2。结论是跨核两笔已 issue；每核第二笔仍排队，真正的同核 Miss-under-Miss 和四笔下游并发保持未实现。此次仅修正 monitor 与验证口径，不改变 RTL 功能和模块接口。
- **复核 v1.3 两入口 MSHR 的真实并发边界。** 在 `codex/v1.3-nonblocking-l1`、源码基线 `06572c0f` 重跑 `coherence_nonblocking_l1_mshr`（5/5 PASS）和 `coherence_hit_under_miss`（Python 2/2、AXI Top 3/3 PASS）。四个 L1 tracking entry 可在首个 CPU 响应前同时有效 381 个采样周期，但 issued L1 controller、Directory Context、Refill MSHR、AXI R outstanding 峰值分别只有 2/2/2/2。根因是每核仍只有一个 `MesiL1Controller`，第二个 entry 要等第一个 miss 响应退休后再派发；所以槽位容量不能当成同核 Miss-under-Miss 或四笔下游并发的证据。
- **冻结 v1.3 Phase 2 Miss-under-Miss 设计契约。** 新增 `docs/l1_miss_under_miss_v1_3_phase2_contract.md`，明确保持 CPU 接口、同核 miss 响应按接受顺序、将本地顺序号与 Directory/Grant/Refill 使用的事务 ID 分开、双槽满时反压、同地址暂不合并、同 Set 初始串行，并列出 L1 阵列端口仲裁、Snoop/Replacement/Reset 冲突和逐资源 Checker。主 Spec、Testplan、DV 记录已链接该契约；目标场景仍标 OPEN，没有增加/伪造 Coverage Bin，也没有改 RTL。

## 2026-11-04

- **闭环配对 Miss 顺序、同 Set 重复替换和 refill MSHR 生命周期。** 新增独立 `MshrLifecycleChecker`，仅使用 handshake Monitor 事件和 CPU 返回值关联 MSHR slot/AXI ID、Line 地址、8 拍 R burst、8 拍 L2 refill、Directory grant 和最终 CPU 响应；新增同 Set 的反序配对冷 Miss 和两轮配对替换场景。首轮测试发现同 Set interlock 会串行执行两笔 Miss，并在 burst 完成后复用相同 AXI ID；Checker 原先只按 ID 聚合，错误把两条 Line 的 16 个 R beat 当作一次 burst。改为按 `ID + Line` 区分 burst，并检查从 Directory 接收到 CPU 返回的时序。完整 `make coherence_full_system_coverage` 通过：45 passed、1 条条件性 Trace Replay 跳过；Required Functional 42/42、Cross 20/20。仅为 DV/文档/覆盖报告变更，RTL 功能和接口未改。

## 2026-11-03

- **配对访问下的脏 L2 victim Checker。** 新增双核并发场景：一个 Core 命中已有行，另一个 Core 冷 miss 到同一已满 L2 Set，并让参考模型预测的 victim 由 M Owner 持有。Checker 按实际接受顺序更新独立模型（Miss 取 Directory 握手，Hit 取 CPU 握手），再核对 victim、Directory、Snoop、8 拍 Owner 数据、AXI 写回和两个 CPU 返回值。初次失败定位到 Toffee 调度下被动 Monitor 会漏掉快速命中请求的短握手脉冲；Hit 使用 Driver 已采样的握手时刻，Miss 仍要求 Directory Monitor 观察到接受事件。定向用例和完整覆盖回归通过：43 passed、1 条条件性 Trace Replay 跳过，Required Functional 39/39、Cross 17/17。该证据仅覆盖此 hit+miss 组合，不代表 paired miss/miss 或所有 MSHR 生命周期已闭环。

- **验证缺口收敛：APB Counter Wrap。** `CachePerformanceCsr` 的六个 32-bit 计数器按模 `2^32` 回绕，原有测试未触及边界。新增 Block 边界场景：测试平台将计数器 Q 值置于最大值附近，再经真实事件输入递增，并通过 APB 检查回绕读数；测试后复位恢复基线。产品 RTL 与接口未修改。
- **修复并验证 Dirty Owner Inclusive Victim 场景。** 新增系统级场景：Core0 将目标行持有为 M，随后通过同 L2 Set 填充触发该行驱逐；Checker 比较独立模型预测的 victim/Directory、Core0 反失效、8 拍 Owner 数据、AXI AW/W/B 与 backing memory，并检查随后重新读取。首次失败暴露的是 Test 对“L2 阵列 dirty 位”的误读：最新数据仍在 M 态 L1 Owner 时，L2 阵列自身 dirty 可以为 0。
- **修正 L2 victim 灰盒监视器字段解码。** Wrapper 暴露的是单个共享 victim 的标量地址、Directory 状态、Owner ID/dirty，以及两核 Sharer bitmap；原监视器错误地按 Core 拆分标量字段。改为按真实字段宽度记录，避免把核号误记为 victim 槽号。
- **扩展独立 L2 Replacement Checker。** Reference Model 记录每次独立预测的 L2 victim、Directory 状态、Sharer/Owner 和原 L1 MESI 状态；Full-System Env 核对 RTL victim、所有驻留副本反失效；U Owner eviction 还核对整行数据和 AXI 写回。Clean 与 Dirty Owner 两个 directed test 通过。
- **扩展 Reset × Stall 定向验证。** 新增复位分别发生在 AXI ARREADY 停顿、AXI RVALID 间隙、AWREADY 停顿、WREADY 停顿、CPU 响应 READY 低和 MMIO 请求 READY 低期间。6 个用例全部通过，并检查 reset epoch、旧事务取消、无陈旧响应及可恢复场景。AXI RREADY/BREADY 在集成顶层固定可接收，APB PREADY 立即响应，不将它们报告为可施加的顶层反压。
- **Reset × Stall 覆盖闭环。** 将上述 6 个实际可施加的 Reset/停顿组合加入稳定 Required Cross Bin，并在每个用例的协议、取消和恢复检查通过后采样；完整 Full-System 覆盖回归再次通过，Required Functional 38/38、Cross 16/16。没有为顶层无法施加的 AXI RREADY/BREADY 或 APB PREADY 停顿新增 Bin。
- **收敛状态。** `make coherence_bus_blocks` PASS；`make coherence_full_system_stress` 的 60 个 seeded 场景 PASS；完整 `make coherence_full_system_coverage` 为 42 passed、1 conditional replay skipped，Required Functional 38/38、Cross 16/16。完整 `make COHERENCE_JOBS=2 coherence_verify` 本地运行到 Benchmark v4 并通过，包含 Block、Formal、集成回归、Python/AXI、Stress、Mutation 和 Benchmark 目标。运行仍有 Verilator empty-pin / unused-signal warnings，不表示 lint 无警告。对应 GitHub Actions 尚未核验。
