# 学习任务 2：Toffee 部分 - 完成说明

本目录是对课程 2 生成的 `DUTSyncFIFO` 的完整 Toffee 验证实现。运行 `make test` 即可复现。

## 任务书交付对应

| 任务步骤 | 实现位置 | 已验证内容 |
| --- | --- | --- |
| 1. pytest + toffee-test | `pyproject.toml`、`tests/conftest.py`、`tests/test_smoke.py` | Fixture 创建 DUT、启动时钟、复位 |
| 2. Bundle | `bundle/__init__.py`、`tests/test_bundle.py` | 读/写/内部端口归类，`enqueue`、`dequeue`，满空及数据顺序 |
| 3. Agent + Executor | `agent/__init__.py`、`tests/test_agent_coverage.py` | 事务 API、复位、并发读写调度组 |
| 4. 功能覆盖率 | `coverage/__init__.py` | 基本、非法边界、满空、指针回绕、数据一致性、复位 |
| 5. Env + 参考模型 | `env/__init__.py`、`ref/__init__.py` | 16 深度队列模型与 Agent 自动返回值比对 |

## Bundle 与 Agent 的边界

- **Bundle** 类似一个很轻量的 Python `interface`：把相关端口命名、绑定、提供单笔底层操作。它不应知道完整测试场景或参考模型。
- **Agent** 建立在 Bundle 上，提供“复位、写一个事务、读一个事务、并发读写”等可读的业务语义；它是测试、参考模型和覆盖率连接的稳定入口。
- **Env** 管理一个验证环境，负责把名为 `fifo` 的 Agent 与参考模型连接；**Model** 用 Python `deque` 保存期望队列，对每一次 Agent 的写/读返回值做自动比对。

思考题 1：enqueue/dequeue 放 Bundle 还是 Agent？
```
Bundle：完整的端口级基本动作
Agent ：调用 Bundle，组成“验证事务”
Test  ：调用 Agent，表达验证场景
```
例如：
```
# Bundle：知道哪些端口构成一次写操作
await write.enqueue(data)

# Agent：知道“这是 FIFO 的入队事务”
await fifo.enqueue(data)

# Test：知道“我要写满 FIFO，再读空 FIFO”
await fifo.enqueue(...)
```
## 覆盖率策略

`FIFOFunctionalCoverage` 是手动采样，原因是覆盖点的语义来自“一个事务是否被接受”，而不是任意一个时钟瞬间。测试覆盖：复位、空闲、正常读写、空读、满写、满/空状态、读写指针回绕、并发读写和数据顺序。

运行：

```bash
cd /mnt/e/workspace/chip/open_verif/labs/course3_toffee_fifo
make test
make report
```

`make clean` 删除本课程根目录的波形（`*.fst`）、Verilator 覆盖率数据、pytest/ Python 缓存和 `reports/`；不会删除课程 2 的 Picker 生成 DUT。

## 本次验收结果

在 Ubuntu WSL 中执行 `make test`：**4 passed**。随后执行 `make report`：功能覆盖率为 **2/2 组、2/2 点、13/13 bin，即 100%**。报告入口为 `reports/course3`；其中 RTL 行覆盖率为 83.78%，它和本任务要求的功能覆盖率是两种不同指标，后续可用更多针对 RTL 分支的场景继续提升。
