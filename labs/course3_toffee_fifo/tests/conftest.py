import toffee
from generated.SyncFIFO import DUTSyncFIFO
from toffee_test import ToffeeRequest, fixture

from bundle import ControlBundle, InternalBundle, ReadBundle, WriteBundle
from coverage import FIFOFunctionalCoverage
from env import SyncFIFOEnv


@fixture
async def fifo_env(toffee_request: ToffeeRequest):
    """每个测试创建一个独立 DUT，并将端口按 Bundle 绑定。"""
    dut = toffee_request.create_dut(DUTSyncFIFO, "clk")
    control = ControlBundle().bind(dut).set_write_mode_as_imme()
    write = WriteBundle().bind(dut).set_write_mode_as_imme()
    read = ReadBundle().bind(dut).set_write_mode_as_imme()
    internal = InternalBundle().bind(dut)

    control.rst_n.value = 1
    write.we_i.value = 0
    write.data_i.value = 0
    read.re_i.value = 0

    coverage = FIFOFunctionalCoverage(internal)
    toffee_request.add_cov_groups(coverage.groups, periodic_sample=False)
    toffee.start_clock(dut)
    return SyncFIFOEnv(control, write, read, internal, coverage)
