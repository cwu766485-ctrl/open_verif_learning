from toffee import Env
from dv.protocol.simplebus.bundle import SimpleBusBundle
from dv.agents.cpu_agent import CpuAgent
from dv.agents.memory_agent import MemoryAgent
from dv.agents.mmio_agent import MmioAgent
from dv.agents.coherence_agent import CoherenceAgent
from dv.coverage import CacheCoverage

class CacheEnv(Env):
    def __init__(self, dut):
        super().__init__()
        self.cpu = CpuAgent(SimpleBusBundle.from_prefix("io_in_").set_name("in").bind(dut))
        self.memory = MemoryAgent(SimpleBusBundle.from_prefix("io_out_mem_").set_name("mem").bind(dut))
        self.mmio = MmioAgent(SimpleBusBundle.from_prefix("io_mmio_").set_name("mmio").bind(dut))
        self.coherence = CoherenceAgent(SimpleBusBundle.from_prefix("io_out_coh_").set_name("coh").bind(dut))
        self.in_agent = self.cpu; self.mem_agent = self.memory
        self.mmio_agent = self.mmio; self.coh_agent = self.coherence
        self.coverage = CacheCoverage()
