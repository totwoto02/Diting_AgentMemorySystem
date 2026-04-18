"""
自动还原器（Assembler）

将多个切片拼装还原为完整文本
"""

from typing import List, Dict, Any, Optional
from diting.mft import MFT


class Assembler:
    """
    切片拼装器

    从 MFT 读取切片指针，捞取所有切片并拼装为原文
    """

    def __init__(self, mft: MFT):
        """
        初始化拼装器

        Args:
            mft: MFT 实例
        """
        self.mft = mft

    def assemble(self, v_path: str) -> Optional[str]:
        """
        拼装还原指定路径的文本

        Args:
            v_path: 虚拟路径

        Returns:
            拼装后的完整文本，未找到返回 None
        """
        # 获取切片指针
        pointers = self.mft.get_lcn_pointers(v_path)

        if not pointers:
            # 没有切片，直接读取原文
            record = self.mft.read(v_path)
            return record['content'] if record else None

        # 读取主记录获取原始内容（作为基础）
        main_record = self.mft.read(v_path)
        if not main_record:
            return None

        # 如果有切片指针，从指针中重建
        # 注意：实际实现中，切片内容应存储在单独的 chunk 表中
        # 这里简化处理：假设 content 字段存储完整原文
        # Phase 2 后续会实现真正的 chunk 存储

        # 临时方案：直接返回主记录内容
        # TODO: 实现真正的 chunk 捞取和拼装
        return main_record.get('content')

    def assemble_from_pointers(
        self,
        pointers: List[Dict[str, Any]],
        full_text: str
    ) -> str:
        """
        从指针和完整文本中还原（用于测试）

        Args:
            pointers: 切片指针列表
            full_text: 完整文本

        Returns:
            拼装后的文本
        """
        if not pointers:
            return full_text

        # 按 chunk_id 排序
        sorted_pointers = sorted(pointers, key=lambda p: p['chunk_id'])

        # 捞取切片并拼装
        slices = []
        for ptr in sorted_pointers:
            offset = ptr['offset']
            length = ptr['length']
            slice_content = full_text[offset:offset + length]
            slices.append(slice_content)

        # 简单拼接（实际需要考虑重叠去重）
        return ''.join(slices)

    def verify_assembly(self, assembled: str, expected: str) -> bool:
        """
        验证拼装结果

        Args:
            assembled: 拼装后的文本
            expected: 期望的原文

        Returns:
            True 如果一致
        """
        return assembled == expected

    def get_assembly_stats(
            self, pointers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取拼装统计信息

        Args:
            pointers: 切片指针列表

        Returns:
            统计信息
        """
        if not pointers:
            return {"chunk_count": 0, "total_length": 0}

        return {
            "chunk_count": len(pointers), "total_length": sum(
                p['length'] for p in pointers), "avg_chunk_size": sum(
                p['length'] for p in pointers) / len(pointers)}
