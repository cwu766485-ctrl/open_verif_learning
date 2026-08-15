# 第二讲：Picker 的安装与使用

> 核心目标：把 Verilog/SystemVerilog RTL 转成可由 Python 驱动的 DUT 库，再用软件工程方式写测试、检查结果、看波形和收集覆盖率。

## 1. Picker 是什么，解决什么问题

Picker 是 RTL 与高级语言验证代码之间的桥梁：它调用 **Verilator**（或 VCS）编译 RTL，生成动态库与语言绑定，使 Python/C++ 等程序能像操作对象一样读写硬件端口、推进时钟、获得波形。

```text
RTL (.v/.sv) ── Picker + Verilator ──> DUT 动态库 (.so) + Python 接口
                                                │
Python 测试 / pytest / Toffee ──────────────────┘
```

价值在于：

- RTL 稳定后可只编译一次；大量测试直接复用生成的 DUT。
- Python 可使用 `assert`、随机库、pytest、数据处理与 CI 生态。
- 将 RTL 转为二进制库后可在一定程度上减少直接交付 RTL 源码的需要。
- `pack` 还可将 UVM 的 transaction 自动封装为 Python 接口；本讲重点是 `export`。

## 2. 你的环境状态

本项目已经完成 Python 验证所需环境：Ubuntu WSL2、Verilator、SWIG、Verible、lcov、Picker、`pytoffee` 和 `toffee-test`。

每次打开新的 WSL 终端，在项目根目录执行：

```bash
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh

picker --check
python -c 'import toffee, toffee_test; print("Toffee ready")'
```

其中 Picker、Verible、虚拟环境及构建缓存都位于 E 盘的 `.tooling/`；系统包由 Ubuntu 管理。`picker --check` 中 C++ 与 Python 为 `OK` 即符合本课程。其他语言显示未启用并不是错误。

## 3. 最重要的命令：`picker export`

最常用的形式：

```bash
picker export path/to/RandomGenerator.v \
  --sname RandomGenerator \
  --lang python \
  --sim verilator \
  --tdir build/RandomGenerator \
  -w RandomGenerator.fst
```

| 参数 | 含义 | 工程建议 |
|---|---|---|
| `file` | 含顶层模块的 RTL 文件 | 多文件设计结合 `--fs` 使用 |
| `--sname` | RTL 顶层模块名 | 永远显式写，避免误选文件最后一个模块 |
| `--fs` | 额外 RTL 文件或 filelist | IP/子模块较多时使用 |
| `--lang python` | 生成 Python DUT 接口 | 本课程固定使用 Python |
| `--sim verilator` | 使用 Verilator 后端 | 默认后端；VCS 是另一可选后端 |
| `--tdir` | 生成目录 | 不要把生成物与手写测试代码混在一起 |
| `-w name.fst` | 开启 FST 波形 | 调试时开；大回归可按需关 |
| `-c` | 开启代码覆盖率 | 后续需要代码覆盖率时打开 |
| `--internal file.yaml` | 静态导出指定内部信号 | 只导出调试/覆盖真正需要的内部状态 |
| `--autobuild false` | 只生成、不立即编译 | 调试生成结果或交给后续构建步骤时使用 |

生成目录中会有 Python 包、动态库（`.so`）、信号描述和 xspcomm 支撑文件。它们共同构成 `DUT<模块名>` 类；不要只复制其中一两个文件。

## 4. DUT 的最小生命周期

```python
from RandomGenerator import DUTRandomGenerator

dut = DUTRandomGenerator()  # 创建仿真实例
dut.InitClock("clk")        # 绑定 RTL 时钟端口

# 写输入、推进时钟、检查输出

dut.Finish()                # 必须执行
```

`Finish()` 不是可有可无的清理动作：它会终止仿真、写出剩余波形/覆盖率数据并释放资源。实际测试建议用 `try/finally` 或后续 Toffee fixture，确保断言失败时它也能执行。

在实验工程中，用 **Makefile** 统一入口最顺手：`make export`、`make test`、`make wave-smoke`、`make clean`、`make distclean`。它的价值不是“替代 Python”，而是声明依赖：测试依赖已生成 DUT，波形依赖已跑过测试。Python 更适合驱动、参考模型和检查器；Shell 更适合一两条临时命令，不宜再单独维护一套工程入口。

## 5. 读写端口与时钟语义

Picker 将端口表示为 `XData`：

