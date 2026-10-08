from toffee_test import case
from base_test import *
import random


@case
async def test_mmio_isolated_from_cache_memory(start_func):
    """MMIO 閺冧浇鐭鹃敍姘愁啎婢跺洤婀撮崸鈧挧?MMIO 缁旑垰褰涢敍灞肩瑝閼宠姤钖勯弻鎾存珮闁?cache memory閵?
    濠碘偓閸旀唻绱扮€?0x3000_0000 閸栧搫鐓欓幍褑顢戦崘娆忔倵鐠囨眹鈧?    濡偓閺屻儻绱癕MIO 閺堝顕Ч鍌樷偓浣规珮闁?memory 濞屸剝婀侀弬鏉款杻鐠囬攱鐪伴敍宀冾嚢閸ョ偛鍨伴崘娆忓弳閻ㄥ嫭鏆熼幑顔衡偓?    鐟曞棛娲婇惄顔界垼閿涙瓉MIO 閸︽澘娼冪拠鎴犵垳閵嗕府MIO request/response閵嗕恭ache bypass閵?    """
    env: NtCacheEnv = await start_func()
    addr = 0x30000000
    mem_before = len(env.mem_ram.requests)
    mmio_before = len(env.mmio_ram.requests)

    write_rsp = await env.in_agent.block_write(addr, 0xCAFE, 0xFF)
    read_rsp = await env.in_agent.block_read(addr)

    assert write_rsp["bits_cmd"] == CMD_WRITERSP
    assert read_rsp["bits_cmd"] == CMD_READLST
    assert read_rsp["bits_rdata"] == 0xCAFE
    assert len(env.mmio_ram.requests) > mmio_before
    assert len(env.mem_ram.requests) == mem_before
