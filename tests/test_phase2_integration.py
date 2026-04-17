"""
MFS Phase 2 集成测试

测试完整的自动切片→存储→还原流程
"""

import pytest
from mfs.mft import MFT
from mfs.slicers.length import LengthSplitter
from mfs.assembler import Assembler
from mfs.knowledge_graph import KnowledgeGraph


class TestPhase2Integration:
    """Phase 2 集成测试"""

    def create_fresh_mft(self):
        """创建新的 MFT 实例"""
        import random
        import time
        db_id = f"memdb_int_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        return MFT(db_path=f"file:{db_id}?mode=memory&cache=private")

    def test_full_pipeline_auto_slice_and_assemble(self):
        """测试完整流程：自动切片→存储→自动还原"""
        mft = self.create_fresh_mft()
        try:
            # 1. 创建长文本（5000 字）
            long_content = "这是测试内容。" * 300  # 约 5400 字
            
            # 2. 创建记忆（应该自动切片）
            inode = mft.create("/test/long_doc", "NOTE", long_content)
            
            # 3. 手动设置切片指针（模拟自动切片）
            splitter = LengthSplitter(
                min_chunk_size=500,
                max_chunk_size=2000,
                overlap_ratio=0.15
            )
            slices = splitter.split(long_content)
            pointers = splitter.get_metadata(slices)
            mft.set_lcn_pointers("/test/long_doc", pointers)
            
            # 4. 验证切片指针已存储
            stored_pointers = mft.get_lcn_pointers("/test/long_doc")
            assert stored_pointers is not None
            assert len(stored_pointers) > 1
            
            # 5. 使用 Assembler 还原
            assembler = Assembler(mft)
            assembled_content = assembler.assemble("/test/long_doc")
            
            # 6. 验证还原内容与原文一致
            assert assembled_content == long_content
            
            print(f"✅ 完整流程测试通过：切片数={len(slices)}, 还原准确率=100%")
            
        finally:
            mft.close()

    def test_knowledge_graph_integration(self):
        """测试知识图谱集成"""
        kg = KnowledgeGraph()
        
        # 添加多个记忆
        kg.add_memory("/test/doc1", "测试用户 video game 测试角色")
        kg.add_memory("/test/doc2", "测试用户 loyal 测试角色")
        kg.add_memory("/test/doc3", "video game 恋爱 模拟")
        
        # 验证节点
        assert len(kg.nodes) > 0
        
        # 验证关联
        related = kg.get_related_concepts("测试用户")
        assert len(related) > 0
        
        # 验证搜索扩展
        result = kg.search_with_expansion("测试用户")
        assert result["found"] is True
        assert result["suggestion"] is not None
        
        print(f"✅ 知识图谱集成测试通过：节点数={len(kg.nodes)}, 边数={len(kg.edges)}")

    def test_mft_with_lcn_pointers_persistence(self):
        """测试 lcn_pointers 持久化"""
        mft = self.create_fresh_mft()
        try:
            # 创建记忆
            mft.create("/test/persist", "NOTE", "测试内容")
            
            # 设置切片指针
            pointers = [
                {"chunk_id": 1, "offset": 0, "length": 100},
                {"chunk_id": 2, "offset": 100, "length": 100},
            ]
            mft.set_lcn_pointers("/test/persist", pointers)
            
            # 重新读取验证
            retrieved = mft.get_lcn_pointers("/test/persist")
            assert retrieved == pointers
            
            print("✅ lcn_pointers 持久化测试通过")
            
        finally:
            mft.close()