```python
dut.seed.value = 0x1234            # 写整个端口
dut.seed[1] = 0                    # 写单 bit
unsigned = dut.random_number.value # 无符号读取，等价于 U()
signed = dut.random_number.S()     # 有符号读取
```

写入模式决定输入何时真正送到仿真器：

- `AsRiseWrite()`：上升沿写入，默认，适合普通同步输入。
- `AsFallWrite()`：下降沿写入，用于满足特定时序驱动要求。
- `AsImmWrite()`：立即写入，适合复位或需要立刻刷新组合逻辑的控制信号。

时钟由 `InitClock("clk")` 绑定。随后：

```python
dut.Step()      # 推进到下一个上升沿之前
dut.Step(5)     # 连续推进五次
dut.StepRis(cb, [dut.reset])  # 在每个上升沿登记回调
dut.StepFal(cb)               # 在每个下降沿登记回调
```

**常见误解：** `Step()` 不是纯粹的“软件延时”，它会推进 DUT 的时序状态。因此复位、寄存器更新、FIFO 出入队等操作，都必须明确对应到哪一个边沿发生。

### 同步与异步两种写法

当前实验使用同步、直观的写法：每次 `Step()` 后检查结果。Picker 还支持 `asyncio`：`await dut.AStep(n)` 等待 n 个周期，`await dut.ACondition(lambda: condition)` 等待条件成立，`await dut.RunStep(n)` 持续驱动时钟。它的用途是并发运行 driver、monitor、scoreboard；但不要把 `async` 当成“自动正确”，并发任务仍必须约定信号何时驱动、何时采样。

## 6. 一个正确的 LFSR 验证骨架

验证不是“打印波形看起来差不多”，而是每个周期将 DUT 与独立参考模型比较：

```python
import random
from RandomGenerator import DUTRandomGenerator

MASK = (1 << 16) - 1

class Lfsr16Model:
    def __init__(self, seed):
        self.state = seed & MASK

    def step(self):
        new_bit = ((self.state >> 15) ^ (self.state >> 14)) & 1
        self.state = ((self.state << 1) | new_bit) & MASK

dut = DUTRandomGenerator()
try:
    dut.InitClock("clk")
    seed = random.randrange(1 << 16)
    dut.seed.value = seed
    dut.reset.value = 1
    dut.Step()
    dut.reset.value = 0
    dut.Step()

    ref = Lfsr16Model(seed)
    for cycle in range(1_000):
        dut.Step()
        ref.step()
        assert dut.random_number.value == ref.state, f"mismatch at cycle {cycle}"
finally:
    dut.Finish()
```

这里的关键不是 LFSR，而是验证范式：**先定义可独立计算期望值的 RM，再按一致的时钟语义推进 DUT/RM，最后用 `assert` 自动判定。**

## 7. 内部信号、波形和回调

### 内部信号

优先把内部信号当作调试辅助，而不是主要检查手段。主检查应尽量基于外部可见行为和参考模型。

- 静态导出：在 YAML 中声明指定内部寄存器，再加 `--internal internal.yaml` 重新导出。
- 动态访问：可通过 VPI；Verilator 下可用 `--rw 1` 的 Mem-Direct 获得更高性能，然后以 `GetInternalSignalList()` / `GetInternalSignal(name)` 访问。

### 波形

导出时用 `-w trace.fst` 开启。Verilator 支持：

- `CloseWaveform()`：暂停记录；暂停前如需要捕获当前组合状态，可先 `RefreshComb()`。
- `OpenWaveform()`：恢复记录。

长回归不应无条件存完整波形：文件大、I/O 重。一个资深工程实践是“失败自动保留、平时关键窗口记录”，并让随机测试输出 seed，保证可复现。

### GTKWave：看一张波形的最小流程

以本实验的 `smoke.fst` 为例：先执行 `make test`，再执行 `make wave-smoke`。在 GTKWave 左侧树中展开 `TOP → SyncFIFO_top`；左下列表是可观察信号。选中 `clk`、`rst_n`、`we_i`、`re_i`、`data_i`、`data_o`、`empty_o`、`full_o`，点击左下角 **Append**（或双击信号），它们才会出现于右侧波形区。

