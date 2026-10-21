# NutShell 双核缓存一致性子系统微架构规格书（中文）

**文档版本**：v0.2（设计评审草案）  
**日期**：2026-10-20  
**设计状态**：P1 控制 RTL、双 L1/L2 阵列、仲裁器及阻塞式子系统顶层已新增；替换完整性与回归验证仍未完成  
**现有仓库**：`cwu766485-ctrl/open_verif_learning`，分支 `cache_coherence`  
**参考路径**：`workspace/nutshell_cache/`（已验证的单 L1 DCache）、`workspace/nutshell_src/`（NutShell Chisel SoC 源码）

> **设计目标**：保留原有 NutShell Cache 的可复用结构，从单 L1 DCache DV 演进为“双 L1 DCache + 共享 L2 + Directory-based MESI”的缓存一致性子系统，并采用 Block-level → Subsystem-level →（可选）真实 CPU/System-level 的验证流程。首版只研究 **两个 Core 的数据 Cache 一致性**，不把 ICache、真实多核 CPU、DMA 一致性当作已实现目标。

---

## 0. NutShell 的真实硬件基线（本版修订重点）

### 0.1 单核 NutShell SoC（源代码已确认）

```text
                         Single NutCore
                     ┌───────────────────┐
Instruction Fetch ──>│ L1 ICache (read-only) │────┐
LSU Load/Store ─────>│ L1 DCache (writable)  │──┐ │
                     └───────────────────┘  │ │
                               ICache misses │ │
                                  ┌───────────▼─┴───────┐
                                  │ CoherenceManager    │
                                  │ probe DCache first  │
                                  └──────────┬──────────┘
                                             │
                           DCache memory path│
                                      ┌──────▼─────────┐
                                      │ SimpleBus Xbar │
                                      └──────┬─────────┘
                                      Optional Prefetcher
                                             │
                                      Optional L2 Cache
                                       (default 128 KiB)
                                             │
                                     AXI Memory Interface
```

- 在 `workspace/nutshell_src/src/main/scala/nutcore/NutCore.scala` 中分别实例化 `icache`（`ro=true`）和 `dcache`（`ro=false`）。这是**同一个 Core 的两种用途不同的 L1 Cache**。
- 在 `workspace/nutshell_src/src/main/scala/system/NutShell.scala` 中，`CoherenceManager` 接收 ICache 的下级读事务，并可向 DCache 发 Probe，然后把读取路径接到下级 Memory。`Coherence.scala` 显示：**读优先探测 DCache，Hit 时直接获取八拍 Release；Miss 才转向下级存储**。这不是两个 CPU Core 之间的 MESI 协议。
- 同一 SoC 顶层有可选 `l2cache`：`CacheConfig(name="l2cache", totalSize=128, cacheLevel=2)`；`top/Settings.scala` 的默认 `HasL2cache=true`、`HasPrefetch=true`，`EmbededSettings` 则设为 `false`。因此不能说 NutShell 没有 L2；但也**不能保证每种 build profile 都启用 L2**。
- 目前被 `workspace/nutshell_cache/rtl` + Python/Toffee 验证的 DUT **仅是单个 L1 DCache**，不包含上述整套单核 SoC，也不包含多核 MESI Directory。
- 现有 L1 `PROBE=0x8` 命中后释放 8×64bit，但**不使原 Cache Line 失效**。分支测试 `test_probe_hit_keeps_line_for_following_lsu_read` 明确检查 Probe 后再次 CPU READ 依然 Hit。新协议必须定义独立的 `SnoopRead`/`SnoopInvalidate`，不能复用旧 Probe 当作失效命令。

### 0.2 为什么新设计有两个 L1 DCache，而不是一个 ICache + 一个 DCache？

新设计是两个**逻辑 Core** 各自拥有 DCache：`Core0/LSU0 → L1D0`、`Core1/LSU1 → L1D1`。两者会读取/修改同一个物理地址，产生单写者/多读者权限问题。每个真实 Core 将来仍可以拥有自己的 ICache，但 **v1 的 ICache 仅在体系结构图中保留、无需实现，亦不参与新的 MESI 验证**。自修改代码、`FENCE.I` 和 I/D 一致性作为未来独立专题。

