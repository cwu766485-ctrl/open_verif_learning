"""CPU role Agent: a real Toffee MasterDriver plus monitor/sequencer hooks."""
from .simplebus.master_driver import MasterDriver
from .simplebus.monitor import SimpleBusMonitor

class CpuAgent(MasterDriver):
    def __init__(self, bundle):
        self.monitor = SimpleBusMonitor("cpu")
        super().__init__(bundle, monitor=self.monitor)
        self.sequencer = self
