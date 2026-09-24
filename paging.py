"""虚拟内存分页模拟器（多级页表 + TLB + 可插拔置换策略）。

模型：
- 虚拟地址 virtual_bits 位；页大小 2**page_bits；页号按 levels
  级均分（levels=2 每级 5 位，levels=3 每级 6 位）。
- 页表按需建立：根 dict -> 逐级 dict -> {frame, dirty}。
- TLB（tlb_size 条，LRU）：vpn -> frame，命中免查页表。
- 置换策略 policy：'fifo'（分配顺序）、'lru'（最久未用）、
  'clock'（引用位 + 时钟扫描）；无空闲帧时换帧，脏页写回。
- 统计：accesses/tlb_hits/tlb_misses/page_faults/evictions/
  dirty_writebacks/hit_rate/page_table_walks。
"""
from __future__ import annotations


class PagingSimulator:
    def __init__(self, virtual_bits: int = 16, page_bits: int = 6,
                 frame_count: int = 8, tlb_size: int = 4,
                 levels: int = 2, policy: str = "lru"):
        self.virtual_bits = virtual_bits
        self.page_bits = page_bits
        self.page_size = 1 << page_bits
        self.frame_count = frame_count
        self.tlb_size = tlb_size
        self.levels = levels
        self.policy = policy
        # 页表根：逐级 dict，最后一级存 {"frame","dirty"}
        self.pt: dict = {}
        # 帧表：frame -> {"vpn": int, "dirty": bool, "ref": bool}
        self.frames: dict = {}
        self.free_frames: list = list(range(frame_count))
        # TLB：vpn -> frame（LRU 序）
        self.tlb: dict = {}
        self._tick = 0
        self._last_used: dict = {}
        self._fifo_order: list = []
        self._clock_hand = 0
        # 统计
        self.accesses = 0
        self.tlb_hits = 0
        self.page_faults = 0
        self.evictions = 0
        self.dirty_writebacks = 0

    # -------------------------------------------------- 接口
    def access(self, vaddr: int, write: bool = False) -> int:
        """访问虚拟地址（读/写），返回物理地址。"""
        raise NotImplementedError

    def stats(self) -> dict:
        """返回全部统计字段（含 hit_rate、page_table_walks）。"""
        raise NotImplementedError
