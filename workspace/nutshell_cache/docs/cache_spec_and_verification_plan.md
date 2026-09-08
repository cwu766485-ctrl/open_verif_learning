# 果壳 Cache：规格、结构与验证计划

## 1. 它是什么 Cache

这份 `rtl/Cache.v` 不是一个独立的 CPU，也不是简单的 SRAM 控制器，而是
NutShell 处理器内存层次中的 Cache 控制器。根据 RTL 的 `dirty` 位、写掩码、
脏行写回、普通内存 refill、MMIO 旁路和 coherence/probe 端口，它更接近
NutShell 的 **DCache（数据 Cache）**，不是只读的 ICache：

- DCache 必须允许 CPU 写数据，所以有 write hit、byte mask 和 dirty bit；
- ICache 通常只读，flush 语义也不同；本 RTL 在 `io_flush` 时触发
  `only allow to flush icache` 断言，说明当前实例是不可用该 flush 路径的可写
  Cache 配置；
- 它仍然不是完整的 CPU Cache 子系统，coherence、内存控制器和 CPU 都在模块外。

## 2. 可从 RTL 直接得到的规格

| 项目 | 规格 |
| --- | --- |
| 地址 | 32 bit 地址字段 |
| word | 64 bit，8 byte |
| line | 8 个 word，即 64 byte |
| 组数 | 128 sets，index 为 `addr[12:6]` |
| 相联度 | 4 ways |
| tag | `addr[31:13]`，19 bit |
| 容量 | `128 × 4 × 64 B = 32 KiB` |
| 数据阵列 | 每个 way 1024 个 64 bit entry，地址为 `{set, word}` |
| 元数据 | 每个 way 保存 tag、valid、dirty |
| 替换 | 优先使用 invalid way；全有效时用 64 bit LFSR 选 victim，不是 LRU |
| 流水 | Stage1 发起 SRAM 读，Stage2 做 tag/hit/victim 判定，Stage3 执行事务 FSM |

地址被拆为：

```text
31             13 12       6 5        3 2       0
+----------------+----------+----------+----------+
|      tag       |   set    | word idx | byte off |
+----------------+----------+----------+----------+
      19 bit         7 bit      3 bit      3 bit
```

## 3. 事务行为

### 读命中

Stage2 找到有效且 tag 相等的 way，Stage3 从四路数据中选择命中的 word，
通过 `io_in_resp_*` 返回读响应。重复读不会访问 `io_out_mem_*`。

### 读缺失

没有命中时先选择 victim。若 victim 是 dirty 行，先通过 memory SimpleBus 做
8-beat 写回；随后发起 8-beat refill，把新 line 写入数据阵列和元数据阵列，
最后返回 CPU 请求的 word。

### 写命中和写缺失

写命中按 8 bit `wmask` 扩展成 64 bit mask，与旧 word 合并并置 dirty。写缺失
需要先取得对应 line，再将新数据按 mask 合并。Cache 返回写入前的 word，冷写
的旧值为 0，这也是参考模型检查的响应语义。

### MMIO 和 coherence

命中判断前会做 NutShell MMIO 地址译码；MMIO 请求绕过 Cache 数据阵列，走
`io_mmio_*`。`io_out_coh_req/resp` 是外部 coherence/probe 端口，顶层 Arbiter
优先接收 coherence 请求；本次新手验证只覆盖 MMIO 旁路，没有覆盖多主一致性。

## 4. 验证思路

采用“接口黑盒 + 参考模型 + 下游副作用检查”的策略：

1. 用 Picker 把 `Cache.v` 生成 Python DUT；
2. Toffee Master Agent 驱动上游 SimpleBus 请求并收集响应；
3. 两个独立的 SimpleBusRam 分别服务普通 memory 和 MMIO，并记录每一笔请求；
4. `CacheRefModel` 用按 word 的 shadow memory 检查读数据、写掩码和写响应旧值；
5. 除了比对最终数据，还检查冷读是否访问 memory、重复读是否命中、MMIO 是否
   污染普通 memory；
6. 用固定随机种子跑混合读写，使回归可复现。

## 5. 当前验证计划和结果

| 用例 | 目标 |
| --- | --- |
| reset | 流水线为空，复位期间无下游事务 |
| read miss -> hit | 首次 refill，第二次命中且不新增 memory read |
| full/masked write | 全字写、单 byte 写和读后数据合并 |
| MMIO isolation | MMIO 读写正确，普通 Cache memory 不增加事务 |
| line order | 同一 line 的 8 个 word 地址互不覆盖 |
| deterministic mixed | 固定种子 64 笔事务逐笔比对 shadow model |
| smoke | 官方基础冒烟场景 |
| dirty eviction | 同一 set 的 5 条 line 填充 4-way，检查 dirty victim 的 burst writeback |
| slow refill/backpressure | 延迟 memory ready/valid 和上游 response ready，检查 refill 不中断、数据不损坏 |
| coherence probe | 检查 probe hit、8-beat line release、probe miss |
| cross-line boundary | 检查 64B line 末尾和下一条 line 首 word 不互相覆盖 |
| long randomized mixed | 固定种子 128 笔冲突、byte mask、读写和替换混合事务 |

原始基线 `make report`：7 个用例全部通过；Verilator RTL 行覆盖率 79.2%（1151/1454）。
新增用例已经写入 `test/test_functional.py`，需要在带有 Picker、Verilator 和 Toffee
运行时的 Linux/WSL 环境中重新执行 `make report`，再把新的通过数和覆盖率写回提交报告。
数据 Cache flush 仍然不会作为通过项，因为当前 RTL 会触发自带设计断言；它被记录为
接口约束。

## 6. 关于重构

The slow-refill test also inserts a one-shot five-cycle gap after the fourth
memory response beat, so the burst must pause and resume without losing order.

`Cache.v` 是 Chisel/FIRRTL 生成物，行尾的 `@[Cache.scala ...]` 标记说明它不是
适合手工维护的源文件。它虽然集中在一个文件中，但已经包含
`CacheStage1`、`CacheStage2`、`CacheStage3`、元数据 SRAM、数据 SRAM 和多个
Arbiter 模块。直接改这个 Verilog 会在下一次 `make gen_dut` 时丢失，也容易破坏
流水线时序。

验证仓库现在还提供了一个不改变功能的可读 RTL 视图：

```bash
make split_rtl
```

它把同一个生成物拆成 `rtl/modular/` 下的 13 个 module 文件，并生成
`Cache.files.f`。`make gen_dut_modular` 使用 Picker 的 file-list 重新编译这组文件；
默认 `make gen_dut` 仍使用原始 `rtl/Cache.v`，因此可以做前后对比。

安全的源级重构边界应是：

- 有 NutShell 原始 Chisel 源码时，拆成 `CacheTop`、`CacheStage1/2/3`、
  `MetaArray`、`DataArray`、`MissHandler`、`MmioPath`、`CohPath`、`Arbiter`
  等源文件；
- 保留生成的 `rtl/Cache.v` 作为构建产物，不手改；
- 每次源级重构后做 golden trace 对比、随机回归、断言检查和覆盖率复验；
- 上游 Chisel 源码副本和源码级重构位于 `../nutshell_src`；生成后的
  `build/rtl/ICache*.sv`、`DCache*.sv`、`L2Cache*.sv` 已通过 Chisel elaboration。
