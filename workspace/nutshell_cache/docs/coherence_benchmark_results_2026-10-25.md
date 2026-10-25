# 双核 MESI 子系统性能测试记录（2026-10-25）

使用从 `coherence_benchmark_starter` 复制的 `add_coherence_perf.py`，对
`CoherentCacheSubsystem` 跑了六组 workload。仿真时钟为 10 ns，内存响应按固定
模型返回，没有额外随机反压。数据是 RTL 周期级仿真结果，不代表综合后时序或芯片性能。

| Workload | 完成操作 | 窗口周期 | 周期/操作 | 请求握手到响应平均周期 | DRAM 读 line | DRAM 写 line | Directory 请求 | Snoop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 热 L1 本地读 | 64 | 321 | 5.02 | 3.00 | 0 | 0 | 0 | 0 |
| 冷 L1/L2/内存读 | 32 | 1217 | 38.03 | 36.00 | 32 | 0 | 32 | 0 |
| 远端 GetS，由 M Owner 提供 | 16 | 481 | 30.06 | 28.00 | 0 | 0 | 16 | 16 |
| S→M Upgrade | 16 | 193 | 12.06 | 10.00 | 0 | 0 | 16 | 16 |
| 双核独立热读 | 64（32 对） | 161 | 2.52 | 3.00 | 0 | 0 | 0 | 0 |
| 同一 L2 set 的 9 条 dirty line | 9 | 485 | 53.89 | 51.78 | 9 | 4 | 16 | 0 |

`周期/操作` 用 workload 总窗口周期除以完成操作数，包含 testbench 逐笔发起的
间隔；它可以反映这组驱动下的吞吐。平均延迟从 CPU 请求 valid/ready 握手计到
响应握手，不含请求等待 ready 的周期。本轮六组的 ready stall 均为 0。

热点读仅在本地完成，没有进入 Directory 或外存。冷读的 32 次 miss 各取回一条
64-byte line。远端 GetS 和升级场景各执行了 16 次 snoop，但没有额外内存读写。
同组 set 冲突压测触发了 9 次 refill 和 4 条 dirty writeback。

运行日志在本机 `reports/coherence/perf.log`。benchmark 脚本会临时扩展 SV harness
并生成 `.before_perf.bak`；测试后按使用指南恢复 harness。随后保留的正式验证入口是
`make coherence_python_test` 与原有 `make coherence_regression`。
