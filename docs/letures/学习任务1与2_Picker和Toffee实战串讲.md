# 学习任务 1 与 2：Picker 和 Toffee 实战串讲

验证对象是一个 **32 bit、深度 16 的同步 FIFO**。它只有在 `clk` 上升沿改变状态，`rst_n=0` 时同步复位；`we_i && !full_o` 才是真正写入，`re_i && !empty_o` 才是真正读出。`wptr/rptr` 为 4 bit，会在 15 后回绕；`counter` 为 5 bit，表示 0 到 16 项。

```text
RTL SyncFIFO.v
     │ Picker export
     ▼
DUTSyncFIFO（Python 可控制的仿真 DUT）
     │ Toffee Bundle / Agent
     ▼
pytest 测试 + 参考模型 + 功能覆盖率 + 波形/报告
```

## 任务 1：用 Picker 验证“端口级正确性”

位置：[course2_picker_fifo](../../labs/course2_picker_fifo)。

Picker 的工作是把 Verilog RTL 编译成 Python 能直接驱动的 `DUTSyncFIFO`。本任务的重点不是重写 RTL，而是学会：初始化输入、驱动时钟、复位、在正确的周期写/读、用断言观察端口和允许导出的内部状态。

| 测试 | 验证什么 | 为什么重要 |
| --- | --- | --- |
| `test_reset_rise_write` | 默认 `AsRiseWrite()` 下的复位 | 认识赋值相对上升沿的时序 |
| `test_reset_immediate_write` | `AsImmWrite()` 下的复位 | 输入提前稳定时，DUT 本周期能采样到它 |
| `test_smoke_dut` | 写 `0x114`、`0x514`，按序读回 | FIFO 最基本的顺序和状态变化 |

`internal.yaml` 使 Picker 同时导出 `wptr`、`rptr`、`counter`。这是学习阶段很有价值的白盒观察：复位后它们都必须是 0；正常读写时用它们理解行为。但真实项目不能把“内部寄存器恰好这样实现”当作主要验收标准，应优先检查可见协议和结果。

运行：

```bash
cd /mnt/e/workspace/chip/open_verif/labs/course2_picker_fifo
make test
make wave-smoke
```

波形中按顺序看 `clk → rst_n → we_i/re_i → data_i/data_o → empty_o/full_o`。刚开始看不懂内部信号完全正常；先回答“这一个上升沿是否接受了读/写请求”，再看指针和计数器即可。

## 任务 2：用 Toffee 把端口操作升级为验证平台

位置：[course3_toffee_fifo](../../labs/course3_toffee_fifo)。本任务复用任务 1 生成的 Picker DUT，不再次手工接触 `.so` 或自动生成文件。

### 1. Fixture：每个测试从干净的 DUT 开始

[`tests/conftest.py`](../../labs/course3_toffee_fifo/tests/conftest.py) 创建 `DUTSyncFIFO`、启动 Toffee 时钟、把全部输入设成明确的初值，并将端口绑定给 Bundle。测试函数只表达场景，不再重复搭环境。

### 2. Bundle：端口的“轻量 interface”

[`bundle/__init__.py`](../../labs/course3_toffee_fifo/bundle/__init__.py) 有四类 Bundle：

- `ControlBundle`：`rst_n`，提供 `reset()`；
- `WriteBundle`：`we_i/data_i/full_o`，提供 `enqueue(data)`；
- `ReadBundle`：`re_i/data_o/empty_o`，提供 `dequeue()`；
- `InternalBundle`：只观察任务书允许的内部状态。

`enqueue()` 在 `full_o=1` 时返回 `False`；`dequeue()` 在 `empty_o=1` 时返回 `None`。这比让测试到处直接操作 `we_i`、`re_i` 更清晰，也能复用。

### 3. Agent：把“端口动作”变为“FIFO 事务”

[`agent/__init__.py`](../../labs/course3_toffee_fifo/agent/__init__.py) 的 `FIFOAgent` 对外提供 `reset`、`enqueue`、`dequeue`、`idle`。这里才是测试、参考模型和覆盖率共同使用的入口。

`enqueue_dequeue()` 用 `Executor` 放进 `write` 和 `read` 两个调度组，在同一个时钟周期并发读写。对于非满非空 FIFO，两个指针都会前进，而 `counter` 不变；这是同步 FIFO 的关键场景。

### 4. Env 与参考模型：不要只相信 DUT 自己

[`ref/__init__.py`](../../labs/course3_toffee_fifo/ref/__init__.py) 用 Python `deque` 表示期望 FIFO：容量 16，满时拒绝写，空时拒绝读。 [`env/__init__.py`](../../labs/course3_toffee_fifo/env/__init__.py) 将它绑定给名为 `fifo` 的 Agent。

于是 `await fifo.enqueue(data)` 的“是否接收”、`await fifo.dequeue()` 的“读出数据”，不仅有测试自己的断言，Toffee 还会把 Agent 返回结果与参考模型的预测自动比较。这是可扩展验证平台最重要的思想：**DUT 是被验证对象，参考模型才是期望行为的独立来源。**

### 5. 功能覆盖率：我们是否真的跑到了关键情形

[`coverage/__init__.py`](../../labs/course3_toffee_fifo/coverage/__init__.py) 对高层事务手工采样，覆盖：复位、空闲、正常读写、空读、满写、并发读写、读/写指针回绕、数据顺序，以及 FIFO 的空/中间/满占用状态。

本次 `make report` 的结果是：功能覆盖率 **13/13 bins，100%**。注意它不是“RTL 行覆盖率”：报告中的 RTL 行覆盖率是 83.78%，说明还有 RTL 语句尚未从所有可能的分支和组合路径经过。功能覆盖率 100% 意味着“我们定义的功能目标都命中”，不等于芯片已经绝对无 bug。

运行：

```bash
cd /mnt/e/workspace/chip/open_verif/labs/course3_toffee_fifo
make test
make report
```

报告在 `reports/course3`；每个测试还有 `.fst` 波形和 Verilator `.dat` 覆盖率数据。执行 `make clean` 会清掉课程 3 的临时结果和报告，但不会清除课程 2 的 Picker DUT。

## 你应该带走的主线

1. 先读规格，把“正确”写成复位、边界、顺序、并发等可检查规则。
2. Picker 解决“怎么让 Python 控 RTL”的问题。
3. Bundle 解决“端口如何整洁复用”的问题。
4. Agent 解决“测试如何用业务事务表达”的问题。
5. Model 解决“期望结果从哪里来”的问题。
6. Coverage 解决“我们是否真正验证到了目标”的问题。

后续最值得你自己动手的练习，是给 FIFO 加随机长序列和断言：每次随机读写后让参考模型自动检查，再观察覆盖率还缺什么。
