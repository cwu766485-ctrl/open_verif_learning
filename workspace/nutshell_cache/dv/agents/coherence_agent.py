"""Coherence role agent; master transport with probe-specific sequences."""
from .cpu_agent import CpuAgent

class CoherenceAgent(CpuAgent):
    def __init__(self, bundle):
        super().__init__(bundle)
        self.monitor.channel = "coherence"
