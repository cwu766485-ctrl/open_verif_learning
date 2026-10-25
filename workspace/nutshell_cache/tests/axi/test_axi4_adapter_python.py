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

    async def start():
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
        memory = Axi4MemoryAgent(dut)
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
