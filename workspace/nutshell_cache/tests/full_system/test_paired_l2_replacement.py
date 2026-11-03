"""Paired CPU traffic with an independently predicted inclusive L2 victim."""

from toffee_test import case

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.checkers.mshr_lifecycle_checker import MshrLifecycleChecker


L2_SET_STRIDE = 512 * 64


async def _fill_l2_set_with_clean_lines(env, base):
    values = {}
    lines = [base + index * L2_SET_STRIDE for index in range(8)]
    for index, line in enumerate(lines):
        value = 0xCACE_0000_0000_0000 | (index << 8)
        env.seed_word(line, value)
        values[line] = value
        await env.cpu_access(index & 1, line)
    return lines, values


async def _check_paired_cold_misses(env, lines, values, *, request_delay=None):
    event_start = len(env.monitor.events)
    result0, result1 = await env.cpu_access_pair(
        CpuRequest(lines[0]), CpuRequest(lines[1]),
        **({"request_delay_cycles": request_delay} if request_delay else {})
    )
    assert (result0, result1) == (values[lines[0]], values[lines[1]])
    events = env.monitor.events[event_start:]
    lifecycle = MshrLifecycleChecker.check(
        events,
        expected_lines=lines,
        expected_words={line: values[line] for line in lines},
        expected_cores={lines[0]: 0, lines[1]: 1},
    )
    assert lifecycle["mshr_allocations"] == 2
    assert lifecycle["mshr_retirements"] == 2
    assert lifecycle["axi_read_beats"] == lifecycle["l2_refill_beats"] == 16
    return events


@case
async def test_paired_hit_and_miss_checks_dirty_l2_victim(full_system_env):
    """Keep an M owner live while a paired request causes same-set eviction.

    Eight lines fill one L2 set while each L1 holds four lines. The owner of
    the model-predicted next victim is promoted to M. A paired L1 hit and
    opposite-core cold miss then forces inclusive replacement. FullSystemEnv
    compares the observed victim, Directory metadata, snoop invalidation,
    owner beats, AXI writeback and backing-memory data against its independent
    model before this testcase credits coverage.
    """
    env = await full_system_env(axi_options={"latency": 12})
    base = 0x0200_0000
    lines = [base + index * L2_SET_STRIDE for index in range(8)]
    initial_words = {}

    for index, line in enumerate(lines):
        words = [0xCACE_0000_0000_0000 | (index << 8) | beat
                 for beat in range(8)]
        env.reference.seed_line(line, words)
        for beat, value in enumerate(words):
            env.axi.seed_word(line + beat * 8, value)
        initial_words[line] = words[0]
        await env.cpu_access(index & 1, line)

    set_index = (base >> 6) & 0x1FF
    next_way = env.reference.l2_next_way[set_index] % 8
    victim = env.reference.l2_ways[set_index][next_way]
    assert victim in lines
    victim_states = env.reference.states[victim]
    owners = [core for core, state in enumerate(victim_states)
              if state in ("E", "M")]
    assert len(owners) == 1, f"expected a sole clean owner before store: {victim_states}"
    owner_core = owners[0]
    dirty_word = 0xD17A_0000_0000_0000 | victim
    await env.cpu_access(owner_core, victim, write=True,
                         data=dirty_word, mask=0xFF)

    hit_line = next(line for line in lines
                    if line != victim and
                    env.reference.states[line][owner_core] != "I")
    miss_core = 1 - owner_core
    miss_line = base + 8 * L2_SET_STRIDE
    refill_word = 0xF111_0000_0000_0000 | miss_line
    env.seed_word(miss_line, refill_word)
    victim_start = len(env.reference.l2_victim_selections)
    event_start = len(env.monitor.events)

    requests = [None, None]
    requests[owner_core] = CpuRequest(hit_line)
    requests[miss_core] = CpuRequest(miss_line)
    results = await env.cpu_access_pair(requests[0], requests[1])

    assert results[owner_core] == initial_words[hit_line]
    assert results[miss_core] == refill_word
    predictions = env.reference.l2_victim_selections[victim_start:]
    assert len(predictions) == 1
    assert predictions[0]["line"] == victim
    events = env.monitor.events[event_start:]
    selected = [event for event in events
                if event["source"] == "l2_victim" and
                event["event_type"] == "select"]
    assert len(selected) == 1 and selected[0]["address"] == victim
    assert selected[0]["directory_state"] == 2  # Directory U: unique M owner.
    assert any(event["source"] == "axi" and
               event["event_type"] == "write_address" and
               event["address"] == victim for event in events)
    assert int(env.dut.protocol_error.value) == 0

    env.coverage.sample_checked_event(
        "FS.CONCURRENCY.PAIRED_L2_DIRTY_VICTIM", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.PAIRED_L2_DIRTY_VICTIM", checked=True
    )


@case
async def test_paired_cold_miss_same_set_uses_directory_accept_order(full_system_env):
    """Two same-set misses update the independent model in observed order."""
    env = await full_system_env(axi_options={"latency": 12})
    base = 0x0240_0000
    await _fill_l2_set_with_clean_lines(env, base)

    line0, line1 = base + 8 * L2_SET_STRIDE, base + 9 * L2_SET_STRIDE
    values = {
        line0: 0x0A00_0000_0000_0000 | line0,
        line1: 0x0B00_0000_0000_0000 | line1,
    }
    for line, value in values.items():
        env.seed_word(line, value)

    events = await _check_paired_cold_misses(
        env, (line0, line1), values, request_delay={0: 1}
    )
    directory_order = [event["address"] & 0xFFFF_FFC0
                       for event in sorted(
                           (event for event in events
                            if event["source"] == "directory" and
                            event["event_type"] == "request_accept" and
                            (event["address"] & 0xFFFF_FFC0) in {line0, line1}),
                           key=lambda event: event["cycle"])]
    assert directory_order == [line1, line0], (
        f"same-set paired misses were not admitted in observed delayed-lane "
        f"order: {directory_order}"
    )
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event(
        "FS.CONCURRENCY.PAIRED_MISS_ORDERING", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.PAIRED_MISS_ORDERING", checked=True
    )


@case
async def test_repeated_paired_misses_replace_one_l2_set(full_system_env):
    """Two paired miss rounds cause four checked replacements in one set."""
    env = await full_system_env(axi_options={"latency": 8})
    base = 0x0280_0000
    await _fill_l2_set_with_clean_lines(env, base)
    event_start = len(env.monitor.events)
    victim_start = len(env.reference.l2_victim_selections)

    all_lines = [base + index * L2_SET_STRIDE for index in range(8, 12)]
    all_values = {
        line: (0xE000_0000_0000_0000 | line)
        for line in all_lines
    }
    for line, value in all_values.items():
        env.seed_word(line, value)

    await _check_paired_cold_misses(env, tuple(all_lines[:2]), all_values)
    await _check_paired_cold_misses(env, tuple(all_lines[2:]), all_values)

    predictions = env.reference.l2_victim_selections[victim_start:]
    observed = [event for event in env.monitor.events[event_start:]
                if event["source"] == "l2_victim" and
                event["event_type"] == "select"]
    assert len(predictions) == len(observed) == 4
    assert [event["address"] for event in observed] == [
        item["line"] for item in predictions
    ]
    assert len({item["line"] for item in predictions}) == 4
    assert int(env.dut.protocol_error.value) == 0
    env.coverage.sample_checked_event(
        "FS.CONCURRENCY.PAIRED_SAME_SET_REPLACEMENTS", checked=True
    )
    env.coverage.sample_checked_cross(
        "FS.CROSS.PAIRED_SAME_SET_REPLACEMENTS", checked=True
    )
