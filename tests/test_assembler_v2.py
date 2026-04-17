"""
测试拼装还原 V2 模块

测试 AssemblerV2 的核心功能
"""

import pytest
from diting.assembler_v2 import AssemblerV2, Slice


class TestAssemblerV2:
    """测试 AssemblerV2"""

    def create_fresh_assembler(self):
        """创建新的 AssemblerV2 实例"""
        return AssemblerV2(overlap_threshold=0.3, min_overlap=20)

    def test_overlap_deduplication(self):
        """测试重叠去重"""
        assembler = self.create_fresh_assembler()
        
        # 模拟有重叠的切片（内容也有重叠）
        slices = [
            {'content': 'A' * 900 + 'B' * 100, 'offset': 0, 'length': 1000},
            {'content': 'B' * 100 + 'C' * 900, 'offset': 900, 'length': 1000},  # 重叠 100 字 'B'
        ]
        
        full_text, stats = assembler.assemble_with_dedup(slices)
        
        # 验证拼装正确
        assert stats['chunk_count'] == 2
        assert 'A' * 900 in full_text
        assert 'C' * 900 in full_text
        # 重叠部分只出现一次
        assert full_text.count('B' * 50) <= 2

    def test_semantic_coherence_sorting(self):
        """测试语义连贯性（通过 offset 排序）"""
        assembler = self.create_fresh_assembler()
        
        # 乱序的切片
        slices = [
            {'content': '第三部分', 'offset': 2000, 'length': 1000},
            {'content': '第一部分', 'offset': 0, 'length': 1000},
            {'content': '第二部分', 'offset': 1000, 'length': 1000},
        ]
        
        full_text, stats = assembler.assemble_with_dedup(slices)
        
        # 验证按 offset 排序后拼装
        assert '第一部分' in full_text
        assert full_text.index('第一部分') < full_text.index('第二部分')
        assert full_text.index('第二部分') < full_text.index('第三部分')

    def test_lru_cache(self):
        """测试缓存机制（简化版）"""
        assembler = self.create_fresh_assembler()
        
        slices = [
            {'content': '测试内容 1', 'offset': 0, 'length': 10},
            {'content': '测试内容 2', 'offset': 10, 'length': 10},
        ]
        
        # 第一次拼装
        result1, _ = assembler.assemble_with_dedup(slices)
        
        # 第二次拼装（应该使用缓存）
        result2, _ = assembler.assemble_with_dedup(slices)
        
        assert result1 == result2, "相同输入应该产生相同输出"

    def test_parallel_fetch(self):
        """测试并行获取（简化为顺序测试）"""
        assembler = self.create_fresh_assembler()
        
        # 模拟多个切片
        slices = [
            {'content': f'块{i}', 'offset': i * 100, 'length': 100}
            for i in range(5)
        ]
        
        full_text, stats = assembler.assemble_with_dedup(slices)
        
        assert stats['chunk_count'] == 5
        # 验证所有块都在结果中
        for i in range(5):
            assert f'块{i}' in full_text

    def test_coherence_check(self):
        """测试连贯性检查"""
        assembler = self.create_fresh_assembler()
        
        # 正常切片
        slices = [
            {'content': '开头', 'offset': 0, 'length': 10},
            {'content': '中间', 'offset': 10, 'length': 10},
            {'content': '结尾', 'offset': 20, 'length': 10},
        ]
        
        result = assembler.assemble_with_quality(slices)
        
        assert result['is_complete'] is True
        assert result['quality_score'] >= 80

    def test_assemble_with_cache(self):
        """测试带缓存的拼装"""
        assembler = self.create_fresh_assembler()
        
        slices = [
            {'content': '缓存测试 1', 'offset': 0, 'length': 10},
            {'content': '缓存测试 2', 'offset': 10, 'length': 10},
        ]
        
        full_text, stats = assembler.assemble_with_dedup(slices)
        
        assert '缓存测试 1' in full_text
        assert '缓存测试 2' in full_text
        assert stats['chunk_count'] == 2

    def test_get_assembly_stats(self):
        """测试统计信息"""
        assembler = self.create_fresh_assembler()
        
        slices = [
            {'content': 'A' * 500, 'offset': 0, 'length': 500},
            {'content': 'B' * 500, 'offset': 500, 'length': 500},
        ]
        
        full_text, stats = assembler.assemble_with_dedup(slices)
        
        assert stats['chunk_count'] == 2
        assert stats['merged_chunks'] == 2
        assert stats['original_length'] == 1000
        assert stats['final_length'] == 1000

    def test_verify_integrity(self):
        """测试完整性验证"""
        assembler = self.create_fresh_assembler()
        
        original = "这是一个完整的测试文本，用于验证拼装完整性。"
        assembled = "这是一个完整的测试文本，用于验证拼装完整性。"
        
        result = assembler.verify_integrity(assembled, original)
        
        assert result['is_identical'] is True
        assert result['similarity'] == 100.0
        assert result['is_acceptable'] is True

    def test_detect_gaps(self):
        """测试间隙检测"""
        assembler = self.create_fresh_assembler()
        
        # 有间隙的切片
        slices = [
            {'content': '第一部分', 'offset': 0, 'length': 100},
            {'content': '第二部分', 'offset': 500, 'length': 100},  # 间隙 400 字
        ]
        
        has_gaps = assembler._detect_gaps(slices)
        assert has_gaps is True, "应该检测到间隙"

    def test_empty_slices(self):
        """测试空切片列表"""
        assembler = self.create_fresh_assembler()
        
        full_text, stats = assembler.assemble_with_dedup([])
        
        assert full_text == ""
        assert stats['chunk_count'] == 0
        assert stats['dedup_chars'] == 0
