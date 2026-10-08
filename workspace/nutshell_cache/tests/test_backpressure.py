from toffee_test import case
from base_test import *
import random


@case
async def test_memory_backpressure_and_slow_refill(start_func):
    """娑撳鐖?backpressure閿涙矮姹夋稉鍝勬鏉?ready/valid閿涘本顥呴弻?refill 閸欘垱娈忛崑婊冭嫙濮濓絿鈥橀幁銏狀槻閵?
    濠碘偓閸旀唻绱板鎯扮箿 memory request ready閵嗕购esponse valid閿涘苯鑻熼崷?burst 娑擃參妫块幓鎺戝弳閸嬫粓銆戦敍娑樻倱閺冭泛娆㈡潻?CPU response ready閵?    濡偓閺屻儻绱伴張鈧紒鍫ｎ嚢閺佺増宓佸锝団€橀敍瀹恊at 娑撳秳娑径渚库偓浣风瑝闁插秴顦查妴浣风瑝娑斿崬绨敍灞肩瘍娑撳秵顒撮柨浣碘偓?    鐟曞棛娲婇惄顔界垼閿涙eady/valid 閹烩剝澧滈妴涔rst counter閵嗕笚SM wait 閻樿埖鈧降鈧?    """
    env: NtCacheEnv = await start_func(start_cpu_response_handler=False)
    env.mem_agent.response_valid_delay = 2
    env.mem_agent.response_beat_delay = 1
    env.mem_agent.response_stall_after = 3
    env.mem_agent.response_stall_cycles = 5

    # The current cache couples CPU request acceptance to downstream ready.
    # Let the miss reach the backing-memory boundary with ready high, then
    # withhold response-ready before the refill can complete.
    reads_before = len(env.mem_ram.read_requests)
    env.cpu.bundle.rsp.ready.value = 1
    await env.cpu.send_req(0x6000, 7, CMD_READ)
    for _ in range(1000):
        if len(env.mem_ram.read_requests) > reads_before:
            break
        await env.cpu.bundle.step()
    assert len(env.mem_ram.read_requests) > reads_before, "miss did not reach backing memory"
    # Withhold ready after the response has time to arrive; the DUT must keep
    # valid and payload stable until this explicit sink accepts the beat.
    response = await env.cpu.get_resp(response_ready_delay=5000)
    assert response["cmd"] == CMD_READLST
    assert response["rdata"] == 0
    assert env.mem_ram.read_requests
    assert env.cpu.protocol_checker.stall_cycles_by_channel.get("rsp", 0) >= 4
