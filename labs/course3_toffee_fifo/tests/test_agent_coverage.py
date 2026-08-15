from toffee_test import case


@case
async def test_agent_reference_and_functional_coverage(fifo_env):
    """任务 2 第 3--5 步：Agent + Model + Executor + 全部覆盖点。"""
    fifo = fifo_env.fifo
    await fifo.reset()
    await fifo.idle()
    assert await fifo.dequeue() is None  # empty 时非法读

    assert await fifo.enqueue(0x100)
    concurrent = await fifo.enqueue_dequeue(0x200)
    # Executor 按调度组名返回结果；读、写在同一个时钟周期完成。
    assert concurrent["write"] is True
    assert concurrent["read"] == 0x100
    assert await fifo.dequeue() == 0x200

    await fifo.reset()
    expected = [0x400 + index for index in range(16)]
    for data in expected:
        assert await fifo.enqueue(data)
    assert int(fifo.write.full_o.value) == 1
    assert not await fifo.enqueue(0xDEAD)  # full 时非法写

    actual = [await fifo.dequeue() for _ in expected]
    assert actual == expected
    assert int(fifo.read.empty_o.value) == 1
    fifo_env.coverage.record("data_match")
    assert fifo_env.coverage.is_complete()
