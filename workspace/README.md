# Workspace 索引

这里是本次学习任务的可复现材料，不包含本机工具链和编译产物。

| 目录 | 用途 | 入口命令 |
| --- | --- | --- |
| `picker_fifo/` | Picker：同步 FIFO 的 Python DUT、复位/读写/波形测试 | `make -C picker_fifo test` |
| `toffee_fifo/` | Toffee：Bundle、Agent、参考模型和功能覆盖率 | `make -C toffee_fifo report` |
| `nutshell_cache/` | NutShell Cache：SimpleBus 环境、独立参考模型、39 个测试和验证报告 | `make -C nutshell_cache report` |
| `nutshell_src/` | NutShell 的 Chisel/Scala 源码和 Cache 模块化说明 | 见 `nutshell_src/CACHE_REFACTOR.md` |

Cache 验证的正式结果记录在 `nutshell_cache/report/nutshell_cache_verification_report.md`：
39/39 个 pytest cases 通过，37/37 功能覆盖目标命中；维护 RTL 原始行覆盖率为 98.0%（845/862），waiver 调整后为 100%（845/845），全源覆盖率为 95.1%（1423/1496）。

GitHub Actions 在干净的 Ubuntu runner 上安装开源工具链、运行形式检查和 8-seed/512-operation 回归；[查看 CI 记录](https://github.com/cwu766485-ctrl/open_verif_learning/actions/workflows/nutshell-cache-dv.yml)。

报告中的 `reports/`、`Cache/`、`generated/`、`build/`、`out/`、波形和 native library 都是本地可再生文件，已被 Git 忽略。
