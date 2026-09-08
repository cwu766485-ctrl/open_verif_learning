# Open Verify Learning Notes

这是基于[万众一芯开放验证](https://open-verify.cc/)新手任务的个人学习仓库：先用 Picker、Toffee 和 pytest 验证同步 FIFO，再完成 NutShell Cache 的验证实战。

仓库保留可阅读、可复现的源码、测试、报告和学习笔记；本机虚拟环境、编译缓存、仿真库、波形和覆盖率原始数据均由 `.gitignore` 排除。

## 内容

| 目录 | 内容 |
| --- | --- |
| `docs/` | 芯片验证基础、Picker、Toffee 及两个学习任务的中文笔记 |
| `workspace/picker_fifo/` | 学习任务 1：Picker 生成 Python DUT，完成复位、读写及波形测试 |
| `workspace/toffee_fifo/` | 学习任务 2：Toffee Bundle、Agent、参考模型、功能覆盖率 |
| `workspace/nutshell_cache/` | 学习任务 3：果壳 Cache 的 Toffee/Picker 验证、功能测试、覆盖率和报告 |
| `workspace/nutshell_src/` | NutShell Chisel/Scala 源码副本；Cache 已按公共类型、三级流水线和顶层连线拆分 |

## 已完成的验证

- 同步 FIFO：32 bit 宽、深度 16、同步低有效复位。
- Picker：导出 Python DUT，比较 `AsRiseWrite()` 与 `AsImmWrite()`，并生成 FST 波形。
- Toffee：实现读/写/控制/内部状态 Bundle，FIFO Agent，Python `deque` 参考模型，以及功能覆盖率。
- Toffee FIFO：4 个 pytest 用例通过；功能覆盖率为 13/13 bins（100%）。
- 果壳 Cache：`make report` 通过 12 个 pytest 用例；Verilator RTL 行覆盖率 80.1%（1164/1454）。
- Cache 验证覆盖复位/流水线排空、cold miss/refill/hit、写回、byte mask、MMIO 隔离、下游 backpressure、coherence probe、跨 line 访问和长随机序列。
- NutShell Cache 源码：已完成 Chisel 源码级模块化，生成 RTL 的模块名按 ICache、DCache、L2Cache 角色区分。

## 运行

建议在 Ubuntu WSL 中使用。先按[万众一芯安装文档](https://open-verify.cc/mlvp/docs/quick-start/installer/)准备 Picker、Toffee、Python 和 Verilator 环境；本仓库不提交这些本机工具文件。

```bash
# 学习任务 1：Picker
cd workspace/picker_fifo
make test

# 学习任务 2：Toffee
cd ../toffee_fifo
make test
make report
make clean

# 学习任务 3：果壳 Cache
cd ../nutshell_cache
make report
```

课程 2 的 `make test` 会在需要时运行 `picker export`，生成本地 `generated/` DUT；课程 3 则复用它。

NutShell 源码重构和 Chisel→FIRRTL/CIRCT→Verilog 生成命令见 [`workspace/nutshell_src/CACHE_REFACTOR.md`](workspace/nutshell_src/CACHE_REFACTOR.md)。生成目录由 `.gitignore` 排除，可随时重新生成。

提交材料索引见 [`workspace/SUBMISSION.md`](workspace/SUBMISSION.md)，Discussion #13 的可复制提交文字见 [`workspace/SUBMISSION_POST.md`](workspace/SUBMISSION_POST.md)。

## 学习资源与来源

- [新手任务](https://open-verify.cc/beginner/task/)
- [同步 FIFO 规格与参考 RTL](https://open-verify.cc/beginner/task/sync_fifo)
- [学习任务 1：Picker](https://open-verify.cc/beginner/task/course/2-picker/)
- [学习任务 2：Toffee](https://open-verify.cc/beginner/task/toffee/)
- [XS-MLVP 开源组织](https://github.com/XS-MLVP)

本仓库是个人学习笔记，不代表万众一芯官方项目或其背书。第三方材料的归属与许可见 [NOTICE.md](NOTICE.md)。
