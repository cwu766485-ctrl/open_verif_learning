format:
1. Chinese
2. update each time when you editing
3. 当前时间戳+对代码进行的修改/遇见的bug/其他值得记录的事情
4. 每次记录尽可能简短

## 2026-10-28（新加坡时间）
- 01:18：收口前复核发现 dense-set 20-seed 压力只由本地 `coherence_verify` 调用，root GitHub Actions 工作流仍有 30 分钟 Coherence timeout；将远端 workflow 纳入本次签核改动，并计划延至 120 分钟，避免全套形式验证与压力回归被超时取消。
- 01:19：加入真实 `MesiL1Controller.sv` 的两处协议变异（M-owner 远端读降级、owner-data 响应标记），以模块 checker 必须拒绝变异 RTL；2/2 捕获。另加 AXI 顶层 R-only、B-only、R+B 五周期响应反压，三种模式均保持 payload/ID/RESP/LAST 并正常排空。
- 01:19：新增 Directory cold-GetS bounded progress harness。首轮断言错误地要求 Grant 周期仍有目录写使能；实际握手已提交并撤销写使能。修正为核对提交后的目录状态/数据，再跑 24-step BMC PASS。该结果只覆盖公平环境下的有界 GetS 路径，不声称无界活性。
- 01:32：完整 `make COHERENCE_JOBS=2 coherence_verify` 退出码 0：模块/总线与 AXI 回归通过；Coherence formal 7/7；SV 38/38 bins、91.6% 汇总行覆盖（RTL 1579/1823，TB 1534/1578）；Python 24/24、功能 36/36、cross 12/12、checker 注错 9/9；AXI Python 3/3；标准与 dense-set 压力各 20 seeds × 200 操作通过；RTL mutation 2/2。
- 01:33：按最新 LCOV 生成 `docs/coherence_coverage_gap_review.md`，把 288 条未命中拆为 RTL 244 条、SV TB 44 条，列出逐文件行号和可测试风险，不将未覆盖防御分支笼统豁免。更新 v1.0.1 manifest 与最终报告；PPA/SRAM 仍排除。
- 10:03：收口源提交 `38fdb74062a8416563e5824589256e1f5d836785` 的 GitHub Actions run `40552490749`：Legacy/Formal 与 Coherence 两个 Job 的所有步骤均 PASS，Dense-set 已由默认 `coherence_verify` 覆盖。同步将 release manifest 和最终报告状态改为 CI 全绿；PPA/SRAM 仍不在范围内。
- 10:24：重写项目首页，增加 MESI 架构、验证状态、仿真性能和运行入口；整理 Directory Lookup、Grant/Snoop 握手分歧、dense-set PutM/Snoop 死锁三个 Bug 案例，并把六类未命中合法恢复路径单列到 v1.1 backlog。该文档候选提交推送后需完整重跑两个 CI Job，再作为正式 Tag 候选。

