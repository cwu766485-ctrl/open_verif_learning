"""Shared Python/Toffee environment for the dual-L1 MESI subsystem."""

from dv.agents.coherent_cpu_agent import DualCoreCpuDriver
from dv.coverage.coherence_coverage import CoherenceCoverage
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard
from dv.sequences.coherence_sequences import DualCoreSequence


class CoherenceEnv:
    """Own the subsystem's shared CPU driver, monitors, and model factory.

    The tuple iterator keeps the original ``dut, memory, perf = await
    coherent_env()`` test idiom working while new tests can use named roles.
    The scoreboard factory deliberately returns a fresh independent model for
    each test/scenario.
    """

    def __init__(self, dut, memory, perf, snoop_data, coverage=None):
        self.dut = dut
        self.memory = memory
        self.perf = perf
        self.snoop_data = snoop_data
        self.cpu = DualCoreCpuDriver(dut)
        self.sequence = DualCoreSequence(self.cpu)
        self.coverage = coverage if coverage is not None else CoherenceCoverage()

    def __iter__(self):
        yield self.dut
        yield self.memory
        yield self.perf

    @staticmethod
    def new_scoreboard():
        return CoherenceScoreboard()
