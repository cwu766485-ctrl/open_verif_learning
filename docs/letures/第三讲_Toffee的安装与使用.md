# 第三讲：Toffee 的安装与使用

> 目标：在 Picker 生成的 DUT 之上，用 Toffee 将“逐根信号驱动”组织成可复用的 Bundle、Agent、Env、参考模型、pytest 用例与功能覆盖率。

## 1. Toffee 与 Picker 的关系

Picker 解决“**Python 怎样访问 Verilog DUT**”；Toffee 解决“**一个可维护的 Python 验证平台该怎样组织**”。两者不是竞争关系。

```text
RTL → Picker/Verilator → DUTSyncFIFO（端口级接口）
                              ↑
                 Toffee Bundle（接口级）
                              ↑
                 Toffee Agent（事务级）
                              ↑
              Env + Reference Model（系统级）
                              ↑
                     pytest 测试用例
```

## 2. 当前安装状态

本项目的 `.tooling/venv` 已安装并验证：

- `pytoffee==0.2.3`
- `toffee-test==0.2.0`
- `pytest`

在新的 WSL 终端先启用环境：

```bash
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh
python -c 'import toffee, toffee_test; print("Toffee ready")'
```

不要无目的升级 `toffee-test`：教程和当前 Toffee 版本是配套使用的，新版本可能调整异步调度、监测接口等 API。

## 3. 为什么要使用 Toffee

课二里的端口级测试可读但会迅速膨胀：每个用例都要反复设置 `we_i/re_i/data_i`、等待时钟、检查状态。Toffee 的抽象边界是：

- **Bundle**：一组物理信号的轻量封装，例如 FIFO 的写端口、读端口、内部状态。
- **Agent**：对一类接口的事务封装，例如 `await fifo.enqueue(data)`、`await fifo.dequeue()`。
- **Env**：把 Agent、参考模型、覆盖率组织在一起；测试不应知道具体端口。
- **Reference Model**：独立的 Python FIFO，定义期望行为并与 Agent 交互结果比对。
- **pytest / toffee-test**：发现、运行、隔离测试资源，自动处理 DUT 的波形与覆盖率文件。

高层测试最终应接近业务语义：

```python
await fifo.reset()
await fifo.enqueue(0x114)
assert await fifo.dequeue() == 0x114
```

而不是每个用例都重复引脚电平序列。

## 4. 第三课练习路线

课程不是一次写完整个平台，而是由低到高五步：

1. **toffee-test 管理测试**：`pyproject.toml` 配置 pytest 的 `pythonpath`，将课二 smoke test 放进 `tests/test_smoke.py`，用 `@toffee_test.testcase` 运行。
2. **Bundle**：实现 `WriteBundle`、`ReadBundle`、`InternalBundle`；在 Bundle 层理解每根端口。
3. **Agent**：实现异步 `reset/enqueue/dequeue`。`@driver_method` 表示主动发起的事务；监测方法用于被动采样输出。
4. **功能覆盖率**：将 FIFO 规格拆为基本操作、空满边界、指针回绕、数据完整性、复位；每项建立覆盖点和 bins，再由测试补足未覆盖场景。
5. **参考模型与 Env**：用 Python 队列实现独立 FIFO 行为，将 Agent 和模型连接；目标不是“测试自己写的模型”，而是在独立的两种实现之间发现不一致。

## 5. 异步的真实含义

Toffee 使用 Python 协程，不是多线程。后台时钟持续推进 DUT；不同协程可以 `await` 同一个时钟事件，因此读、写、monitor、scoreboard 能并发且保持可重复的时序。

常见等待方式包括：

- `await ClockCycles(dut, n)`：等待 n 个周期；
- `await RisingEdge(pin)` / `FallingEdge(pin)`：等待边沿；
- `await Value(pin, value)` / `Condition(...)`：等待条件满足；
- `toffee.gather(...)` 或 `Executor`：并发启动多个驱动事务。

异步函数若没有 `await`，仍会阻塞其他任务；如果两个任务同周期写同一根信号，必须先定义清楚仲裁/优先级。这是同步硬件验证中最容易被忽略的规则。

## 6. pytest 与 toffee-test

`pytest` 发现 `tests/test_*.py` 中 `test_*` 函数；`toffee-test` 在其上增加 Toffee 的异步测试和资源管理。

本项目固定使用 `toffee-test==0.2.0`。该版本的最小异步测试写法是：

```python
from toffee_test.testcase import case

@case
async def test_toffee_is_running():
    assert True
```

注意不要写成 `@toffee_test.testcase`：在 0.2.0 中 `testcase` 是模块名，不是装饰器函数。部分较新的在线文档使用 `@toffee_test.testcase`，不能直接混用。

测试平台应使用 fixture 创建 DUT/Env。fixture 的意义是：每个 case 拿到全新资源；无论成功、失败还是抛异常，都能收尾并保留该 case 的波形、覆盖率。运行报告：

```bash
pytest -sv --toffee-report
```

报告目录与文件名可用 `--report-dir`、`--report-name` 指定。测试名字、断言信息、随机 seed 都应能帮助你一眼复现失败。

## 7. Bundle、Agent 的职责边界

Bundle 不应包含“整个业务场景”，它代表一个接口及其局部、可复用的电平操作。Agent 才向上提供事务方法；测试组合多个 Agent 完成场景；Env 管理它们并对接模型/覆盖率。

对本 FIFO：`WriteBundle.enqueue(data)` 可以包含对 `we_i/data_i` 的单次端口动作；`FIFOAgent.enqueue(data)` 用 `@driver_method` 向模型和上层暴露这笔“入队事务”。这既保留 Bundle 的接口复用性，又让 Agent 有一致的事务调度与模型匹配入口。

## 8. 验证完成的定义

不是“pytest 全绿”就结束。至少要同时满足：关键场景通过；参考模型逐事务/逐周期比对；功能覆盖率表明空/满/回绕/非法读写/复位等目标均被触发；代码覆盖率用于发现 RTL 未执行区域；每个失败都可由 seed、日志、波形复现。

## 一句话复盘

**Picker 把硬件变成可调用对象；Toffee 把调用对象的 Python 脚本变成可复用、可并发、可度量的验证平台。**
