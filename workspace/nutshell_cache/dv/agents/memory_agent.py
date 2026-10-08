"""Backing-memory role Agent: a real Toffee SimpleBus slave driver."""
from .simplebus.slave_driver import SlaveDriver
from .simplebus.monitor import SimpleBusMonitor

class MemoryAgent(SlaveDriver):
    def __init__(self, bundle):
        self.monitor = SimpleBusMonitor("memory")
        super().__init__(bundle, monitor=self.monitor)
