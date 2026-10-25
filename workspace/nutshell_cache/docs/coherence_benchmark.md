# 双核 MESI 子系统性能 Benchmark

这是隔离运行的性能 workload，不属于功能回归。`add_coherence_perf.py` 在当前
`tests/subsystem/rtl/CoherentCacheSubsystem_tb.sv` 中添加 `+perf_only` 模式，并先备份
原文件为 `.before_perf.bak`。该 workload 复用现有 CPU transaction driver、内存模型、
数据 scoreboard 和一致性参考状态。

## 运行

在仓库根目录执行：

```bash
python3 add_coherence_perf.py
make coherence_build
reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +perf_only \
  | tee reports/coherence/perf.log
grep '^COHERENCE_PERF' reports/coherence/perf.log
```

`+perf_only` 只运行 benchmark，不运行后面的功能回归序列。普通的
`make coherence_smoke` 和 `make coherence_regression` 不带该 plusarg，不会跑 benchmark。
脚本要求源代码锚点唯一；锚点不匹配时会停止，不会盲目改写文件。
本轮运行后的实测表格见
[`coherence_benchmark_results_2026-10-25.md`](coherence_benchmark_results_2026-10-25.md)。

## 六组 workload

1. 预热后 64 次 L1 热读。
2. 32 条不同 cache line 的冷读。
3. 16 次由 Core0 的 M owner 向 Core1 提供数据的远程 GetS。
4. 16 次 S→M upgrade。
5. 两个 core 同时访问各自热 line，共 32 对。
6. 9 条 dirty line 映射到同一个 8-way L2 set，触发冲突回收。

## 输出字段

每行 `COHERENCE_PERF` 包含完成操作数、benchmark 窗口周期、`cycles_per_op`、CPU
请求握手到响应握手的平均周期数，以及 64-byte memory line read/write、Directory 请求和
snoop 数量。`cycles_per_op` 包含逐笔发起请求的间隔，可衡量此 driver 下的吞吐；
`mean_req_to_resp_cycles` 从 CPU request valid/ready 握手开始计时，不包含 ready 等待。

当前结果是单次、无额外随机反压的 RTL 周期数据。要比较 PPA 或给出稳定分位数，还需要
可控内存延迟、p50/p95 直方图、多 seed 重复和相同 trace 的配置对照；当前报告不代表
物理时序或硅面积。
