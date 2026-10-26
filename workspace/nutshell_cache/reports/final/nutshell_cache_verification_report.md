# NutShell MESI Cache v1.0 — 综合技术与验证报告

更新日期：2026-10-26  
适用分支：`cache_coherence`  版本基线：MESI v1.0（`release/v1.0`），维护候选：v1.0.1  
项目：双核 MESI Cache 子系统，包含私有 L1、共享 L2/Directory、内存 AXI4 适配器及 APB 性能 CSR。

## 1. 执行摘要

当前交付已经从旧的单核 L1 DCache 学习验证项目演进为双核自定义 MESI 一致性缓存子系统。报告、验证入口与性能数据均以当前 MESI RTL 为对象；旧 L1 验证保留为独立回归，不再充当 MESI 的验证依据。`release/v1.0` 维持冻结；本报告记录 `cache_coherence` 上的维护候选结果，不移动或重打 v1.0 标签。

本次更新修复了一处共享 refill 与 Snoop 竞争中的 ready/valid 协议缺陷，并启用无数据 clean invalidation 与 L2 refill 并行。相同定向 workload 下，Core1 Store 请求到响应由 14 cycles 降至 10 cycles；数据、目录状态与协议错误检查均通过。PPA/SRAM 实现评估按当前计划暂不包含。

本次收尾补充双 sharer / dirty owner 的长压测 L2 victim 触发、独立 L1 victim-to-Put 对照、覆盖/报告更新和 testbench lint 告警分类。一个更激进的随机地址池实验仍未闭合，限制见第 7 节。

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

## 5. 回归与验收结果

以下表格记录本次源码对应的最新本地回归结果。最近一次此前提交的 GitHub Actions 两个 job 均通过；本次更新推送后，应再以新提交的 Legacy 与 Coherence job 为最终 CI 记录。

| 验证目标 | 结果 | 边界说明 |
| --- | --- | --- |
| Legacy L1 regression | 46 passed; 23 skipped; 3 deselected | 独立保留的单 L1 兼容测试 |
| Coherence SV regression | smoke + multisnoop + 5 seeds PASS; 34/34 功能 bins; 92.8% 行覆盖 | 模块、集成 directed 与固定随机 seed |
| Python/Toffee MESI | 21 passed; 30/30 功能 bins; 9/9 checker fault injections caught | 独立数据/权限 scoreboard、L1 victim/Put 对照与 MESI mutation sensitivity |
| Extended Python stress | 20/20 seeds; 4,000 mixed operations; 710 L1 evictions; 3 modeled live L2 evictions | 包含 1 dirty-owner 与 1 two-sharer victim 的固定 replay 前导；另有未通过的更激进同 L2 set 随机实验，见第 7 节 |
| AXI adapter / AXI subsystem | adapter Python 3 passed; AXI top 5 seeds PASS | 五通道、4 outstanding、ID/error/reset/backpressure 测试 |
| Bounded formal | 6/6 组件目标 PASS | 组件级、有界深度 |
| Product-top lint | `CoherentCacheSubsystem` 与 `CoherentCacheAxiSubsystem` 均 0 Warning | 集成 SV testbench 仍有已分类的 bench-only warnings |
| PPA/SRAM 实现 | 未执行 | 本次排除，需目标工艺/库/约束后评估 |

## 6. 性能数据与复现

性能 workload 固定 seed、初始 cache 状态和可配置内存响应延迟。基准输出 latency、P95、ops/cycle、L1/L2 refill hit/miss、Snoop、dirty writeback、AXI 读写 line/byte 数与 bytes/cycle。模拟周期数据只比较同一仿真配置下的设计行为。

```bash
source scripts/env.sh
make gen_dut && make test
make COHERENCE_JOBS=2 coherence_verify
make COHERENCE_JOBS=2 coherence_benchmark_v3
```

主要产物：

- [`MESI v1.0 验证计划`](../../docs/cache_spec_and_verification_plan.md)
- [`Benchmark v3 测量与定义`](../../docs/coherence_benchmark_v3_results_2026-10-25.md)
- [`clean Snoop/refill A/B 原始结果`](../../benchmarks/results/p2_clean_snoop_fill_ab.json)
- [`更新日志`](../../docs/update_log.md)

## 7. 当前限制与后续

- 一项额外的压力实验把九条随机读写行全部映射到同一个 L2 set，同时运行双核并发和反压；20 个 seed 中 14 个触发 Directory reference-state mismatch 或 CPU response timeout/protocol error。该混合压力场景尚未定位根因，因此当前 20×200 签收池改为十条同 L1 set、分布在四个 L2 set 的行，并在 `0x5eed` 前导中独立确定性触发 dirty-owner 与 two-sharer 九行 L2 victim。确定性 victim、L1 victim/Put 对照和已配置的 20×200 回归均通过；不能据此宣称更激进的全同 L2 set 并发随机场景已通过。
- 集成 SV testbench 的 Verilator build 仍会报告 testbench 级 `PINCONNECTEMPTY` / `PINMISSING`（非验证实例的可选 monitor 端口）、`WIDTHEXPAND` / `WIDTHTRUNC`、`MISINDENT`、`TIMESCALEMOD`、`UNUSEDSIGNAL`，以及 testbench/reference-model `MULTIDRIVEN`。`SharedL2DirectoryArray.line_wr_ready` 的 `MULTIDRIVEN` 来自一项层级 `force` backpressure 测试注入。两个实际产品顶层单独 lint 均为零 Warning；这些 bench 警告没有通过全局 waiver 隐藏。
- PPA、真实 SRAM macro 映射/面积与时序签核仍未执行；当前 Verilator 仿真数据不是物理实现结果。
- L1 仍为 blocking，完整系统 CPU 请求不能持续产生四个 outstanding miss；四个 Directory context/MHSR 的局部容量不等于四个 CPU 端到端并行 miss。
- Formal 尚未覆盖整个双核 cache 的无界数据正确性与所有并发事务；当前结论限于组件有界证明及仿真回归。
- `release/v1.0` 是冻结的 MESI v1.0 基线；v1.0.1 维护记录独立放在 [`docs/releases/v1.0.1.md`](../../docs/releases/v1.0.1.md)，不移动冻结分支或标签。
