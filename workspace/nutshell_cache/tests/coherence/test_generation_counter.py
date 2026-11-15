"""Test Generation Counter MESI subsystem tests."""

from .support import *


@case
async def test_python_generation_counter_litmus(coherent_env):
    """Run 100 DATA/READY/ACK generations with backpressure and exact checks."""
    dut, memory, _ = await coherent_env(
        response_delay=2,
        backpressure_periods={"read_req": 7},
        response_gap_periods={"read_data": 5},
    )
    memory.arm_stall("read_req", cycles=2)
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    model.track_l1_replacement = False
    data_addr, ready_addr, ack_addr = (
        0x0330_0000, 0x0330_0040, 0x0330_0080
    )
    for addr in (data_addr, ready_addr, ack_addr):
        line = addr & ~0x3F
        memory.lines.setdefault(line, [memory.word(line, beat) for beat in range(8)])
        model.seed_word(addr, memory.lines[line][(addr >> 3) & 7])
    memory.lines[ready_addr & ~0x3F][0] = 0
    memory.lines[ack_addr & ~0x3F][0] = 0
    model.seed_word(ready_addr, 0)
    model.seed_word(ack_addr, 0)
    transaction_lock = asyncio.Lock()
    access_count = 0

    async def checked(core, addr, *, write=False, data=0):
        nonlocal access_count
        async with transaction_lock:
            access_count += 1
            return await _model_access(
                cpu, model, memory.snoop_data, core, addr, write=write,
                data=data,
                response_stall_cycles=2 if access_count % 11 == 0 else 0,
            )

    async def producer():
        for generation in range(1, 101):
            payload = 0xDADA_0000_0000_0000 | generation
            await checked(0, data_addr, write=True, data=payload)
            await checked(0, ready_addr, write=True, data=generation)
            for _ in range(32):
                ack = await checked(0, ack_addr)
                if ack == generation:
                    break
                assert ack < generation, (
                    f"producer observed future ACK {ack} at generation {generation}"
                )
            else:
                raise AssertionError(f"generation {generation} ACK timed out")

    consumed = []

    async def consumer():
        for generation in range(1, 101):
            for _ in range(32):
                ready = await checked(1, ready_addr)
                if ready == generation:
                    break
                assert ready < generation, (
                    f"consumer skipped generation {generation}: READY={ready}"
                )
            else:
                raise AssertionError(f"generation {generation} READY timed out")
            payload = await checked(1, data_addr)
            expected = 0xDADA_0000_0000_0000 | generation
            assert payload == expected, (
                f"generation {generation}: DATA={payload:#018x}, "
                f"expected={expected:#018x}"
            )
            await checked(1, ack_addr, write=True, data=generation)
            consumed.append(generation)

    await asyncio.gather(producer(), consumer())
    assert consumed == list(range(1, 101))
    assert await checked(1, ready_addr) == 100
    assert await checked(0, ack_addr) == 100
    assert await checked(0, data_addr) == (0xDADA_0000_0000_0000 | 100)
    for addr in (data_addr, ready_addr, ack_addr):
        memory.snoop_data.assert_directory_matches(model, addr)
    assert memory.stalls["read_req"] > 0
    assert sum(cpu.response_stall_cycles.values()) > 0
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("litmus_generation_counter_100")
    PYTHON_COVERAGE.sample_external("litmus_generation_backpressure")
    PYTHON_COVERAGE.sample_interleaving("data_ready_ack_100_generations")
    _record_model(model)


