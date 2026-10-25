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
