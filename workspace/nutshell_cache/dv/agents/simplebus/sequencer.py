"""Minimal async sequencer, analogous to a UVM sequencer."""
import asyncio

class SimpleBusSequencer:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def get(self):
        return await self.queue.get()
