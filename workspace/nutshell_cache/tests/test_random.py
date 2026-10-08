from toffee_test import case
from base_test import *
import random
import os


@case
async def test_long_randomized_mixed_sequence(start_func):
    """閸ュ搫鐣剧粔宥呯摍閻?128 缁楁棃鏆遍梾蹇旀簚鎼村繐鍨敍姘辨偅閸氬牐顩惄鏍у暱缁愪降鈧焦娴涢幑顫偓浣瑰负閻礁鎷扮拠璇插晸濞ｅ嘲鎮庨妴?
    濠碘偓閸旀唻绱伴崷銊ヮ樋娑?line/set 娑撳﹪娈㈤張娲偓澶嬪 word閵嗕浇顕伴崘娆戣閸ㄥ鎷?byte mask閵?    濡偓閺屻儻绱板В蹇曠應娴滃濮熼柈鎴掔瑢 shadow model 鐎佃鐦敍灞惧瘮缂侇厽顥呴弻銉╂毐閺堢喓濮搁幀浣风閼峰瓨鈧佲偓?    鐟曞棛娲婇惄顔界垼閿涙岸鏆辨惔蹇撳灙閻樿埖鈧胶鐤粔顖樷偓浣稿暱缁愪焦娴涢幑顫偓涔╥rty line閵嗕線娈㈤張?byte mask閵?    """
    env: NtCacheEnv = await start_func()
    seeds = (
        0x20260908, 0x5EED, 0xC0FFEE,
        0xDEADBEEF, 0xBAD5EED, 0x13579BDF,
    )
    extra_seeds = os.getenv("NUTSHELL_RANDOM_SEEDS", "")
    if extra_seeds.strip():
        seeds += tuple(int(value.strip(), 0) for value in extra_seeds.split(",") if value.strip())
    for seed_index, seed in enumerate(seeds):
        rng = random.Random(seed)
        shadow = {}
        base = 0xA000 + seed_index * 0x10000

        for _ in range(64):
            line = rng.randrange(24)
            word = rng.randrange(8)
            addr = base + line * 0x40 + word * 8
            aligned = addr & ~0x7
            if rng.randrange(2):
                data = rng.getrandbits(64)
                mask = rng.randrange(1, 0x100)
                old_data = shadow.get(aligned, 0)
                response = await env.in_agent.block_write(addr, data, mask)
                assert response["bits_cmd"] == CMD_WRITERSP, f"seed=0x{seed:x} addr=0x{addr:x}"
                assert response["bits_rdata"] == old_data, f"seed=0x{seed:x} addr=0x{addr:x}"
                byte_mask = sum(
                    0xFF << (8 * byte) for byte in range(8) if mask & (1 << byte)
                )
                shadow[aligned] = (old_data & ~byte_mask) | (data & byte_mask)
            else:
                response = await env.in_agent.block_read(addr)
                assert response["bits_cmd"] == CMD_READLST, f"seed=0x{seed:x} addr=0x{addr:x}"
                assert response["bits_rdata"] == shadow.get(aligned, 0), f"seed=0x{seed:x} addr=0x{addr:x}"

@case
async def test_deterministic_mixed_sequence(start_func):
    """閸ュ搫鐣剧粔宥呯摍閻?64 缁楁梹璐╅崥鍫ｎ嚢閸愭瑱绱伴悽?shadow/reference model 濡偓閺屻儳濮搁幀浣圭川鏉╂稏鈧?
    濠碘偓閸旀唻绱伴崶鍝勭暰闂呭繑婧€缁夊秴鐡欐禍褏鏁撴径姘辩矋鐠囨眹鈧礁鍟撻崪宀勬閺?byte mask閵?    濡偓閺屻儻绱板В蹇旑偧鐠囩粯鏆熼幑顔衡偓浣稿晸閸濆秴绨查弮褍鈧ジ鍏樻稉?Python shadow model 娑撯偓閼锋番鈧?    鐟曞棛娲婇惄顔界垼閿涙俺顕伴崘娆庢唉閺囪￥鈧椒绗夐崥?word閵嗕線鍎撮崚鍡楀晸閵嗕礁鎳℃稉?缂傚搫銇戦悩鑸碘偓浣芥祮閹诡潿鈧?    """
    env: NtCacheEnv = await start_func()
    rng = random.Random(0xCAFE)
    shadow = {}

    for _ in range(64):
        line = rng.randrange(8)
        word = rng.randrange(8)
        addr = 0x4000 + line * 0x40 + word * 8
        if rng.randrange(2):
            data = rng.getrandbits(64)
            mask = rng.randrange(1, 0x100)
            old_data = shadow.get(addr & ~0x7, 0)
            response = await env.in_agent.block_write(addr, data, mask)
            assert response["bits_cmd"] == CMD_WRITERSP
            assert response["bits_rdata"] == old_data
            byte_mask = sum(
                0xFF << (8 * byte) for byte in range(8) if mask & (1 << byte)
            )
            shadow[addr & ~0x7] = (old_data & ~byte_mask) | (data & byte_mask)
        else:
            response = await env.in_agent.block_read(addr)
            assert response["bits_cmd"] == CMD_READLST
            assert response["bits_rdata"] == shadow.get(addr & ~0x7, 0)
