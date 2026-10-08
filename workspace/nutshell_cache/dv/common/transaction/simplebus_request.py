"""Protocol-level request transaction (UVM sequence-item equivalent)."""
from dataclasses import dataclass

@dataclass
class SimpleBusRequest:
    addr: int
    size: int = 3
    cmd: int = 0
    wmask: int = 0
    wdata: int = 0
    user: int = 0

    # Compatibility names used by the original Toffee environment.
    @property
    def mask(self):
        return self.wmask

    @property
    def data(self):
        return self.wdata

    def as_legacy(self):
        from utils.common import ReqMsg
        return ReqMsg(self.addr, self.cmd, self.size, self.wmask, self.wdata)
