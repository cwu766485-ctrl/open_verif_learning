"""任务 2 的 Toffee Env：把 Agent、参考模型和覆盖率连接起来。"""

import toffee

from agent import FIFOAgent
from ref import FIFOReferenceModel


class SyncFIFOEnv(toffee.Env):
    def __init__(self, control, write, read, internal, coverage):
        super().__init__()
        self.fifo = FIFOAgent(control, write, read, internal, coverage)
        self.coverage = coverage
        self.reference_model = FIFOReferenceModel()
        self.attach(self.reference_model)
