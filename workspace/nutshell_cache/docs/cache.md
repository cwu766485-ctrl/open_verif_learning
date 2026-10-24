# NutShell 双核缓存一致性子系统微架构规格书（中文）

**文档版本**：v0.2（设计评审草案）  
**日期**：2026-10-20  
**设计状态**：双 L1 + 共享 L2/Directory 已接通 AXI4 line adapter 与 APB 性能 CSR；顶层及模块回归正在验证，仍需扩大系统级验证与 formal 范围
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
              ┌─────┴─────────────┐
              ▼                   ▼
       AXI4 Master Adapter   APB Performance CSR
        64-bit / 8-beat       Counters / Status
              │                   │
              ▼                   ▼
       AXI Memory Model     Software / Debug
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

**首版事务能力**：每 L1 最多发起 1 笔未完成的 CPU Coherent Miss；全局 Directory 最多处理 1 笔事务。Snoop 与本地 CPU 事务按第 6.2 节的同址/异址规则仲裁；协议保证无内部循环等待，外部响应反压则要求最终解除。

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
6. **Snoop 进度**：本地 CPU miss/refill 与 Snoop 的同址交错按第 6.2 节序列化；异址 Snoop 可独立接收。Directory 全局串行，外部 CPU response ready 和 Snoop response ready 最终解除是进展假设。
7. **Reset 协调**：初版系统同步 Reset 清除所有暂态、目录所有权和旧 Response；旧请求不得在 Reset 后再次完成。Reset 后需重新初始化目录和 Meta Array。
8. **Eviction**：L1 M→PutM 写回最新数据；L2 Inclusive Victim 必须先处理任何 L1 Sharer/Owner，再驱逐目录 Tag。
9. **MMIO**：地址 `[0x3000_0000, 0x8000_0000)` 依 NutShell 现有译码走
   bypass，不参与普通 MESI/L1/L2 分配；通过独立 MMIO 请求/响应端口与外设互连。
   v1 LSU 请求为 64-bit word，MMIO `size=3'b011`，写入 Byte Mask 原样转发。

### 6.1 v1 Backing Memory 接口契约（冻结）

- `reset` 是同步、高有效、全子系统共用的复位。外存适配器必须在复位时取消
  已接受的读写事务，清除待发送 beat/response，并保证复位释放后不返回旧事务的
  响应；因此事务号可在复位后重新使用。若实际 memory controller 做不到取消，须在
  它与本子系统之间增加 drain/epoch wrapper，不能直接连接。
- Memory 不得在对应 request 握手的同一周期返回该事务的首个 response：读数据最早
  在 read request 握手后的下一周期有效；写 response 最早在 write beat 7 握手后的
  下一周期有效。`valid` 未握手时，response payload（含 `txn_id`、beat、data、
  `last`、`error`）必须保持稳定。
- Read request 握手后，成功事务返回同一 `txn_id` 的 8 个 64-bit beat，beat 为
  0..7，`last` 只在 beat 7。Memory 可以任意暂停 valid 或接收端。失败事务返回一个
  带相同 `txn_id`、`beat_idx=0`、`error=1`、`last=1` 的终止 beat，随后不再发送
  该事务的数据。
- Write request 握手后，Memory 接收同一 `txn_id` 的 8 个 64-bit beat；beat 7
  握手不代表写入完成。之后必须返回一个带相同 `txn_id` 的 write response；
  `error=0` 表示整行写入完成，`error=1` 表示写失败。L2 victim 只有收到成功
  response 后才能清 dirty 或释放目录项。
- Memory response 的错误事务号、错误 beat/last、非预期 response，以及 read/write
  error 都触发 fail-stop：置位 sticky `fatal_error`、停止接收新 CPU/MMIO 请求并
  抑制成功响应；不自动重试。SoC 必须先隔离/停止发起端，再对整个子系统复位。
  该契约保证故障不会被伪装成成功数据，但不承诺从外存故障中透明恢复。

### 6.2 Snoop 接收与进度规则（冻结）

