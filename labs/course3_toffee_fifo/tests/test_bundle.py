from toffee_test import case


@case
async def test_bundle(fifo_env):
    """任务 2 第 2 步：直接使用 Bundle 验证一次写、一次读。"""
    await fifo_env.fifo.control.reset()
    assert await fifo_env.fifo.write.enqueue(0x114)
    assert int(fifo_env.fifo.read.empty_o.value) == 0
    assert await fifo_env.fifo.read.dequeue() == 0x114
    assert int(fifo_env.fifo.read.empty_o.value) == 1


@case
async def test_full_empty(fifo_env):
    """写满、非法满写、读空、非法空读，并检查完整数据顺序。"""
    await fifo_env.fifo.control.reset()
    expected = [0x100 + index for index in range(16)]
    for data in expected:
        assert await fifo_env.fifo.write.enqueue(data)
    assert int(fifo_env.fifo.write.full_o.value) == 1
    assert not await fifo_env.fifo.write.enqueue(0xDEAD)

    actual = [await fifo_env.fifo.read.dequeue() for _ in expected]
    assert actual == expected
    assert int(fifo_env.fifo.read.empty_o.value) == 1
    assert await fifo_env.fifo.read.dequeue() is None