---

## 1. 目标、边界和验收条件

### 1.1 目标（v1）

1. 使用两个独立的 LSU Agent 驱动两份 L1 DCache；同一个地址允许在两个 Core 中被访问。
2. 基于目录实现 **MESI**：Modified (M)、Exclusive (E)、Shared (S)、Invalid (I)。
3. 共享 L2 Tag/Data Array；Directory 记录每个 L1 的 Sharer/Owner，并控制最新数据来源。
4. 完成 `GetS`、`GetM`、`Upgrade`、`SnoopRead`、`SnoopInvalidate`、`PutS/E/M`、Grant/Ack 等完整事务。
5. 支持 64 B 整行 8×64bit 数据传输，支持 Byte Mask、Backpressure、阻塞型 Miss、Dirty Writeback 和 Reset Recovery。
6. 建立独立全局 Reference Model、Scoreboard、Functional Coverage、Assertions 及有限范围 Formal Proof。

### 1.2 暂不实现（v1）

- 两个真实 CPU Core、Instruction-side MESI、自修改代码缓存失效、DMA/I/O Coherence。
- LR/SC、AMO、多事务乱序完成、多个 MSHR、跨 Directory Bank 高并发、Prefetch。
- 完整 AXI ACE / CHI 兼容、全系统 RISC-V Memory Model 形式证明。
- 真实芯片 Fmax、PPA 收敛保证。所有性能对比先限定在相同仿真环境的 RTL 周期。

### 1.3 成功标准

- 所有合法 MESI 稳态和必要的暂态转换均有 Directed Tests 与 Checker。
- 对同一条 Line，不存在两个 Modified Owner；任何 M/E 的存在要求另一 L1 为 I。
- Core Read 返回最新数据，Core Write 获得排他权限后才能产生可见修改；没有重复 Grant、丢失 ACK 或脏数据丢失。
- 无穷等待性质仅在明确公平性条件下讨论；有限深度死锁检查不能被声称为无界证明。
- 保留旧 `nutshell_cache` 回归作为升级基线，不能让 MESI 升级掩盖已有错误。

---

## 2. 目标硬件架构与容量配置

```text
   LSU Agent 0                        LSU Agent 1
       │                                  │
   L1 DCache 0                      L1 DCache 1
   32KiB / 4-way                    32KiB / 4-way
   MESI + Snoop FSM                 MESI + Snoop FSM
       │                                  │
       └────────────┬─────────────────────┘
                    ▼
           Coherent Interconnect
       (request/snoop/data/ack channels)
                    │
                    ▼
             Directory Controller
          (Sharers / Owner / FSM)
                    │
                    ▼
            Shared L2 Tag/Data
          256KiB / 8-way [拟定]
                    │
                    ▼
           Backing Memory Model
```

| 属性 | L1 DCache 0/1 | 共享 L2（拟定） |
|---|---|---|
| 容量 | 各 32 KiB | 256 KiB |
| 相联度 | 4-way | 8-way |
| Set 数 | 128 | 512 |
| Cache Line | 64 B | 64 B |
| 数据传输 | 64bit × 8 拍 | 64bit × 8 拍 |
| 写策略 | Write-back + Write-allocate | Write-back，具体回写状态需跟 Directory 协调 |
| 元数据 | Tag + MESI + Replacement | Tag + Directory State + Sharers + Owner + Dirty/有效性 |
| Miss 机制 | v1 Blocking | v1 Blocking |

**寻址**：基于当前测试平台的 32-bit 地址模型。L1：`tag[31:13]`, `set[12:6]`, `word[5:3]`, `byte[2:0]`；L2：`tag[31:15]`, `set[14:6]`, `line offset[5:0]`。

**Inclusive 设计规则**：v1 采用 L2 **Tag/Directory Inclusion**。若任何 L1 持有 Line A，L2 必须保留 A 的目录和 Tag；但 **L2 Data 不一定最新**（L1 的 M Owner 可以具有最新副本）。L2 驱逐 A 时必须先完成对 L1 的 Back-Invalidation / Dirty Owner 数据回收。

