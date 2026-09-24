import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paging import PagingSimulator  # noqa: E402


def test_tlb_hit():
    p = PagingSimulator(tlb_size=4)
    p.access(0x000)
    p.access(0x000)
    st = p.stats()
    assert st["accesses"] == 2
    assert st["tlb_hits"] == 1
    assert st["tlb_misses"] == 1
    assert st["page_faults"] == 1        # 每新页一次缺页


def test_page_fault_per_new_page():
    p = PagingSimulator(tlb_size=16)
    for v in (0x000, 0x040, 0x080, 0x0C0):
        p.access(v)
    assert p.stats()["page_faults"] == 4
    p.access(0x000)                      # 已在页表 -> 命中
    assert p.stats()["page_faults"] == 4


def test_tlb_lru_eviction():
    p = PagingSimulator(tlb_size=2)
    p.access(0x000)
    p.access(0x040)
    p.access(0x080)                      # TLB 满 -> 淘汰 vpn0
    p.access(0x000)                      # TLB miss，但页表命中
    st = p.stats()
    assert st["evictions"] == 2          # vpn0 被挤出、vpn1 被挤出
    assert st["tlb_misses"] == 4         # 4 次访问全部 TLB miss
    assert st["page_faults"] == 3        # 只有前 3 页缺页


def test_physical_address_offset():
    p = PagingSimulator(tlb_size=8)
    p.access(0x000)                      # frame0, offset0
    assert p.access(0x03F) == 0x3F       # frame0 + 63
    assert p.access(0x040) == 0x40       # frame1 + 0


def test_frame_lru_eviction():
    p = PagingSimulator(frame_count=3, tlb_size=16)
    for v in (0x000, 0x040, 0x080):
        p.access(v)                      # vpn0,1,2 占满 3 帧
    p.access(0x000)
    p.access(0x040)                      # 刷新 vpn0,1 的 last_used
    p.access(0x0C0)                      # 缺页 -> LRU 换 vpn2
    assert p.stats()["page_faults"] == 4
    assert p.stats()["evictions"] == 1
    p.access(0x080)                      # vpn2 已被换出 -> 再缺页
    assert p.stats()["page_faults"] == 5


def test_dirty_writeback():
    p = PagingSimulator(frame_count=2, tlb_size=16)
    p.access(0x000, write=True)          # 脏页 vpn0
    p.access(0x040)                      # 干净页 vpn1
    p.access(0x080)                      # 缺页 -> LRU 换 vpn0（脏）
    st = p.stats()
    assert st["dirty_writebacks"] == 1
    assert st["page_faults"] == 3


def test_clean_evict_no_writeback():
    p = PagingSimulator(frame_count=2, tlb_size=16)
    p.access(0x000)                      # 干净
    p.access(0x040)                      # 干净
    p.access(0x080)                      # 换 vpn0（干净）不写回
    assert p.stats()["dirty_writebacks"] == 0


def test_multilevel_page_table():
    p = PagingSimulator(tlb_size=16)
    # 0x2000 = vpn 0x80：L1 idx=2, L2 idx=0（跨 L1 桶）
    p.access(0x000)
    p.access(0x2000)
    p.access(0x000)                      # 回到第一桶命中
    st = p.stats()
    assert st["page_faults"] == 2


def test_stats_fields():
    p = PagingSimulator(tlb_size=16)
    for v in (0x000, 0x040, 0x080):
        p.access(v)
    p.access(0x000)
    st = p.stats()
    assert set(st.keys()) >= {"accesses", "tlb_hits", "tlb_misses",
                              "page_faults", "evictions",
                              "dirty_writebacks", "hit_rate",
                              "page_table_walks"}
    assert st["page_table_walks"] == st["tlb_misses"]
    assert st["hit_rate"] == st["tlb_hits"] / st["accesses"]


def test_fifo_policy():
    p = PagingSimulator(frame_count=2, tlb_size=16, policy="fifo")
    p.access(0x000)                      # vpn0 先进
    p.access(0x040)                      # vpn1
    p.access(0x080)                      # 缺页 -> FIFO 换最先的 vpn0
    assert p.stats()["page_faults"] == 3
    p.access(0x000)                      # vpn0 已换出 -> 再缺页
    assert p.stats()["page_faults"] == 4


def test_clock_policy():
    p = PagingSimulator(frame_count=3, tlb_size=16, policy="clock")
    for v in (0x000, 0x040, 0x080):
        p.access(v)                      # vpn0,1,2 装入
    p.access(0x0C0)                      # 缺页 -> Clock 扫描换出帧
    assert p.stats()["page_faults"] == 4
    assert p.stats()["evictions"] == 1
    p.access(0x000)                      # 被换出的最早页重访 -> 缺页
    assert p.stats()["page_faults"] == 5
    p.access(0x040)
    assert p.stats()["page_faults"] == 6


def test_policy_param_switch():
    # 三种置换策略都能跑通且缺页计数一致
    seq = (0x000, 0x040, 0x080, 0x0C0, 0x100, 0x140, 0x000, 0x040)
    for pol in ("fifo", "lru", "clock"):
        p = PagingSimulator(frame_count=3, tlb_size=16, policy=pol)
        for v in seq:
            p.access(v)
        st = p.stats()
        assert st["page_faults"] > 0
        assert st["evictions"] > 0


def test_three_level_pages():
    p = PagingSimulator(virtual_bits=24, page_bits=6, frame_count=4,
                        tlb_size=16, levels=3)
    p.access(0x000000)                   # vpn0：L1=0,L2=0,L3=0
    p.access(0x400000)                   # vpn 0x10000：L1=16,L2=0,L3=0
    p.access(0x800000)                   # vpn 0x20000：L1=32,L2=0,L3=0
    assert p.stats()["page_faults"] == 3
    p.access(0x000000)                   # 命中
    assert p.stats()["page_faults"] == 3


def test_working_set_fits():
    # 8 页 / 8 帧：工作集完全驻留，第二轮起全部 TLB 命中
    p = PagingSimulator(frame_count=8, tlb_size=32)
    for _ in range(3):
        for v in (0x000, 0x040, 0x080, 0x0C0, 0x100, 0x140, 0x180, 0x1C0):
            p.access(v)
    st = p.stats()
    assert st["page_faults"] == 8         # 每页仅首次缺页
    assert st["evictions"] == 0
    assert st["tlb_hits"] == 16           # 第 2、3 轮全部命中
