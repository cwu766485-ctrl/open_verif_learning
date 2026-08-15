"""课程 2：直接使用 Picker 生成的 SyncFIFO DUT。

运行前请执行一次 README 中的 picker export 命令。
"""

from generated.SyncFIFO import DUTSyncFIFO


def new_dut(waveform_filename: str) -> DUTSyncFIFO:
    """创建 DUT，并在第一个有效时钟沿前把所有输入驱动为确定值。"""
    dut = DUTSyncFIFO(waveform_filename=waveform_filename)
    dut.InitClock("clk")
    # 数据通路激励在时钟沿前必须已经稳定；否则默认的 Rise 写入会晚一个沿被 DUT 看见。
    dut.we_i.AsImmWrite()
    dut.re_i.AsImmWrite()
    dut.data_i.AsImmWrite()
    dut.we_i.value = 0
    dut.re_i.value = 0
    dut.data_i.value = 0
    return dut


def reset_fifo(dut: DUTSyncFIFO, cycles: int = 5, immediate: bool = False) -> None:
    """低有效同步复位：保持低电平 cycles 拍，再释放两拍。"""
    if immediate:
        dut.rst_n.AsImmWrite()
    else:
        dut.rst_n.AsRiseWrite()

    dut.rst_n.value = 0
    dut.Step(cycles)
    dut.rst_n.value = 1
    dut.Step(2)


def assert_reset_state(dut: DUTSyncFIFO) -> None:
    """课程任务 2：不仅检查端口，也检查导出的内部状态。"""
    assert dut.data_o.value == 0, "reset 后 data_o 必须为 0"
    assert dut.empty_o.value == 1, "reset 后 FIFO 必须为空"
    assert dut.full_o.value == 0, "reset 后 FIFO 不能为满"
    assert dut.SyncFIFO_wptr.value == 0, "reset 后写指针必须为 0"
    assert dut.SyncFIFO_rptr.value == 0, "reset 后读指针必须为 0"
    assert dut.SyncFIFO_counter.value == 0, "reset 后计数器必须为 0"


def test_reset_rise_write() -> None:
    """任务 1：默认上升沿写入模式的复位；观察 reset_rise.fst。"""
    dut = new_dut("reset_rise.fst")
    try:
        reset_fifo(dut, immediate=False)
        assert_reset_state(dut)
    finally:
        dut.Finish()


def test_reset_immediate_write() -> None:
    """任务 1：rst_n 立即写入模式；观察 reset_immediate.fst 并与默认模式比较。"""
    dut = new_dut("reset_immediate.fst")
    try:
        reset_fifo(dut, immediate=True)
        assert_reset_state(dut)
    finally:
        dut.Finish()


def test_smoke_dut() -> None:
    """任务 3：写入 0x114、0x514，再按顺序读回并检查状态。"""
    dut = new_dut("smoke.fst")
    try:
        reset_fifo(dut)

        # Write #1
        dut.we_i.value = 1
        dut.re_i.value = 0
        dut.data_i.value = 0x114
        dut.Step()
        assert dut.empty_o.value == 0, (
            "首次有效写入后 FIFO 不应为空："
            f"empty={dut.empty_o.value}, counter={dut.SyncFIFO_counter.value}, "
            f"we={dut.we_i.value}, data_i=0x{dut.data_i.value:x}"
        )
        assert dut.full_o.value == 0, "首次有效写入后 FIFO 不应为满"

        # Write #2
        dut.data_i.value = 0x514
        dut.Step()

        # Read #1
        dut.we_i.value = 0
        dut.re_i.value = 1
        dut.Step()
        assert dut.data_o.value == 0x114, "第一次读取必须得到最早写入的数据"

        # Read #2
        dut.Step()
        assert dut.data_o.value == 0x514, "第二次读取必须得到第二笔数据"
        assert dut.empty_o.value == 1, "读完两笔数据后 FIFO 必须为空"
    finally:
        dut.Finish()


if __name__ == "__main__":
    test_reset_rise_write()
    test_reset_immediate_write()
    test_smoke_dut()
    print("Course 2 Picker FIFO tests: PASS")
