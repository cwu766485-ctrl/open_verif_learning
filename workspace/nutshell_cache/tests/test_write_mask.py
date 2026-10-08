from toffee_test import case
from base_test import *
import random


@case
async def test_write_read_and_byte_mask(start_func):
    """閸愭瑥鎳℃稉顓濈瑢鐎涙濡幒鈺冪垳閿涙艾鍘涢崑姘弿鐎涙鍟撻敍灞藉晙閸欘亝娲块弬鐗堟付娴?byte閿涘本娓堕崥搴ゎ嚢閸ョ偛鎮庨獮鍓佺波閺嬫嚎鈧?
    濠碘偓閸旀唻绱癴ull write -> read -> mask=0x01 閻ㄥ嫰鍎撮崚鍡楀晸 -> read閵?    濡偓閺屻儻绱伴崘娆忔惙鎼存棁绻戦崶鐐存＋閸婅壈顕㈡稊澶涚礉閺堫亪鈧鑵戦惃?byte 娣囨繃瀵旀稉宥呭綁閵?    鐟曞棛娲婇惄顔界垼閿涙rite hit閵嗕攻yte mask merge閵嗕龚irty bit閵嗕龚ata array 閸愭瑥鍙嗛妴?    """
    env: NtCacheEnv = await start_func()
    addr = 0x1800
    original = 0x1122334455667788
    updated = 0x11223344556677AA

    write_rsp = await env.in_agent.block_write(addr, original, 0xFF)
    assert write_rsp["bits_cmd"] == CMD_WRITERSP
    assert await env.in_agent.block_read(addr) == {
        "valid": True,
        "bits_rdata": original,
        "bits_cmd": CMD_READLST,
    }

    masked_rsp = await env.in_agent.block_write(addr, 0xAA, 0x01)
    assert masked_rsp["bits_cmd"] == CMD_WRITERSP
    read_rsp = await env.in_agent.block_read(addr)
    assert read_rsp["bits_rdata"] == updated