建议观察顺序：先看 `clk` 与 `rst_n`，确认复位覆盖了若干上升沿；再看 `we_i/data_i`，找到两笔写入 `0x114`、`0x514`；最后看 `re_i/data_o` 和 `empty_o/full_o`，确认读出顺序和状态变化。总览不清楚时，在时间轴上拖拽选中一个短区间，按放大按钮或滚轮放大；需要比较两个时刻时，在时间轴单击放置 Marker，底部/顶部会显示位置和值。对总线信号右键可改为十六进制显示。波形用于定位“何时错”；`assert` 与参考模型才用于判定“是否错”。

### 回调

`StepRis(callback, [...])` 与 `StepFal(...)` 可在特定边沿执行检查、采样覆盖率或记录事务。传的是函数对象 `callback`，不是 `callback()`；回调第一个参数是当前周期数。

### 组合逻辑与波形窗口

`RefreshComb()` 只重算组合逻辑，不推进时钟；常规时序测试只用 `Step()` 即可。若已经用 `-w` 启用波形，Verilator 后端可用 `CloseWaveform()` 暂停记录、`OpenWaveform()` 恢复记录。暂停前若刚改了输入且需要记录最终组合输出，应先 `RefreshComb()`。这是一种控制长回归波形体积的手段。

## 8. 覆盖率：本讲先建立接口概念

Picker 的 `-c` 开启 **代码覆盖率** 数据收集。Python 侧的 **功能覆盖率** 由 Toffee / toffee-test 建模，例如：

```python
import toffee.funcov as fc

g = fc.CovGroup("adder")
g.add_watch_point(
    dut.io_cout,
    {"cout=0": fc.Eq(0), "cout=1": fc.Eq(1)},
    name="carry_out",
)
dut.StepRis(lambda cycle: g.sample())
```

覆盖率的正确顺序是：**Spec 功能点 → 测试点/覆盖 bins → 激励 → 采样 → 未覆盖项分析 → 补测试**。不是先写个覆盖点，再为了 100% 而制造无意义激励。

`-c` 产生的是 Verilator 的代码覆盖率数据（例如 `VSyncFIFO_coverage.dat`）；功能覆盖率回答的是“规格场景是否都发生过”，两者互补、不可替代。使用 pytest/toffee-test 时，通常在 fixture 的 teardown 中合并覆盖组；加 `--toffee-report` 可生成可视化报告。

## 9. 本讲命令的边界

`picker --check` 用于确认安装路径与已启用语言。`picker export` 才是本讲日常使用的命令：把 RTL 编译/封装为高层语言 DUT 接口。对于多文件 RTL，用 `--fs` 提供 filelist；务必显式写 `--sname` 指定顶层；`--internal` 是静态导出内部信号；`--rw 1`（仅 Verilator）可启用更高性能的 Mem-Direct 动态内部信号访问。

`picker pack` 是另一条路线：把已有 UVM `sequence_item` 自动封装成 Python 等语言可调用的事务接口。它用于“已有 UVM 环境，想让 Python 发事务”的场景；本 FIFO 实验是直接 `export` RTL，不涉及 `pack`。

## 10. 第二讲完整知识清单

到这里，第二讲网页的主干已经都覆盖：Picker 的定位（`export` 和 `pack`）、Linux/Verilator/SWIG/Verible/lcov 依赖、DUT 动态库及多语言接口、`Finish()`、端口读写与 XData 三种写模式、静态/动态内部信号、时钟推进/异步等待/边沿回调、动态波形、`assert` 与参考模型、代码覆盖率与功能覆盖率、`--check`/路径查询和 `export` 常用参数、多时钟/多实例的高级能力。Docker 镜像只是可选的预装环境；当前 WSL 原生环境已可用，因此不必再引入 Docker 这一层。

## 11. 进入下一讲前应会的排错清单

1. `source .tooling/env.sh && picker --check`：先确认 Python 支持为 OK。
2. `picker export ... --sname <top>`：明确顶层、文件列表和输出目录。
3. 端口名、时钟名与 RTL 完全一致；先跑 reset + 一两个 `Step()` 的 smoke test。
4. 每个时序动作都明确在哪个沿生效；不要把组合刷新和时钟推进混为一谈。
5. `assert` 错误必须包括周期、输入、实际值和预期值；随机测试要记录 seed。
6. 无论成功或失败，都调用 `Finish()`。

## 一句话复盘

**Picker 负责把 RTL 变成可调用 DUT；验证代码负责驱动、推进和检查；参考模型负责定义正确答案；波形与覆盖率负责解释和量化“我们到底测了什么”。**
