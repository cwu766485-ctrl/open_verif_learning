"""Coherence probe transaction; kept separate from CPU load/store intent."""
from dataclasses import dataclass

@dataclass
class CoherenceProbe:
    addr: int
    size: int = 7
