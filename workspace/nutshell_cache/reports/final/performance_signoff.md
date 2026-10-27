# NutShell MESI v1.0 性能签核摘要

**结论：** 已完成 MESI v1.0 的仿真性能与功能验证交付。Benchmark A/B、AXI 顶层数据和随机压力分别说明性能趋势、总线流量和协议/数据压力；它们不是同一种指标，也不合并成一个吞吐数字。性能数字来自表中注明的 benchmark 候选源版本；之后的并发正确性修复另以完整回归和同组压力测试验收。结果可用于课程/项目展示和设计讨论，不等同于 ASIC/FPGA PPA 或真实应用性能签核。

## 版本与复现环境

| 项目 | 记录 |
| --- | --- |
| 分支 | `cache_coherence` |
| 本次基准对应源提交 | [`0c2c43251ec93f795dd286da42fccefae5373ae8`](https://github.com/cwu766485-ctrl/open_verif_learning/commit/0c2c43251ec93f795dd286da42fccefae5373ae8) |
| 性能 A/B 基线 | `231894463fc26c3e40211402a212ffae9412c44c`，Benchmark v3 优化提交 `e3008dc` 的父提交；比较的是 Grant 读预取优化前后 |
| 基准复跑时间 | 2026-10-27 19:23，新加坡时间；当前修复候选上重跑 Benchmark v3 |
| 仿真时钟 | 10 ns 周期（100 MHz 仿真时钟） |
| 工具 | Python 3.12.3、pytest 9.1.1、Picker 0.9.0、Verilator 5.053 devel (`v5.052-521-g6388139f7`)、Toffee pytest 插件 0.2.0 |
| Cache benchmark 内存 | 可读写 64-byte line 模型；可配置 2/20/50/100-cycle 响应延迟 |
| AXI benchmark 内存 | 独立可读写 AXI RAM 模型，64-byte INCR burst、独立地址/ID/beat/write-response 检查 |

基线 JSON/CSV 不含源代码 SHA。基线 SHA 根据 Git 历史确认：`2318944` 是引入 Grant 预取和 Benchmark v3 A/B 结果的 `e3008dc` 的直接父提交。本次 cache 和 AXI 候选性能数据均在源提交 `0c2c432` 对应的修复候选上复跑；同一源快照同时完成 `coherence_verify`。该提交对应的 GitHub Actions run [40516921592](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40516921592) 已创建，报告更新时仍在队列中，完成后再补录结论。`release/v1.0` 仍保持冻结。

复跑命令：

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_benchmark_v3 coherence_axi_e2e
```

## RTL 优化与 A/B 性能

**P3：Grant 与共享 L2 读预取重叠。** Directory 的 data Grant 被接受时，同周期发起对应的 L2 line read；阵列接受后直接进入数据流，若阵列未 ready 则保留原重试路径。独立断言检查 Grant 地址与预取地址一致。

| 工作负载/指标 | 预优化基线 | 当前候选 | 变化 |
| --- | ---: | ---: | ---: |
| Warm L1 read 平均延迟 | 2 cycles | 2 cycles | 不变 |
| L1 replacement 后 L2 hit，32 个样本 | 23 cycles | 22 cycles | 少 1 cycle（4.35%） |
| Cold miss 串行，内存延迟 2 cycles，16 个请求 | 608 cycles | 592 cycles | 少 16 cycles（2.63%） |
| 双核并行 cold miss，内存延迟 2 cycles，16 个请求 | 424 cycles | 408 cycles | 少 16 cycles（3.77%） |
| 双核并行相对串行加速比，内存延迟 2 / 100 cycles | 1.434× / 1.904× | 1.451× / 1.917× | 同负载窗口比值 |
| Ownership write ping-pong，16 次写 | 25.44 cycles | 24.50 cycles | 少 0.94 cycle（3.69%） |
| Dirty L2 victim，100-cycle 内存延迟 | 259 cycles | 258 cycles | 少 1 cycle |

L2 hit 专项测试覆盖四档内存延迟下共 32 次访问；每次均为 L1 miss/L2 refill hit、返回值通过独立数据检查、后备内存读数为 0。双核 cold-miss 在 2/20/50/100-cycle 延迟下分别测量，候选双核并行窗口为 408/547/752/1152 cycles，候选串行窗口为 592/886/1408/2208 cycles。

五个 fixed-seed 混合 workload 的均值如下。每个 seed 有独立 architectural scoreboard 和目标行最终读回；该结果用于观察混合流量趋势，L2 hit 的直接优化证据仍是上表的 32 样本专项测试。

| 指标 | 基线 | 当前候选 | 变化 |
| --- | ---: | ---: | ---: |
| 平均请求到响应 | 17.538 cycles | 17.200 cycles | -1.93% |
| 每 seed 平均 ops/cycle | 0.04865 | 0.04957 | +1.91% |
| 平均内存流量 | 0.45575 B/cycle | 0.46444 B/cycle | +1.91% |
| 每 seed P95 延迟范围 | 60–64 cycles | 59–65 cycles | 最大值增加 1 cycle |

**P2：clean Snoop 与 L2 refill 并行。** 单独的固定 seed A/B 记录在 [`p2_clean_snoop_fill_ab.json`](../../benchmarks/results/p2_clean_snoop_fill_ab.json)。两种变体都保留 ready/valid 握手修复，只改变 clean invalidation 是否可与 refill 数据写入重叠：Core1 Store 响应从 14 降至 10 cycles（28.57%）；refill 响应均为 36 cycles。dirty-owner Snoop 仍等待共享 L2 数据写口。该项是单一竞争场景的定向结果，不是广泛 workload 的平均提升。

## AXI 顶层性能

AXI 顶层使用五个固定 seed，每 seed 64 个 CPU 请求；读写 RAM 检查 64-byte burst、ID、beat、响应和读回数据。表中是五个 seed 的算术平均值：

| 指标 | 预优化基线 | 当前候选 | 变化 |
| --- | ---: | ---: | ---: |
| CPU 请求到响应均值 | 29.913 cycles | 29.206 cycles | -2.36% |
| 吞吐 | 0.03309 ops/cycle | 0.03383 ops/cycle | +2.23% |
| AXI 读流量 | 0.55392 B/cycle | 0.56627 B/cycle | +2.23% |
| AXI 写流量 | 0.18378 B/cycle | 0.18788 B/cycle | +2.23% |
| AXI 总流量 | 0.73770 B/cycle | 0.75415 B/cycle | +2.23% |
| 每 seed P95 延迟算术平均 | 87 cycles | 88 cycles | +1 cycle |
| 最大并发读 burst | 2 | 2 | 不变 |
| AR/AW/W stalls | 每 seed 均非零 | 每 seed 均非零 | 已施加并计数 |
| R/B stalls | 0 | 0 | 此顶层 workload 未覆盖 |

完整 cache top 的双 L1 控制器仍是 blocking，因此 AXI 顶层 workload 只观察到最多两个并发读 burst；四笔 outstanding 与五通道反压由独立 AXI adapter 验证，不能据此声称整机有四个并行 CPU miss。

## 压力回归与并发问题闭环

`make coherence_stress` 的最新归档结果是 20 个固定 seed × 200 个随机操作槽，共 4,000 个槽；其中记录了 660 个双 lane 请求对。它的目标是功能/协议覆盖，不采样 latency 或 bandwidth，不能和 Benchmark 的 ops/cycle、B/cycle 直接相加或互相替代。

| 压力回归观察 | 对应的性能 workload | 两者各自回答的问题 |
| --- | --- | --- |
| cold read/write、L1 hit、L2 refill hit/miss | Warm L1、L2 hit after L1 replacement、serialized/parallel cold miss | Stress 证明数据/状态路径可工作；Benchmark 测相应受控初态下的延迟和吞吐 |
| 双 lane 不同地址请求、同地址 MESI 竞争 | Parallel dual-L1 cold miss、seeded mixed dual-core | Stress 检查并发一致性；Benchmark 只报告固定配对/固定 seed 的性能样本 |
| Remote GetS/GetM、Shared upgrade、owner data | Ownership write ping-pong、seeded mixed dual-core | Stress 核对数据、权限、目录及 owner 数据；Benchmark 量化所选序列的响应时间 |
| L1 eviction、dirty-owner L2 victim、两核共享 S victim | Dirty L2 victim writeback、独立 L1 victim/Put test | Stress 的 9-line 前导强制真实 live victim 并校验 snoop、数据和回收；Benchmark 测定向 dirty victim 的周期数 |
| 反压与并发事务 | AXI 顶层 workload、独立 4-outstanding adapter stress | Stress 回归 line-memory/一致性进度；AXI workload 统计总线 burst 和带宽 |

标准压力覆盖文件报告：710 次 L1 eviction、3 次模型观测到的 live L2 eviction，其中 1 次 dirty-owner victim、1 次双 sharer shared victim；同时记录 1,744 次 L2 refill hit、539 次 refill miss、542 次从 M owner 读取、439 次 shared upgrade。9-line victim 前导检查 dirty writeback 响应、reload 数据、两个 sharer 的失效和目录最终状态。原始数据见 [`coherence_python_stress_coverage.json`](../../benchmarks/results/coherence_python_stress_coverage.json)、[`stress config`](../coherence/stress/config.json) 和 [`JUnit`](../coherence/stress/results.xml)。

此前将 9 个随机行强制映射到同一 L2 set 并双核并发时，20 seeds 中 14 个触发 Directory 状态错误、协议错误或响应超时。回放将根因缩小为 replacement PutM 与尚未被 L1 接受的 owner-data Snoop 相互等待：PutM 要等数据被 L2 接收，L1 又因等待 PutM 而不能接受 Snoop。当前实现允许 PutM 在该 Snoop 尚未握手、且没有正在进行的 snoop 数据传输时先提交；一旦 owner-data Snoop 已接受，L2 写口仍保持互斥。Directory 对无数据 ACK 继续从权威 L2 行恢复数据。修复后同一 dense-set workload 为 20/20 seeds、4,000/4,000 操作槽通过，且每个 seed 均完成数据、MESI/Directory 状态和事务结束检查。结果见 [`dense-set config`](../coherence/dense_l2_stress/config.json)、[`JUnit`](../coherence/dense_l2_stress/results.xml) 和 [`coverage`](../../benchmarks/results/coherence_python_dense_l2_set_coverage.json)。

本次最终候选验证（2026-10-27）包含 RTL directed/integrated 回归 38/38 功能 bins、91.6% 行覆盖；Python/Toffee 24/24，独立功能 bins 36/36、cross 12/12，fault injection 9/9；AXI Python 3/3；标准与 dense-set 随机压力分别为 20×200 PASS。6 个组件级 bounded formal/cover 目标通过，不代表双核顶层无界证明。D01/D02/D04 分别由 message-passing litmus、同/异 cache-line false-sharing 对照、coverage/testplan/scoreboard 证据链覆盖；新增 Tests A/B/C 为这三个 Python litmus，均通过。

独立 `CoherenceScoreboard` 不读取 DUT 的推导 MESI 状态；它维护逐 word architectural data、两个 L1 的 MESI 副本、byte mask、L1/L2 replacement 和由副本推导的 Directory owner/sharer。监视器以已接受的 Put、Snoop、数据 beat 和 Directory commit 与模型对照；每个随机 CPU 操作后比较目录，并对写操作做读回。随机 stress 模式让 DUT 选择真实 L1 victim，通过已接受 Put 更新副本模型，故不在该随机模式里二次预测 victim way；victim-way 预测另由独立 directed L1 replacement→Put 测试检查。

源验证提交 [`0c2c432`](https://github.com/cwu766485-ctrl/open_verif_learning/commit/0c2c43251ec93f795dd286da42fccefae5373ae8) 对应的 GitHub Actions run [40516921592](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40516921592)：Coherence job 已 PASS；Legacy job 截至 2026-10-27 22:26（新加坡时间）仍卡在 `Install open-source RTL toolchain dependencies`，GitHub 未提供活动步骤日志，故整个 Actions run 尚未完成。Legacy 本地 `make gen_dut && make test` 为 46 passed、26 skipped、3 deselected。此前 run [40338433620](https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/40338433620) 对应旧源提交 `20bd7df`，不替代本次结果。

## 限制与签核边界

- 当前通过的 dense-set test 是固定的 9-line same-set 前导加双核随机/反压混跑（20 seeds × 200 operations），不是对所有可能 L2 set 交错、外部时序和系统活性组合的穷举证明；bounded formal 也不替代该完整性证明。
- 仿真 10 ns 是 testbench 时间刻度，不是目标芯片时钟约束。B/cycle 是模型接口计数，不是 DRAM/芯片真实带宽；未跑 Fmax、面积、功耗、SRAM macro 映射、综合或布局布线。
- 当前没有真实 CPU/application workload；微基准使用固定地址、固定 seed、可控内存响应延迟和指定初始 cache 状态。
- 双核 blocking L1、共享 Directory/L2 数据端口会限制端到端并行；AXI adapter 的四笔 outstanding 不等于 cache top 支持四个未完成 CPU miss。
- 当前 Formal 为 6 个组件级、有界目标；不构成整个双核系统的无界证明。

## 原始结果与复现入口

- Cache v3：[`JSON`](../../benchmarks/results/coherence_benchmark_v3.json) / [`CSV`](../../benchmarks/results/coherence_benchmark_v3.csv)
- A/B baseline：[`JSON`](../../benchmarks/results/coherence_benchmark_v3_baseline.json) / [`CSV`](../../benchmarks/results/coherence_benchmark_v3_baseline.csv)
- AXI 顶层：[`JSON`](../../benchmarks/results/axi_top_benchmark_v3.json) / [`CSV`](../../benchmarks/results/axi_top_benchmark_v3.csv)
- AXI baseline：[`JSON`](../../benchmarks/results/axi_top_benchmark_v3_baseline.json) / [`CSV`](../../benchmarks/results/axi_top_benchmark_v3_baseline.csv)
- clean Snoop A/B：[`JSON`](../../benchmarks/results/p2_clean_snoop_fill_ab.json) / [`CSV`](../../benchmarks/results/p2_clean_snoop_fill_ab.csv)
- stress coverage：[`JSON`](../../benchmarks/results/coherence_python_stress_coverage.json)
- dense same-set stress coverage：[`JSON`](../../benchmarks/results/coherence_python_dense_l2_set_coverage.json)
- false-sharing D02 A/B：[`JSON`](../../reports/coherence/false_sharing_ab.json)

