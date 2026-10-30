"""Test Message Passing MESI subsystem tests."""

from .support import *


@case
async def test_python_message_passing_litmus(coherent_env):
    """Check completed producer stores become visible through distinct lines."""
    dut, memory, _ = await coherent_env(
        response_delay=3,
        backpressure_periods={"read_req": 5},
        response_gap_periods={"read_data": 4},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    model.track_l1_replacement = False
    data_addr, ready_addr = 0x0310_0000, 0x0310_0040
    payload, generation = 0xCAFE_0123_4567_89AB, 1
    for addr in (data_addr, ready_addr):
        model.seed_word(addr, memory.word(addr, (addr >> 3) & 7))

    # The LSU driver waits for each Store response before allowing the next
    # operation. This tests coherence visibility under that ordering contract;
    # it does not claim an ISA acquire/release or RISC-V fence guarantee.
    await _model_access(cpu, model, memory.snoop_data, 0, data_addr,
                        write=True, data=payload)
    await _model_access(cpu, model, memory.snoop_data, 0, ready_addr,
                        write=True, data=generation,
                        response_stall_cycles=2)
    observed_ready = await _model_access(
        cpu, model, memory.snoop_data, 1, ready_addr
    )
    assert observed_ready == generation
    observed_payload = await _model_access(
        cpu, model, memory.snoop_data, 1, data_addr
    )
    assert observed_payload == payload
    for addr in (data_addr, ready_addr):
        memory.snoop_data.assert_directory_matches(model, addr)
    assert memory.stalls["read_req"] > 0
    assert sum(cpu.response_stall_cycles.values()) >= 2
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("litmus_message_passing")
    PYTHON_COVERAGE.sample_interleaving("message_passing_distinct_lines")
    _record_model(model)
