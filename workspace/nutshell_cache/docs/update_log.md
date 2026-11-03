# Update Log

所有记录按时间倒序，简要说明变更、发现的问题和修复思路。

## 2026-11-03

- **验证缺口收敛：APB Counter Wrap。** `CachePerformanceCsr` 的六个 32-bit 计数器按模 `2^32` 回绕，原有测试未触及边界。新增 Block 边界场景：测试平台将计数器 Q 值置于最大值附近，再经真实事件输入递增，并通过 APB 检查回绕读数；测试后复位恢复基线。产品 RTL 与接口未修改。
- **修复并验证 Dirty Owner Inclusive Victim 场景。** 新增系统级场景：Core0 将目标行持有为 M，随后通过同 L2 Set 填充触发该行驱逐；Checker 比较独立模型预测的 victim/Directory、Core0 反失效、8 拍 Owner 数据、AXI AW/W/B 与 backing memory，并检查随后重新读取。首次失败暴露的是 Test 对“L2 阵列 dirty 位”的误读：最新数据仍在 M 态 L1 Owner 时，L2 阵列自身 dirty 可以为 0。
- **修正 L2 victim 灰盒监视器字段解码。** Wrapper 暴露的是单个共享 victim 的标量地址、Directory 状态、Owner ID/dirty，以及两核 Sharer bitmap；原监视器错误地按 Core 拆分标量字段。改为按真实字段宽度记录，避免把核号误记为 victim 槽号。
- **扩展独立 L2 Replacement Checker。** Reference Model 记录每次独立预测的 L2 victim、Directory 状态、Sharer/Owner 和原 L1 MESI 状态；Full-System Env 核对 RTL victim、所有驻留副本反失效；U Owner eviction 还核对整行数据和 AXI 写回。Clean 与 Dirty Owner 两个 directed test 通过。
- **扩展 Reset × Stall 定向验证。** 新增复位分别发生在 AXI ARREADY 停顿、AXI RVALID 间隙、AWREADY 停顿、WREADY 停顿、CPU 响应 READY 低和 MMIO 请求 READY 低期间。6 个用例全部通过，并检查 reset epoch、旧事务取消、无陈旧响应及可恢复场景。AXI RREADY/BREADY 在集成顶层固定可接收，APB PREADY 立即响应，不将它们报告为可施加的顶层反压。
- **Reset × Stall 覆盖闭环。** 将上述 6 个实际可施加的 Reset/停顿组合加入稳定 Required Cross Bin，并在每个用例的协议、取消和恢复检查通过后采样；完整 Full-System 覆盖回归再次通过，Required Functional 38/38、Cross 16/16。没有为顶层无法施加的 AXI RREADY/BREADY 或 APB PREADY 停顿新增 Bin。
- **收敛状态。** `make coherence_bus_blocks` PASS；`make coherence_full_system_stress` 的 60 个 seeded 场景 PASS；完整 `make coherence_full_system_coverage` 为 42 passed、1 conditional replay skipped，Required Functional 38/38、Cross 16/16。完整 `make COHERENCE_JOBS=2 coherence_verify` 本地运行到 Benchmark v4 并通过，包含 Block、Formal、集成回归、Python/AXI、Stress、Mutation 和 Benchmark 目标。运行仍有 Verilator empty-pin / unused-signal warnings，不表示 lint 无警告。对应 GitHub Actions 尚未核验。
