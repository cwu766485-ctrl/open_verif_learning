format:
1. Chinese
2. update each time when you editing
3. 当前时间戳+对代码进行的修改/遇见的bug/其他值得记录的事情
4. 每次记录尽可能简短
## 2026-10-24（新加坡时间）
- 20:24：拆分请求仲裁器的 valid/payload 与 ready 组合逻辑，定位并消除 `UNOPTFLAT` 组合环路告警。
- 20:28：清理未使用 RTL 信号；目录验证改用 harness 记录已接收 opcode，避免形式验证依赖已移除的硬件状态；补上 L1 阵列读未命中错误上报。
- 20:31–20:36：为四上下文 Directory MSHR bank 增加独立 formal harness、BMC 与覆盖目标。形式化展开暴露 commit 上下文选择的组合依赖；改为匹配向量加优先选择，并映射 SV 数组供 Yosys 处理。
- 20:39：MSHR bank 12 周期有界检查通过；覆盖检查到 2 个及 4 个上下文同时活动。结果是有界证据，不代表无界证明。
- 21:15：汇总近期 RTL/formal 改动并同步到 GitHub `cache_coherence` 分支；后续代码修改完成后立即提交并推送。

- 2026-10-24 21:24 +08：发现本地副本的 `Readme.md` 落后于分支版本；按分支恢复四上下文/AXI说明，避免同步时回退文档。

- 2026-10-24 23:17 +08：按功能重构 RTL，隔离 `legacy_l1`；将 SV bench 与 Python 用例归入 `tests/` 分类目录，并同步 Makefile、filelist、formal、coverage waiver 和文档路径。静态路径审计通过，未重跑仿真/formal。

- 2026-10-24 23:17 +08：发现 `.gitignore` 仅放行 `tests/**/*.py`，迁入的 SV bench 会被忽略；补充 `.sv/.v` 例外并确认新目录文件可纳入提交。

- 2026-10-24 23:36 +08：复现子系统仿真编译失败，根因是 TB 读取已拆分的 L1 私有 metadata 信号。增加顶层 Array metadata commit 监视端口；参考 MESI 状态不再从 DUT commit 状态回填，而由 CPU 请求、snoop/Put 事务推演。
- 2026-10-24 23:36 +08：功能覆盖闭环改为按 checker 完成后输出的结构化 `COV_EVENT` 记录计数，覆盖表增加 stimulus/checker 与 MESI/请求者/snoop/data/beats 事务轴；旧 PASS 文本不再计 bin。
- 2026-10-24 23:36 +08：`make coherence_formal` 全部目标通过；修复后的 RTL/TB 首轮 elaboration 已通过，正在重跑完整仿真回归。
- 2026-10-24 23:43 +08：完整 verify 首次运行在 cluster bench `.*` 接口检查处失败；为 cluster bench 补接 metadata monitor 并断言两个 refill commit。模块测试通过。
- 2026-10-24 23:43 +08：新增 `DirectoryMshrBank_tb`：验证四个不同地址并行上下文、同地址抑制、第五笔请求反压、逆序 refill 完成、目录写/Grant 反压、单上下文等待 snoop 时其余三笔进展，以及四上下文活动时 reset 取消；定向仿真通过。
- 2026-10-24 23:47 +08：修复完整回归的第二处 monitor 缺口：参考模型漏记 L2 live victim 对 L1 的 back-invalidation，曾误报 Core1 残留 M 副本；改为按 core 导出已握手 snoop monitor，参考状态由协议事件推演，不采样 DUT 期望状态或 FSM 编码。
- 2026-10-24 23:54 +08：修复 TB 旧层级 metadata 引用；完整 directed + 5 seeds、独立 4-context MSHR 压力仿真通过，结构化覆盖 34/34，RTL 行覆盖 93.1%；AXI lint/E2E 与 6 个 formal BMC/cover targets 全通过（有限深度）。顶层仍有非致命 `UNOPTFLAT`/未使用信号告警。

