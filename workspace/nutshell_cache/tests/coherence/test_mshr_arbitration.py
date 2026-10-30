"""Integrated MSHR/context concurrency and backpressure checks."""

from collections import Counter

from .support import *


@case
async def test_python_mshr_contexts_progress_under_memory_backpressure(coherent_env):
    """Two different L2 sets retain independent contexts during read stalls."""
    env = await coherent_env(
        response_delay=12,
        backpressure_periods={"read_req": 3},
        response_gap_periods={"read_data": 4},
    )
    memory, model = env.memory, env.new_scoreboard()
    memory.arm_stall("read_req", cycles=2)
    addresses = (0x0680_0000, 0x0680_0040)
    expected = []
    for address in addresses:
        value = memory.word(address, (address >> 3) & 7)
        expected.append(value)
        model.seed_word(address, value)

    results = await env.sequence.run_pair(
        CpuAccess(0, addresses[0]), CpuAccess(1, addresses[1]),
        response_stall_cycles=2,
    )
    assert results == tuple(expected)
    for core, address, value in zip((0, 1), addresses, results):
        model.observe(core, address, response_data=value)
        memory.snoop_data.assert_directory_matches(model, address)

    reads = [item for item in memory.read_requests
             if item[0] in {address & ~0x3F for address in addresses}]
    assert Counter(item[0] for item in reads) == Counter(addresses)
    assert len({item[1] for item in reads}) == 2, reads
    assert env.perf.peak_mshr_occupancy >= 2, env.perf.mshr_occupancy_histogram
    assert env.perf.peak_directory_contexts >= 2, \
        env.perf.directory_context_histogram
    assert memory.stalls["read_req"] >= 2
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_external("directory_mshr_dual_context_backpressure")
    env.coverage.sample_interleaving("distinct_set_contexts_read_stalled")
    _record_model(model)


