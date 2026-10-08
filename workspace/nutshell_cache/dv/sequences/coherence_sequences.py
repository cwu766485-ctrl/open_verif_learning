class ProbeSequence:
    def __init__(self, coherence_agent, addr):
        self.coherence_agent, self.addr = coherence_agent, addr

    async def run(self):
        return await self.coherence_agent.probe(self.addr)