- 同一 L1 的 CPU FSM 与 Snoop FSM 可并行处理不同 cache line。异址 Snoop 不因本地
  miss/refill 或 CPU response stall 被挡住；共享 metadata 写口发生竞争时，Snoop
  metadata 更新优先，CPU 更新保持 valid/payload 并等待。
- 同址冲突按 CPU 阶段处理：CPU 已进入 refill、metadata commit 或 response/store
  commit 阶段时，Snoop 保持 valid 并等待；CPU request 仍在 Directory request/grant
  阶段时，Snoop 可以先执行，Directory 随后基于更新后的目录状态处理排队请求。
  被前一笔事务反失效的旧 Upgrade 会由 Directory 作为 GetM 恢复，并从当前 owner
  取回完整数据。
- CPU 与 Snoop 在两个 FSM 都 idle 时同周期请求同一行，Snoop 优先接收，CPU request
  不握手，随后重试。这避免 E→M 本地 store 晚于 SnoopRead 数据采样提交。
- Directory 全局一次只处理一笔事务；等待 owner/sharer Snoop 时不会启动第二笔
  Directory 事务。Snoop response 和 CPU response 接收方最终拉高 ready 是进度假设；
  对 Directory 阶段同址冲突采用 Snoop 先行，避免“Directory 等 Snoop、CPU 等
  Directory”的循环依赖。Reset 取消两侧所有暂态和未完成握手。

### 6.3 SRAM 组织与端口映射（v1 冻结）

RTL 数组采用以下逻辑组织，实际 FPGA BRAM/ASIC SRAM 宏由目标工艺 adapter 映射；
宏不得改变地址、字节掩码、握手或复位语义。

| Array | 逻辑分 bank | 元数据 | 逻辑端口/冲突处理 |
|---|---|---|---|
| 每份 L1 data | 8 个 64-bit beat bank；每 bank 512 行（128 set × 4 way），总 32 KiB | 与数据分开 | 1 个 CPU word-read、1 个串行 Snoop line-read、1 个 64-bit write 端口；CPU store 与 refill 写按 L1 FSM 串行，Snoop line-read 可与异址 CPU lookup 并行 |
| 每份 L1 tag/state | 4 way × 128 set；每行 tag、valid、MESI | replacement pointer 每 set 独立小寄存器 | CPU 与 Snoop 两个 lookup 读口、一个 metadata 写口；同周期写冲突由 Snoop 优先，CPU 等待；reset 清 valid/state 可见元数据，不要求清 data RAM |
| Shared L2 data | 8 个 64-bit beat bank；每 bank 4096 行（512 set × 8 way），总 256 KiB | 与数据分开 | 1 个串行整行读端口 + 1 个整行写端口；全局 Directory/line engine 串行化 line read/write，memory beat 与 owner beat 共用 write port |
| Shared L2 directory/tag | 8 way × 512 set；每行 tag、valid、DIR、sharers、owner、dirty | 与 L2 tag 同步更新 | 每周期一个 lookup/victim 读操作及一个更新操作；v1 Directory 全局串行；reset 清 valid，invalid 行的 tag/state 不参与 lookup |

每份 L1 的 data 总量为 8×512×64 bit=32 KiB；共享 L2 为
8×4096×64 bit=256 KiB。现有多维 `logic` 数组是可执行行为模型，不是已选定的
foundry macro。同步 SRAM 的读延迟由 wrapper 表示为 ready/valid 流水级，并保持
请求/返回事务关联。当前未指定 FPGA 型号或 ASIC 工艺，因此冻结的是端口、bank、
reset 和优先级映射，不包含具体 macro 名称、时序角、面积或 PPA 承诺。

### 6.4 AXI4 memory adapter 与 APB performance CSR

`CoherentCacheAxiSubsystem` 保留 Directory/L2 的 line-memory 契约，在下游加入
64-bit AXI4 Master Adapter。每个缓存行使用 8-beat INCR burst：`ARLEN/AWLEN=7`、
`ARSIZE/AWSIZE=3`、`ARID/AWID` 保留 line transaction ID；LOCK 为 0，CACHE 固定
`4'b0011`，PROT 固定 `3'b000`。写回整行时
`WSTRB=8'hff`；AW 与 W 独立握手，最后一个 W beat 后才接收 B。读通道将 R beat
恢复为原 line 接口；AXI RRESP 错误会形成终止 line error，并在适配器内部 drain
该 burst 剩余 beat。BRESP/RRESP 及返回 ID 错误会传到 cache 错误状态。

