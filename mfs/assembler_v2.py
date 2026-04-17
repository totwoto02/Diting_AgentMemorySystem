"""
Assembler V2 - 优化的拼装器

支持智能去重、重叠检测、质量评分
"""

from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass


@dataclass
class Slice:
    """切片数据结构"""
    chunk_id: int
    offset: int
    length: int
    content: str
    
    @property
    def end_pos(self) -> int:
        """结束位置"""
        return self.offset + self.length
    
    def get(self, key: str, default=None):
        """兼容字典访问"""
        if key == 'content':
            return self.content
        elif key == 'offset':
            return self.offset
        elif key == 'length':
            return self.length
        elif key == 'chunk_id':
            return self.chunk_id
        return default
    
    def __getitem__(self, key: str):
        """支持下标访问"""
        if key == 'content':
            return self.content
        elif key == 'offset':
            return self.offset
        elif key == 'length':
            return self.length
        elif key == 'chunk_id':
            return self.chunk_id
        raise KeyError(key)


class AssemblerV2:
    """优化的拼装器"""

    def __init__(self, overlap_threshold: float = 0.3, min_overlap: int = 20):
        """
        初始化拼装器

        Args:
            overlap_threshold: 重叠检测阈值（0-1）
            min_overlap: 最小重叠字符数
        """
        self.overlap_threshold = overlap_threshold
        self.min_overlap = min_overlap

    def assemble_with_dedup(self, slices: List[Dict[str, Any]]) -> Tuple[str, Dict]:
        """
        拼装切片并去重

        Args:
            slices: 切片列表，每个包含 content, offset, length

        Returns:
            (拼装后的文本，统计信息)
        """
        if not slices:
            return "", {"chunk_count": 0, "dedup_chars": 0}

        # 按 offset 排序
        sorted_slices = sorted(slices, key=lambda x: x.get('offset', 0))

        # 合并重叠部分
        merged = []
        dedup_chars = 0

        for i, slice in enumerate(sorted_slices):
            if i == 0:
                merged.append(slice)
            else:
                prev = merged[-1]
                overlap = self._detect_overlap(prev, slice)

                if overlap > 0:
                    # 有重叠，去重
                    dedup_chars += overlap
                    # 只添加不重叠的部分
                    new_content = slice['content'][overlap:]
                    if new_content:
                        merged.append({
                            'content': new_content,
                            'offset': slice['offset'],
                            'length': len(new_content)
                        })
                else:
                    # 无重叠，直接添加
                    merged.append(slice)

        # 拼装最终文本
        full_text = ''.join(s['content'] for s in merged)

        stats = {
            "chunk_count": len(slices),
            "merged_chunks": len(merged),
            "dedup_chars": dedup_chars,
            "original_length": sum(s.get('length', len(s['content'])) for s in slices),
            "final_length": len(full_text)
        }

        return full_text, stats

    def _detect_overlap(self, slice1: Dict, slice2: Dict) -> int:
        """
        检测两个切片的重叠部分

        Args:
            slice1: 前一个切片
            slice2: 后一个切片

        Returns:
            重叠字符数
        """
        content1 = slice1.get('content', '')
        content2 = slice2.get('content', '')

        # 获取可能的重叠区域
        end1 = content1[-100:] if len(content1) > 100 else content1
        start2 = content2[:100] if len(content2) > 100 else content2

        # 使用序列匹配检测重叠
        matcher = SequenceMatcher(None, end1, start2)
        match = matcher.find_longest_match(
            0, len(end1),
            0, len(start2)
        )

        if match.size >= self.min_overlap:
            # 计算重叠比例
            overlap_ratio = match.size / min(len(end1), len(start2))
            if overlap_ratio >= self.overlap_threshold:
                return match.size

        return 0

    def assemble_with_quality(self, slices: List[Dict[str, Any]], 
                              expected_length: Optional[int] = None) -> Dict[str, Any]:
        """
        拼装并评估质量

        Args:
            slices: 切片列表
            expected_length: 期望的总长度（可选）

        Returns:
            拼装结果和質量评分
        """
        full_text, stats = self.assemble_with_dedup(slices)

        # 质量评分
        quality_score = 100.0
        issues = []

        # 检查 1: 是否有去重
        if stats['dedup_chars'] > 0:
            quality_score -= 5
            issues.append(f"检测到 {stats['dedup_chars']} 字符重复")

        # 检查 2: 切片数量是否合理
        if stats['chunk_count'] > 20:
            quality_score -= 10
            issues.append(f"切片数量过多 ({stats['chunk_count']} 片)")

        # 检查 3: 长度是否匹配期望
        if expected_length:
            length_diff = abs(len(full_text) - expected_length)
            if length_diff > expected_length * 0.1:
                quality_score -= 15
                issues.append(f"长度偏差 {length_diff} 字")

        # 检查 4: 是否有明显断裂
        if self._detect_gaps(slices):
            quality_score -= 20
            issues.append("检测到内容断裂")

        return {
            "content": full_text,
            "stats": stats,
            "quality_score": quality_score,
            "issues": issues,
            "is_complete": quality_score >= 80
        }

    def _detect_gaps(self, slices: List[Dict[str, Any]]) -> bool:
        """检测是否有内容断裂"""
        if len(slices) < 2:
            return False

        sorted_slices = sorted(slices, key=lambda x: x.get('offset', 0))

        for i in range(1, len(sorted_slices)):
            prev = sorted_slices[i-1]
            curr = sorted_slices[i]

            prev_end = prev.get('offset', 0) + prev.get('length', len(prev.get('content', '')))
            curr_start = curr.get('offset', 0)

            # 检查是否有间隙
            if curr_start > prev_end + 10:  # 允许 10 字符误差
                return True

        return False

    def verify_integrity(self, assembled: str, original: str) -> Dict[str, Any]:
        """
        验证拼装完整性

        Args:
            assembled: 拼装后的文本
            original: 原始文本

        Returns:
            验证结果
        """
        # 计算相似度
        matcher = SequenceMatcher(None, assembled, original)
        similarity = matcher.ratio()

        # 检测差异
        diff_count = sum(1 for op in matcher.get_opcodes() if op[0] != 'equal')

        return {
            "similarity": similarity * 100,
            "diff_count": diff_count,
            "is_identical": assembled == original,
            "is_acceptable": similarity >= 0.95,
            "missing_chars": len(original) - len(assembled),
            "extra_chars": len(assembled) - len(original)
        }
    
    def close(self):
        """关闭拼装器（清理资源）"""
        pass  # AssemblerV2 不需要特殊清理
    
    def cache_slice(self, slice_id: str, content: str):
        """缓存切片（简化实现）"""
        if not hasattr(self, '_cache'):
            self._cache = {}
        self._cache[slice_id] = content
    
    def get_cached_slice(self, slice_id: str) -> str:
        """获取缓存的切片"""
        if not hasattr(self, '_cache'):
            self._cache = {}
        return self._cache.get(slice_id)
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        if not hasattr(self, '_cache'):
            self._cache = {}
        return {
            'size': len(self._cache),
            'keys': list(self._cache.keys())
        }
