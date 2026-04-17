"""
测试 Phase 2: lcn_pointers 字段支持
"""

import pytest
from diting.mft import MFT


def create_fresh_mft():
    """创建新的 MFT 实例（独立内存数据库）"""
    import random
    import time
    # 使用唯一标识确保每个测试独立
    db_id = f"memdb_lcn_{int(time.time()*1000)}_{random.randint(0, 10000)}"
    return MFT(db_path=f"file:{db_id}?mode=memory&cache=private")


class TestLCNPointers:
    """测试 lcn_pointers 字段功能"""

    def test_set_and_get_lcn_pointers(self):
        """测试设置和获取切片指针"""
        mft = create_fresh_mft()
        try:
            # 创建记忆
            mft.create("/test/doc", "NOTE", "测试文档")

            # 设置切片指针
            pointers = [
                {"chunk_id": 1, "offset": 0, "length": 500},
                {"chunk_id": 2, "offset": 500, "length": 500},
                {"chunk_id": 3, "offset": 1000, "length": 200},
            ]
            assert mft.set_lcn_pointers("/test/doc", pointers) is True

            # 获取切片指针
            retrieved = mft.get_lcn_pointers("/test/doc")
            assert retrieved == pointers
            assert len(retrieved) == 3
        finally:
            mft.close()

    def test_get_lcn_pointers_nonexistent(self):
        """测试获取不存在的记忆的切片指针"""
        mft = create_fresh_mft()
        try:
            assert mft.get_lcn_pointers("/nonexistent") is None
        finally:
            mft.close()

    def test_get_lcn_pointers_deleted(self):
        """测试获取已删除记忆的切片指针"""
        mft = create_fresh_mft()
        try:
            # 创建并删除
            mft.create("/test/doc", "NOTE", "测试文档")
            pointers = [{"chunk_id": 1, "offset": 0, "length": 500}]
            mft.set_lcn_pointers("/test/doc", pointers)
            mft.delete("/test/doc")

            # 已删除的记忆不应返回指针
            assert mft.get_lcn_pointers("/test/doc") is None
        finally:
            mft.close()

    def test_has_slices(self):
        """测试 has_slices 方法"""
        mft = create_fresh_mft()
        try:
            mft.create("/test/doc", "NOTE", "测试文档")

            # 初始无切片
            assert mft.has_slices("/test/doc") is False

            # 设置切片后
            pointers = [{"chunk_id": 1, "offset": 0, "length": 500}]
            mft.set_lcn_pointers("/test/doc", pointers)
            assert mft.has_slices("/test/doc") is True
        finally:
            mft.close()

    def test_empty_pointers(self):
        """测试空指针列表"""
        mft = create_fresh_mft()
        try:
            mft.create("/test/doc", "NOTE", "测试文档")

            # 设置空指针列表
            mft.set_lcn_pointers("/test/doc", [])
            assert mft.has_slices("/test/doc") is False
        finally:
            mft.close()

    def test_update_lcn_pointers(self):
        """测试更新切片指针"""
        mft = create_fresh_mft()
        try:
            mft.create("/test/doc", "NOTE", "测试文档")

            # 初始指针
            pointers_v1 = [{"chunk_id": 1, "offset": 0, "length": 500}]
            mft.set_lcn_pointers("/test/doc", pointers_v1)

            # 更新指针
            pointers_v2 = [
                {"chunk_id": 1, "offset": 0, "length": 300},
                {"chunk_id": 2, "offset": 300, "length": 300},
            ]
            mft.set_lcn_pointers("/test/doc", pointers_v2)

            # 验证更新
            retrieved = mft.get_lcn_pointers("/test/doc")
            assert retrieved == pointers_v2
            assert len(retrieved) == 2
        finally:
            mft.close()

    def test_multiple_paths(self):
        """测试多个路径的切片指针独立"""
        mft = create_fresh_mft()
        try:
            # 创建多个记忆
            mft.create("/test/doc1", "NOTE", "文档 1")
            mft.create("/test/doc2", "NOTE", "文档 2")

            # 设置不同的切片指针
            mft.set_lcn_pointers("/test/doc1", [{"chunk_id": 1, "offset": 0, "length": 500}])
            mft.set_lcn_pointers("/test/doc2", [
                {"chunk_id": 2, "offset": 0, "length": 300},
                {"chunk_id": 3, "offset": 300, "length": 300},
            ])

            # 验证独立
            pointers1 = mft.get_lcn_pointers("/test/doc1")
            pointers2 = mft.get_lcn_pointers("/test/doc2")
            assert len(pointers1) == 1
            assert len(pointers2) == 2
            assert pointers1[0]["chunk_id"] == 1
            assert pointers2[0]["chunk_id"] == 2
        finally:
            mft.close()
