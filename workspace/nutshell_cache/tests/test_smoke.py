from toffee_test import case
from base_test import *
import random

@case
async def test_smoke(start_func):
    """閸╄櫣顢呴崘鎺斿劔娑撳骸鎼锋惔鏃堛€庢惔蹇ョ窗妤犲矁鐦夐張鈧亸蹇氼嚢閸愭瑦绁︾粙瀣嫲鏉╃偟鐢婚棃鐐烘▎婵夌偠顕Ч鍌樷偓?
    濠碘偓閸旀唻绱伴崘鐤嚢閸︽澘娼?0x1閵嗕礁鍟撻崶鐐叉倱閸︽澘娼冮敍宀€鍔ч崥搴ょ箾缂侇厼褰傞柅浣疯⒈娑?non-blocking read閵?    濡偓閺屻儻绱扮拠?閸愭瑥鎼锋惔鏂挎嚒娴犮倖顒滅涵顕嗙礉娑撱倓閲滈崫宥呯安閹稿顕Ч鍌炪€庢惔蹇氱箲閸ョ偑鈧?    鐟曞棛娲婇惄顔界垼閿涙艾鐔€閺?ready/valid閵嗕竼PU response channel閵嗕浇绻涚紒顓☆嚞濮瑰倹甯撻梼鐔粹偓?    """
    env: NtCacheEnv = await start_func()

    first_read = await env.in_agent.block_read(0x1)
    assert first_read["bits_cmd"] == CMD_READLST
    assert first_read["bits_rdata"] == 0

    write_rsp = await env.in_agent.block_write(0x1, 0x1, 0x1)
    assert write_rsp["bits_cmd"] == CMD_WRITERSP

    await env.in_agent.non_block_read(0x1)
    await env.in_agent.non_block_read(0x2)

    first = await env.in_agent.recv()
    second = await env.in_agent.recv()
    assert first["bits_cmd"] == CMD_READLST
    assert second["bits_cmd"] == CMD_READLST
