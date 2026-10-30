"""Reusable transaction sequences for Python/Toffee coherence tests."""

from dataclasses import dataclass

from dv.agents.coherent_cpu_agent import CpuRequest


@dataclass(frozen=True)
class CpuAccess:
    """One architectural CPU request used by a directed sequence."""

    core: int
    addr: int
    write: bool = False
    data: int = 0
    mask: int = 0xFF


class DualCoreSequence:
    """Submit one or two requests through the single packed-port driver."""

    def __init__(self, cpu_driver):
        self.cpu = cpu_driver

    async def run_pair(self, *accesses: CpuAccess, max_cycles=1000,
                       request_delay_cycles=None, response_stall_cycles=0):
        if not 1 <= len(accesses) <= 2:
            raise ValueError("a dual-core sequence needs one or two CPU accesses")
        by_core = {}
        for access in accesses:
            if access.core not in (0, 1) or access.core in by_core:
                raise ValueError("sequence requires at most one request per core")
            by_core[access.core] = CpuRequest(
                access.addr, access.write, access.data, access.mask
            )
        return await self.cpu.access_pair(
            by_core.get(0), by_core.get(1), max_cycles=max_cycles,
            request_delay_cycles=request_delay_cycles,
            response_stall_cycles=response_stall_cycles,
        )


class ProbeSequence:
    def __init__(self, coherence_agent, addr):
        self.coherence_agent, self.addr = coherence_agent, addr

    async def run(self):
        return await self.coherence_agent.probe(self.addr)
