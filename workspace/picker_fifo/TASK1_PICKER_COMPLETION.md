# 学习任务 1：Picker 部分 - 完成说明

## 验收结果

在 Ubuntu WSL 中执行：

```bash
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh
cd workspace/picker_fifo
make test
```

结果：`Course 2 Picker FIFO tests: PASS`。

本次运行生成：

- `reset_rise.fst`：`rst_n` 使用默认上升沿写入模式的复位波形；
- `reset_immediate.fst`：`rst_n` 使用立即写入模式的复位波形；
- `smoke.fst`：两次写入、两次读出的冒烟测试波形；
- `VSyncFIFO_coverage.dat`：Verilator 代码覆盖率数据。

## 验证对象：SyncFIFO

SyncFIFO 是单时钟、低有效同步复位的 FIFO：数据宽度 32 bit，深度 16 项，按先进先出顺序读写。

| 信号 | 方向 | 作用 |
|---|---|---|
| `clk` | 输入 | 所有状态在上升沿更新 |
| `rst_n` | 输入 | 低有效同步复位 |
| `we_i` / `data_i` | 输入 | 写请求和 32 bit 写数据 |
| `re_i` | 输入 | 读请求 |
| `data_o` | 输出 | 成功读出时给出数据 |
| `full_o` / `empty_o` | 输出 | 满/空状态 |

内部有 16 项 RAM、4 bit 的 `wptr` 与 `rptr`、5 bit 的 `counter`。指针只需 4 bit，因为自然回绕即可覆盖 0 到 15；计数器必须 5 bit，因为它需要表示 16。

有效事务不是单看 `we_i` / `re_i`：

```text
wvalid = we_i && !full_o
rvalid = re_i && !empty_o
```

因此“满时写”和“空时读”不会改变指针、计数或输出数据。读写同时有效时，两个指针都前进，但 `counter` 不变，因为 FIFO 的存量没有变化。

## 任务要求与实现对应

| 任务要求 | 对应实现 |
|---|---|
| 创建 FIFO DUT 类 | `Makefile` 的 `picker export ... --lang python --sim verilator`，生成 `generated/SyncFIFO/DUTSyncFIFO` |
| 导出内部信号 | `internal.yaml` 导出 `wptr`、`rptr`、`counter` |
| 默认模式复位并导出波形 | `test_reset_rise_write()`，输出 `reset_rise.fst` |
| 立即模式复位并比较波形 | `test_reset_immediate_write()`，输出 `reset_immediate.fst` |
| 复位后断言端口与指针 | `assert_reset_state()` 检查 `data_o`、`empty_o`、`full_o`、两个指针和计数器 |
| 写入 `0x114`、`0x514`，再读回 | `test_smoke_dut()` |
| 检查首写后状态 | 第一次写后断言 `empty_o == 0`、`full_o == 0` |
| 检查 FIFO 顺序 | 两次读分别断言 `data_o == 0x114`、`data_o == 0x514` |

## 为什么初始化不只设置 rst_n 也要把端口设置在确定值

仿真开始时，输入端口没有确定的值。即使设计使用 Verilator 的二值后端而没有显式看到 `X`，未初始化的 `we_i`、`re_i`、`data_i` 仍会使测试依赖工具默认值，掩盖真实问题。

所以 `new_dut()` 把 `we_i`、`re_i`、`data_i` 配置为 `AsImmWrite()` 并赋零；复位测试再单独选择 `rst_n` 的写入时机。这样每个测试都从确定、可复现的输入状态开始。

## 写入模式与波形观察

Picker 的默认 `AsRiseWrite()` 会在时钟上升沿阶段应用赋值；`AsImmWrite()` 会在推进时钟前立即把值驱动到 DUT。对同步电路而言，输入是否已在上升沿前稳定，会影响 DUT 本次还是下次采样到该值。

打开波形：

```bash
make wave-reset-rise
make wave-reset-immediate
make wave-smoke
```

在 GTKWave 中添加 `clk`、`rst_n`、`we_i`、`re_i`、`data_i`、`data_o`、`empty_o`、`full_o`。比较两张 reset 波形时，看 `rst_n` 跳变相对 `clk` 上升沿的位置；看 `smoke.fst` 时，按“复位 → 写 0x114 → 写 0x514 → 读 0x114 → 读 0x514”的顺序核对。

## 本任务的工程边界

应维护：`rtl/SyncFIFO.v`、`internal.yaml`、`test_picker_fifo.py`、`Makefile` 与文档。

不应手改：`generated/` 下的 Python 绑定、`.so`、wrapper、模板和缓存。它们是 `picker export` 的构建产物；需要重建时执行 `make export`，彻底清理时执行 `make distclean`。
