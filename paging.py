"""虚拟内存分页模拟器（二级页表 + TLB + LRU 置换）。

模型：
- 虚拟地址 virtual_bits 位（默认 16），页大小 2**page_bits 字节
  （默认 6 位 = 64B）。
- 页号拆两级：L1 索引（高 5 位）+ L2 索引（低 5 位），
  页内偏移为最低 page_bits 位。
- 物理内存 frame_count 帧（每帧一页）；页表按需建立
  （L1 -> L2 -> {frame, dirty}），缺页时分配帧，无空闲帧按 LRU
  置换；被置换页若 dirty 需写回（dirty_writebacks 计数）。
- TLB（tlb_size 条，LRU）：vpn -> frame，命中免查页表；
  满时淘汰最久未用条目（evictions 计数）。
"""
from __future__ import annotations


class PagingSimulator:
    def __init__(self, virtual_bits: int = 16, page_bits: int = 6,
                 frame_count: int = 8, tlb_size: int = 4):
        self.virtual_bits = virtual_bits
        self.page_bits = page_bits
        self.page_size = 1 << page_bits
        self.frame_count = frame_count
        self.tlb_size = tlb_size
        # 页表：l1[l1_idx] = {l2: {l2_idx: {"frame": f, "dirty": bool}}}
        self.l1: dict = {}
        # 帧表：frame -> {"vpn": int, "dirty": bool}
        self.frames: dict = {}
        self.free_frames: list = list(range(frame_count))
        # TLB：OrderedDict vpn -> frame
        self.tlb: dict = {}
        self._tick = 0
        self._last_used: dict = {}
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
        """返回 {accesses, tlb_hits, tlb_misses, page_faults,
        evictions, dirty_writebacks}。"""
        raise NotImplementedError