## 2026-10-29（新加坡时间）
- 10:50：提交 `87ea0d3` 的 `cache-regression` 与 `coherence-regression` 均 PASS。复核发现 GitHub 首页文件名应规范为 `README.md`，已完成大小写改名；此文件名收尾会形成新的候选 SHA，并重新运行完整 CI 后再决定打 Tag。
- 14:41：同步最新验证产物：Python Functional Coverage Closure 达到 37/37；标准与 Dense L2 stress 各 20/20 通过。仅更新报告与日志，RTL 未变。
- 18:40：冻结文档澄清 Directory 4-context/共享端口与同 set 序列化、协议 Opcode、ID 参数和逻辑 SRAM 边界；RCV-01 标记为合法 L1 不可达，RCV-02/03 对应独立 Python checker 已闭环。新增 stale Upgrade 覆盖后，文档候选更新为 Python 26 tests、38/38 bins；最终 Actions 待本次推送复核。
- 18:40：将 `put_xfer_start_core` 移出 Snoop payload `always_comb`，消除 Verilator 对过程级依赖产生的 `UNOPTFLAT`；删除 MSHR bank 未读的 `req_opcode_q` 状态。产品顶层 lint 已重跑，正在执行 MSHR/集成及全量回归。
- 18:47：完整回归发现 MSHR formal 仍引用被删除的 `req_opcode_q`；改由 harness 从已握手请求独立记录每个 context 的 Opcode，避免 checker 依赖实现冗余寄存器，重跑 formal 与全门禁。
- 19:08：全量 `make COHERENCE_JOBS=2 coherence_verify` 以退出码 0 完成：组件仿真、AXI 集成、7/7 bounded formal、SV 38/38 bins（91.6% 汇总行覆盖）、Python 26/26（38/38 功能 bins、12/12 cross、checker fault injection 9/9）、AXI Python 3/3、标准及 Dense-set 各 20 seeds × 200 操作、RTL mutation 2/2 均通过。重编译确认产品顶层 lint 无 Warning、集成 TB 无 `UNOPTFLAT`；TB 保留已分类的空端口/位宽/未使用信号提示。最终候选仍需以推送后 Legacy 与 Coherence Actions 均通过签核；PPA/SRAM 不在范围内。
- 19:11：更新最终报告与签核摘要后，默认 Python 环境缺 `reportlab`，改用项目已有 `.tooling/report-pdf-venv` 重建 PDF 成功；本地工作目录无 `.git` 元数据，GitHub 同步需基于远端 `cache_coherence` HEAD 创建快进提交。
- 20:24：整理 `docs/`：当前 MESI 规格、验证计划、Benchmark v3 与签核材料保留为主文档；旧单 L1 基线移入 `archive/legacy/`，旧 benchmark 结果移入 `archive/benchmarks/`，历史架构、平台说明和更新日志归档。补充归档索引并修正报告链接；未删除历史内容，未修改 RTL。
- 22:49：收口 v1.1 backlog 的 RCV-03：新增 Python/Toffee 定向竞态，独立匹配 Snoop ACK 的 target/txn、PutM→PutAck 与 GetS→DATA_E 的 txn ID、ACK 后 L2 hit、脏数据和最终 U/E 权限；补充请求/Grant opcode 与 ID 监视，区分合法 PutAck。完整 Python suite 25/25、覆盖 37/37 与 cross 12/12；AXI 顶层 lint/elaboration 通过（有一条既有 `DirectoryMshrBank.req_opcode_q` unused 警告）。等待本次 GitHub Actions 完整复核。
- 23:21：GitHub Actions run `40710699152`（提交 `bd0b7e2`）Legacy 与 Coherence 两个 Job 均 PASS；Coherence Formal 7/7、SV 功能覆盖 38/38、Python 25/25 与 37/37 bins、checker 注错 9/9、RTL mutation 2/2、标准及 dense-set 压力各 20/20 seeds。日志确认 ACK→L2 定向用例通过。同步修正 Coverage Gap Review：该风险已由 Python/Toffee 关闭，但仍不冒充 integrated SV LCOV 命中。

