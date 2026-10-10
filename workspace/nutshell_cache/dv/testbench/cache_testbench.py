"""Reusable verification composition root for the cache SimpleBus DUT."""

from toffee import ClockCycles

from dv.env.cache_env import CacheEnv
from dv.scoreboard.cache_scoreboard import CacheScoreboard
from dv.checkers.cache_protocol_checker import CacheProtocolChecker
from dv.checkers.dut_properties import CacheDutProperties


class CacheTestbench:
    def __init__(self, dut):
        self.env = CacheEnv(dut)
        self.env.dut = dut
        self.env.testbench = self
        self.scoreboard = CacheScoreboard()
        self.checker = CacheProtocolChecker("cpu")
        self.coherence_checker = CacheProtocolChecker("coherence")
        self.properties = CacheDutProperties(
            tag_model=self.scoreboard.reference.cache_tags
        )
        self.coverage = self.env.coverage
        self.scoreboard.coverage = self.coverage

        self.env.cpu.protocol_checker.name = "cpu"
        self.env.memory.protocol_checker.name = "memory"
        self.env.mmio.protocol_checker.name = "mmio"
        self.env.coherence.protocol_checker.name = "coherence"

        self.env.cpu.monitor.subscribe(self.scoreboard)
        self.env.cpu.monitor.subscribe(self.properties)
        self.env.memory.monitor.subscribe(self.scoreboard)
        self.env.coherence.monitor.subscribe(self.scoreboard)
        self.env.cpu.monitor.subscribe(self.coverage)
        self.env.cpu.monitor.subscribe(self.checker)
        self.env.coherence.monitor.subscribe(self.coverage)
        self.env.coherence.monitor.subscribe(self.coherence_checker)
        self.env.memory.monitor.subscribe(self.coverage)
        self.env.mmio.monitor.subscribe(self.coverage)

    def on_reset(self):
        """Discard canceled protocol work and permit reset to break a stall."""
        self.properties.on_reset()
        self.scoreboard.on_reset()
        self.checker.on_reset()
        self.coherence_checker.on_reset()
        self.coverage.on_reset()
        for agent in (self.env.cpu, self.env.coherence, self.env.memory, self.env.mmio):
            agent.protocol_checker.reset()

    def finalize(self):
        self.properties.assert_drained()
        self.scoreboard.assert_no_errors()
        self.checker.assert_clean()
        self.coherence_checker.assert_clean()
        if self.properties.forward_data_cycles:
            self.coverage.sample(data_forwarding="same_word")
        self.coverage.assert_clean()
        stall_counts = {}
        for name, agent in (
            ("cpu", self.env.cpu), ("coherence", self.env.coherence),
            ("memory", self.env.memory), ("mmio", self.env.mmio),
        ):
            agent.protocol_checker.assert_no_errors()
            for channel, cycles in agent.protocol_checker.stall_cycles_by_channel.items():
                stall_counts[f"{name}.{channel}"] = cycles
        self.coverage.add_protocol_stalls(stall_counts)

    async def reset(self, pulse_cycles=2, recovery_cycles=128):
        """Pulse DUT reset and wait for the metadata array's sweep to finish."""
        self.on_reset()
        dut = self.env.dut
        dut.reset.AsImmWrite(); dut.reset.value = 1; dut.reset.AsRiseWrite()
        await ClockCycles(dut, pulse_cycles)
        dut.reset.value = 0
        if recovery_cycles:
            await ClockCycles(dut, recovery_cycles)
