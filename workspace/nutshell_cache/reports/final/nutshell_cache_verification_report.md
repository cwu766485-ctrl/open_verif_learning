# NutShell MESI Cache v1.0 — 综合技术与验证报告

更新日期：2026-10-27  
适用分支：`cache_coherence`  版本基线：MESI v1.0（`release/v1.0`），维护候选：v1.0.1  
项目：双核 MESI Cache 子系统，包含私有 L1、共享 L2/Directory、内存 AXI4 适配器及 APB 性能 CSR。

## 1. 执行摘要

当前交付已经从旧的单核 L1 DCache 学习验证项目演进为双核自定义 MESI 一致性缓存子系统。报告、验证入口与性能数据均以当前 MESI RTL 为对象；旧 L1 验证保留为独立回归，不再充当 MESI 的验证依据。`release/v1.0` 维持冻结；本报告记录 `cache_coherence` 上的维护候选结果，不移动或重打 v1.0 标签。

本次更新修复了一处共享 refill 与 Snoop 竞争中的 ready/valid 协议缺陷，并启用无数据 clean invalidation 与 L2 refill 并行。相同定向 workload 下，Core1 Store 请求到响应由 14 cycles 降至 10 cycles；数据、目录状态与协议错误检查均通过。PPA/SRAM 实现评估按当前计划暂不包含。

本次更新闭合了此前随机回归中“九条行落在同一 L2 set、双核并发与反压”失败：20 seeds 中原先 14 个触发 Directory mismatch、协议错误或响应超时。根因是 L1 replacement PutM 与尚未握手的 owner-data Snoop 相互等待；RTL 只在 Snoop 尚未被接受、且无正在进行的 snoop 数据传输时允许 PutM 先提交。修复后原 dense-set 工作负载 20/20 seeds、4,000/4,000 随机操作通过。

