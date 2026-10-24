format:
1. Chinese
2. update each time when you editing
3. 当前时间戳+对代码进行的修改/遇见的bug/其他值得记录的事情
4. 每次记录尽可能简短
## 2026-10-24（新加坡时间）
- 20:24：拆分请求仲裁器的 valid/payload 与 ready 组合逻辑，定位并消除 `UNOPTFLAT` 组合环路告警。
- 20:28：清理未使用 RTL 信号；目录验证改用 harness 记录已接收 opcode，避免形式验证依赖已移除的硬件状态；补上 L1 阵列读未命中错误上报。
- 20:31–20:36：为四上下文 Directory MSHR bank 增加独立 formal harness、BMC 与覆盖目标。形式化展开暴露 commit 上下文选择的组合依赖；改为匹配向量加优先选择，并映射 SV 数组供 Yosys 处理。
- 20:39：MSHR bank 12 周期有界检查通过；覆盖检查到 2 个及 4 个上下文同时活动。结果是有界证据，不代表无界证明。
- 21:15：汇总近期 RTL/formal 改动并同步到 GitHub `cache_coherence` 分支；后续代码修改完成后立即提交并推送。
