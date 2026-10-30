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
