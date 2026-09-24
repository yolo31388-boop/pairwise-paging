# Pair-wise GSB 基线：虚拟内存分页模拟器

题目（feature 迭代）：实现二级页表 + TLB + LRU 置换的虚拟内存分页模拟器。

- 骨架：`paging.py`（PagingSimulator 方法均 `raise NotImplementedError`）
- 验收：`python -m pytest tests/test_paging.py -q` 全绿
- 约束：只 import 标准库；页表、TLB、置换、dirty 写回必须真实实现
