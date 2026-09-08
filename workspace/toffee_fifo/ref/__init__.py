"""同步 FIFO 的队列级参考模型。"""

from collections import deque

import toffee


class FIFOReferenceModel(toffee.Model):
    """只描述可观察行为：容量 16、先进先出、满/空时拒绝访问。"""

    def __init__(self):
        super().__init__()
        self._queue = deque()

    @toffee.driver_hook("fifo.reset")
    def reset(self):
        self._queue.clear()

    @toffee.driver_hook("fifo.enqueue")
    def enqueue(self, data: int) -> bool:
        if len(self._queue) == 16:
            return False
        self._queue.append(data & 0xFFFFFFFF)
        return True

    @toffee.driver_hook("fifo.dequeue")
    def dequeue(self) -> int | None:
        return self._queue.popleft() if self._queue else None