当前 Directory 一次只处理一笔 line transfer，适配器每类最多一个 outstanding
事务，读写状态彼此独立。系统级 reset 必须同时作用于 AXI memory/interconnect，
因为 AXI 本身没有取消已接受事务的通道。

APB3 performance CSR 是只读寄存器窗口：`0x00` hit、`0x04` miss、`0x08` snoop、
`0x0c` 成功 dirty writeback、`0x10` 错误状态、`0x14` 累计 cache access cycles、
`0x18` 已完成 cache access 数。访问周期按每周期 outstanding 的缓存 LSU 数累加，
包括 response backpressure；软件用 `0x14 / 0x18` 计算平均访问延迟。Counters 是
32-bit、reset 清零、溢出回绕；MMIO bypass 不计入 hit/miss/latency。写 CSR 或访问
未映射 offset 返回 `PSLVERR`。本阶段只实现 APB，不实现 JTAG TAP；未来 Debug
Bridge 可以连接该寄存器窗口。

`make coherence_bus_blocks` 验证 burst 字段、通道反压、R 错误 drain、CSR 计数与
APB 只读行为；`make coherence_axi_lint` elaboration 完整 AXI/APB 子系统顶层。

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

**当前实现记录（2026-10-24）**：`rtl/coherence/` 已新增协议编码、L1
MESI 控制 FSM、单事务 Directory 控制 FSM、两份 32 KiB MESI L1 阵列、请求
仲裁器，以及 256 KiB 共享 L2/Directory 阵列。`CoherentCacheSubsystem` 将这些
模块连成阻塞式 CPU-to-memory 路径，支持 L2/内存八拍 refill、owner SnoopData
回写到 L2，以及 L1 的 PutS/PutE/PutM 替换事务。PutM 会传回完整八拍，收到
PutAck/commit 后才清除 victim 并重放原 miss。L2 victim 回收覆盖无副本的
`DIR_I`、逐个反失效 sharer 的 `DIR_S`，以及反失效 `DIR_U` owner 并回收整行
数据；dirty victim 在释放目录项前写回内存。MMIO 地址 `[0x3000_0000,
0x8000_0000)` 走独立 bypass FSM，不进入 L1/L2/Directory；reset 期间 CPU、
MMIO 和 backing-memory 边界的 valid/ready 握手均被屏蔽。Memory 请求与整行
数据 beat 携带当前 `txn_id`，refill 端拒绝 ID 不匹配的数据；外部 Memory 必须
与子系统共用 reset，以取消 reset 前未完成的请求。当前 `make coherence_smoke` 已用
定向场景通过 E→M 静默升级、M Owner 被远端读/写、E Owner 被远端写、S→M
升级、MMIO 旁路读写与 Byte Mask、跨整行八拍数据检查、M/S/E L1 victim、DIR_U 脏 owner 回收、
DIR_S 双 sharer 反失效，以及回写后再读数据等检查。Directory 会拒绝未登记为
在 `DIR_S` 中未登记为 sharer 的 Upgrade 会被拒绝；在 `DIR_U` 下来自非 owner 的
排队/过期 Upgrade 则按 GetM 恢复，先对当前 owner 做失效 Snoop 并取回最新整行，再
授予带数据的 M，避免并发 Upgrade 形成死锁或无数据 Grant。
模块级回归分别直接实例化并检查 `MesiL1Array`、`MesiL1Controller`、
`DirectoryController` 和 `SharedL2DirectoryArray`。入口为 `make coherence_modules`，
也可单独运行 `coherence_l1_array`、`coherence_l1_controller`、
`coherence_directory`、`coherence_l2_array`。当前覆盖阵列 refill/byte mask/替换、
八拍行读停顿、L1 E→M 与 GetS refill/SnoopData、Directory GetS/owner intervention/
Upgrade、L2 dirty victim 安全回收，以及 L1 refill/L2 line write/Directory Snoop 的
错误响应检测。`make coherence_formal` 包括 request arbiter 与 L1 CPU/Snoop
arbiter 性质证明，以及 Directory/L1 控制器 16-step bounded safety checks；这些模块级
仿真与局部 formal 检查都不等于全子系统形式证明。
当前子系统回归通过了 ready/valid 反压、活动事务 reset 取消、同址双核与异址并发、
地址域边界和字节掩码 corner cases。TB scoreboard 比较读数据并按 mask 更新写入参考值；
monitor assertions 检查外部与内部通道 payload 稳定、MESI 唯一可写者及目录元数据。
每次运行含 80 个受周期性 stall 影响的随机访问；`make coherence_random` 用五个 seed
运行完整 directed + random suite。活动事务 reset 覆盖 refill request、MMIO response、CPU
response、owner SnoopData stream 和被反压的 dirty L2 writeback beat。当前内存接口采用
第 6.1 节冻结的共享同步 reset、终止 read error beat、独立 write response 和 sticky
fail-stop 错误；定向用例确认 read error 不产生 CPU 成功 response，write error 保留
`victim_addr_q` 指向的 valid/dirty L2 行。测试显式压住有效 refill beat 的 L2 ready，
并检查 valid/payload 一直保持到握手；Snoop 用例覆盖同址 E→M 等待、Directory 等 grant
期间的过期 Upgrade 恢复、以及 CPU response stall 时异址 Snoop 继续推进。`make
coherence_smoke` 通过默认 seed；`make coherence_random` 的五个 seed（每个含 80 笔随机
操作和完整 directed suite）均通过。`make coherence_formal` 包含 request arbiter 与
CPU/Snoop 仲裁性质证明，以及 Directory/L1 各 16-step bounded safety checks；后者检查
地址/事务路由、元数据、反压下 payload 稳定、Snoop/refill 路由和 reset 取消。
这些有界检查不等于无界控制器证明；**整个 MESI/L2 子系统仍未做 formal proof**。
SRAM 端口/bank/reset 映射见第 6.3 节；现有 `logic` 数组仍是行为模型，具体目标工艺宏
尚未映射。