@case
async def test_python_generation_counter_concurrent_lanes(coherent_env):
    """Run the same 100-generation protocol with both CPU lanes in flight."""
    dut, memory, _ = await coherent_env(
        response_delay=3,
        backpressure_periods={"read_req": 5},
        response_gap_periods={"read_data": 3},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    model.track_l1_replacement = False
    data_addr, ready_addr, ack_addr = (
        0x0340_0000, 0x0340_0040, 0x0340_0080
    )
    for addr in (data_addr, ready_addr, ack_addr):
        line = addr & ~0x3F
        memory.lines.setdefault(line, [memory.word(line, beat) for beat in range(8)])
        model.seed_word(addr, memory.lines[line][(addr >> 3) & 7])
    memory.lines[ready_addr & ~0x3F][0] = 0
    memory.lines[ack_addr & ~0x3F][0] = 0
    model.seed_word(ready_addr, 0)
    model.seed_word(ack_addr, 0)

    interleavings = []
    accepted_transactions = []
    transaction_start = len(cpu.transactions)

    async def pair(core0, core1, *, delayed_core=1):
        group = cpu.request_group
        delays = {delayed_core: 2}
        before = len(cpu.transactions)
        results = await cpu.access_pair(
            core0, core1, request_delay_cycles=delays,
            response_stall_cycles=1,
        )
        transactions = cpu.transactions[before:]
        assert len(transactions) == 2
        assert {item["core"] for item in transactions} == {0, 1}
        assert {item["request_group"] for item in transactions} == {group}
        first, second = sorted(transactions, key=lambda item: item["accepted_cycle"])
        if first["core"] == 0 and second["core"] == 1:
            interleavings.append({
                "group": group,
                "core0_accept": first["accepted_cycle"],
                "core1_accept": second["accepted_cycle"],
                "core0_response": first["response_cycle"],
                "core1_response": second["response_cycle"],
            })
        return results

    consumed = []
    for generation in range(1, 101):
        payload = 0xDADA_0000_0000_0000 | generation

        # Producer DATA and consumer's prior READY load are independent lines.
        data_write, ready_old = await pair(
            CpuRequest(data_addr, write=True, data=payload),
            CpuRequest(ready_addr),
        )
        assert data_write == model.word(data_addr)
        assert ready_old == generation - 1
        model.observe(0, data_addr, write=True, write_data=payload,
                      write_mask=0xFF)
        model.observe(1, ready_addr, response_data=ready_old)

        # The consumer must observe this READY before it is allowed to read DATA.
        ready_write, ready_poll = await pair(
            CpuRequest(ready_addr, write=True, data=generation),
            CpuRequest(ready_addr),
        )
        assert ready_write == generation - 1
        assert ready_poll in (generation - 1, generation)
        model.observe(0, ready_addr, write=True, write_data=generation,
                      write_mask=0xFF)
        if ready_poll == generation:
            model.observe(1, ready_addr, response_data=ready_poll)
        for _ in range(8):
            if ready_poll == generation:
                break
            ready_poll = await _model_access(
                cpu, model, memory.snoop_data, 1, ready_addr
            )
            assert ready_poll <= generation
        assert ready_poll == generation, (
            f"consumer did not observe READY generation {generation}"
        )

        # The Producer's ACK poll overlaps the Consumer's DATA load. The
        # Consumer's program order is READY observation -> DATA -> ACK store.
        ack_previous, data_read = await pair(
            CpuRequest(ack_addr), CpuRequest(data_addr)
        )
        assert ack_previous == generation - 1
        assert data_read == payload
        model.observe(0, ack_addr, response_data=ack_previous)
        model.observe(1, data_addr, response_data=data_read)
        consumed.append(generation)

        # Consumer ACK and producer's poll overlap. Either old or new ACK is
        # legal for this concurrent read/write; the Producer retries if needed.
        ack_old, ack_write = await pair(
            CpuRequest(ack_addr),
            CpuRequest(ack_addr, write=True, data=generation),
        )
        assert ack_old in (generation - 1, generation)
        assert ack_write in (generation - 1, generation)
        model.observe(1, ack_addr, write=True, write_data=generation,
                      write_mask=0xFF)
        if ack_old == generation:
            model.observe(0, ack_addr, response_data=ack_old)
        for _ in range(8):
            if ack_old == generation:
                break
            ack_old = await _model_access(
                cpu, model, memory.snoop_data, 0, ack_addr
            )
            assert ack_old <= generation
        assert ack_old == generation, f"producer missed ACK generation {generation}"

    assert consumed == list(range(1, 101))
    accepted_transactions = cpu.transactions[transaction_start:]
    assert len(accepted_transactions) >= 800
    assert len({(item["core"], item["request_group"])
                for item in accepted_transactions}) == len(accepted_transactions)
    assert any(item["core1_accept"] < item["core0_response"]
               for item in interleavings), (
        "two Python tasks did not produce a CPU request accepted while the "
        "other core's response was still outstanding"
    )
    for addr in (data_addr, ready_addr, ack_addr):
        memory.snoop_data.assert_directory_matches(model, addr)
    assert memory.snoop_data.directory_requests
    assert memory.snoop_data.directory_grants
    assert memory.snoop_data.snoops
    assert not memory.snoop_data.beat_errors
    assert memory.stalls["read_req"] > 0
    assert sum(cpu.response_stall_cycles.values()) > 0
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("litmus_generation_counter_100")
    PYTHON_COVERAGE.sample_external("litmus_generation_backpressure")
    PYTHON_COVERAGE.sample_interleaving("data_ready_ack_100_generations")
    _record_model(model)
    trace = {
        "scenario": "generation_counter_concurrent_lanes_100",
        "checker": "generation sequence, byte-accurate MESI/data scoreboard, "
                   "directory commit, unique CPU transaction, and cycle overlap",
        "generations": consumed,
        "cpu_transactions": accepted_transactions,
        "request_overlaps": interleavings,
        "directory_requests": memory.snoop_data.directory_requests,
        "directory_grants": memory.snoop_data.directory_grants,
        "directory_commits": memory.snoop_data.directory_commits,
        "snoops": memory.snoop_data.snoops,
        "owner_data_transfers": memory.snoop_data.transfers,
        "final_directory": {
            f"0x{addr:08x}": model.directory_view(addr)
            for addr in (data_addr, ready_addr, ack_addr)
        },
    }
    trace_path = Path("reports/coherence/generation_counter_concurrent_trace.json")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
