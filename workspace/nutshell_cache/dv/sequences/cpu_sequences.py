"""Small reusable CPU scenario helpers."""
class ReadSequence:
    def __init__(self, cpu_agent, addr):
        self.cpu_agent, self.addr = cpu_agent, addr

    async def run(self):
        return await self.cpu_agent.block_read(self.addr)

class WriteSequence:
    def __init__(self, cpu_agent, addr, data, mask=0xFF):
        self.cpu_agent, self.addr, self.data, self.mask = cpu_agent, addr, data, mask

    async def run(self):
        return await self.cpu_agent.block_write(self.addr, self.data, self.mask)
