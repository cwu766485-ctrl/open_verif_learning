"""同步 FIFO 的功能覆盖率模型。"""

from dataclasses import dataclass

import toffee


@dataclass
class _OperationProbe:
    event: str = "init"


class FIFOFunctionalCoverage:
    """任务书要求的操作、边界、指针和数据完整性覆盖点。"""

    def __init__(self, internal):
        self._probe = _OperationProbe()
        self.operations = toffee.CovGroup("fifo_operations")
        self.operations.add_watch_point(
            self._probe,
            {
                "reset": lambda probe: probe.event == "reset",
                "idle": lambda probe: probe.event == "idle",
                "write_ok": lambda probe: probe.event == "write_ok",
                "read_ok": lambda probe: probe.event == "read_ok",
                "empty_read_blocked": lambda probe: probe.event == "empty_read_blocked",
                "full_write_blocked": lambda probe: probe.event == "full_write_blocked",
                "simultaneous_rw": lambda probe: probe.event == "simultaneous_rw",
                "write_wrap": lambda probe: probe.event == "write_wrap",
                "read_wrap": lambda probe: probe.event == "read_wrap",
                "data_match": lambda probe: probe.event == "data_match",
            },
            name="operation_and_boundary",
        )
        self.occupancy = toffee.CovGroup("fifo_occupancy")
        self.occupancy.add_watch_point(
            internal.SyncFIFO_counter,
            {
                # CovGroup 得到的是 Picker 的 XPin；实际采样值在 .value 中。
                "empty": lambda count: int(count.value) == 0,
                "middle": lambda count: 0 < int(count.value) < 16,
                "full": lambda count: int(count.value) == 16,
            },
            name="occupancy_state",
        )

    @property
    def groups(self):
        return [self.operations, self.occupancy]

    def record(self, event: str) -> None:
        """手工采样：每个高层操作结束后记录最有意义的状态。"""
        self._probe.event = event
        self.operations.sample()
        self.occupancy.sample()

    def is_complete(self) -> bool:
        return all(group.is_all_covered() for group in self.groups)
