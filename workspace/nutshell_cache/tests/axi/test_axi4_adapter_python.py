"""Five-channel AXI4 Python/Toffee verification for LineMemoryAxi4Adapter."""

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, case, fixture

from dv.agents.axi4_memory_agent import Axi4MemoryAgent

try:
    from line_axi_python import DUTLineMemoryAxi4PythonWrapper
except ImportError:
    DUTLineMemoryAxi4PythonWrapper = None


@fixture
async def axi_adapter_env(toffee_request: ToffeeRequest):
    if DUTLineMemoryAxi4PythonWrapper is None:
        pytest.skip("run make coherence_axi_python_build before the AXI4 Python test")

    async def start(*, memory_options=None):
        dut = toffee_request.create_dut(DUTLineMemoryAxi4PythonWrapper, "clock")
        for name in (
            "line_rd_req_valid", "line_rd_req_addr", "line_rd_req_id",
            "line_rd_data_ready", "line_wr_req_valid", "line_wr_req_addr",
            "line_wr_req_id", "line_wr_data_valid", "line_wr_data_id",
            "line_wr_data_beat", "line_wr_data", "line_wr_data_last",
            "line_wr_rsp_ready",
        ):
            getattr(dut, name).value = 0
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        start_clock(dut)
        await ClockCycles(dut, 4)
        dut.reset.value = 0
        memory = Axi4MemoryAgent(dut, **(memory_options or {}))
        async with Executor(exit="none") as executor:
            executor(memory.run(), sche_group="axi4_memory")
        return dut, memory

    return start


async def _send_read(dut, addr, txn_id):
    dut.line_rd_req_addr.value = addr
    dut.line_rd_req_id.value = txn_id
    dut.line_rd_req_valid.value = 1
    for _ in range(100):
        if int(dut.line_rd_req_ready.value):
            await ClockCycles(dut, 1)
            dut.line_rd_req_valid.value = 0
            return
        await ClockCycles(dut, 1)
    dut.line_rd_req_valid.value = 0
    raise TimeoutError(f"line read request ID={txn_id} was not accepted")


async def _send_write_req(dut, addr, txn_id):
    dut.line_wr_req_addr.value = addr
    dut.line_wr_req_id.value = txn_id
    dut.line_wr_req_valid.value = 1
    for _ in range(100):
        if int(dut.line_wr_req_ready.value):
            await ClockCycles(dut, 1)
            dut.line_wr_req_valid.value = 0
            return
        await ClockCycles(dut, 1)
    dut.line_wr_req_valid.value = 0
    raise TimeoutError(f"line write request ID={txn_id} was not accepted")


async def _send_write_beat(dut, txn_id, beat, data):
    dut.line_wr_data_id.value = txn_id
    dut.line_wr_data_beat.value = beat
    dut.line_wr_data.value = data
    dut.line_wr_data_last.value = int(beat == 7)
    dut.line_wr_data_valid.value = 1
    for _ in range(100):
        if int(dut.line_wr_data_ready.value):
            await ClockCycles(dut, 1)
            dut.line_wr_data_valid.value = 0
            return
        await ClockCycles(dut, 1)
    dut.line_wr_data_valid.value = 0
    raise TimeoutError(f"line write data ID={txn_id} beat={beat} not accepted")


@case
async def test_axi4_four_outstanding_bursts_id_ordering_and_backpressure(
        axi_adapter_env):
    dut, memory = await axi_adapter_env()
    read_ids = [1, 3, 5, 7]
    read_addrs = [0x2000_0000 + 0x100 * index for index in range(4)]
    write_ids = [2, 4, 6, 8]
    write_addrs = [0x2100_0000 + 0x100 * index for index in range(4)]

    # Fill all four read slots before allowing any burst to finish.
    for addr, txn_id in zip(read_addrs, read_ids):
        await _send_read(dut, addr, txn_id)

    for addr, txn_id in zip(write_addrs, write_ids):
        memory.expected_write_words[txn_id] = [
            memory.write_word(txn_id, beat) for beat in range(8)
        ]
        await _send_write_req(dut, addr, txn_id)
    # Interleave line-side data by ID. AXI4 has no WID, so the adapter must
    # still emit complete bursts in AW acceptance order without mixing beats.
    for beat in range(8):
        for txn_id in write_ids:
            await _send_write_beat(
                dut, txn_id, beat, memory.expected_write_words[txn_id][beat]
            )

    for _ in range(700):
        if (len(memory.read_completion_order) == 4 and
                len(memory.write_completion_order) == 4):
            break
        await ClockCycles(dut, 1)

    assert len(memory.read_accepts) == 4
    assert len(memory.read_beat_accepts) == 32
    assert len(memory.read_completion_order) == 4
    assert len(set(memory.read_completion_order)) == 4
    assert memory.read_completion_order != read_ids, (
        "RAM must return read bursts out of request order to exercise RID routing"
    )
    assert len(memory.write_address_accepts) == 4
    assert len(memory.write_beat_accepts) == 32
    assert len(memory.write_completion_order) == 4
    assert set(memory.write_completion_order) == set(write_ids)
    assert memory.write_completion_order != write_ids, (
        "RAM must return B responses out of AW order across distinct IDs"
    )
    assert memory.peak_reads == 4
    assert memory.peak_writes == 4
    assert not memory.line_read_addr, "some accepted read lines did not complete"
    for channel in ("AR", "AW", "W", "R", "B"):
        assert memory.stalls[channel] > 0, f"AXI {channel} backpressure was not exercised"
    assert int(dut.mon_stability_error.value) == 0, (
        "AXI VALID/payload stability broke while a channel was stalled"
    )
    assert int(dut.protocol_error.value) == 0