- 2026-10-25 10:14 +08：修复 Mutation runner 的 RTL 重构路径遗漏（CacheStage3、MetaWriteArbiter、DataWriteArbiter）；本机 formal mutation 4/4 成功捕获注入错误。
- 2026-10-25 10:14 +08：修正 benchmark hit/miss 口径：统计 CPU 请求握手时的 L1 MESI 状态，S 态 Store 记为 Upgrade Miss；ready 等待与响应延迟分开计数，并断言 TB 分类与 RTL perf event 一致。
- 2026-10-25 10:14 +08：从 `coherence_benchmark_starter` 导入工具并跑完六组 workload；数据记录在 `docs/coherence_benchmark_results_2026-10-25.md`，完成后恢复临时扩展的 SV harness。
- 2026-10-25 10:14 +08：增加 Picker packed-port wrapper、Python CPU/line-memory agents、独立 MESI/data scoreboard 和首个 owner-transfer pytest。曾因 async fixture 在 Toffee 时钟 loop 外等待而卡住；将时钟初始化移入 testcase loop 后，Python MESI smoke 通过。SV benches 暂留作迁移对照基线。
- 2026-10-25 10:28 +08：完整回归揭示 reset 取消的 6 笔已接收 miss 造成 hit/miss 对账差异；拆分 accepted 事件对账与 completed latency 样本后，`make coherence_regression` 通过，功能覆盖 34/34、RTL 行覆盖 93.2%。
- 2026-10-25 10:28 +08：`make formal` 全部通过，包括 coherence/legacy BMC、cover、SAT 检查和 Mutation Testing 4/4；`make test` 为 46 passed、1 skipped、2 deselected。修正 Picker 输出目录复用问题后，`make coherence_python_test` 从干净构建通过（1 passed）。
- 2026-10-25 10:28 +08：补充 `.gitignore` 放行 `dv/` 下的 SV wrapper，确保新 Picker DUT adapter 能随 DV 源码同步。
- 2026-10-25 13:51 +08：Benchmark v2 加入逐级 L1/L2 hit/miss rate 与读、写、总带宽；发现 dirty L2 victim workload 会污染后续读测试初态，将其移到全部延迟档位之后。四档主 workload 与 100-cycle dirty writeback 均通过，Python 3/3、覆盖闭合 13/13。
- 2026-10-25 13:51 +08：重跑模块/AXI RTL、bounded Formal 与 coherence regression：均通过；34/34 功能覆盖、RTL 行覆盖 93.1%。顶层 testbench 仍有非致命 UNOPTFLAT 和 lint 提示。
- 2026-10-25 13:53 +08：Picker/Verilator wrapper clean rebuild 后 `make coherence_python_verify` 通过，3/3 pytest、13/13 Python functional bins。
- 2026-10-25 14:06 +08：GitHub Actions 中 RTL、Formal、SV regression 与 coverage 均通过，但 coherence job 的 Python 阶段因独立 runner 缺少 Picker 失败；给 root workflow 补装 pinned Picker 和 Python DV 依赖并重新触发 CI。
- 2026-10-25 15:06 +08：扩展 Toffee 定向与 4 个固定随机种子；加入活动 refill reset、CPU/AXI 多通道反压、owner 数据传输与 Directory commit 独立检查，Python 覆盖闭环 22/22。
- 2026-10-25 15:10 +08：随机回归复现共享 L2 查找口竞争：Transfer/Grant 查找期间新 Directory context 采到错误行的旧目录状态。用 `dir_lookup_available` 同时门控 MSHR 输入 valid 与上游 ready，阻止错误分配；增加查找地址断言及握手后的 snoop/data/目录监视。
- 2026-10-25 15:15 +08：Python/Toffee 端到端 10 项通过；SV directed、5 随机种子及四 Context MSHR 压力回归通过，功能覆盖 34/34、RTL 行覆盖 93.1%。Formal 全目标正在重跑。
- 2026-10-25 15:19 +08：`make COHERENCE_JOBS=2 coherence_formal` 全目标通过，含仲裁器、Directory、MSHR bank 与 L1 Controller 检查；其中 BMC/覆盖深度有限，不作为无界证明。
- 2026-10-25 19:19 +08：Grant 竞争定向复现出第二层握手 bug：仅压低 Directory ready 未压低 L1 Grant valid，L1 已消费 Grant 但顶层引擎没有启动对应数据流，导致响应永久等待。现对 valid/ready 同步仲裁并加断言；相位扫描命中 transfer/grant 冲突后，两路响应及独立数据检查通过。
- 2026-10-25 19:19 +08：修正 Benchmark 阶段采样：L1 miss 以内部握手事件为准，避免 wrapper ready 采样相位丢失 L1→Directory 样本；给固定随机种子加入确定的一周期内存请求反压。Python/Toffee 16/16、功能 bins 26/26、cross 8/8，AXI4 五通道压力测试 1/1；完整 formal 与 SV 回归待重跑。
- 2026-10-25 19:25 +08：修复后的顶层 directed + 5-seed SV coherence 回归通过，功能覆盖 34/34、RTL 行覆盖 93.1%；四 Context MSHR 压力、逆序 refill、snoop 独立进展和活动 reset 均通过。
- 2026-10-25 19:25 +08：`make COHERENCE_JOBS=2 coherence_formal` 全部目标通过；Python/Toffee 16/16、Python 功能/cross 覆盖 26/26 与 8/8、AXI4 Python 五通道压力 1/1。Formal 为有界/组件级证据；GitHub Actions 全量 CI 待本次推送后确认，PPA 未运行。

