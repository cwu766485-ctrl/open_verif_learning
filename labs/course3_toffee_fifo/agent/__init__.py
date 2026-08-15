"""把 FIFO 的 Bundle 组合为有业务语义的 Agent。"""

import toffee


class FIFOAgent(toffee.Agent):
    """对测试和参考模型提供 reset/enqueue/dequeue 等事务级 API。"""

    def __init__(self, control, write, read, internal, coverage):
        self.control = control
        self.write = write
        self.read = read
        self.internal = internal
        self.coverage = coverage
        super().__init__(control)

    @toffee.driver_method()
    async def reset(self) -> None:
        await self.control.reset()
        assert int(self.read.empty_o.value) == 1
        assert int(self.write.full_o.value) == 0
        assert int(self.internal.SyncFIFO_wptr.value) == 0
        assert int(self.internal.SyncFIFO_rptr.value) == 0
        assert int(self.internal.SyncFIFO_counter.value) == 0
        self.coverage.record("reset")

    @toffee.driver_method()
    async def enqueue(self, data: int) -> bool:
        old_wptr = int(self.internal.SyncFIFO_wptr.value)
        accepted = await self.write.enqueue(data)
        if accepted and old_wptr == 15:
            self.coverage.record("write_wrap")
        else:
            self.coverage.record("write_ok" if accepted else "full_write_blocked")
        return accepted

    @toffee.driver_method()
    async def dequeue(self) -> int | None:
        old_rptr = int(self.internal.SyncFIFO_rptr.value)
        data = await self.read.dequeue()
        if data is not None and old_rptr == 15:
            self.coverage.record("read_wrap")
        else:
            self.coverage.record("read_ok" if data is not None else "empty_read_blocked")
        return data

    async def idle(self) -> None:
        """产生一个无读写的周期，用于覆盖空闲操作。"""
        await self.control.step()
        self.coverage.record("idle")

    async def enqueue_dequeue(self, data: int):
        """用两个调度组并行发起一次写和一次读。"""
        async with toffee.Executor() as executor:
            executor(self.enqueue(data), sche_group="write")
            executor(self.dequeue(), sche_group="read")
        self.coverage.record("simultaneous_rw")
        return executor.get_results()
