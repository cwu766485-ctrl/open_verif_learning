"""MMIO role agent; protocol is a SimpleBus slave, model is separate."""
from .memory_agent import MemoryAgent

class MmioAgent(MemoryAgent):
    def __init__(self, bundle):
        super().__init__(bundle)
        self.monitor.channel = "mmio"