| 阶段 | RTL 交付 | DV Gate |
|---|---|---|
| P0 基线冻结 | 保存单 L1 RTL、修订 SPEC；解释 Probe 保留 Line；定位长冲突 Trace 超时 | 旧 pytest/coverage/formal 可复现，已知问题单独登记 |
| P1 协议与 FSM | Coherence Protocol Package + 独立 MESI FSM + Directory FSM（无需真实 L2） | 全部合法稳态/暂态、One-Hot、Protocol Assert |
| P2 双 L1 Coherence 子系统 | 双 L1、仲裁、Directory、L2 和阻塞式 Memory adapter 已连通；PutS/PutE/PutM 替换与 miss 重放已接入 | GetS/GetM/Upgrade、Owner Snoop、M/S/E replacement、并发、主要通道反压和 reset 定向用例通过 |
| P3 AXI/APB 外部集成 | 新增 `CoherentCacheAxiSubsystem`、64-bit 8-beat AXI4 line adapter、只读 APB performance CSR；模块测试与顶层 elaboration 已加入 Make/CI gate | 当前提交需完成模块定向运行和 AXI/APB 顶层检查；AXI 每类一个 outstanding，与阻塞式 Directory 匹配 |
| P4 签收强化 | 子系统随机/断言、arbiter formal、Directory/L1 bounded safety checks 已建立 | 仍需无界控制器/全 subsystem formal、更多 corner/mutation/覆盖率与性能基线 |
| P5 可选优化 | 多 MSHR/并行 Directory/ICache/DMA/真实双核 | 新增 Spec、各级 Regression 与性能对照 |

---

## 9. Chisel 与 SystemVerilog 源码归属规则