本次也完成 D01/D02/D04 及 Tests A/B/C：message-passing、同/异 cache-line false-sharing 对照、generation-counter 通信均通过，并登记到 Testplan/coverage。RTL 源验证提交为 [`0c2c432`](https://github.com/cwu766485-ctrl/open_verif_learning/commit/0c2c43251ec93f795dd286da42fccefae5373ae8)，本地 `make COHERENCE_JOBS=2 coherence_verify` 通过；cache 与 AXI 性能数据在同一修复候选快照复跑。首次完整 CI run [40516921592](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40516921592) 的 Legacy job 在 45 分钟 timeout 后被取消。提高 timeout 到 90 分钟后，完整 follow-up run [40527215667](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40527215667) 在验证提交 `75a7533` 上成功：Legacy（含 Formal 与 Regression）和 Coherence 均 PASS，没有跳过验证目标。本地 Legacy `make test` 为 46 passed、26 skipped、3 deselected。PPA/SRAM 评估不在本次交付范围。

## 2. 硬件架构

- 两个私有 L1 Data Cache，每个 32 KiB、4-way、64-byte line；各自连接 LSU/CPU 请求接口。
- 自定义 MESI 协议连接 L1 与共享 Directory，不依赖外部标准一致性协议。
- 共享 256 KiB、8-way L2 与 inclusive Directory；Directory 使用四个事务上下文，内存 refill 路径有四个 MSHR。
- L2 refill、Grant、Snoop 和 dirty writeback 仍共享部分阵列/数据通路资源；L1 控制器仍是 blocking。
- Line Memory AXI4 Adapter 支持带 ID 的 burst 请求和多笔 outstanding；完整 cache top 的 CPU miss 并行度仍受 blocking L1 与 Directory/共享资源约束。
- APB Performance CSR 暴露 hit、miss、snoop、dirty writeback 与协议错误等软件可读统计。

## 3. 验证平台

新 MESI 验证使用 Python/pytest、Toffee、Picker 和 Verilator。Python CPU 与内存 agent 通过 packed-port wrapper 驱动 RTL；协议 monitor 采集已握手的请求、Grant、Snoop、目录提交和数据 beat。Reference model 根据 CPU 操作及协议事务推演每个 Core 的行数据和 MESI 权限，scoreboard 检查返回数据、跨核可见性、目录权限及 owner 数据传输。

功能覆盖由 testcase 在 checker 成功后产生结构化事件，再对 feature、requester、MESI 状态、opcode、owner/source 与传输 beat 等维度做 closure。SV directed/random 回归保留为 RTL 集成基线；Python/Toffee 正在逐步接管独立功能验证。Legacy 单 L1 测试继续独立运行。

Formal 由 SymbiYosys/Yosys SAT 的组件级 bounded checks 组成，覆盖仲裁器、Directory、MSHR bank、L1 controller 等局部安全性与可达性。结果是有界/局部证据，不代表完整子系统无界证明。

## 4. 本次缺陷与优化

**故障现象：** refill 写入共享 L2 时，Directory bank 因共享资源拉低 Snoop `ready`，但顶层仍将 `valid` 直接送给 L1。L1 接收了失效请求，Directory context 没有接受同一笔事务，随后 L1 响应无法匹配活动 Directory context，Store 卡住且没有协议错误标志。

**修复：** 将下游 Snoop `valid` 与 Directory `ready` 统一使用同一个准入条件，避免 L1 与 Directory 对握手是否发生产生分歧；加入断言，任何 L1 已接收的 Snoop 必须同时被 Directory bank 接收。Owner-data Snoop 仍等待 refill 数据写端口空闲；只让不需回收数据的 clean invalidation 与 refill 重叠。

**同一 workload A/B：** Core0 发起不同 L2 set 的 cold refill 时，Core1 对双方均为 S 的另一条 line 执行 Store，触发 clean invalidation。固定 seed `0xC1EA5EED`，相同请求顺序、内存模型和状态检查。

| 指标 | 保守串行基线 | clean Snoop 并行 | 变化 |
| --- | ---: | ---: | ---: |
| refill 开始到 Snoop 被接受 | 9 cycles | 5 cycles | 提前 4 cycles |
| Store 请求到 Snoop 被接受 | 8 cycles | 4 cycles | 提前 4 cycles |
| Store 请求到响应 | 14 cycles | 10 cycles | 减少 4 cycles（28.6%） |
| refill 请求到响应 | 36 cycles | 36 cycles | 不变 |
| 返回数据/Directory 检查 | PASS | PASS | — |

此优化只针对 clean invalidation 与 refill 数据流的资源重叠，不宣称提升物理频率、面积、SRAM 推断质量或 DRAM 带宽。原 Benchmark v3 的隔离 L2 hit 优化数据仍保留：32 个样本平均响应由 23 降至 22 cycles，详见 [`coherence_benchmark_v3_results_2026-10-25.md`](../../docs/coherence_benchmark_v3_results_2026-10-25.md)。

**同组并发死锁闭环：** 更激进的 9 行同 L2 set 双核压力曾在 20 seeds 中有 14 个失败。回放定位为 replacement PutM 等待 L2 写入，而 L1 又因同一 Directory owner-data Snoop 尚未被接受而无法继续，形成握手等待环。顶层现允许 PutM 仅在该 Snoop 尚未握手、且当前没有 snoop 数据传输时先提交；已接受的 owner-data Snoop 仍保持 L2 写口互斥。Directory 对无数据 ACK 从权威 L2 数据恢复。修复后同一压力配置 20/20 seeds × 200 operations 通过，逐事务检查数据、MESI/Directory 状态和响应结束。

## 5. 回归与验收结果

以下表格记录 2026-10-27 RTL 源提交 `0c2c432` 的本地回归结果。CI 门禁候选 `75a7533` 的完整 run [40527215667](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40527215667) 已通过；旧 run [40516921592](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40516921592) 的 Legacy job 在 Formal 阶段因 45 分钟 timeout 被取消，随后通过延长到 90 分钟完整重跑闭环。

| 验证目标 | 结果 | 边界说明 |
| --- | --- | --- |
| Legacy L1 regression (`make test`) | 46 passed; 26 skipped; 3 deselected | 独立保留的单 L1 兼容测试；本地重新生成 Picker DUT 后运行 |
| Coherence SV regression | 38/38 功能 bins; 91.6% 行覆盖 | 模块、集成 directed 与固定随机 seed |
| Python/Toffee MESI | 24 passed; 36/36 功能 bins; 12/12 cross bins; 9/9 checker fault injections caught | 独立数据/权限 scoreboard、L1 victim/Put 对照、D01/D02/D04 与 Tests A/B/C |
| Extended Python stress | 标准与 dense-set 均 20/20 seeds × 200 操作；标准压力记录 710 次 L1 eviction、3 次 live L2 victim | dense-set 覆盖同 L2 set 双核并发/反压；两种压力均检查数据、MESI/Directory 状态与事务完成 |
| AXI adapter / AXI subsystem | Adapter Python 3 passed; AXI top 5 seeds PASS | 五通道、ID/error/reset/backpressure；top benchmark peak read outstanding 为 2 |
| Bounded formal | 6/6 组件目标 PASS | 组件级、有界深度；不代表系统级无界证明 |
| Product-top lint | `CoherentCacheSubsystem` 与 `CoherentCacheAxiSubsystem` 均 0 Warning | 集成 SV testbench 仍有已分类的 bench-only warnings |
| GitHub Actions | PASS: Legacy/Formal + Coherence | Run 40527215667 on `75a7533`; all jobs green, no verification target skipped |

门禁核对：`Makefile` 已定义 `coherence_dense_set_stress`，并由 `coherence_verify` 调用；Actions 的 Coherence 步骤执行 `make -C workspace/nutshell_cache COHERENCE_JOBS=1 coherence_verify`。因此 dense-set 已进入自动回归，截图中“缺少 Make target”的描述对应旧快照。Legacy 的 45 分钟 timeout 已提高至 90 分钟，完整 Formal/Regression 在 run 40527215667 中通过。
| PPA/SRAM 实现 | 未执行 | 本次排除，需目标工艺/库/约束后评估 |

## 6. 性能数据与复现

性能 workload 固定 seed、初始 cache 状态和可配置内存响应延迟。当前候选数据显示 warm L1 read 2 cycles、L2 hit 22 cycles；五 seed mixed workload 平均 17.20 cycles、0.04957 ops/cycle、0.46444 B/cycle。模拟周期数据只比较同一仿真配置下的设计行为，不是 DRAM 带宽或芯片 Fmax。完整 A/B 数字、source/baseline SHA、工作负载映射、scoreboard 与限制见[性能签核摘要](performance_signoff.md)。

```bash
source scripts/env.sh
make gen_dut && make test
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_benchmark_v3
```

主要产物：

- [`MESI v1.0 验证计划`](../../docs/cache_spec_and_verification_plan.md)
- [`Benchmark v3 测量与定义`](../../docs/coherence_benchmark_v3_results_2026-10-25.md)
- [`最终性能签核摘要`](performance_signoff.md)
- [`clean Snoop/refill A/B 原始结果`](../../benchmarks/results/p2_clean_snoop_fill_ab.json)
- [`更新日志`](../../docs/update_log.md)

## 7. 当前限制与后续

- 同 L2 set 压力曾有 14/20 seeds 失败。根因和修复已由原失败分布复测闭环：PutM 可绕过尚未握手 owner-data Snoop 的循环等待；一旦 Snoop 已握手或数据流进行中，仍禁止共享 L2 写口冲突。修复后 dense-set 20/20 seeds × 200 操作通过，并纳入 Makefile 与 CI 自动回归。该有限随机回归与 bounded formal 仍不能穷举所有 set、时序和系统活性组合。
- 集成 SV testbench 的 Verilator build 仍会报告 testbench 级 `PINCONNECTEMPTY` / `PINMISSING`（非验证实例的可选 monitor 端口）、`WIDTHEXPAND` / `WIDTHTRUNC`、`MISINDENT`、`TIMESCALEMOD`、`UNUSEDSIGNAL`，以及 testbench/reference-model `MULTIDRIVEN`。`SharedL2DirectoryArray.line_wr_ready` 的 `MULTIDRIVEN` 来自一项层级 `force` backpressure 测试注入。两个实际产品顶层单独 lint 均为零 Warning；这些 bench 警告没有通过全局 waiver 隐藏。
- PPA、真实 SRAM macro 映射/面积与时序签核仍未执行；当前 Verilator 仿真数据不是物理实现结果。
- L1 仍为 blocking，完整系统 CPU 请求不能持续产生四个 outstanding miss；四个 Directory context/MHSR 的局部容量不等于四个 CPU 端到端并行 miss。
- Formal 尚未覆盖整个双核 cache 的无界数据正确性与所有并发事务；当前结论限于组件有界证明及仿真回归。
- `release/v1.0` 是冻结的 MESI v1.0 基线；v1.0.1 维护记录独立放在 [`docs/releases/v1.0.1.md`](../../docs/releases/v1.0.1.md)，不移动冻结分支或标签。
