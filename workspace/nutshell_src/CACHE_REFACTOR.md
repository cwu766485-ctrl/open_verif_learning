# NutShell Cache 源码重构说明

## 目标

这次修改保持 Cache 的时序和接口行为不变，只做源码组织和生成模块命名优化：

| 文件 | 职责 |
| --- | --- |
| `src/main/scala/nutcore/mem/CacheTypes.scala` | 配置、地址划分、Meta/Data Bundle、公共 IO |
| `src/main/scala/nutcore/mem/CacheStage1.scala` | 请求接收以及 Meta/Data Array 读请求 |
| `src/main/scala/nutcore/mem/CacheStage2.scala` | Tag 比较、命中判断、无效 way/随机 victim 选择 |
| `src/main/scala/nutcore/mem/CacheStage3.scala` | 命中响应、写回、重填、MMIO、coherence 和状态机 |
| `src/main/scala/nutcore/mem/CacheTop.scala` | Cache 顶层连线、Array、流水线和 bypass/dummy 实现 |

原来的 `Cache.scala` 保留为入口说明文件，避免后续读者误以为 Cache 逻辑仍然集中在一个文件中。

## 生成 RTL

NutShell 使用 Chisel/FIRRTL/CIRCT 生成 SystemVerilog。Windows 下在本目录执行：

```powershell
$env:NOOP_HOME = (Get-Location).Path
cmd /c ".\mill.bat -i generator.test.runMain top.TopMain --target-dir build\rtl BOARD=sim CORE=inorder --split-verilog"
```

`mill.bat` 是与仓库 `.mill-version`（0.12.17）匹配的启动器。生成结果位于 `build/rtl/`，Cache 相关模块使用稳定名称：

```text
ICache.sv       ICacheStage1.sv  ICacheStage2.sv  ICacheStage3.sv
DCache.sv       DCacheStage1.sv  DCacheStage2.sv  DCacheStage3.sv
L2Cache.sv      L2CacheStage1.sv L2CacheStage2.sv L2CacheStage3.sv
```

命名来自 `CacheConfig.name`，不再依赖 Chisel 对重复实例自动生成的 `Cache_1`、`Cache_2` 后缀。`--split-verilog` 会将模块拆成独立的 `.sv` 文件，便于波形、审查和综合工具使用。

## 构建验证

已使用 `BOARD=sim CORE=inorder` 完成 Chisel elaboration 和 FIRRTL/CIRCT 生成。构建输出仍有 NutShell 原有的 4 条动态索引 warning，但没有 Cache 重构引入的编译错误。

本目录之外的 `workspace/nutshell_cache` 仍保留学习任务使用的独立 Cache DUT 和 7 项 Toffee/RTL 覆盖率报告；它可以继续通过 `make report` 复现验证结果。
