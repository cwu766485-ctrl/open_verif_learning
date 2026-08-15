"""同步 FIFO 的 Toffee Bundle。

Bundle 只负责把一组端口整理成一个可复用的操作接口；它不知道参考模型，
也不决定测试场景。这正是它与 Agent 的边界。
"""

import toffee


class ControlBundle(toffee.Bundle):
    """时钟域控制端口。"""

    rst_n = toffee.Signal()

    async def reset(self, cycles: int = 5) -> None:
        """执行同步、低有效复位，并留两个周期让输出稳定。"""
        self.rst_n.value = 0
        await self.step(cycles)
        self.rst_n.value = 1
        await self.step(2)


class WriteBundle(toffee.Bundle):
    """FIFO 写通道：写使能、写数据，以及写侧背压 ``full_o``。"""

    we_i = toffee.Signal()
    data_i = toffee.Signal()
    full_o = toffee.Signal()

    async def enqueue(self, data: int) -> bool:
        """尝试写入一个字，返回这次写入是否被 FIFO 接收。"""
        accepted = not bool(self.full_o.value)
        self.data_i.value = data
        self.we_i.value = 1
        await self.step()
        self.we_i.value = 0
        return accepted


class ReadBundle(toffee.Bundle):
    """FIFO 读通道：读使能、读数据，以及读侧背压 ``empty_o``。"""

    re_i = toffee.Signal()
    data_o = toffee.Signal()
    empty_o = toffee.Signal()

    async def dequeue(self) -> int | None:
        """尝试读一个字；空 FIFO 的非法读返回 ``None``。"""
        accepted = not bool(self.empty_o.value)
        self.re_i.value = 1
        await self.step()
        self.re_i.value = 0
        return int(self.data_o.value) if accepted else None


class InternalBundle(toffee.Bundle):
    """任务书允许观察的内部状态；用于断言和功能覆盖率。"""

    SyncFIFO_wptr = toffee.Signal()
    SyncFIFO_rptr = toffee.Signal()
    SyncFIFO_counter = toffee.Signal()