**首版事务能力**：每 L1 最多发起 1 笔未完成的 CPU Coherent Miss；全局 Directory 最多处理 1 笔事务。Snoop 接收/响应**不能因为本地 CPU Miss 而永久被阻塞**，需具备独立缓冲、优先处理或显式冲突仲裁机制；否则两个 L1 可能循环等待导致死锁。

---

## 3. L1 MESI 稳态和目录状态

### 3.1 L1 的四态

| 状态 | 数据是否有效 | 允许本地读 | 允许本地直接写 | 说明 |
|---|---|---|---|---|
| I | 否 | 否，须 GetS/GetM | 否 | Line 不在本地 |
| S | 是 | 是 | 否，须 Upgrade | 可能多个 L1 共享，只读权限 |
| E | 是 | 是 | 是：本地 E→M | 唯一且尚未修改，静默升级 |
| M | 是 | 是 | 是 | 唯一 Dirty Owner，最新数据可能不在 L2 |

### 3.2 Directory 的 I/S/U 抽象

| 目录态 | sharers[1:0] | owner_id | 语义 |
|---|---|---|---|
| I | 00 | none | 没有 L1 持有（L2 自己可能存在该 Line） |
| S | 01/10/11 | none | 一个或两个 L1 持有 S |
| U | 00 | Core0 或 Core1 | 一个唯一 Owner，可在 L1 内部为 E 或 M |

**最重要的约束**：由于 E→M 不需要通知 Directory，目录在 U 状态下不能假定 Owner 持有的是干净数据；当其他 Core 请求该 Line，必须先 Snoop Owner，获取正确数据和权限。

**推荐的关键不变量**：

```
L1_0.M  -> L1_1.I
L1_1.M  -> L1_0.I
L1_0.E  -> L1_1.I
L1_1.E  -> L1_0.I
L1_0.S && L1_1.S 允许
Any L1 resident -> L2 tag/directory resident
Directory.U -> unique valid owner
```

只检查 `!(M0 && M1)` 不够，因为还要禁止 `M/S`、`E/S`、`E/M` 等不合法组合。暂态期间需要围绕 Grant/ACK **提交边界**定义 Assertion，不能把合法的过渡过程误判为稳态冲突。

---

## 4. 协议通道与消息定义

### 4.1 物理接口（v1 建议）

- `request`：L1 → Directory；`valid, ready, src_id, txn_id, line_addr, opcode`。
- `snoop`：Directory → L1；`valid, ready, target_id, txn_id, line_addr, opcode`。
- `data_response`：双向/分别布线的八拍数据流；每拍 `data[63:0], beat_idx[2:0], last, txn_id`。
- `ack/grant`：Invalidation ACK、Ownership Grant、Put ACK；含 `txn_id`。
- 所有 Beat 在 `valid && ready` 时传输。`valid && !ready` 时 Payload 必须保持稳定。
- 32-bit 地址按 64B Line 对齐，事务头携带 Line Address；CPU 8-bit `wmask` 是 Word 级 Store 的内部属性，并不是目录权限消息。

### 4.2 请求与控制消息

| Opcode（暂不分配数值） | 方向 | 定义 |
|---|---|---|
| GetS | L1→Directory | 请求读共享权限及数据；无其他 Sharer 时可以授 E |
| GetM | L1→Directory | 本地 I 态请求完整写权限及数据 |
| Upgrade | L1→Directory | 本地 S 态请求写权限，无须重复回传已有行数据 |
| SnoopRead | Directory→Owner | 获取最新 Line，原 Owner 转 S |
| SnoopInvalidate | Directory→Sharer/Owner | 目标释放权限并转 I；若 Owner 可能 Dirty，必须返回权威数据 |
| InvAck | L1→Directory | Shared 副本失效完成 |
| SnoopData | Owner→Directory | 完整八拍最新数据并确认权限释放/降级 |
| DataGrantS/E/M | Directory→L1 | 八拍数据 + 对应最终权限 |
| GrantM | Directory→L1 | 已持有 S 数据时，授予写权限 |
| PutS / PutE / PutM | L1→Directory | 释放对应权限；PutM 含八拍 Dirty 数据 |
| PutAck | Directory→L1 | Eviction/Release 完成，可以释放本地资源 |