## 2026-10-25（新加坡时间）
- 20:52：Benchmark v3 增至 32 个独立 L2 hit 样本和五个 Python mixed seed；AXI 子系统顶层增加五种子 burst/反压/吞吐采样，JSON/CSV 与 baseline 一并保存。
- 20:52：A/B 优化在 data Grant 接受时预发 L2 line read；32 次 L2 hit 从 23 降至 22 cycles，mixed workload 数据 scoreboard、AXI 顶层五种子和 P3 定向对照通过。
- 20:52：补齐 v1.0 冻结清单、Benchmark v3 报告，并将 Legacy 与 Coherence 分成独立 CI jobs；本机 `make gen_dut && make test` 为 46 passed，`make coherence_verify` 全目标通过（SV 34/34、Python 16/16、Python bins 26/26、6 个 bounded formal targets、AXI adapter 1/1）。
- 20:53：给 v3 加入交付门槛断言（32 个 L2 hit、五个 seed、零后备内存读）；Picker/Verilator 定向重跑 1 passed。

- 2026-10-25 23:03 +08：并发 refill/Store 定向测试复现 ready/valid 分歧：Directory 因 L2 fill 拉低 ready，但 Snoop valid 仍到达 L1；L1 接收、Directory 未接收，响应永久无法匹配。统一 Snoop valid/ready 准入条件并加入握手断言；随后允许不需回收 owner data 的 clean invalidation 与 refill 重叠，owner-data 事务仍等待共享 L2 写端口。
- 2026-10-25 23:03 +08：同一固定 workload A/B 通过数据和 Directory 独立检查；clean Snoop 并行后，Store 响应 14→10 cycles（减少 28.6%），Snoop 接受提前 4 cycles，refill 仍为 36 cycles。原始 JSON/CSV 与方法写入 `benchmarks/results/p2_clean_snoop_fill_ab.*` 和 Benchmark v3 说明。
- 2026-10-25 23:03 +08：重写最终综合报告为 MESI v1.0，加入双 L1/共享 L2+Directory/AXI/APB 架构、验证平台、已知限制、回归结果和 P2 A/B 数据；补充 Markdown-to-PDF 构建器。PPA/SRAM 与更深压力测试按本次范围继续排除。
- 2026-10-25 23:08 +08：PDF 页面检查发现中文链接标签使用 Courier 时缺字；改为 CJK 字体渲染后重新生成两页报告，并用 PDF reader 确认可正常提取全文。

## 2026-10-26（新加坡时间）
- 19:28：20-seed/4,000 笔 Python/Toffee 随机回归发现 refill 与 dirty-owner SnoopRead 争用 L2 写口形成死锁；调整为 refill 独占完成整条 line 后再接收 SnoopRead，并暂停 L1 replacement 期间的 snoop 准入。加入写口保持断言。
- 19:28：随机替换压力暴露参考模型预测 way 与并发失效后的真实替换顺序不一致；改由已握手 Put 事务更新 L1 副本记录，仍独立检查 MESI、Directory 和数据。修复后 `make coherence_stress` 20/20 seeds、4,000 笔通过；formal、Python fault injection（9/9）、功能覆盖（27/27）及 AXI Python（3/3）通过。
- 19:34：全量 `make coherence_verify` 通过：RTL 模块/总线与系统回归、34/34 SV 功能 bins、92.7% RTL 行覆盖、6 个 bounded formal 目标、Python 20/20、故障注入 9/9、AXI 3/3、长随机 20/20。Verilator 仍报告顶层 snoop/写口 `UNOPTFLAT` 及空端口/未使用信号告警，作为后续 lint 收敛项记录。
