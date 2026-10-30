"""Test Flow Control MESI subsystem tests."""

from .support import *


@case
async def test_python_masked_stores_to_modified_line(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    address = 0x0020_0100
    model.seed_word(address, memory.word(address, (address >> 3) & 7))

    # The first partial store allocates the line with GetM; the second exercises
    # the silent M-hit store path and checks that untouched bytes are preserved.
    for value, mask in ((0xA5869770CC27FDBA, 0x3F),
                        (0xCD388E7C56F288BF, 0x40)):
        await cpu.access(0, address, write=True, data=value, mask=mask)
        model.observe(0, address, write=True, write_data=value,
                      write_mask=mask)
    independent_address = address + 0x40
    model.seed_word(independent_address,
                    memory.word(independent_address, (independent_address >> 3) & 7))
    snoop_cursor = len(memory.snoop_data.transfers)
    snoop_req_cursor = len(memory.snoop_data.snoops)
    result0, result1 = await cpu.access_pair(
        CpuRequest(independent_address), CpuRequest(address)
    )
    model.observe(0, independent_address, response_data=result0)
    memory.snoop_data.assert_directory_matches(model, independent_address)
    model.observe(1, address, response_data=result1)
    assert result1 == model.word(address)
    line = address & ~0x3F
    expected_line = [model.data.get(line + 8 * beat, memory.word(line, beat))
                     for beat in range(8)]
    assert any(item["line"] == line and item["core"] == 0 and item["opcode"] == 0
               for item in memory.snoop_data.snoops[snoop_req_cursor:])
    memory.snoop_data.assert_line_data(address, expected_line, since=snoop_cursor)
    memory.snoop_data.assert_directory_matches(model, address)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("byte_mask_m_hit")
    _record_model(model)

@case
async def test_python_memory_and_cpu_backpressure(coherent_env):
    dut, memory, perf = await coherent_env(
        response_delay=3,
        response_gap_periods={"read_data": 5},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()

    # Stall a CPU response after it becomes valid and verify the held payload.
    address = 0x0012_3450
    model.seed_word(address, memory.word(address, (address >> 3) & 7))
    memory.arm_stall("read_req", 2)
    result = await cpu.access(0, address, response_stall_cycles=4)
    model.observe(0, address, response_data=result)
    assert cpu.response_stall_cycles[0] >= 4

    # Dirty eight lines in one L2 set, then force a live inclusive victim.
    # Periodic ready deassertion stalls the line request and write-data paths.
    dirty_base = 0x0080_6000
    for index in range(8):
        line = dirty_base + index * 32768
        value = 0xBACC000000000000 | index
        core = 0 if index < 4 or index == 8 else 1
        model.seed_word(line, memory.word(line, 0))
        await cpu.access(core, line, write=True, data=value)
        model.observe(core, line, write=True, write_data=value,
                      write_mask=0xFF)

    # Arm two-cycle stalls before the ninth line causes the live dirty victim
    # write request and eight-beat write data stream.
    memory.arm_stall("write_req", 2)
    memory.arm_stall("write_data", 2)
    line = dirty_base + 8 * 32768
    value = 0xBACC000000000008
    model.seed_word(line, memory.word(line, 0))
    await cpu.access(0, line, write=True, data=value)
    model.observe(0, line, write=True, write_data=value, write_mask=0xFF)

    assert memory.stalls["read_req"] > 0
    assert memory.stalls["write_req"] > 0
    assert memory.stalls["write_data"] > 0
    assert memory.response_gaps["read_data"] > 0
    assert memory.write_beats >= 8
    assert len(memory.write_responses) == len(memory.write_requests)
    assert int(dut.protocol_error.value) == 0

    PYTHON_COVERAGE.sample_external("cpu_response_backpressure",
                                    cpu.response_stall_cycles[0])
    PYTHON_COVERAGE.sample_external("memory_read_request_backpressure",
                                    memory.stalls["read_req"])
    PYTHON_COVERAGE.sample_external("memory_write_request_backpressure",
                                    memory.stalls["write_req"])
    PYTHON_COVERAGE.sample_external("memory_write_data_backpressure",
                                    memory.stalls["write_data"])
    PYTHON_COVERAGE.sample_external("memory_read_response_gaps",
                                    memory.response_gaps["read_data"])
    _record_model(model)

@case
async def test_python_reset_cancels_active_refill(coherent_env):
    dut, memory, _ = await coherent_env(response_delay=80)
    cpu = DualCoreCpuDriver(dut)
    address = 0x0018_9020
    prior_requests = len(memory.read_requests)

    # Submit a cold miss and wait for the memory agent to accept its line read.
    dut.cpu_req_addr.value = address
    dut.cpu_req_write.value = 0
    dut.cpu_req_wmask.value = 0xFF
    dut.cpu_req_wdata.value = 0
    dut.cpu_resp_ready.value = 0
    dut.cpu_req_valid.value = 1
    accepted = False
    for _ in range(40):
        await ClockCycles(dut, 1)
        if int(dut.cpu_req_ready.value) & 1:
            accepted = True
            break
    dut.cpu_req_valid.value = 0
    assert accepted, "cold miss was not accepted before reset"
    for _ in range(40):
        if len(memory.read_requests) > prior_requests:
            break
        await ClockCycles(dut, 1)
    assert len(memory.read_requests) > prior_requests, "refill did not reach memory"

    dut.reset.value = 1
    await ClockCycles(dut, 3)
    dut.reset.value = 0
    assert memory.reset_cancelled["reads"] > 0
    await ClockCycles(dut, 140)
    for _ in range(5):
        await ClockCycles(dut, 1)
        assert int(dut.cpu_resp_valid.value) == 0, "reset leaked a stale CPU response"

    # The reset canceled the cache transaction, not backing-memory contents or
    # the ability to issue the same line again.
    model = CoherenceScoreboard()
    model.seed_word(address, memory.word(address, (address >> 3) & 7))
    result = await cpu.access(0, address)
    model.observe(0, address, response_data=result)
    assert result == memory.word(address, (address >> 3) & 7)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("reset_during_refill")
    _record_model(model)

@pytest.mark.parametrize("seed", [0x7319, 0xD1A6, 0xA11CE, 0xBADC0DE])
@case
async def test_owner_transfer_and_cold_grant_under_backpressure(coherent_env, seed):
    """Check transfer/grant data correctness under memory backpressure."""
    ready_period = 3 + seed % 5
    response_gap = 4 + seed % 4
    dut, memory, perf = await coherent_env(
        response_delay=seed % 5 + 1,
        backpressure_periods={"read_req": ready_period},
        response_gap_periods={"read_data": response_gap},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    owner_addr = 0x0240_0000 + (seed & 0xFF) * 0x1000
    model.seed_word(owner_addr,
                    memory.word(owner_addr, (owner_addr >> 3) & 7))
    # Guarantee each parameterized replay sees a request-channel stall even
    # when its deterministic modulo phase would otherwise miss all valid cycles.
    memory.arm_stall("read_req", cycles=1)

    # Move ownership from Core1 to Core0 so the next Core1 read must retrieve
    # the latest line through SnoopRead while another line requests an L2 grant.
    value1 = 0xC010_0000_0000_0000 | seed
    await cpu.access(1, owner_addr, write=True, data=value1)
    model.observe(1, owner_addr, write=True, write_data=value1)
    value0 = 0xFACE_0000_0000_0000 | seed
    mask0 = 0x55
    await cpu.access(0, owner_addr, write=True, data=value0, mask=mask0)
    model.observe(0, owner_addr, write=True, write_data=value0,
                  write_mask=mask0)
    assert model.states[owner_addr & ~0x3F] == ["M", "I"]
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    for pair_index in range(6):
        grant_addr = 0x0300_0000 + (seed & 0xFF) * 0x10000 + pair_index * 64
        model.seed_word(grant_addr,
                        memory.word(grant_addr, (grant_addr >> 3) & 7))
        snoop_cursor = len(memory.snoop_data.transfers)
        snoop_req_cursor = len(memory.snoop_data.snoops)
        read_cursor = len(memory.read_requests)
        grant_result, owner_result = await cpu.access_pair(
            CpuRequest(grant_addr), CpuRequest(owner_addr),
            response_stall_cycles=1 + seed % 3,
        )
        assert grant_result == memory.word(grant_addr, (grant_addr >> 3) & 7)
        model.observe(0, grant_addr, response_data=grant_result)
        assert owner_result == model.word(owner_addr)
        model.observe(1, owner_addr, response_data=owner_result)
        assert len(memory.read_requests) == read_cursor + 1, (
            "the cold grant must read backing memory once; owner transfer must "
            "come from L1 without a second memory read"
        )
        owner_snoops = [item for item in
                        memory.snoop_data.snoops[snoop_req_cursor:]
                        if item["line"] == (owner_addr & ~0x3F) and
                        item["core"] == 0]
        assert owner_snoops and owner_snoops[-1]["opcode"] == 0, (
            f"seed={seed:#x}: expected Core0 SnoopRead, got {owner_snoops}; "
            f"all snoops={memory.snoop_data.snoops[snoop_req_cursor:]}; "
            f"transfers={memory.snoop_data.transfers[snoop_cursor:]}"
        )
        expected_line = [
            model.data.get((owner_addr & ~0x3F) + beat * 8,
                           memory.word((owner_addr & ~0x3F) + beat * 8, beat))
            for beat in range(8)
        ]
        memory.snoop_data.assert_line_data(owner_addr, expected_line,
                                           since=snoop_cursor)
        memory.snoop_data.assert_directory_matches(model, owner_addr)
        memory.snoop_data.assert_directory_matches(model, grant_addr)
        if pair_index < 5:
            # Restore M ownership so each replay exercises a fresh owner
            # transfer instead of an L1 S-state read hit on later iterations.
            update = 0xBEEF_0000_0000_0000 | (seed << 4) | pair_index
            await cpu.access(0, owner_addr, write=True, data=update, mask=0xAA)
            model.observe(0, owner_addr, write=True, write_data=update,
                          write_mask=0xAA)
            memory.snoop_data.assert_directory_matches(model, owner_addr)

    assert memory.stalls["read_req"] > 0
    assert int(dut.protocol_error.value) == 0
    _record_model(model)