**禁止的简化**：不要把旧的 `PROBE(0x8)` 同时解释为 `SnoopRead` 和 `SnoopInvalidate`。它原本不会 Invalidate；MESI 需要显式的动作编码和 ACK 语义。

---

## 5. MESI 状态转移与事务行为

### 5.1 L1 稳态转换

| 当前态 | 事件 | 动作 | 结果态 |
|---|---|---|---|
| I | CPU Read | 发 GetS，接收 DataGrantS/E | S 或 E |
| I | CPU Write | 发 GetM，获得数据+权限后执行 masked write | M |
| S | CPU Read | Hit | S |
| S | CPU Write | 发 Upgrade，等所有 Conflicting Sharers 失效 ACK | M |
| E | CPU Read | Hit | E |
| E | CPU Write | Silent E→M，执行 masked write | M |
| M | CPU Read/Write | Hit | M |
| E/M | SnoopRead | 提供最新 Line，Owner 降级 | S |
| S | SnoopInvalidate | 失效并 ACK | I |
| E/M | SnoopInvalidate | 提供最新 Line、释放所有权 | I |
| S/E/M | Local Eviction | PutS/PutE/PutM，等 Ack | I |

**暂态（建议）**：`IS_WAIT_DATA`、`IM_WAIT_DATA`、`SM_WAIT_ACK`、`MI_PUT_DATA`、`SNOOP_WAIT_DATA`、`EVICT_WAIT_ACK`；同时规定每个暂态中 CPU/ Snoop 的 Ready 行为及 Reset 退出路径。不能只画四个稳态就开始写 RTL。

### 5.2 Directory 事务表

| 当前目录态 + 请求 | 必须执行的行为 | 结束状态 |
|---|---|---|
| I + GetS | 从 L2/Memory 获取 Line；无 Sharer 可授 E | U(owner=requester) |
| I + GetM | 取 Line 并授写权限 | U(owner=requester) |
| S + GetS | 由 L2 提供干净数据；登记新的 Sharer | S |
| S + GetM/Upgrade | Invalidate 其他 Sharers，收齐 InvAck，最后 Grant | U(owner=requester) |
| U + 其他 Core GetS | SnoopRead Owner，回收最新 Line，两个 Core 转 S | S(sharers=11) |
| U + 其他 Core GetM | SnoopInvalidate Owner，回收数据/权限后 GrantM | U(owner=requester) |
| S/U + PutS/E/M | 处理副本移除、Dirty 回收和相应 Ack | I/S/U 之一 |
| L2 Victim + Sharers/Owner | Back-invalidate / 回收 Dirty 数据，必要时写回 Memory，再驱逐 | 目录项释放 |

**授权排序**：不得在冲突 Owner/Sharer 尚未确认释放权限前发出可提交的 `GrantM`。数据 Grant 应在八拍传输完成、权限安全后生效。第一版不做同一 Miss 的 Early Restart。

### 5.3 四个必须实现的事务时序

**场景 A：共享读**

```
初始: L1_0=I, L1_1=I, Directory=I
Core0 Read A -> GetS -> DataGrantE -> L1_0=E, Dir=U(0)
Core1 Read A -> GetS -> SnoopRead(0) -> SnoopData
             -> DataGrantS -> L1_0=S, L1_1=S, Dir=S(11)
```

**场景 B：S/S 升级写**

```
L1_0=S, L1_1=S
Core1 Write A -> Upgrade -> SnoopInvalidate(Core0)
              -> InvAck(Core0) -> GrantM(Core1)
结果: L1_0=I, L1_1=M, Dir=U(1)
```

**场景 C：M Owner 被远程 Read**

