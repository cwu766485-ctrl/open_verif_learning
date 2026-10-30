"""Test Dual Lane MESI subsystem tests."""

from .support import *


@case
async def test_python_same_line_dual_lane_requests(coherent_env):
    dut, memory, _ = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    address = 0x0230_1280
    initial = memory.word(address, (address >> 3) & 7)
    model.seed_word(address, initial)

    results = await cpu.access_pair(CpuRequest(address), CpuRequest(address))
    assert results == (initial, initial)
    model.observe(0, address, response_data=results[0])
    model.observe(1, address, response_data=results[1])

    value0, mask0 = 0x1122334455667788, 0x0F
    value1, mask1 = 0xAABBCCDDEEFF0011, 0xF0
    await cpu.access_pair(CpuRequest(address, True, value0, mask0),
                          CpuRequest(address, True, value1, mask1))
    model.observe(0, address, write=True, write_data=value0,
                  write_mask=mask0)
    model.observe(1, address, write=True, write_data=value1,
                  write_mask=mask1)
    expected = model.word(address)
    readback = await cpu.access(0, address)
    assert readback == expected
    model.observe(0, address, response_data=readback)
    memory.snoop_data.assert_directory_matches(model, address)
    assert int(dut.protocol_error.value) == 0
    PYTHON_COVERAGE.sample_external("same_line_dual_lane")
    _record_model(model)
