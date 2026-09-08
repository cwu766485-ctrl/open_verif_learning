# Workspace 索引

这里是本次学习任务的可复现材料，不包含本机工具链和编译产物。

| 目录 | 用途 | 入口命令 |
| --- | --- | --- |
| `picker_fifo/` | Picker：同步 FIFO 的 Python DUT、复位/读写/波形测试 | `make -C picker_fifo test` |
| `toffee_fifo/` | Toffee：Bundle、Agent、参考模型和功能覆盖率 | `make -C toffee_fifo report` |
| `nutshell_cache/` | NutShell Cache：SimpleBus 环境、参考模型、12 个测试和报告 | `make -C nutshell_cache report` |
| `nutshell_src/` | NutShell 的 Chisel/Scala 源码和 Cache 模块化说明 | 见 `nutshell_src/CACHE_REFACTOR.md` |

Cache 验证的正式结果记录在 `nutshell_cache/report/nutshell_cache_verification_report.md`：
12 个测试通过，RTL 行覆盖率 80.1%（1164/1454）。

报告中的 `reports/`、`Cache/`、`generated/`、`build/`、`out/`、波形和 native library 都是本地可再生文件，已被 Git 忽略。
