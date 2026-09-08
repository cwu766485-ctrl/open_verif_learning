from toffee_test import case


@case
async def test_reset_with_fixture(fifo_env):
    """任务 2 第 1 步：fixture 建 DUT，测试只表达复位意图。"""
    await fifo_env.fifo.reset()
