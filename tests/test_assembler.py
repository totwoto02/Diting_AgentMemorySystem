"""
测试自动还原器
"""

import pytest
from diting.mft import MFT
from diting.assembler import Assembler


class TestAssembler:
    """测试 Assembler"""

    def create_fresh_mft(self):
        """创建新的 MFT 实例（独立内存数据库）"""
        import random
        import time
        db_id = f"memdb_asm_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        return MFT(db_path=f"file:{db_id}?mode=memory&cache=private")

    def test_assemble_no_slices(self):
        """测试无切片情况（直接返回原文）"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            mft.create("/test/doc", "NOTE", "完整原文内容")
            result = assembler.assemble("/test/doc")
            assert result == "完整原文内容"
        finally:
            mft.close()

    def test_assemble_with_slices(self):
        """测试有切片情况"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            full_text = "这是一段测试文本" * 100
            mft.create("/test/doc", "NOTE", full_text)
            pointers = [
                {"chunk_id": 1, "offset": 0, "length": 500},
                {"chunk_id": 2, "offset": 500, "length": 500},
            ]
            mft.set_lcn_pointers("/test/doc", pointers)
            result = assembler.assemble("/test/doc")
            assert result == full_text
        finally:
            mft.close()

    def test_assemble_nonexistent(self):
        """测试不存在的记忆"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            result = assembler.assemble("/nonexistent")
            assert result is None
        finally:
            mft.close()

    def test_assemble_from_pointers(self):
        """测试从指针还原"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            full_text = "A" * 1000
            pointers = [
                {"chunk_id": 1, "offset": 0, "length": 500},
                {"chunk_id": 2, "offset": 500, "length": 500},
            ]
            
            result = assembler.assemble_from_pointers(pointers, full_text)
            
            assert result == full_text
        finally:
            mft.close()

    def test_verify_assembly(self):
        """测试验证拼装结果"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            assembled = "测试文本"
            expected = "测试文本"
            
            assert assembler.verify_assembly(assembled, expected) is True
            
            wrong = "错误文本"
            assert assembler.verify_assembly(assembled, wrong) is False
        finally:
            mft.close()

    def test_assembly_stats(self):
        """测试拼装统计"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            pointers = [
                {"chunk_id": 1, "offset": 0, "length": 500},
                {"chunk_id": 2, "offset": 500, "length": 500},
                {"chunk_id": 3, "offset": 1000, "length": 200},
            ]
            
            stats = assembler.get_assembly_stats(pointers)
            
            assert stats["chunk_count"] == 3
            assert stats["total_length"] == 1200
            assert stats["avg_chunk_size"] == 400
        finally:
            mft.close()

    def test_assembly_stats_empty(self):
        """测试空指针统计"""
        mft = self.create_fresh_mft()
        try:
            assembler = Assembler(mft)
            stats = assembler.get_assembly_stats([])
            
            assert stats["chunk_count"] == 0
            assert stats["total_length"] == 0
        finally:
            mft.close()
