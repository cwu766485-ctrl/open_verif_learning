"""Slow full-capacity data-pattern walk for the L1 DCache array."""

import pytest

from toffee_test import case
from base_test import *


@pytest.mark.slow
@case
async def test_full_cache_array_data_patterns(start_func):
    """Sweep every 64-bit word with stuck-at and alternating-bit patterns.

    The 32 KiB address span is aligned to the cache capacity. It contains four
    lines for each of the 128 sets, so the test fills all four ways without
    creating an eviction. Each pattern is written across the full array and
    read back before the next pattern overwrites it.
    """
    env = await start_func()

    cache_bytes = 128 * 4 * 64
    word_bytes = 8
    word_count = cache_bytes // word_bytes
    base = 0x01000000  # Cacheable and aligned to the 32 KiB cache capacity.
    patterns = (
        ("all_zero", 0x0000000000000000),
        ("all_one", 0xFFFFFFFFFFFFFFFF),
        ("alternating_10", 0xAAAAAAAAAAAAAAAA),
        ("alternating_01", 0x5555555555555555),
        # Unlike the uniform passes, this catches word/line address aliasing.
        ("address_signature", None),
    )

    def expected_word(pattern, addr):
        if pattern is not None:
            return pattern
        return ((addr & 0xFFFFFFFF) << 32) | (~addr & 0xFFFFFFFF)

    writes_before = len(env.mem_ram.write_requests)

    for pattern_name, pattern in patterns:
        for word_index in range(word_count):
            addr = base + word_index * word_bytes
            data = expected_word(pattern, addr)
            response = await env.cpu.block_write(addr, data, 0xFF)
            assert response["bits_cmd"] == CMD_WRITERSP, (
                f"{pattern_name}: bad write response at 0x{addr:08x}"
            )

        for word_index in range(word_count):
            addr = base + word_index * word_bytes
            response = await env.cpu.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST, (
                f"{pattern_name}: bad read response at 0x{addr:08x}"
            )
            expected = expected_word(pattern, addr)
            assert response["bits_rdata"] == expected, (
                f"{pattern_name}: expected 0x{expected:016x} at "
                f"0x{addr:08x}, got 0x{response['bits_rdata']:016x}"
            )

    assert len(env.mem_ram.write_requests) == writes_before, (
        "the four-line-per-set sweep should fit without dirty eviction"
    )
