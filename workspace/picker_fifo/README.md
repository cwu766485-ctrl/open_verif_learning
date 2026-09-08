# Picker 课程 2：同步 FIFO 实验

本目录对应“学习任务 1：Picker 部分”。所有命令均在 Ubuntu WSL 中执行。

```bash
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh
cd workspace/picker_fifo
```

## 统一入口：Makefile（推荐）

本目录在 WSL 下，最适合使用 Makefile 管理“生成 → 测试 → 看波形 → 清理”的依赖关系：

```bash
make help
make export       # 只生成 Python DUT，适合学习 Picker export
make test         # 生成 DUT 后运行所有测试
make wave-smoke   # 打开 smoke.fst
make clean        # 清理测试产物
make distclean    # 进一步清理 generated/ 编译产物
```

本实验只保留 Makefile 这一套入口，避免同一件事有两种命令。

## Step 1：生成 Python DUT（底层命令）

```bash
picker export rtl/SyncFIFO.v \
  --sname SyncFIFO \
  --lang python \
  --sim verilator \
  --tdir generated/SyncFIFO \
  --internal internal.yaml \
  -w SyncFIFO.fst \
  -c
```

`generated/SyncFIFO` 是可重新生成的构建产物；手写 RTL 和测试文件不要放进该目录。

## Step 2：运行测试

```bash
python test_picker_fifo.py
```

本测试会分别创建三份波形在**本目录根部**（不是 `generated/` 内）：

- `reset_rise.fst`：`rst_n` 用默认上升沿写入；
- `reset_immediate.fst`：`rst_n` 用立即写入；
- `smoke.fst`：FIFO 写入与读出流程。

例如查看冒烟测试波形：

```bash
gtkwave smoke.fst
```

本课程实际使用的测试在 `test_picker_fifo.py`：

- `test_reset_rise_write`：默认上升沿写入模式的复位。
- `test_reset_immediate_write`：`rst_n.AsImmWrite()` 后的复位。
- `test_smoke_dut`：写入 `0x114`、`0x514` 后按 FIFO 顺序读回。

两种复位测试会额外生成 `reset_rise.fst` 与 `reset_immediate.fst`，用于观察同一个赋值在默认上升沿写入与立即写入模式下的时序差异。

`make clean` / `make distclean` 都不会删除 `rtl/`、`internal.yaml`、`test_picker_fifo.py` 或本 README。