```
Core0 持有 A=M，A 的最新数据为 0x1234，L2 可能仍是旧值
Core1 Read A -> GetS -> SnoopRead(Core0)
             -> Core0 返回最新 64B -> Core0 M->S
             -> Core1 收到最新数据并进入 S
结果: 两份 S 数据相同、值最新，Dir=S(11)
```

**场景 D：M Owner 被远程 Write**

```
Core0 持有 A=M
Core1 Write A -> GetM -> SnoopInvalidate(Core0)
              -> 收齐 Owner SnoopData/完成确认
              -> Core1 获得 M 并进行 Byte Mask Write
结果: Core0=I, Core1=M, Dir=U(1)
```

---

## 6. 数据正确性、Reset、Backpressure、死锁约束

1. **单写者 / 多读者**：任意时刻，只有一个 Core 可以持有写权限；两个共享副本都只能处于 S。
2. **最新数据源**：Directory U 下，可能 Dirty 的 Owner 数据优先于 L2/Memory；禁止将旧 L2 Data 当作最新 Line 返回。
3. **Byte Mask**：CPU 写只更新指定 Byte；远程 Snoop 需要返回修改后的完整 64 B。
4. **完整 Transfer**：每次整行数据恰好 8 拍，beat index 正确、不重复、不丢失、`last` 仅在最终拍。
5. **Ready/Valid**：在所有 Channel Stall 期间保持 Valid/Payload；Beat Counter 只在握手时推进。
6. **Snoop 进度**：本地 CPU Miss/Refill 阻塞时，Snoop 不能与 Directory 等待形成循环依赖。实现时必须设计相应 Buffer/优先级/撤销重试路径，并用压力测试验证。
7. **Reset 协调**：初版系统同步 Reset 清除所有暂态、目录所有权和旧 Response；旧请求不得在 Reset 后再次完成。Reset 后需重新初始化目录和 Meta Array。
8. **Eviction**：L1 M→PutM 写回最新数据；L2 Inclusive Victim 必须先处理任何 L1 Sharer/Owner，再驱逐目录 Tag。
9. **MMIO**：仍走原有 Bypass，不参与普通 MESI Line Allocation；必须明确地址域。

---

## 7. 验证总体架构：Block → Subsystem → System

```
Block DV:
  L1 MESI FSM / Snoop Adapter
  Directory FSM / Directory RAM
  L2 Cache Controller / Arrays
  Coherent Arbiter / Router
           │
           ▼
Subsystem DV:
  LSU Agent0 → L1D0 ┐
                    ├→ Interconnect → Directory/L2 → Memory Model
  LSU Agent1 → L1D1 ┘
           │
           ▼
System DV (可选):
  双真实 Core + ICache/FENCE.I + OS/软件工作负载
```

### 7.1 Block-level Test Plan

| 模块 | Directed Cases | Assertions/Coverage |
|---|---|---|
| MESI FSM | I→E/S、I→M、S→M、E→M、M→S、M→I，暂态接收 Snoop | 非法转换、无提前授写权限、所有 State Transition |
| Directory | I/S/U 与 GetS/GetM/Upgrade/Put，Sharers 00/01/10/11 | Unique Owner、ACK 全收齐、Dir State × Req |
| L2 | Read/Write Hit/Miss、四种 Way/Set 占用、Dirty Victim、8-beat Burst | Tag 命中、数据与地址、Replacement、Beat 计数 |
| Interconnect | 两 L1 同时 Valid、相同/不同地址、Snoop 与 Data 反压 | Grant 唯一、无错路由、Payload Stable、Fairness Assumptions |
| Snoop Adapter | Dirty Owner、Clean Owner、S Sharer、Release 途中 Reset | Data 最新、Invalidate ACK、No Stale Response |

### 7.2 Subsystem-level Directed Scenarios

