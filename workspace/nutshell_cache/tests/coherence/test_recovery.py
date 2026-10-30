"""Recovery MESI subsystem tests."""

from .support import *


@case
async def test_python_l1_replacement_victim_matches_put(coherent_env):
    """Check the reference replacement way against the accepted Put line."""
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    base = 0x0060_4000
    line_stride = 32768  # same 4-way L1 set; distinct tags
    request_cursor = len(memory.snoop_data.directory_requests)

    for index in range(6):
        address = base + index * line_stride
        expected = memory.word(address, (address >> 3) & 7)
        model.seed_word(address, expected)
        response = await cpu.access(0, address)
        assert response == expected
        model.observe(0, address, response_data=response)

    matched = _assert_replacement_put_trace(model, memory,
                                            request_cursor=request_cursor)
    assert len(matched) == 2
    assert [line for _, line, _ in matched] == [base, base + line_stride]
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("l1_replacement_put_match")
    _record_model(model)

@pytest.mark.parametrize("owner_state", ["M", "E"])
@pytest.mark.parametrize("owner_core", [0, 1])
@case
async def test_python_snoop_ack_retries_from_authoritative_l2(
        coherent_env, owner_state, owner_core):
    """Close E/M replacement races that retry a no-data SnoopRead from L2."""
    env = await coherent_env()
    dut, memory, _ = env
    cpu = env.cpu
    peer = 1 - owner_core
    attempts = []

    # A fifth same-index Core0 line evicts its first Modified line. Offset the
    # remote GetS across the replacement handshake to land in the window where
    # the Directory has snapshotted the old owner but L1 has retired it with
    # PutM. Each attempt uses a different set so misses do not disturb setup.
    for attempt, delay in enumerate((0, 1, 2, 3, 4, 6, 8, 10, 12)):
        model = CoherenceScoreboard()
        line = 0x0300_0000 + attempt * 64
        stride = 32768
        owner_word = (0xA11C_0000_0000_0000 | attempt
                      if owner_state == "M" else None)
        initial = memory.word(line, (line >> 3) & 7)
        model.seed_word(line, initial)
        if owner_state == "M":
            await _model_access(cpu, model, memory.snoop_data, owner_core, line,
                                write=True, data=owner_word)
        else:
            await _model_access(cpu, model, memory.snoop_data, owner_core, line)
        for way in range(1, 4):
            address = line + way * stride
            model.seed_word(address, memory.word(address, (address >> 3) & 7))
            await _model_access(cpu, model, memory.snoop_data, owner_core, address)
        expected_states = ["I", "I"]
        expected_states[owner_core] = owner_state
        assert model.states[line & ~0x3F] == expected_states
        assert model.l1_way_view(owner_core, line) == 0

        snoop_cursor = len(memory.snoop_data.snoops)
        response_cursor = len(memory.snoop_data.directory_snoop_response_cycles)
        transfer_cursor = len(memory.snoop_data.transfers)
        lookup_cursor = len(memory.snoop_data.l2_lookups)
        grant_cursor = len(memory.snoop_data.directory_grants)
        commit_cursor = len(memory.snoop_data.directory_commits)
        request_cursor = len(memory.snoop_data.directory_requests)
        read_cursor = len(memory.read_requests)
        replacement_line = line + 4 * stride
        model.seed_word(replacement_line,
                        memory.word(replacement_line,
                                    (replacement_line >> 3) & 7))
        replacement_word = 0xBEEF_0000_0000_0000 | attempt

        pair = await env.sequence.run_pair(
            CpuAccess(owner_core, replacement_line, write=True,
                      data=replacement_word),
            CpuAccess(peer, line),
            request_delay_cycles={peer: delay},
        )
        line_tag = line & ~0x3F
        accepted_snoops = [
            event for event in memory.snoop_data.snoops[snoop_cursor:]
            if event["core"] == owner_core and event["line"] == line_tag and
            event["opcode"] == 0
        ]
        responses = memory.snoop_data.directory_snoop_response_cycles[
            response_cursor:
        ]
        ack_responses = [
            response for response in responses
            if response["valid"] and response["ready"] and
            response["target"] == owner_core and response["opcode"] == 0 and
            any(snoop["txn"] == response["txn"] for snoop in accepted_snoops)
        ]
        attempts.append({"delay": delay, "snoops": accepted_snoops,
                         "responses": responses,
                         "lookups": memory.snoop_data.l2_lookups[lookup_cursor:]})
        if not ack_responses:
            continue

        assert len(ack_responses) == 1, ack_responses
        ack = ack_responses[0]
        put_opcode = 0b101 if owner_state == "M" else 0b100
        put_event = [event for event in memory.snoop_data.directory_requests[
            request_cursor:] if event["line"] == line_tag and
            event["core"] == owner_core and event["opcode"] == put_opcode]
        assert len(put_event) == 1, put_event
        assert put_event[0]["cycle"] <= ack["cycle"], (put_event, ack)
        gets = [event for event in memory.snoop_data.directory_requests[
            request_cursor:] if event["line"] == line_tag and
            event["core"] == peer and event["opcode"] == 0b000]
        assert len(gets) == 1, gets

        refills = [event for event in memory.snoop_data.l2_lookups[lookup_cursor:]
                   if event["line"] == line_tag and event["cycle"] > ack["cycle"]]
        assert len(refills) == 1 and refills[0]["hit"], refills
        assert not [event for event in memory.snoop_data.transfers[transfer_cursor:]
                    if event["line"] == line_tag], (
            "a no-data Snoop ACK must recover from L2, not owner-data beats"
        )
        assert not [request for request in memory.read_requests[read_cursor:]
                    if request[0] == line_tag], (
            "authoritative L2 retry unexpectedly fell through to backing memory"
        )
        expected_owner_word = owner_word if owner_state == "M" else initial
        assert pair[peer] == expected_owner_word, (pair[peer], expected_owner_word)
        grants = [event for event in memory.snoop_data.directory_grants[grant_cursor:]
                  if event["line"] == line_tag]
        data_grants = [event for event in grants if event["opcode"] != 0b100]
        put_acks = [event for event in grants if event["opcode"] == 0b100]
        assert len(data_grants) == 1 and data_grants[0]["cycle"] > \
            refills[0]["cycle"], grants
        assert (data_grants[0]["dst"], data_grants[0]["opcode"]) == (peer, 0b001), \
            data_grants[0]
        assert len(put_acks) == 1 and put_acks[0]["dst"] == owner_core, grants
        assert data_grants[0]["txn"] == gets[0]["txn"], (gets, data_grants)
        assert put_acks[0]["txn"] == put_event[0]["txn"], (put_event, put_acks)

        # The independent model learns replacement from the accepted PutE/M
        # protocol request. It then predicts an Exclusive grant to Core1.
        model.track_l1_replacement = False
        model.observe_l1_put(owner_core, line, put_opcode)
        model.observe(owner_core, replacement_line, write=True,
                      write_data=replacement_word, write_mask=0xFF)
        model.observe(peer, line, response_data=pair[peer])
        expected_final = ["I", "I"]
        expected_final[peer] = "E"
        assert model.states[line_tag] == expected_final
        memory.snoop_data.assert_directory_matches(model, line)
        final_commits = [event for event in
                         memory.snoop_data.directory_commits[commit_cursor:]
                         if event["line"] == line_tag]
        assert final_commits, "retry/grant did not commit Directory metadata"
        assert (final_commits[-1]["state"], final_commits[-1]["sharers"],
                final_commits[-1]["owner"]) == (2, 0, peer), final_commits[-1]
        assert int(dut.protocol_error.value) == 0
        PYTHON_COVERAGE.sample_external("snoop_ack_l2_retry")
        PYTHON_COVERAGE.sample_external(
            f"snoop_ack_l2_retry_{owner_state.lower()}_owner"
        )
        PYTHON_COVERAGE.sample_external(
            f"snoop_ack_l2_retry_{owner_state.lower()}_owner_core{owner_core}"
        )
        _record_model(model)
        return

    raise AssertionError(
        "fixed replacement/GetS offset sweep did not produce a no-data Snoop ACK "
        f"followed by an L2 hit retry: {attempts}"
    )