## 2026-10-27（新加坡时间）
- 19:25：定位并闭合同 L2 set 压力中的 14/20 seed 失败：L1 replacement PutM 与 Directory 尚未握手的 owner-data Snoop 互等；仅在 Snoop 未接受且没有在途 snoop 数据时允许 PutM 先提交，已握手的 owner-data 流仍独占共享 L2 写口。原失败 dense-set 回归现为 20/20 seeds × 200 操作通过。
- 19:25：修正 MSHR formal 对同线 replacement Put 与 stalled Snoop 合法旁路的约束；补充 Directory/L1 harness 缺失 monitor/错误端口，加入同线 Put 序列化和 stalled-Snoop-target coverage bins。六个 bounded formal/cover 目标通过。
- 19:25：最终 `make COHERENCE_JOBS=2 coherence_verify` 退出码 0；SV 38/38 bins、91.6% RTL 行覆盖，Python/Toffee 24/24、功能 36/36、cross 12/12、故障注入 9/9，AXI Python 3/3，标准与 dense-set 压力均 20/20。
- 19:25：完成 D01/D02/D04 与 Test A/B/C 的最终映射；当前候选 Benchmark v3 重跑：L1 warm hit 2 cycles、L2 hit 22 cycles、五 seed mixed workload 17.20 cycles / 0.04957 ops/cycle / 0.46444 B/cycle。修订综合报告与性能签核；PPA/SRAM 不在本次签核范围。当前候选推送与 Actions 复核待完成。
- 19:27：`make gen_dut` 成功；Legacy/Python `make test` 为 46 passed、26 skipped、3 deselected。重建综合验证报告 PDF，并更新总报告回归数据；报告用 Noto/WQY 本地字体生成，字体文件只保存在忽略的 `.tooling/` 环境目录。
- 22:03：将 RTL、Python DV、Formal harness、coverage、benchmark 原始结果及签核报告共 47 个文件推送到 `cache_coherence`，源验证提交为 `0c2c43251ec93f795dd286da42fccefae5373ae8`。该提交的 GitHub Actions run `40516921592` 已创建，检查时 Legacy 与 Coherence 两个 job 均排队；报告明确保留此状态，待 run 完成后再更新结论。
- 22:26：Actions run `40516921592` 的 Coherence job PASS；Legacy job 仍停在 apt 依赖安装且活动日志不可取。报告改记为部分完成，不把未结束 CI 宣称为全绿；本地 Legacy `make gen_dut && make test` 为 46 passed、26 skipped、3 deselected。PPA/SRAM 仍不在本次交付范围。
- 23:02：核对 Actions 最终状态：run `40516921592` 的 Coherence PASS；Legacy 在 `make formal` 阶段于 45 分钟 job timeout 后取消，后续 regression 未执行。确认 Makefile 已有 `coherence_dense_set_stress`，且 `coherence_verify` 和已通过的 Coherence job 会执行它；图中关于缺少该门禁的描述已过期。将 Legacy job timeout 提至 90 分钟并保留完整 Formal/Regression；同步修正 v1.0.1 说明中旧的 dense-set 14/20 失败数据，等待完整 Actions 重跑后再固定版本。
- 23:04：推送 follow-up commit `75a7533107c4c0f279dbfe7ebbcb9bc8f0c00b81`，将 Legacy CI timeout 从 45 提至 90 分钟，并同步 release manifest 与最终报告。完整 Actions run `40527215667` 已启动；等待 Legacy Formal/Regression 和 Coherence 全部结束后再固定 v1.0.1。
- 23:27：完整 Actions run `40527215667` 在验证提交 `75a7533` 上结束，Legacy/Formal 与 Coherence 两个 job 均 PASS；Makefile 标准压力及 dense-set 20 seeds × 200 已在 CI 回归中执行。同步修正 v1.0.1 manifest、综合报告和性能签核，记录旧 45 分钟取消原因及 90 分钟完整重跑结果。PPA/SRAM 物理实现仍排除；v1.0.1 已具备发布条件，尚未创建 tag/Release。
- 23:31：复核远端交付和 Actions job steps，确认 `cache-regression` 的 Formal/Regression 与 `coherence-regression` 均成功；清除 Release Manifest 中遗留的“待 CI”措辞，修正报告表格并重建 PDF。GitHub 连接器可更新分支但没有 tag/Release 创建接口，因此只将 v1.0.1 标记为 release-ready，未伪造发布标签。

