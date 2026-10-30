"""Test Victims MESI subsystem tests."""

from .support import *


@case
async def test_python_parallel_misses_l2_hit_and_dirty_writeback(coherent_env):
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()

    # One packed driver accepts two independent cold misses in the same window.
    parallel = await cpu.access_pair(
        CpuRequest(0x0020_4100), CpuRequest(0x0020_8100)
    )
    PYTHON_COVERAGE.sample_external("parallel_cold_miss_pair")
    for core, addr, result in ((0, 0x0020_4100, parallel[0]),
                               (1, 0x0020_8100, parallel[1])):
        expected = memory.word(addr, (addr >> 3) & 7)
        model.seed_word(addr, expected)
        model.observe(core, addr, response_data=result)
        assert result == expected
    assert len(memory.read_requests) == 2

    # Core1 reads Core0's E line, then Core0 upgrades S->M with a byte mask.
    addr = 0x0020_4100
    response = await cpu.access(1, addr)
    model.observe(1, addr, response_data=response)
    old_word = model.word(addr)
    update = 0x1122334455667788
    mask = 0b01010101
    await cpu.access(0, addr, write=True, data=update, mask=mask)
    model.observe(0, addr, write=True, write_data=update, write_mask=mask)
    merged = model.word(addr)
    response = await cpu.access(1, addr)
    model.observe(1, addr, response_data=response)
    assert response == merged and response != old_word
    PYTHON_COVERAGE.sample_external("byte_mask_write")

    # Five addresses share L1 and L2 set indices. The L1 copy of the first
    # line is replaced while its inclusive L2 copy remains available.
    l2_before = perf.snapshot()
    reads_before = len(memory.read_requests)
    l2_addr = 0x0040_1000
    for way in range(5):
        address = l2_addr + way * 32768
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        result = await cpu.access(0, address)
        model.observe(0, address, response_data=result)
        assert result == expected
    assert model.l1_way_view(0, l2_addr) is None
    result = await cpu.access(0, l2_addr)
    model.observe(0, l2_addr, response_data=result)
    assert result == memory.word(l2_addr, (l2_addr >> 3) & 7)
    l2_after = perf.snapshot()
    assert len(memory.read_requests) == reads_before + 5
    assert l2_after["l2_refill_hit"] > l2_before["l2_refill_hit"]

    # Keep four M lines live in each L1 for one L2 set. The ninth line first
    # performs Core0's local PutM, then forces L2 to invalidate a still-live
    # Core1 owner, collect its data, and write the victim to memory.
    dirty_base = 0x0080_2000
    expected_values = {}
    for n in range(9):
        line_addr = dirty_base + n * 32768
        value = 0xCAFE000000000000 | n
        core = 0 if n < 4 or n == 8 else 1
        await cpu.access(core, line_addr, write=True, data=value)
        model.seed_word(line_addr, memory.word(line_addr, 0))
        model.observe(core, line_addr, write=True, write_data=value,
                      write_mask=0xFF)
        expected_values[line_addr] = value
    assert memory.write_requests, "dirty L2 replacement should issue a writeback"
    assert memory.write_beats >= 8
    assert int(dut.protocol_error.value) == 0

    first = memory.write_requests[0][0]
    assert first in expected_values
    assert not model.l2_contains(first)
    reads_before = len(memory.read_requests)
    result = await cpu.access(1, first)
    model.observe(1, first, response_data=result)
    assert result == expected_values[first]
    assert len(memory.read_requests) > reads_before
    assert len(memory.write_responses) == len(memory.write_requests)
    PYTHON_COVERAGE.sample_external("dirty_writeback", len(memory.write_requests))
    PYTHON_COVERAGE.sample_external("write_response", len(memory.write_responses))

    # Force a shared S victim from an 8-way L2 set. Both L1s retain the seventh
    # line as S while the ninth line allocates, so both copies must be invalidated.
    shared_base = 0x0100_0000
    shared_target = shared_base + 6 * 32768
    shared_lines = [shared_base + index * 32768 for index in range(9)]
    for index in range(6):
        core = 0 if index < 3 else 1
        address = shared_lines[index]
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        response = await cpu.access(core, address)
        assert response == expected
        model.observe(core, address, response_data=response)

    for core in (0, 1):
        expected = memory.word(shared_target, (shared_target >> 3) & 7)
        model.seed_word(shared_target, expected)
        response = await cpu.access(core, shared_target)
        assert response == expected
        model.observe(core, shared_target, response_data=response)
        memory.snoop_data.assert_directory_matches(model, shared_target)

    address = shared_lines[7]
    expected = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, expected)
    response = await cpu.access(0, address)
    assert response == expected
    model.observe(0, address, response_data=response)
    assert model.states[shared_target] == ["S", "S"]
    assert model.l1_way_view(0, shared_target) is not None
    assert model.l1_way_view(1, shared_target) is not None

    set_index = model._l2_set(shared_target)
    predicted_victim = model.l2_ways[set_index][model.l2_next_way[set_index] % 8]
    assert predicted_victim == shared_target
    shared_expected_words = [memory.word(shared_target, beat)
                             for beat in range(8)]
    snoop_cursor = len(memory.snoop_data.snoops)
    write_cursor = len(memory.write_requests)
    address = shared_lines[8]
    expected = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, expected)
    response = await cpu.access(0, address)
    assert response == expected
    model.observe(0, address, response_data=response)

    shared_victims = [item for item in model.l2_evictions
                      if item["line"] == shared_target and item["state"] == "S"]
    assert {item["core"] for item in shared_victims} == {0, 1}
    assert {item["core"] for item in memory.snoop_data.snoops[snoop_cursor:]
            if item["line"] == shared_target} == {0, 1}
    if any((write[0] & ~0x3F) == shared_target
           for write in memory.write_requests[write_cursor:]):
        # An E→S owner transfer may conservatively mark the L2 data dirty;
        # if it writes back, verify every beat rather than requiring no AW.
        assert tuple(memory._read_word(shared_target, beat)
                     for beat in range(8)) == tuple(shared_expected_words)
    assert not model.l2_contains(shared_target)
    memory.snoop_data.assert_directory_matches(model, shared_target)
    PYTHON_COVERAGE.sample_external("l2_shared_victim_back_invalidation")

    _record_model(model)
    assert PYTHON_COVERAGE.l2_live_evictions >= 1, "live inclusive L2 eviction was not modeled"
