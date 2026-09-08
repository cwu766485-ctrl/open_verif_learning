# Open Verify 任务提交说明

## 提交入口

新手任务的代码和报告应在
[UnityChipForXiangShan Discussions #13](https://github.com/XS-MLVP/UnityChipForXiangShan/discussions/13)
中直接回复提交。果壳 Cache 的任务要求和报告字段见
[官方任务页](https://open-verify.cc/beginner/task/nutshell-cache/)。

## 本工作区对应材料

- `picker_fifo/`：学习任务 1，Picker FIFO；
- `toffee_fifo/`：学习任务 2，Toffee FIFO；
- `nutshell_cache/`：学习任务 3，果壳 Cache；
- `nutshell_cache/report/nutshell_cache_verification_report.md`：可直接阅读的报告；
- `nutshell_cache/report/nutshell_cache_verification_report.md`：最终 Markdown 报告（正式版本）；
- `nutshell_cache/reports/cache`：Toffee 测试报告；
- `nutshell_cache/reports/rtl/index.html`：Verilator RTL 覆盖率报告。

## 复核命令

```bash
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh
make -C workspace/picker_fifo test
make -C workspace/toffee_fifo report
make -C workspace/nutshell_cache report
```

回复 Discussion 时建议附上 Cache 验证代码、Markdown 报告和报告截图或
链接。`nutshell_cache/Cache/`、波形和 coverage 数据是本机生成物，审阅者可按
`Readme.md` 的 `make gen_dut`、`make report` 重新生成；如果打包上传，可以不带
这些大文件。若使用私有仓库，需要给官方审阅者开放读取权限。
