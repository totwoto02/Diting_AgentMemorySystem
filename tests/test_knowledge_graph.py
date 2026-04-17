"""
测试知识图谱模块
"""

import pytest
from diting.knowledge_graph import KnowledgeGraph


class TestKnowledgeGraph:
    """测试 KnowledgeGraph"""

    def test_extract_keywords(self):
        """测试关键词提取"""
        kg = KnowledgeGraph()
        text = "测试用户 video game 测试角色 loyal"
        
        keywords = kg.extract_keywords(text)
        
        assert len(keywords) > 0
        # 验证有关键词被提取
        assert any(kw in keywords for kw in ["测试用户", "video game", "测试角色", "loyal"])

    def test_add_memory(self):
        """测试添加记忆"""
        kg = KnowledgeGraph()
        
        kg.add_memory("/test/doc1", "测试用户 video game")
        kg.add_memory("/test/doc2", "测试角色 video game")
        
        # 验证节点
        assert len(kg.nodes) > 0
        
        # 验证边
        assert len(kg.edges) > 0

    def test_get_related_concepts(self):
        """测试获取相关概念"""
        kg = KnowledgeGraph()
        
        # 添加多个记忆建立关联
        kg.add_memory("/test/doc1", "测试用户 video game 测试角色")
        kg.add_memory("/test/doc2", "测试用户 loyal 测试角色")
        kg.add_memory("/test/doc3", "video game loyal")
        
        related = kg.get_related_concepts("测试用户")
        
        assert len(related) > 0
        assert "video game" in [r["concept"] for r in related] or "game" in [r["concept"] for r in related]

    def test_search_with_expansion(self):
        """测试搜索扩展"""
        kg = KnowledgeGraph()
        
        kg.add_memory("/test/doc1", "测试用户 video game 测试角色")
        
        result = kg.search_with_expansion("测试用户")
        
        assert result["found"] is True
        assert "related_concepts" in result
        assert result["suggestion"] is not None

    def test_search_nonexistent(self):
        """测试搜索不存在的概念"""
        kg = KnowledgeGraph()
        
        result = kg.search_with_expansion("不存在的词")
        
        assert result["found"] is False
        assert result["related_concepts"] == []

    def test_get_stats(self):
        """测试获取统计信息"""
        kg = KnowledgeGraph()
        
        kg.add_memory("/test/doc1", "测试用户 video game")
        kg.add_memory("/test/doc2", "测试角色 loyal")
        
        stats = kg.get_stats()
        
        assert stats["node_count"] > 0
        assert stats["edge_count"] >= 0