@pytest.mark.parametrize("owner_core", [0, 1])
@pytest.mark.parametrize("owner_state", ["S", "E", "M"])
@case
async def test_python_replacement_replays_after_same_line_snoop(
        coherent_env, owner_core, owner_state):
    """A replacement Put racing a peer Snoop retires then replays its CPU miss."""
    env = await coherent_env(response_delay=2)
    cpu, memory, monitor = env.cpu, env.memory, env.snoop_data
    peer = 1 - owner_core
    stride = 32768  # same L1 index, distinct tags
    offsets = (0, 1, 2, 3, 4, 6, 8)

    for attempt, delay in enumerate(offsets):
        model = env.new_scoreboard()
        victim = 0x0900_0000 + attempt * 64
        initial = memory.word(victim, (victim >> 3) & 7)
        dirty = 0xD1A7_0000_0000_0000 | (owner_core << 8) | attempt
        peer_store = 0xBEEF_0000_0000_0000 | (owner_core << 8) | attempt
        model.seed_word(victim, initial)
        if owner_state == "M":
            await _model_access(cpu, model, monitor, owner_core, victim,
                                write=True, data=dirty)
        else:
            await _model_access(cpu, model, monitor, owner_core, victim)
        if owner_state == "S":
            await _model_access(cpu, model, monitor, peer, victim)
        for way in range(1, 4):
            address = victim + way * stride
            model.seed_word(address, memory.word(address, (address >> 3) & 7))
            await _model_access(cpu, model, monitor, owner_core, address)
        assert model.states[victim & ~0x3F][owner_core] == owner_state
        assert model.l1_way_view(owner_core, victim) == 0

        replacement = victim + 4 * stride
        replacement_data = 0xCAFE_0000_0000_0000 | attempt
        model.seed_word(replacement,
                        memory.word(replacement, (replacement >> 3) & 7))
        request_cursor = len(monitor.directory_requests)
        snoop_cursor = len(monitor.snoops)
        grant_cursor = len(monitor.directory_grants)
        state_cursor = len(monitor.replacement_state_samples)

        model.track_l1_replacement = False
        remote_write = owner_state == "S"
        pair = await env.sequence.run_pair(
            CpuAccess(owner_core, replacement, write=True,
                      data=replacement_data),
            CpuAccess(peer, victim, write=remote_write, data=peer_store),
            request_delay_cycles={peer: delay},
        )
        snoops = [item for item in monitor.snoops[snoop_cursor:]
                  if item["core"] == owner_core and item["line"] == victim and
                  item["opcode"] == int(remote_write)]
        puts = [item for item in monitor.directory_requests[request_cursor:]
                if item["core"] == owner_core and item["line"] == victim and
                item["opcode"] == {"S": 0b011, "E": 0b100,
                                   "M": 0b101}[owner_state]]
        if not snoops:
            continue

        assert len(snoops) == 1, snoops
        assert len(puts) == 1, puts
        assert any(sample[f"core{owner_core}"] == 9
                   for sample in monitor.replacement_state_samples[state_cursor:]), \
            "replacement controller did not enter REPLACE_REPLAY"
        if remote_write:
            await cpu.access(peer, victim)
            assert (await cpu.access(peer, victim)) == peer_store
        else:
            expected = dirty if owner_state == "M" else initial
            assert pair[peer] == expected, (owner_state, pair[peer], expected)
        # The peer's final Grant must follow the replacement PutAck. This
        # establishes the legal linearization used by the independent model:
        # the replacement removes its old copy before the peer's retried miss.
        put_ack = [event for event in monitor.directory_grants[grant_cursor:]
                   if event["line"] == victim and event["dst"] == owner_core and
                   event["opcode"] == 0b100]
        peer_grants = [event for event in monitor.directory_grants[grant_cursor:]
                       if event["line"] == victim and event["dst"] == peer and
                       event["opcode"] != 0b100]
        assert len(put_ack) == 1 and len(peer_grants) == 1, \
            (put_ack, peer_grants)
        assert put_ack[0]["cycle"] < peer_grants[0]["cycle"], \
            (put_ack, peer_grants)
        assert put_ack[0]["txn"] == puts[0]["txn"], (put_ack, puts)

        # Reconstruct the final model from accepted Directory events. The
        # model never reads DUT MESI or internal L1 metadata.
        seen_operations = set()
        for event in monitor.directory_requests[request_cursor:]:
            if event["opcode"] in _PUT_OPCODES:
                model.observe_l1_put(event["core"], event["line"],
                                     event["opcode"])
                seen_operations.add(
                    ("put", event["core"], event["line"], event["opcode"])
                )
        for event in sorted(monitor.directory_requests[request_cursor:],
                            key=lambda item: item["cycle"]):
            if event["opcode"] in _PUT_OPCODES:
                continue
            if event["line"] == (replacement & ~0x3F) and \
                    event["core"] == owner_core:
                key = ("cpu", owner_core, replacement & ~0x3F)
                if key not in seen_operations:
                    model.observe(owner_core, replacement, write=True,
                                  write_data=replacement_data)
                    seen_operations.add(key)
            elif event["line"] == (victim & ~0x3F) and event["core"] == peer:
                key = ("cpu", peer, victim & ~0x3F)
                if key not in seen_operations:
                    if remote_write:
                        model.observe(peer, victim, write=True,
                                      write_data=peer_store)
                    else:
                        model.observe(peer, victim, response_data=pair[peer])
                    seen_operations.add(key)
        memory.snoop_data.assert_directory_matches(model, victim)
        memory.snoop_data.assert_directory_matches(model, replacement)
        assert int(env.dut.protocol_error.value) == 0
        env.coverage.sample_external("replacement_replay_put_snoop_conflict")
        env.coverage.sample_external(
            f"replacement_replay_{owner_state.lower()}_core{owner_core}"
        )
        env.coverage.sample_interleaving(
            f"put_{owner_state.lower()}_snoop_core{owner_core}"
        )
        _record_model(model)
        return

    raise AssertionError(
        f"no same-line Put/Snoop overlap observed for core{owner_core} "
        f"owner state {owner_state}; offsets={offsets}"
    )