@case
async def test_dual_core_owner_transfer_and_data_visibility(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    addr = 0x4010
    initial = memory.word(addr, (addr >> 3) & 7)
    scoreboard = CoherenceScoreboard()
    scoreboard.seed_word(addr, initial)

    response = await cpu.access(0, addr)
    scoreboard.observe(0, addr, response_data=response)
    assert len(memory.read_requests) == 1

    # A second core reads the line while core0 owns it. The directory should
    # obtain the current line from the owner instead of issuing another DRAM read.
    response = await cpu.access(1, addr)
    scoreboard.observe(1, addr, response_data=response)
    assert len(memory.read_requests) == 1

    updated = 0xD00DFEED12345678
    write_response = await cpu.access(1, addr, write=True, data=updated)
    scoreboard.observe(1, addr, write=True, write_data=updated,
                       response_data=write_response)
    response = await cpu.access(0, addr)
    scoreboard.observe(0, addr, response_data=response)
    scoreboard.assert_covered("cold_read", "remote_read_from_E",
                              "shared_upgrade", "remote_read_from_M")
    assert len(memory.read_requests) == 1
    assert int(dut.protocol_error.value) == 0
    _record_model(scoreboard)

@case
async def test_python_stale_upgrade_recovers_after_peer_invalidation(coherent_env):
    """A queued S->M Upgrade must recover after a competing writer invalidates S."""
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    addr = 0x0052_8040
    initial_line = tuple(memory.word(addr + 8 * beat, beat) for beat in range(8))
    model.seed_line(addr, initial_line)

    # Establish S/S first. Then let Core1's Upgrade win arbitration while
    # Core0's Upgrade is queued behind the same-line ownership transaction.
    reads = await cpu.access_pair(CpuRequest(addr), CpuRequest(addr))
    for core in (0, 1):
        model.observe(core, addr, response_data=reads[core])
    assert model.states[addr & ~0x3F] == ["S", "S"]

    req_cursor = len(memory.snoop_data.directory_requests)
    grant_cursor = len(memory.snoop_data.directory_grants)
    snoop_cursor = len(memory.snoop_data.snoops)
    transfer_cursor = len(memory.snoop_data.transfers)
    core1_value = 0x1111222233334444
    core0_value = 0xAAAABBBBCCCCDDDD
    await cpu.access_pair(
        CpuRequest(addr, True, core0_value),
        CpuRequest(addr, True, core1_value),
        request_delay_cycles={0: 1},
    )

    accepted = [item for item in memory.snoop_data.directory_requests[req_cursor:]
                if item["line"] == (addr & ~0x3F)]
    assert [(item["core"], item["opcode"]) for item in accepted] == [
        (1, 0b010), (0, 0b010)
    ], f"expected Core0's stale Upgrade after Core1 invalidated it: {accepted}"
    grants = [item for item in memory.snoop_data.directory_grants[grant_cursor:]
              if item["line"] == (addr & ~0x3F)]
    assert [(item["dst"], item["opcode"]) for item in grants] == [
        (1, 0b011), (0, 0b010)
    ], f"stale Upgrade was not recovered as data-bearing GetM: {grants}"
    snoops = memory.snoop_data.snoops[snoop_cursor:]
    assert [(item["core"], item["opcode"]) for item in snoops
            if item["line"] == (addr & ~0x3F)] == [(0, 1), (1, 1)]

    # The second Upgrade must recover Core1's just-written authoritative line.
    model.observe(1, addr, write=True, write_data=core1_value)
    expected_owner_line = tuple(model.word(addr + 8 * beat) for beat in range(8))
    memory.snoop_data.assert_line_data(addr, expected_owner_line,
                                       since=transfer_cursor)
    model.observe(0, addr, write=True, write_data=core0_value)
    assert model.directory_view(addr)["owner"] == 0
    assert int(dut.protocol_error.value) == 0

    result = await cpu.access(1, addr)
    model.observe(1, addr, response_data=result)
    assert result == core0_value
    memory.snoop_data.assert_directory_matches(model, addr)
    PYTHON_COVERAGE.sample_external("stale_upgrade_recovery")
    _record_model(model)
