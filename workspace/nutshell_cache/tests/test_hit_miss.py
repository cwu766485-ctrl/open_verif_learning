from toffee_test import case
from base_test import *
import random


@case
async def test_cross_cache_line_access(start_func):
    """鐠?line 鏉堝湱鏅敍姘瀻閸掝偉顔栭梻顔荤瑐娑撯偓閺?line 閻ㄥ嫭娓堕崥搴濈娑?word 閸滃奔绗呮稉鈧弶?line 閻ㄥ嫮顑囨稉鈧稉?word閵?
    濠碘偓閸旀唻绱扮拋鍧楁６ 0x83F8 娑?0x8400閿涘矁绻栨稉銈勯嚋閸︽澘娼冮幁鏉裤偨鐠恒劏绉?64B line 鏉堝湱鏅妴?    濡偓閺屻儻绱版稉銈嗘蒋 line 閻ㄥ嫭鏆熼幑顔惧缁斿绱濋崷鏉挎絻娴ｅ簼缍呴崚鍥у瀻娑撳秳绱版稉鑼殠閵?    鐟曞棛娲婇惄顔界垼閿涙ine offset 鏉堝湱鏅妴涔籩t/tag 闁插秵鏌婄拋锛勭暬閵嗕胶娴夐柇?line refill閵?    """
    env: NtCacheEnv = await start_func()
    first_addr = 0x83F8
    second_addr = 0x8400
    first_data = 0x1111222233334444
    second_data = 0xAAAABBBBCCCCDDDD

    await env.in_agent.block_write(first_addr, first_data, 0xFF)
    await env.in_agent.block_write(second_addr, second_data, 0xFF)

    assert (await env.in_agent.block_read(first_addr))["bits_rdata"] == first_data
    assert (await env.in_agent.block_read(second_addr))["bits_rdata"] == second_data



@case
async def test_read_miss_then_hit(start_func):
    """鐠囪崵宸辨径鍗炴倵閸涙垝鑵戦敍姘鳖儑娑撯偓濞喡ゎ嚢鐟欙箑褰傞弫瀛樻蒋 cache line refill閿涘瞼顑囨禍灞绢偧鐠囪鎳℃稉顓犵处鐎涙ǜ鈧?
    濠碘偓閸旀唻绱版潻鐐电敾娑撱倖顐肩拋鍧楁６閸氬奔绔存稉顏勬勾閸р偓閵?    濡偓閺屻儻绱扮粭顑跨濞嗭紕鈥樼€圭偠顔栭梻?backing memory閿涙稓顑囨禍灞绢偧鏉╂柨娲栭惄绋挎倱閺佺増宓佹稉鏂剧瑝閸愬秷顔栭梻?memory閵?    鐟曞棛娲婇惄顔界垼閿涙ag compare閵嗕购ead miss閵?-beat refill閵嗕购ead hit閵?    """
    env: NtCacheEnv = await start_func()
    addr = 0x1000

    first = await env.in_agent.block_read(addr)
    reads_after_miss = len(env.mem_ram.read_requests)
    second = await env.in_agent.block_read(addr)

    assert first["bits_cmd"] == CMD_READLST
    assert second["bits_cmd"] == CMD_READLST
    assert second["bits_rdata"] == first["bits_rdata"]
    assert reads_after_miss > 0, "the cold read must access backing memory"
    assert len(env.mem_ram.read_requests) == reads_after_miss, (
        "a repeated read of the same line should be a cache hit"
    )


@case
async def test_back_to_back_hit_write_then_read_forwarding(start_func):
    """Check same-line data forwarding with queued requests and a stalled sink."""
    env: NtCacheEnv = await start_func()
    addr = 0x3A00
    old_data = 0x0123456789ABCDEF
    new_data = 0xFEDCBA9876543210

    await env.in_agent.block_write(addr, old_data, 0xFF)
    reads_before = len(env.mem_ram.read_requests)
    env.cpu.response_ready_delay = 12
    await env.cpu.non_block_write(addr, new_data, 0xFF)
    await env.cpu.non_block_read(addr)

    write_response = await env.cpu.recv()
    read_response = await env.cpu.recv()
    assert write_response["bits_cmd"] == CMD_WRITERSP
    assert write_response["bits_rdata"] == old_data
    assert read_response["bits_cmd"] == CMD_READLST
    assert read_response["bits_rdata"] == new_data
    assert len(env.mem_ram.read_requests) == reads_before, (
        "queued same-line hit traffic must not issue another refill"
    )
    assert env.testbench.properties.forward_data_cycles > 0, (
        "back-to-back same-word hit traffic must exercise the data forwarding path"
    )


@case
async def test_queued_conflict_misses_preserve_tag_state(start_func):
    """Queue two cold stores to one set and verify both refilled tags/data."""
    env: NtCacheEnv = await start_func()
    addresses = (0x4400, 0x6400)
    values = (0x1111AAAABBBB2222, 0x3333CCCCDDDD4444)

    await env.cpu.non_block_write(addresses[0], values[0], 0xFF)
    await env.cpu.non_block_write(addresses[1], values[1], 0xFF)
    responses = (await env.cpu.recv(), await env.cpu.recv())
    assert [rsp["bits_cmd"] for rsp in responses] == [CMD_WRITERSP, CMD_WRITERSP]
    assert [rsp["bits_rdata"] for rsp in responses] == [0, 0]

    reads_after_refill = len(env.mem_ram.read_requests)
    for addr, expected in zip(addresses, values):
        response = await env.cpu.block_read(addr)
        assert response["bits_rdata"] == expected
    assert len(env.mem_ram.read_requests) == reads_after_refill, (
        "the queued conflicting fills must retain both lines in the 4-way set"
    )



@case
async def test_sequential_words_preserve_order(start_func):
    """閸氬奔绔?cache line 閻?8 娑?word閿涙岸鐛欑拠?line 閸?word index 閸?burst 妞ゅ搫绨妴?
    濠碘偓閸旀唻绱伴崥鎴滅閺?64B line 閻?8 娑?8B word 閸掑棗鍩嗛崘娆忓弳娑撳秴鎮撻崐纭风礉閸愬秹鈧劒閲滅拠璇叉礀閵?    濡偓閺屻儻绱板В蹇庨嚋 word 閻欘剛鐝涙穱婵囧瘮閿涘奔绗夐懗钘夋礈 refill beat 閹存牕婀撮崸鈧幏鍏煎复閼板奔绨伴惄姝岊洬閻╂牓鈧?    鐟曞棛娲婇惄顔界垼閿涙ord index閵?-beat line閵嗕笍ata Array 鐞涘苯鍞寸€佃娼冮妴?    """
    env: NtCacheEnv = await start_func()
    base = 0x2800
    expected = {}

    for index in range(8):
        addr = base + index * 8
        data = 0xA500000000000000 | index
        expected[addr] = data
        response = await env.in_agent.block_write(addr, data, 0xFF)
        assert response["bits_cmd"] == CMD_WRITERSP

    for addr, data in expected.items():
        response = await env.in_agent.block_read(addr)
        assert response["bits_cmd"] == CMD_READLST
        assert response["bits_rdata"] == data