## 2026-10-27（新加坡时间）
- 17:05：按 D01/D02/D04 新增 message-passing、100 代 DATA/READY/ACK 与 false-sharing A/B Python/Toffee 测试、coverage map 和 Testplan 说明；文档明确这些 litmus 只验证 LSU 驱动顺序下的一致性，不代表 ISA memory-ordering 证明。
- 17:05：复现九条随机 Cache Line 映射到同一 L2 set 的压力失败。首个 Snoop 路径互锁未消除 seed `0x5eed` 的 operation 65 协议错误/CPU 超时；增加错误来源诊断，RTL 根因仍待闭环。
- 18:11：回放 seed `0x13e3779b9` 定位 L1 Array 将持有 MESI_E 权限的合法 Store 误报为错误（Store 检查只接受 M）；修正为 Store 原子写数据并完成 E→M，重放消除了该 Array fatal，但仍暴露 Directory owner 与模型结果不一致，压力问题尚未关闭。
- 18:12：为 Directory commit monitor 与压力失败诊断补充仿真周期/已接收请求记录，以区分并发 RTL 提交顺序与参考模型排序。
- 18:13：确认同一 seed 的 Directory 错 owner 根因：并行 MSHR 共用实时 req bundle，Snoop 等待期间后到的 PutM 改写了前一 GetM 的 fallback owner/opcode。DirectoryController 现锁存 opcode 并在恢复时使用事务内 src/opcode；新增对手请求覆盖该 Snoop-ACK→L2-refill 恢复路径。
- 18:14：Directory directed bench elaboration 指出 testbench `.*` 漏接既有 `protocol_error_code` 端口；补齐连接后继续回归。
- 18:15：Directory bench 旧用例仍把 owner SnoopRead 的 ACK 当作 fatal；该协议路径已设计为从 L2 恢复，故将期望更新为 refill+GetS/GrantE 检查，不再把合法恢复判成错误。
- 18:16：`make coherence_directory` 通过；新增用例在活动 GetM 等 Snoop 时改写共享请求输入为另一核 GetS，验证恢复仍按原事务写 owner0 并返回 GrantM；GetS 缺 owner data 的 L2 重取路径也通过。
- 18:19：强制 clean rebuild 后，原失败 seed `0x13e3779b9` 的双核/同 L2 set 回放 PASS；原先 Store E-state fatal 与 Directory owner 污染均未再出现。
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
- 2026-10-25 10:14 +08：从 `coherence_benchmark_starter` 导入工具并跑完六组 workload；数据现归档于 `docs/archive/benchmarks/coherence_benchmark_results_2026-10-25.md`，完成后恢复临时扩展的 SV harness。
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
- 2026-10-26 20:43 +08：收敛 Coherence 顶层 lint：移除 Cluster 重复组合上报的 L1 line-read miss（Array 已锁存错误），拆分 Subsystem 握手组合锥，并让 fatal 后已发出的内存响应可排空；两个产品顶层 lint 均零 Warning。修复 Legacy fault-injection 测试硬编码 4/实际 9 的过期断言。`make test` 46 passed；`make coherence_verify`、SV 34/34 bins、Python 20/20、AXI 3/3、压力随机 20 seeds/4,000 ops 与全部 bounded formal 通过；RTL 行覆盖 92.8%。
- 2026-10-26 22:16 +08：补独立 L1 victim→PutS/E/M 对照、dirty-owner 与双 sharer 的九行 L2 live-victim 压测前导；发现 reference model 漏推进 PutM/owner-data 写后的 L2 replacement pointer，已补并由 20 seeds/4,000 ops 回归。覆盖为 Python 30/30、stress 710 次 L1 eviction / 3 次 live L2 eviction（含 dirty、shared）、SV 34/34 与 92.8% 行覆盖；Legacy 46 passed、AXI 3/3、checker injection 9/9、bounded formal 6/6，两个产品顶层 lint 0 Warning。另试九条随机读写均压同一 L2 set 并发，14/20 seeds 出现 Directory mismatch 或 response timeout/protocol error；记录为未闭合 stress 限制，不计入通过项。修复 stress 配置生成器的 Python 布尔值拼写后，独立 `make coherence_stress` 20/20 通过；完整 Actions 需在最终推送提交上复核。
- 2026-10-26 23:57 +08：在候选源提交 `20bd7df` 上重跑 `coherence_benchmark_v3` 与 `coherence_axi_e2e`，分别 1 项 cache benchmark pytest 通过、AXI 顶层 5 seeds 全通过。确认 L2 hit 32/32 为 22 cycles、0 次后备内存读；AXI 平均延迟 29.206 cycles、吞吐 0.03383 ops/cycle、流量 0.75415 B/cycle。检查后发现旧 benchmark 文档的五 seed 混合均值与保存 JSON 不一致，按原始行修正为 17.538→17.259 cycles、0.04865→0.04960 ops/cycle、0.45575→0.46467 B/cycle。
- 2026-10-26 23:57 +08：新增最终性能签核摘要，明确候选/基线 SHA、Python/Picker/Verilator 环境、P3 Grant 预取与 P2 clean Snoop A/B、AXI 五 seed 指标、独立 scoreboard 观察点及限制；把 20 seed × 200 操作槽的随机压力与 latency/BW benchmark 分开映射，避免把功能压力计数当成性能数据。最新 GitHub Actions run `40338433620` 在 `20bd7df` 上 Legacy 与 Coherence jobs 均 PASS；PPA/真实 SRAM 和全同 L2 set 的激进随机并发仍不在已通过范围内。
