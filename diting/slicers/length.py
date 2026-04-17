"""
自动切片器模块

将长文本自动切分为多个切片，每个切片 500-2000 字
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Slice:
    """切片数据结构"""
    chunk_id: int
    offset: int
    length: int
    content: str


class LengthSplitter:
    """
    按长度切分器

    将长文本按 500-2000 字切分，保留 10-20% 重叠
    """

    def __init__(
        self,
        min_chunk_size: int = 500,
        max_chunk_size: int = 2000,
        overlap_ratio: float = 0.15
    ):
        """
        初始化切分器

        Args:
            min_chunk_size: 最小切片大小（字）
            max_chunk_size: 最大切片大小（字）
            overlap_ratio: 重叠率（0.1-0.2）
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_ratio = max(0.1, min(0.2, overlap_ratio))

    def split(self, text: str) -> List[Slice]:
        """
        切分文本

        Args:
            text: 待切分的文本

        Returns:
            切片列表
        """
        if not text:
            return []

        # 如果文本长度小于最小切片大小，直接返回单一切片
        if len(text) <= self.min_chunk_size:
            return [Slice(
                chunk_id=1,
                offset=0,
                length=len(text),
                content=text
            )]

        slices = []
        chunk_id = 1
        current_pos = 0
        overlap_size = 0

        while current_pos < len(text):
            # 计算当前切片的结束位置
            remaining = len(text) - current_pos
            
            if remaining <= self.max_chunk_size:
                # 最后一片，包含所有剩余内容
                chunk_content = text[current_pos:]
                chunk_length = len(chunk_content)
            else:
                # 中间片，取最大切片大小
                chunk_content = text[current_pos:current_pos + self.max_chunk_size]
                chunk_length = self.max_chunk_size

            # 计算重叠部分（从下一片开始位置回退）
            if chunk_id > 1 and overlap_size > 0:
                # 包含前一片的重叠部分
                chunk_content = text[current_pos - overlap_size:current_pos + self.max_chunk_size]
                chunk_length = len(chunk_content)

            # 创建切片
            slice_obj = Slice(
                chunk_id=chunk_id,
                offset=current_pos,
                length=chunk_length,
                content=chunk_content
            )
            slices.append(slice_obj)

            # 更新位置（减去重叠部分）
            step = chunk_length - overlap_size
            current_pos += step
            chunk_id += 1

            # 计算下一片的重叠大小
            if current_pos < len(text):
                remaining_after = len(text) - current_pos
                overlap_size = min(
                    int(self.max_chunk_size * self.overlap_ratio),
                    remaining_after
                )

        return slices

    def get_metadata(self, slices: List[Slice]) -> List[Dict[str, Any]]:
        """
        获取切片元数据（用于存储到 lcn_pointers）

        Args:
            slices: 切片列表

        Returns:
            元数据列表
        """
        return [
            {
                "chunk_id": s.chunk_id,
                "offset": s.offset,
                "length": s.length
            }
            for s in slices
        ]
