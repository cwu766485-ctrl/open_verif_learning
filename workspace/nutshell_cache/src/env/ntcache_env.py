from ref.ref_cache import *
from coverage import CacheCoverage

class NtCacheEnv(Env):
    def __init__(self, dut):
        super().__init__()
        self.in_agent   = SimpleBusMasterAgent(SimpleBusBundle.from_prefix("io_in_").set_name("in").bind(dut))
        self.mem_agent  = SimpleBusSlaveAgent(SimpleBusBundle.from_prefix("io_out_mem_").set_name("mem").bind(dut))
        self.mmio_agent = SimpleBusSlaveAgent(SimpleBusBundle.from_prefix("io_mmio_").set_name("mmio").bind(dut))
        self.coh_agent  = SimpleBusMasterAgent(SimpleBusBundle.from_prefix("io_out_coh_").set_name("coh").bind(dut))
        # Functional coverage is independent from Verilator RTL line coverage.
        # Agents/monitors may sample this object without coupling to pytest.
        self.coverage = CacheCoverage()
        self.attach(CacheRefModel())
