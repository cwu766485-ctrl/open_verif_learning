# Discussion #13 提交模板

将以下内容复制到 [UnityChipForXiangShan Discussion #13](https://github.com/XS-MLVP/UnityChipForXiangShan/discussions/13)，再把链接和附件替换成自己的仓库/文件。

```markdown
## 万众一芯新手任务：NutShell Cache 验证

大家好，这是我的 NutShell Cache 验证任务提交。

### 代码与报告

- 验证代码仓库：https://github.com/cwu766485-ctrl/open_verif_learning/tree/codex/nutshell-cache-dv
- 验证报告（Markdown）：https://github.com/cwu766485-ctrl/open_verif_learning/blob/codex/nutshell-cache-dv/workspace/nutshell_cache/report/nutshell_cache_verification_report.md
- 验证报告（PDF）：`workspace/nutshell_cache/nutshell_cache_report_demo.pdf`
- 干净环境 CI 记录：https://github.com/cwu766485-ctrl/open_verif_learning/actions/workflows/nutshell-cache-dv.yml
- Toffee HTML 报告：执行 `make report` 后生成的 `workspace/nutshell_cache/reports/cache`
- RTL 覆盖率报告：执行 `make report` 后生成的 `workspace/nutshell_cache/reports/rtl/index.html`

### 复现环境

```bash
cd workspace/nutshell_cache
source scripts/env.sh
make gen_dut
make formal
make report
```

### 验证结果

- Linux/WSL `make report`：39/39 pytest cases 通过，包含冲突替换、writeback、backpressure、probe、reset cancellation、跨 line 和多 seed 随机序列
- 功能覆盖：37/37 goals（100%）；维护 RTL 原始 line coverage：98.0%（845/862），waiver 调整后 100%（845/845）
- 含生成 DUT/wrapper 的全源 line coverage：95.1%（1423/1496）；CI 每次使用 8 个固定 seed、512 笔随机操作
- Fault injection：4/4 个代表性错误被 checker 捕获；形式验证范围和假设见验证报告
- 覆盖内容：复位/流水线排空、cold miss/refill/hit、整字写、byte mask、MMIO 隔离、dirty eviction/writeback、下游延迟、coherence probe、跨 Cache line 访问和长随机序列

报告包含功能梳理、测试点分解、测试用例、参考模型、结果分析和未覆盖项说明。
欢迎审核和提出改进建议。
```

官方任务要求提交验证代码和报告，报告应包含功能梳理、测试点分解、测试用例、结果分析和结论；如果使用私有仓库，需要给官方审核者读取权限，也可以上传加密压缩包并提供密码。
