# NutShell L1 DCache 开源验证报告

更新日期：2026-10-10
验证对象：NutShell RISC-V SoC 的 L1 DCache，SimpleBus 模块边界
验证工具：Python、Toffee、Picker、Verilator、pytest、Yosys、SymbiYosys

## 1. 目标与结论

本项目面向嵌入式/边缘 RISC-V 工作负载，构建一套可复现、无需商业仿真器的 Cache 模块级验证环境。当前回归通过 **39/39 个 pytest cases**，命中 **37/37 个功能覆盖目标**；维护 RTL 原始行覆盖率为 **98.0%（845/862）**。经审查的 waiver 调整后为 **100%（845/845）**。这些结果代表开源工具链下的高质量回归，不等同于商业 sign-off 或等价性签核。

## 2. DUT 与验证架构

验证配置为 **32-KiB、4-way set-associative、64-byte cache line、64-bit datapath**，共 128 组。验证环境在 SimpleBus 边界组合 CPU、memory、MMIO 和 coherence 事务角色，由 monitor、checker、reference model、scoreboard 及功能覆盖采样器协同工作。

参考模型分为 CPU 可见稀疏内存模型和独立 set-associative tag 状态模型。后者跟踪 tag、valid、dirty 状态，独立预测 hit/miss、invalid-first refill way 和精确 LFSR victim way。Scoreboard 对照返回数据、响应命令、下游路由、dirty victim 地址，以及 writeback 的八个数据 beat、mask、命令和 burst 地址。

Ready/valid checker 检查 stalled payload 稳定；协议 checker 检查响应缺失、重复、过期及非法命令；DUT property checker 统计已接收、完成和 reset-abort 的事务并检查替换选择器不变量。

## 3. 测试计划

回归覆盖以下场景：

- Read/write hit、miss、8-bit byte mask、same-word forwarding 和跨 cache-line 访问；
- 空/部分/满 set 占用、clean/dirty victim，以及同一 set 的 4-way 冲突替换；
- 八拍 refill/writeback、下游和 CPU 侧 backpressure、排队 miss；
- MMIO bypass、coherence probe/release、复位中止 refill 和复位后恢复；
- 六个固定 seed 的随机混合事务，每个 seed 64 笔，共 **384 笔随机操作**。

功能覆盖计划将 set occupancy、hit/miss、partial write、victim 类型、backpressure channel、probe/release、reset cancellation 和 forwarding 列为 closure goals。`make report` 在任一目标未命中时失败。

## 4. 回归、覆盖率与故障注入

| 指标 | 结果 |
| --- | ---: |
| pytest cases | 39/39 通过 |
| 功能覆盖目标 | 37/37（100%） |
| 维护 RTL 原始行覆盖率 | 98.0%（845/862） |
| 维护 RTL waiver-adjusted statement coverage | 100%（845/845） |
| RTL + generated DUT/wrapper 全源行覆盖率 | 95.1%（1423/1496） |
| checker fault injection | 4/4 个代表性错误被捕获 |

覆盖 waiver 仅用于明确的非目标或不可达代码：断言失败诊断、复位后不可自然到达的 LFSR 零状态恢复、DCache 禁用的 flush 路径、CPU 不支持的 burst 请求路径，以及两个 LCOV 控制行记录。waiver 不替代原始覆盖率；简历与报告均保留 raw coverage 数字。

CI 在干净 Ubuntu runner 上重新安装工具链、生成 DUT、运行形式检查及覆盖率闭环，并额外执行两个固定 seed；每次 CI 共 **8 个固定 seed、512 笔随机操作**。最新状态与历史运行记录见 [GitHub Actions](https://github.com/cwu766485-ctrl/open_verif_learning/actions/workflows/nutshell-cache-dv.yml)。

## 5. 形式验证范围

`make formal` 包含三个 SymbiYosys gate 和一个有界 Yosys SAT 检查：

| 检查 | 范围与约束 |
| --- | --- |
| Replacement selector | 检查 LFSR recurrence 及非零 reset state |
| Cache way selector | 检查 replacement/refill one-hot 选择；使用 unique-tag invariant |
| Cache Stage2 | 检查 backpressure 下 request payload 稳定 |
| Cache Stage3 | 8-cycle bounded SAT，检查 response provenance/duplicate retirement、reset cancellation 和 stalled response valid/command stability；data arrays 抽象为常量 |

Stage3 检查是**有界安全性检查**，不是无界响应生命周期证明。完整 response data-payload 稳定由仿真 checker 检查；无界端到端响应生命周期证明和 full-cache reset proof 仍是明确的后续方向。CPU 接口约束为稳定保持至完成的单拍 `READ`/`WRITE`，外部 memory 的 refill/writeback 使用八拍 burst；不把 CPU 端不支持的 `READBST` 当作合法请求。

非 gate 的形式探索记录保存在本地 `reports/formal/experimental/`，与 `make formal` 正式 gate 分离。某些探索因 SMT solver `BrokenPipeError` 或未解析的 `SRAMTemplate` blackbox 在求解前结束；这些是 harness/tool setup 失败，不是 property counterexample，也不计为通过的形式证明。分类说明见 [`formal/README.md`](../formal/README.md)。

## 6. 复现方式

在 Ubuntu/WSL 或 GitHub Actions runner 上，从仓库根目录执行：

```bash
cd workspace/nutshell_cache
source scripts/env.sh
make gen_dut
make formal
make report
```

`make formal` 生成 SBY/Yosys 日志；`make report` 运行回归、合并每个 Toffee test 的 Verilator `.dat`、检查 RTL waiver 和 37 项功能 closure，并运行 fault injection。HTML、覆盖率原始数据、波形及生成 DUT 位于本地 `reports/`、`Cache/` 等目录，不作为源码提交；CI 会上传可检查的报告 artifact。

## 7. 范围说明

本项目验证 NutShell DCache 模块边界，不声称验证整个 SoC、真实工作负载性能或流片 sign-off。当前 RTL 的 DCache flush 会触发其设计断言，因此不作为通过用例；shared Stage3 内部保留的 hierarchy-specific burst 分支也不等同于 CPU 端合法接口。项目重点是展示 Python 驱动的自检环境、独立参考模型、协议/时序检查、覆盖率闭环、开源仿真与可解释的形式属性。
