"""Test Snoop Fill Concurrency MESI subsystem tests."""

from .support import *


@pytest.mark.parametrize("owner_core", [0, 1])
@case
async def test_clean_snoop_overlaps_l2_fill_stream(coherent_env, owner_core):
    """A clean invalidate on another set must not wait for the refill writer."""
    dut, memory, _ = await coherent_env(response_delay=2)
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    other_core = 1 - owner_core
    owner_addr = 0x0020_3000
    refill_addr = 0x0020_2000
    store_data = 0xC1EA_5EED_7654_3210
    model.seed_word(owner_addr, memory.word(owner_addr, (owner_addr >> 3) & 7))

    first = await cpu.access(owner_core, owner_addr)
    assert first == model.word(owner_addr)
    model.observe(0, owner_addr, response_data=first)
    second = await cpu.access(other_core, owner_addr)
    assert second == model.word(owner_addr)
    model.observe(1, owner_addr, response_data=second)
    memory.snoop_data.assert_directory_matches(model, owner_addr)

    d = dut
    d.cpu_resp_ready.value = 0
    snoop_start = len(memory.snoop_data.snoops)

    async def issue(core, address, *, write=False, data=0):
        bit = 1 << core
        d.cpu_req_valid.value = bit
        d.cpu_req_addr.value = (address & 0xFFFFFFFF) << (32 * core)
        d.cpu_req_write.value = bit if write else 0
        d.cpu_req_wmask.value = (0xFF << (8 * core)) if write else 0
        d.cpu_req_wdata.value = (data & ((1 << 64) - 1)) << (64 * core)
        for _ in range(200):
            await ClockCycles(d, 1)
            if int(d.cpu_req_ready.value) & bit:
                accepted_cycle = memory.snoop_data.cycle
                d.cpu_req_valid.value = 0
                return accepted_cycle
        d.cpu_req_valid.value = 0
        raise TimeoutError(f"core{core} request {address:#x} was not accepted")

    async def response(core, address, *, write=False, expected=None):
        bit = 1 << core
        d.cpu_resp_ready.value = bit
        for _ in range(300):
            await ClockCycles(d, 1)
            if int(d.cpu_resp_valid.value) & bit:
                got_addr = (int(d.cpu_resp_addr.value) >> (32 * core)) & 0xFFFFFFFF
                got_write = (int(d.cpu_resp_write.value) >> core) & 1
                got_data = (int(d.cpu_resp_rdata.value) >> (64 * core)) & ((1 << 64) - 1)
                assert got_addr == address
                assert got_write == int(write)
                if expected is not None:
                    assert got_data == expected
                d.cpu_resp_ready.value = 0
                await ClockCycles(d, 1)
                return got_data, memory.snoop_data.cycle
        d.cpu_resp_ready.value = 0
        raise TimeoutError(
            f"core{core} response {address:#x} timed out; "
            f"fill={int(d.monitor_l2_fill_active.value)} "
            f"protocol_error={int(d.protocol_error.value)} "
            f"reads={memory.read_requests} "
            f"snoops={memory.snoop_data.snoops[snoop_start:]} "
            f"l1_rsp={memory.snoop_data.snoop_response_cycles[-20:]} "
            f"dir_rsp={memory.snoop_data.directory_snoop_response_cycles[-20:]} "
            f"commits={memory.snoop_data.directory_commits[-8:]}"
        )

    refill_expected = memory.word(refill_addr, (refill_addr >> 3) & 7)
    model.seed_word(refill_addr, refill_expected)
    refill_accept_cycle = await issue(owner_core, refill_addr)
    for _ in range(300):
        if int(d.monitor_l2_fill_active.value):
            break
        await ClockCycles(d, 1)
    else:
        raise TimeoutError("memory refill never entered the shared L2 fill stream")
    fill_start_cycle = memory.snoop_data.cycle

    store_accept_cycle = await issue(other_core, owner_addr, write=True, data=store_data)
    _, store_response_cycle = await response(other_core, owner_addr, write=True)
    _, refill_response_cycle = await response(
        owner_core, refill_addr, expected=refill_expected
    )

    invalidations = [
        event for event in memory.snoop_data.snoops[snoop_start:]
        if event["line"] == (owner_addr & ~0x3F) and event["opcode"] == 1
    ]
    assert invalidations, "shared-line store did not issue a clean invalidation"
    overlapped = any(event["during_l2_fill"] for event in invalidations)

    model.observe(other_core, owner_addr, write=True, write_data=store_data,
                  write_mask=0xFF)
    model.observe(owner_core, refill_addr, response_data=refill_expected)
    updated = await cpu.access(owner_core, owner_addr)
    assert updated == store_data
    model.observe(owner_core, owner_addr, response_data=updated)
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    memory.snoop_data.assert_directory_matches(model, refill_addr)
    assert int(d.protocol_error.value) == 0

    row = {
        "workload": "clean_snoop_during_l2_fill",
        "owner_core": owner_core,
        "seed": 0xC1EA5EED,
        "fill_start_to_snoop_accept_cycles": invalidations[0]["cycle"] - fill_start_cycle,
        "store_request_to_snoop_accept_cycles": invalidations[0]["cycle"] - store_accept_cycle,
        "store_request_to_response_cycles": store_response_cycle - store_accept_cycle,
        "fill_snoop_overlap": overlapped,
        "refill_request_to_response_cycles": refill_response_cycle - refill_accept_cycle,
        "data_check": "PASS",
        "directory_check": "PASS",
    }
    print("P2_FILL_SNOOP," + json.dumps(row, sort_keys=True))
    PYTHON_COVERAGE.sample_external("clean_snoop_during_l2_fill")
    PYTHON_COVERAGE.sample_interleaving("clean_snoop_fill_writer_overlap")
    _record_model(model)
    expect_overlap = bool(int(os.environ.get("P2_EXPECT_OVERLAP", "1")))
    assert overlapped == expect_overlap, (
        f"clean Snoop/refill overlap={overlapped}, expected {expect_overlap}"
    )