NutShell L1 的原始权威源码为 `workspace/nutshell_src/src/main/scala/nutcore/mem/CacheStage*.scala` 等 Chisel 文件。当前单 L1 验证子项目 `workspace/nutshell_cache/rtl` 是另一套独立维护的 Verilog 基线。

**推荐现阶段做法**：先基于已有单 L1 RTL 冻结回归，P1 可使用独立手写 SystemVerilog 做 MESI/Directory FSM；L1 结构性改造优先修改模块化 Chisel 源码，经 `--split-verilog` 生成 RTL，再复用 Verilator/Toffee DV。若要全部使用 Chisel，先完成单模块 Chisel→生成 SV→波形→Formal 的 Debug PoC；每个模块必须只有一个权威源代码版本，不能长期双向手改 Chisel 和它生成的 Verilog。

---

## 10. Design Review 决策与剩余项

以下架构决策已落入 RTL：

- Directory 使用 I/S/U，兼容 L1 的 E→M 静默升级。
- L2 保留 inclusive Tag/Directory；驱逐 live victim 前先反失效 L1，dirty owner 数据先回收。
- 每个 L1 只有一个阻塞式 miss，Directory 全局串行；L1 Snoop 有独立 FSM。同址
  Snoop/CPU 依阶段仲裁，异址 Snoop 可并行推进；同址 E→M stall、过期 Upgrade 和
  异址 Snoop stall 场景已加入定向回归，后续仍可扩大压力组合与 liveness 验证。
- 同址 CPU/Snoop 逐行串行，idle 同周期冲突由 Snoop 获胜；异址 Snoop 可在 CPU FSM 活跃时接收。CPU/Snoop response ready 最终解除是进度假设。
- SRAM 逻辑组织已冻结为 64-bit × 8 beat banks、每份 L1 32 KiB、共享 L2 256 KiB；同步读延迟通过 wrapper ready/valid 表示。因没有目标 FPGA/工艺，具体 macro 型号、时序和 PPA 未定。
- 新的一致性消息与旧 SimpleBus Probe 语义分开。
- v1 验证边界是两个 LSU Agent 和 DCache；真实双 Core、ICache MESI、DMA coherence 不在当前实现内。
- 已接入 256 KiB / 8-way Shared L2/Directory 阵列。

GitHub Actions 当前已运行 `make coherence_verify`；本次增加的 AXI/APB 模块测试与顶层 elaboration 也已并入该 gate，需以本次 RTL 验证和下一次 Actions 结果作为交付依据。源码边界为旧单 L1 RTL 基线与新增手写 SystemVerilog coherence 子系统分别维护，后续应继续避免双权威源。

---

## 11. 源码依据与阅读入口

- [`NutShell.scala`：L1/CoherenceManager/L2 顶层连接](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/system/NutShell.scala)
- [`NutCore.scala`：ICache/DCache 实例](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/nutcore/NutCore.scala)
- [`Settings.scala`：HasL2cache 默认及嵌入式开关](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/top/Settings.scala)
- [`Coherence.scala`：对 DCache 的现有 Probe/Forward 流程](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/system/Coherence.scala)
- [`CacheTop.scala`：当前 Chisel Cache Pipeline/Array 连接](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_src/src/main/scala/nutcore/mem/CacheTop.scala)
- [`test_coherence.py`：现有 Probe 不失效语义及相关测试](https://github.com/cwu766485-ctrl/open_verif_learning/blob/cache_coherence/workspace/nutshell_cache/tests/test_coherence.py)

**状态声明（2026-10-22）**：仓库已实现双 LSU Agent 驱动的双 L1 MESI、Directory 和 256 KiB 共享 L2 RTL，并有集成级定向/随机回归；内存错误契约、Snoop 进度规则和逻辑 SRAM 映射已冻结。具体回归结果与 formal 边界见第 8 节。这是可运行的阻塞式 RTL 子系统原型，不代表已接入两个真实 NutShell Core，也不代表完整 subsystem formal、具体工艺 SRAM/PPA 或芯片签收完成。本 SPEC 第 0 节描述的 NutShell 单核基线来自可检查的 Chisel 源码；它与新增的双 L1 一致性子系统是不同范围。
