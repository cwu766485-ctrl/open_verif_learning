# 文档归档索引

此目录保存历史规格、阶段性验证说明和旧版结果，供追溯设计演进使用。归档内容不是当前实现状态的签核依据；若历史描述与当前文件冲突，以主文档、RTL、DV 和最新报告为准。

## 当前维护文档

- [MESI Cache 规格与架构](../cache.md)
- [RTL 目录与模块说明](../../rtl/README.md)
- [Python/Toffee DV 平台](../../dv/README.md)
- [验证计划与覆盖映射](../testplan_to_coverage_matrix.md)
- [Benchmark 方法](../coherence_benchmark.md)
- [Benchmark v3 结果](../coherence_benchmark_v3_results_2026-10-25.md)
- [最终验证报告](../../reports/final/nutshell_cache_verification_report.md)

## 归档内容

- `legacy/`：原单 L1 DCache 的接口说明和规格/验证基线；不能代替当前双 L1 MESI 规格。
- `benchmarks/`：Benchmark v1/v2 历史测量；当前性能结果以 Benchmark v3 为准。
- `coherence_rtl.md`：MESI RTL 的历史实现快照；当前目录结构以 `rtl/README.md` 为准。
- `python_open_source_verification.md`：Python 验证平台的历史迁移说明；当前环境以 `dv/README.md` 为准。
- `update_log.md`：项目开发与验证的时间记录，继续作为更新日志维护。