@pytest.mark.parametrize("owner_core", [0, 1])
@case
async def test_dirty_owner_snoop_and_refill_share_l2_write_port_safely(
        coherent_env, owner_core):
    """Dirty owner data must wait while the L2 refill owns its write port."""
    dut, memory, _ = await coherent_env(
        response_delay=10, response_gap_periods={"read_data": 4},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    requester = 1 - owner_core
    owner_addr = 0x0060_3000
    refill_addr = 0x0060_2000
    model.seed_word(owner_addr,
                    memory.word(owner_addr, (owner_addr >> 3) & 7))
    dirty_value = 0xD17A_0000_0000_0000 | owner_core
    await cpu.access(owner_core, owner_addr, write=True, data=dirty_value)
    model.observe(owner_core, owner_addr, write=True, write_data=dirty_value)
    assert model.states[owner_addr & ~0x3F][owner_core] == "M"

    model.seed_word(refill_addr,
                    memory.word(refill_addr, (refill_addr >> 3) & 7))
    expected_owner_line = [
        model.data.get((owner_addr & ~0x3F) + beat * 8,
                       memory.word((owner_addr & ~0x3F) + beat * 8, beat))
        for beat in range(8)
    ]
    read_cursor = len(memory.read_requests)
    snoop_cursor = len(memory.snoop_data.snoops)
    transfer_cursor = len(memory.snoop_data.transfers)
    conflict_cursor = len(memory.snoop_data.shared_write_conflicts)

    results = await cpu.access_pair(
        CpuRequest(refill_addr), CpuRequest(owner_addr)
    ) if owner_core == 0 else await cpu.access_pair(
        CpuRequest(owner_addr), CpuRequest(refill_addr)
    )
    # access_pair returns by physical lane, so map the values back to requests.
    if owner_core == 0:
        refill_result, owner_result = results
    else:
        owner_result, refill_result = results

    expected_refill = model.word(refill_addr)
    assert refill_result == expected_refill
    assert owner_result == dirty_value
    model.observe(owner_core, refill_addr, response_data=refill_result)
    model.observe(requester, owner_addr, response_data=owner_result)
    memory.snoop_data.assert_line_data(
        owner_addr, expected_owner_line, since=transfer_cursor)
    memory.snoop_data.assert_directory_matches(model, refill_addr)
    memory.snoop_data.assert_directory_matches(model, owner_addr)
    memory.snoop_data.assert_no_shared_write_conflict()
    owner_snoops = [
        event for event in memory.snoop_data.snoops[snoop_cursor:]
        if event["line"] == (owner_addr & ~0x3F) and event["core"] == owner_core
    ]
    assert owner_snoops and owner_snoops[-1]["opcode"] == 0
    assert len(memory.read_requests) == read_cursor + 1, (
        "dirty owner forwarding should not issue an extra memory read"
    )
    assert len(memory.snoop_data.shared_write_conflicts) == conflict_cursor
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("dirty_owner_snoop_during_l2_fill")
    PYTHON_COVERAGE.sample_interleaving("dirty_owner_waits_for_l2_fill_port")
    _record_model(model)
