# Open Verify Learning Notes

基于[万众一芯开放验证](https://open-verify.cc/)新手任务的个人学习记录：使用 Picker、Toffee 和 pytest 验证一个同步 FIFO。

本仓库的重点是“可阅读的验证代码和学习笔记”，而不是提交本机工具安装目录或仿真二进制产物。

## 内容

| 目录 | 内容 |
| --- | --- |
| `docs/` | 芯片验证基础、Picker、Toffee 及两个学习任务的中文笔记 |
| `labs/course2_picker_fifo/` | 学习任务 1：Picker 生成 Python DUT，完成复位、读写及波形测试 |
| `labs/course3_toffee_fifo/` | 学习任务 2：Toffee Bundle、Agent、参考模型、功能覆盖率 |

## 已完成的验证

- 同步 FIFO：32 bit 宽、深度 16、同步低有效复位。
- Picker：导出 Python DUT，比较 `AsRiseWrite()` 与 `AsImmWrite()`，并生成 FST 波形。
- Toffee：实现读/写/控制/内部状态 Bundle，FIFO Agent，Python `deque` 参考模型，以及功能覆盖率。
- 课程 3 测试：4 个 pytest 用例通过；功能覆盖率为 13/13 bins（100%）。

## 运行

建议在 Ubuntu WSL 中使用。先按[万众一芯安装文档](https://open-verify.cc/mlvp/docs/quick-start/installer/)准备 Picker、Toffee、Python 和 Verilator 环境；本仓库不提交这些本机工具文件。

```bash
# 学习任务 1
cd labs/course2_picker_fifo
make test

# 学习任务 2
cd ../course3_toffee_fifo
make test
make report
make clean
```

课程 2 的 `make test` 会在需要时运行 `picker export`，生成本地 `generated/` DUT；课程 3 则复用它。

## 学习资源与来源

- [新手任务](https://open-verify.cc/beginner/task/)
- [同步 FIFO 规格与参考 RTL](https://open-verify.cc/beginner/task/sync_fifo)
- [学习任务 1：Picker](https://open-verify.cc/beginner/task/course/2-picker/)
- [学习任务 2：Toffee](https://open-verify.cc/beginner/task/toffee/)
- [XS-MLVP 开源组织](https://github.com/XS-MLVP)

本仓库是个人学习笔记，不代表万众一芯官方项目或其背书。第三方材料的归属与许可见 [NOTICE.md](NOTICE.md)。