- 两核先后读取同一行，E→S，Sharers=11；反向 Core ID 组合都测。
- 共享行 S/S 时一方写，另一方 Invalidate，GrantM 不早于 InvAck。
- E 静默变 M，再被另一核读，确保最新数据而非旧 L2 数据。
- M Owner 被另一核请求 GetM；含 Write Mask、八拍数据、Owner 转移。
- 同一行同时 GetS/GetM、同时 GetM/GetM、不同地址并发；全局串行化后无错配。
- Local L1 Eviction 的 PutS/PutE/PutM；L2 Inclusive Eviction 后回收 L1 副本。
- 所有 Request/Snoop/Data/Ack 通道分别施加 Backpressure，含第 0、3、7 拍停止。
- 在 Snoop Ack、Line Transfer、Refill、Writeback 等暂态施加 Reset。
- 不同 Set 相同 Tag、相同 Set 不同 Tag、跨 64B Boundary、部分 Byte 写。

### 7.3 Reference Model / Scoreboard

- **全局真实值**：每个物理地址的最新字节值（software oracle）。
- **状态模型**：两个 L1 的每行 Tag/Way/MESI；L2 目录状态、Sharers/Owner、数据是否最新及 Dirty Ownership。
- **事务模型**：已接受的 Request、Pending Snoop、待 ACK 列表、八拍编号、最终授权及 Reset 取消。
- **检查时机**：以 `valid && ready` 为准，按事务 Commit/状态转换点检查，不在未完成暂态强行要求稳态不变量。

### 7.4 Functional Coverage（新项目草案，不是原 DCache 45 Goals）

| Coverpoint / Cross | 目标 Bins |
|---|---|
| Core×Operation×Hit/Miss | Core{0,1} × Read/Write × Hit/Miss |
| MESI Transitions | I→E、I→S、I→M、S→M、E→M、E→S、M→S、S→I、E→I、M→I |
| Directory State×Request | I/S/U × GetS/GetM/Upgrade（合法组合） |
| Sharers/Owner | Sharers=00/01/10/11，Owner=none/0/1（合法组合） |
| Snoop×Source State | SnoopRead/Invalidate × S/E/M × Core0/Core1（合法组合） |
| Data Transfer | L2/Memory/Owner × 8-beat 完成 × Stall/No-Stall |
| Eviction | L1/L2 × Clean/Dirty × Sharer/Owner Exist |
| Races | GetS+GetS、GetS+GetM、GetM+GetM、Snoop vs Local Miss |
| Reset | Idle、Wait ACK、Transfer、Writeback |

**Coverage 原则**：非法组合应单独标记为 Ignore/Illegal，并用 Assertions 防止，而不是盲目要求覆盖全部笛卡尔积。每个 Cover Bin 必须有 Test 触发策略和 Checker。

### 7.5 Formal 计划

- `assert`: `M/E` 唯一权限、不存在双 M、Directory 的 Owner/Sharer 元数据合法、M Grant 前已清除冲突副本、八拍 Last 唯一、Stall 时 Payload Stable、Reset 无旧响应。
- `cover`: 从 I/S/U 到所有合法状态转移、Dirty Owner Data Snoop、Full Invalidate ACK、最后一拍 Release。
- `assume`: 上游协议输入合法、下级最终应答、公平性仅用于 Liveness 证明。
- 独立状态机可做归纳证明；整个缓存子系统的时序性质先做明确上限的 Bounded Model Checking。绝不将有界验证宣传成全局无界 Proof。

---

## 8. 开发阶段与通过门槛

**当前实现记录（2026-10-21）**：`rtl/coherence/` 已新增协议编码、L1
MESI 控制 FSM、单事务 Directory 控制 FSM、两份 32 KiB MESI L1 阵列、请求
仲裁器，以及 256 KiB 共享 L2/Directory 阵列。`CoherentCacheSubsystem` 将这些
模块连成阻塞式 CPU-to-memory 路径，支持 L2/内存八拍 refill、owner SnoopData
回写到 L2，以及无 sharer/owner 的 `DIR_I` L2 victim 回收；脏 victim 会先写回
内存，再清 dirty 并失效目录项。L1 Put/PutAck 替换和带有效 L1 副本的 L2
victim back-invalidation 尚未实现：L1 有效 victim 会让 miss 停住，L2 live
victim 会令 line engine 报错停机。内存写接口以最后一拍握手作为完成，没有
独立写响应。新增 RTL 尚未编译、仿真或回归。

