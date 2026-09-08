# 果壳 Cache 验证报告

日期：2026-09-08  
工程目录：`workspace/nutshell_cache/`

## 1. 验证结论

本次验证使用 Picker 生成 Python DUT，使用 Toffee Agent、参考模型和
`pytest` 对 NutShell Cache 的 SimpleBus 接口进行了验证。

最终命令 `make report` 的结果为：

- 12 个测试全部通过（`12 passed`）；
- Toffee HTML 报告：`reports/cache`；
- Verilator RTL 行覆盖率：80.1%（1164/1454），详细页面为
  `reports/rtl/index.html`；
- 测试波形：`cache.fst`。

结论：在本报告覆盖的复位、读缺失填充、读命中、写回读、字节掩码、MMIO
路由、连续字访问和可复现混合事务场景下，DUT 与参考模型行为一致。

## 2. 验证对象和接口

验证对象为 `rtl/Cache.v` 的 `Cache` 模块。Cache 通过 SimpleBus 接收上游
请求，并根据地址将事务路由到 Cache backing memory 或 MMIO 从设备。RTL
实现包含多级流水、4 路组相联数据阵列和按 Cache line 的 refill 路径。

本次环境观察并检查以下边界：

| 类别 | 检查内容 |
| --- | --- |
| 请求类型 | `CMD_READ` 和 `CMD_WRITE` |
| 响应类型 | `CMD_READLST` 和 `CMD_WRITERSP` |
| 数据宽度 | 64 bit word |
| 写掩码 | 8 byte mask，从全写到单 byte 写 |
| 普通内存 | 冷读产生 backing-memory 访问，重复读命中 Cache |
| MMIO | `0x30000000` 区域走 MMIO，不产生普通 Cache memory 访问 |

## 3. 验证环境

```text
test/
  base_test.py       复位、时钟、DUT 和从设备 responder
  test_smoke.py      基线冒烟测试
  test_functional.py 功能场景和可复现混合事务
src/env/
  bundle.py          SimpleBus 请求/响应 Bundle
  simplebus_agents.py 上游 Master Agent
  simpleram.py       memory/MMIO responder 和事务记录
src/ref/ref_cache.py  SimpleBus 参考模型
```

`base_test.py` 为每个用例建立独立环境，启动 DUT、上游 Master、普通内存
从设备和 MMIO 从设备。`SimpleBusRam` 保存收到的事务列表，因此测试不仅
检查最终响应数据，也检查请求是否走到了正确的下游端口。

## 4. 测试点和用例

| 用例 | 测试点 | 通过判据 |
| --- | --- | --- |
| `test_reset_drains_pipeline` | 复位后的流水线状态 | `io_empty=1`，复位期间无下游事务 |
| `test_read_miss_then_hit` | 冷读、line refill、重复读命中 | 首次读访问 memory，第二次读返回相同数据且不增加 memory read 次数 |
| `test_write_read_and_byte_mask` | 全字写和单 byte 掩码写 | 写响应正确，读回原值，再读回只更新目标 byte 的新值 |
| `test_mmio_isolated_from_cache_memory` | MMIO 路由 | MMIO 写后读回 `0xCAFE`，普通 memory 计数不变 |
| `test_sequential_words_preserve_order` | 一条 line 内的 8 个相邻 word | 8 个地址逐一写入后逐一读回，数据和顺序一致 |
| `test_deterministic_mixed_sequence` | 混合读写和随机 byte mask | 固定种子 `0xCAFE` 产生 24 笔事务，逐笔和 shadow model 比较 |
| `test_smoke` | 官方基础 smoke 场景 | 复位、读、写和响应命令均满足基线要求 |

## 5. 参考模型和测试修正

验证过程中发现示例环境中有两个会掩盖 DUT 行为的问题，已在本工程中修正：

1. `SimpleBusMasterAgent.non_block_write` 原来用位置参数构造 `ReqMsg`，导致
   写数据落入 `size` 字段。现在改为显式关键字参数 `mask=`、`data=`。
2. 参考模型的写响应原来固定返回 0。Cache 写命中时返回写入前的 word，因而
   参考模型现在先保存旧值，再更新 shadow data，并返回旧值。

这些修改属于验证环境和参考模型修正，不改变 `rtl/Cache.v`。

## 6. 结果和覆盖率

运行命令：

```bash
cd /mnt/e/workspace/chip/open_verif/workspace/nutshell_cache
source ../../.tooling/env.sh
make report
```

结果摘要：

```text
12 passed
RTL line coverage: 80.1% (1164 of 1454 lines)
```

`reports/cache` 是 Toffee 生成的 HTML 测试报告，`reports/rtl` 是
`verilator_coverage` 和 `genhtml` 生成的 RTL 覆盖率报告。覆盖率未达到 100%
是预期的：本次任务没有实现 coherence、victim buffer 和完整冲突替换矩阵，
也没有把所有内部状态组合列为功能覆盖目标。

## 7. 限制和未覆盖项

- `io_flush` 在当前 RTL 中对该 Cache 配置会触发“only allow to flush icache”的
  设计断言，因此没有把数据 Cache flush 作为通过用例；这应作为 DUT 接口约束
  在后续规格确认中单独处理。
- 本次验证没有覆盖多主设备 coherence、victim 输出接口和跨 line 的复杂替换。
- 测试使用固定种子的可复现序列，重点是稳定回归，不等同于随机约束覆盖。

## 8. 提交材料

建议在 UnityChipForXiangShan 的 GitHub Discussion #13 中直接回复：

- `workspace/nutshell_cache/` 中的验证代码和 `Readme.md`；
- 本报告 `report/nutshell_cache_verification_report.md`（以及生成的 PDF）；
- `reports/cache` 和 `reports/rtl` 的测试、覆盖率产物；
- 如需打包，保留 `make gen_dut` 说明，让审阅者可在本地重新生成 Picker
  DUT，而不是依赖本机生成的二进制文件。

官方提交要求：报告包含功能原理、测试点分解、测试用例、结果分析和结论；
代码包含验证环境和测试用例。提交入口为
`XS-MLVP/UnityChipForXiangShan` 的 Discussions #13。
