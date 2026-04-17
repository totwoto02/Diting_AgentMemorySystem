"""
测试自动切片器
"""

import pytest
from diting.slicers.length import LengthSplitter, Slice


class TestLengthSplitter:
    """测试 LengthSplitter"""

    def test_split_short_text(self):
        """测试短文本（小于最小切片大小）"""
        splitter = LengthSplitter(min_chunk_size=500, max_chunk_size=2000)
        text = "这是一段短文本"
        slices = splitter.split(text)
        
        assert len(slices) == 1
        assert slices[0].chunk_id == 1
        assert slices[0].offset == 0
        assert slices[0].length == len(text)
        assert slices[0].content == text

    def test_split_long_text(self):
        """测试长文本切分"""
        splitter = LengthSplitter(min_chunk_size=500, max_chunk_size=2000)
        text = "A" * 5000  # 5000 字
        
        slices = splitter.split(text)
        
        # 应该切分为多个切片
        assert len(slices) >= 3
        assert len(slices) <= 15
        
        # 验证切片 ID 连续
        for i, slice_obj in enumerate(slices):
            assert slice_obj.chunk_id == i + 1

    def test_split_overlap(self):
        """测试重叠切分"""
        splitter = LengthSplitter(
            min_chunk_size=500,
            max_chunk_size=2000,
            overlap_ratio=0.15
        )
        text = "A" * 5000
        
        slices = splitter.split(text)
        
        # 验证有重叠（除了最后一片）
        if len(slices) > 1:
            for i in range(len(slices) - 1):
                # 相邻切片应该有重叠内容
                current_end = slices[i].offset + slices[i].length
                next_start = slices[i + 1].offset
                # 下一片的开始应该 <= 前一片结束（有重叠或刚好衔接）
                assert next_start <= current_end

    def test_split_metadata(self):
        """测试获取切片元数据"""
        splitter = LengthSplitter()
        text = "A" * 5000
        slices = splitter.split(text)
        
        metadata = splitter.get_metadata(slices)
        
        assert len(metadata) == len(slices)
        for i, meta in enumerate(metadata):
            assert 'chunk_id' in meta
            assert 'offset' in meta
            assert 'length' in meta
            assert meta['chunk_id'] == slices[i].chunk_id

    def test_empty_text(self):
        """测试空文本"""
        splitter = LengthSplitter()
        slices = splitter.split("")
        
        assert slices == []

    def test_exact_chunk_size(self):
        """测试刚好等于最大切片大小"""
        splitter = LengthSplitter(min_chunk_size=500, max_chunk_size=2000)
        text = "A" * 2000
        
        slices = splitter.split(text)
        
        assert len(slices) == 1
        assert slices[0].length == 2000

    def test_just_over_chunk_size(self):
        """测试略大于最大切片大小"""
        splitter = LengthSplitter(min_chunk_size=500, max_chunk_size=2000)
        text = "A" * 2001
        
        slices = splitter.split(text)
        
        # 应该切分为 2 片
        assert len(slices) == 2
