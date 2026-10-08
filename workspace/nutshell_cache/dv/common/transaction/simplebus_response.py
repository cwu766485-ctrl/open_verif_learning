"""Protocol-level response transaction."""
from dataclasses import dataclass

@dataclass
class SimpleBusResponse:
    cmd: int
    rdata: int = 0
    user: int = 0

    def as_dict(self):
        result = {"valid": True, "bits_cmd": self.cmd, "bits_rdata": self.rdata}
        if self.user:
            result["bits_user"] = self.user
        return result
