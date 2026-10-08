"""Small configuration object shared by the testbench and role agents."""
from dataclasses import dataclass

@dataclass
class CacheConfig:
    line_bytes: int = 64
    words_per_line: int = 8
    ways: int = 4
    sets: int = 128