| 阶段 | RTL 交付 | DV Gate |
|---|---|---|
| P0 基线冻结 | 保存单 L1 RTL、修订 SPEC；解释 Probe 保留 Line；定位长冲突 Trace 超时 | 旧 pytest/coverage/formal 可复现，已知问题单独登记 |
| P1 协议与 FSM | Coherence Protocol Package + 独立 MESI FSM + Directory FSM（无需真实 L2） | 全部合法稳态/暂态、One-Hot、Protocol Assert |
| P2 双 L1 Coherence 子系统 | 双 L1、仲裁、Directory、L2 和阻塞式 Memory read/write adapter 顶层已连通；Put/PutAck 尚未接入 | GetS/GetM/Upgrade/Owner Snoop/Concurrent Cases 全通过 |
| P3 真实 L2 | 256 KiB 8-way Tag/Data/Directory Array 已新增；空目录 victim 与 dirty writeback 已接通；live victim back-invalidation 未实现 | Block L2 Regression、系统 Invalidation/Writeback |
| P4 签收强化 | Formal/Random/Mutation/Coverage + 系统性能基线 | 覆盖率与排除项说明、所有不变量/数据检查、重现脚本 |
| P5 可选优化 | 多 MSHR/并行 Directory/ICache/DMA/真实双核 | 新增 Spec、各级 Regression 与性能对照 |

---

## 9. Chisel 与 SystemVerilog 源码归属规则

NutShell L1 的原始权威源码为 `workspace/nutshell_src/src/main/scala/nutcore/mem/CacheStage*.scala` 等 Chisel 文件。当前单 L1 验证子项目 `workspace/nutshell_cache/rtl` 是另一套独立维护的 Verilog 基线。

**推荐现阶段做法**：先基于已有单 L1 RTL 冻结回归，P1 可使用独立手写 SystemVerilog 做 MESI/Directory FSM；L1 结构性改造优先修改模块化 Chisel 源码，经 `--split-verilog` 生成 RTL，再复用 Verilator/Toffee DV。若要全部使用 Chisel，先完成单模块 Chisel→生成 SV→波形→Formal 的 Debug PoC；每个模块必须只有一个权威源代码版本，不能长期双向手改 Chisel 和它生成的 Verilog。

---

## 10. Design Review 待确认项

- [ ] Directory 使用 I/S/U，支持 L1 E→M 静默升级。
- [ ] 初版采用 L2 Tag/Directory Inclusive，Dirty Owner 数据可能比 L2 新。
- [ ] 第一版每 L1 最多 1 Pending Miss + 全局 1 Directory Transaction，但 Snoop 必须有独立进度机制。
- [ ] 新的 Coherence 消息与原始 SimpleBus Probe 语义分离。
- [ ] v1 不接入 ICache MESI / DMA / 真实双 Core，先把两个 LSU Agent 的 DCache Coherence 验证完成。
- [ ] 先使用 Behavioral L2 验证协议，再加入 256KiB/8-way Synthesizable L2。
- [ ] 确认 Chisel/SV 源码归属和 CI 生成流程。

---

## 11. 源码依据与阅读入口

- [`NutShell.scala`：L1/CoherenceManager/L2 顶层连接](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/system/NutShell.scala)
- [`NutCore.scala`：ICache/DCache 实例](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/nutcore/NutCore.scala)
- [`Settings.scala`：HasL2cache 默认及嵌入式开关](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/top/Settings.scala)
- [`Coherence.scala`：对 DCache 的现有 Probe/Forward 流程](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/system/Coherence.scala)
- [`CacheTop.scala`：当前 Chisel Cache Pipeline/Array 连接](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/nutcore/mem/CacheTop.scala)
- [`test_coherence.py`：现有 Probe 不失效语义及相关测试](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_cache/tests/test_coherence.py)

**状态声明**：本 SPEC 中原始 NutShell 硬件基线源自当前仓库可检查的源码；双核 L1/D MESI、Directory、256KiB L2 和系统级验证均是新项目的设计与验收目标，不应作为已完成成果陈述。
