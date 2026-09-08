# Discussion #13 提交模板

将以下内容复制到 [UnityChipForXiangShan Discussion #13](https://github.com/XS-MLVP/UnityChipForXiangShan/discussions/13)，再把链接和附件替换成自己的仓库/文件。

```markdown
## 万众一芯新手任务：NutShell Cache 验证

大家好，这是我的 NutShell Cache 验证任务提交。

### 代码与报告

- 验证代码仓库：https://github.com/cwu766485-ctrl/open_verif_learning/tree/c4da358
- 验证报告（Markdown）：`workspace/nutshell_cache/report/nutshell_cache_verification_report.md`
- 验证报告（PDF）：`workspace/nutshell_cache/report/nutshell_cache_verification_report.pdf`
- Toffee HTML 报告：`workspace/nutshell_cache/reports/cache`
- RTL 覆盖率报告：`workspace/nutshell_cache/reports/rtl/index.html`

### 复现环境

```bash
cd workspace/nutshell_cache
source ../../.tooling/env.sh
make gen_dut
make report
```

### 验证结果

- 基线 7 个 pytest 用例全部通过；新增冲突替换、writeback、backpressure、probe、跨 line 和长随机序列后，请在 Linux/WSL 重跑并把最终用例数填在这里
- 基线 RTL line coverage：79.2%（1151/1454）；新增回归后的覆盖率请以 `make report` 结果为准
- 覆盖内容：复位/流水线排空、cold miss/refill/hit、整字写、byte mask、MMIO 隔离、dirty eviction/writeback、下游延迟、coherence probe、跨 Cache line 访问和长随机序列

报告包含功能梳理、测试点分解、测试用例、参考模型、结果分析和未覆盖项说明。
欢迎审核和提出改进建议。
```

官方任务要求提交验证代码和报告，报告应包含功能梳理、测试点分解、测试用例、结果分析和结论；如果使用私有仓库，需要给官方审核者读取权限，也可以上传加密压缩包并提供密码。
