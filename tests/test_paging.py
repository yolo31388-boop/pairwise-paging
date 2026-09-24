import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paging import PagingSimulator  # noqa: E402


def test_tlb_hit():
    p = PagingSimulator()
    p.access(0x100)            # vpn=4
    p.access(0x130)            # 同页（偏移 0x30）
    st = p.stats()
    assert st["tlb_hits"] == 1
    assert st["page_faults"] == 1


def test_page_fault_per_new_page():
    p = PagingSimulator()
    p.access(0x000)
    p.access(0x040)            # vpn=1
    p.access(0x100)            # vpn=4
    assert p.stats()["page_faults"] == 3
    assert p.stats()["accesses"] == 3


def test_tlb_lru_eviction():
    p = PagingSimulator(tlb_size=2)
    p.access(0x000)            # vpn0 -> TLB
    p.access(0x040)            # vpn1 -> TLB
    p.access(0x080)            # vpn2 -> 淘汰 vpn0
    p.access(0x000)            # vpn0 不在 TLB -> miss（页表仍 present）
    st = p.stats()
    assert st["tlb_hits"] == 0
    assert st["evictions"] == 2      # vpn0、vpn1 各被淘汰一次
    assert st["page_faults"] == 3   # vpn0 页表还在，不再缺页


def test_physical_address_offset():
    p = PagingSimulator()
    pa1 = p.access(0x010)
    pa2 = p.access(0x130)      # 同页不同偏移
    assert pa1 == 0x10         # frame0*64 + 0x10
    assert pa2 == 0x30 + 64    # frame0*64 + 0x30


def test_frame_eviction_lru():
    p = PagingSimulator(frame_count=4, tlb_size=8)
    for v in range(0x000, 0x140, 0x40):   # 5 个不同页
        p.access(v)
    st = p.stats()
    assert st["page_faults"] == 5
    assert st["evictions"] == 1           # 第 5 页挤掉最早页
    # LRU 被置换的是 vpn0
    p.access(0x000)
    assert p.stats()["page_faults"] == 6  # vpn0 已被逐出，重新缺页


def test_dirty_writeback():
    p = PagingSimulator(frame_count=2, tlb_size=4)
    p.access(0x000, write=True)   # vpn0 写脏
    p.access(0x040)               # vpn1
    p.access(0x080)               # 缺帧 -> 置换 vpn0（脏）-> 写回
    st = p.stats()
    assert st["dirty_writebacks"] == 1
    assert st["evictions"] == 1


def test_clean_eviction_no_writeback():
    p = PagingSimulator(frame_count=2, tlb_size=4)
    p.access(0x000)               # vpn0 只读，干净
    p.access(0x040)
    p.access(0x080)               # 置换 vpn0（干净）-> 不写回
    assert p.stats()["dirty_writebacks"] == 0


def test_multilevel_page_table():
    # vpn 跨越 L1 高位：0x000(vpn0) 与 0x2000(vpn128, l1=4)
    p = PagingSimulator()
    p.access(0x000)
    p.access(0x2000)
    p.access(0x2000)              # 命中 TLB
    st = p.stats()
    assert st["page_faults"] == 2
    assert st["tlb_hits"] == 1
    assert len(p.l1) >= 2         # 两级页表都建了


def test_stats_fields():
    p = PagingSimulator()
    p.access(0x000)
    st = p.stats()
    assert set(st.keys()) >= {"accesses", "tlb_hits", "tlb_misses",
                              "page_faults", "evictions",
                              "dirty_writebacks"}
    assert st["accesses"] == 1
    assert st["tlb_misses"] == 1