@case
async def test_axi4_error_responses_id_reuse_and_4k_boundary(axi_adapter_env):
    dut, memory = await axi_adapter_env(memory_options={
        "read_error_beats": {5: 3}, "write_error_ids": {6},
    })

    # The final 64-byte line of a 4 KiB page is legal: its eighth beat ends at
    # the page boundary without crossing it.
    await _send_read(dut, 0x2000_FFC0, 5)
    await _send_read(dut, 0x2200_0040, 3)
    for _ in range(180):
        if set(memory.read_completion_order) == {3, 5}:
            break
        await ClockCycles(dut, 1)
    assert set(memory.read_completion_order) == {3, 5}
    assert memory.line_read_errors and memory.line_read_errors[0][:2] == (5, 3)
    assert not memory.line_read_addr
    assert memory.read_accepts[0][1] == 0x2000_FFC0

    # IDs are legal to reuse once the prior transaction has retired.
    await _send_read(dut, 0x2200_0080, 3)
    for _ in range(100):
        if memory.read_completion_order.count(3) == 2:
            break
        await ClockCycles(dut, 1)
    assert memory.read_completion_order.count(3) == 2

    txn_id = 6
    address = 0x2100_FFC0
    memory.expected_write_words[txn_id] = [
        memory.write_word(txn_id, beat) for beat in range(8)
    ]
    await _send_write_req(dut, address, txn_id)
    for beat, data in enumerate(memory.expected_write_words[txn_id]):
        await _send_write_beat(dut, txn_id, beat, data)
    for _ in range(500):
        if memory.write_completion_order:
            break
        await ClockCycles(dut, 1)
    assert memory.write_completion_order == [txn_id]
    assert memory.line_write_errors and memory.line_write_errors[0][0] == txn_id
    assert memory.write_address_accepts[0][1] == address
    assert int(dut.protocol_error.value) == 0


@case
async def test_axi4_reset_cancels_outstanding_and_allows_id_reuse(axi_adapter_env):
    dut, memory = await axi_adapter_env()
    read_id, write_id = 9, 10
    await _send_read(dut, 0x2300_1000, read_id)
    for _ in range(100):
        if any(item[0] == read_id for item in memory.read_accepts):
            break
        await ClockCycles(dut, 1)
    assert any(item[0] == read_id for item in memory.read_accepts)

    memory.expected_write_words[write_id] = [
        memory.write_word(write_id, beat) for beat in range(8)
    ]
    await _send_write_req(dut, 0x2300_2000, write_id)
    for beat, data in enumerate(memory.expected_write_words[write_id]):
        await _send_write_beat(dut, write_id, beat, data)
    for _ in range(100):
        if (any(item[0] == write_id for item in memory.write_address_accepts) and
                any(item[0] == write_id for item in memory.write_beat_accepts)
                and sum(item[0] == write_id for item in memory.write_beat_accepts) == 8):
            break
        await ClockCycles(dut, 1)
    assert any(item[0] == write_id for item in memory.write_address_accepts)
    assert sum(item[0] == write_id for item in memory.write_beat_accepts) == 8
    assert not memory.write_completion_order

    dut.reset.value = 1
    await ClockCycles(dut, 3)
    dut.reset.value = 0
    await ClockCycles(dut, 8)
    assert memory.reset_cancelled == {"reads": 1, "writes": 1}
    assert int(dut.line_rd_data_valid.value) == 0
    assert int(dut.line_wr_rsp_valid.value) == 0

    # The canceled read ID can be allocated again after reset and returns data.
    await _send_read(dut, 0x2300_1000, read_id)
    for _ in range(150):
        if memory.read_completion_order:
            break
        await ClockCycles(dut, 1)
    assert memory.read_completion_order == [read_id]
    assert int(dut.protocol_error.value) == 0
