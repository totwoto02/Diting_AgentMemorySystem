"""
测试知识图谱优化模块（Phase 2）

TDD 第一步：先写测试
"""

import pytest
from mfs.knowledge_graph_v2 import KnowledgeGraphV2, Concept, Edge


class TestKnowledgeGraphV2:
    """测试 KnowledgeGraphV2"""

    def create_fresh_kg(self):
        """创建新的知识图谱实例"""
        import random
        import time
        db_id = f"memdb_kg_v2_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        return KnowledgeGraphV2(db_path=f"file:{db_id}?mode=memory&cache=private")

    def test_add_concept(self):
        """测试添加概念"""
        kg = self.create_fresh_kg()
        try:
            # 添加概念
            concept_id = kg.add_concept(
                name="video game",
                type="category",
                aliases=["romance game", "女性向游戏"]
            )
            
            assert concept_id > 0
            
            # 验证概念存在
            concept = kg.get_concept_by_name("video game")
            assert concept is not None
            assert concept["name"] == "video game"
            assert "romance game" in concept["aliases"]
        finally:
            kg.close()

    def test_add_alias(self):
        """测试添加别名"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            
            # 添加别名
            kg.add_alias("测试用户", "小九")
            kg.add_alias("测试用户", "JJ")
            
            # 验证别名
            concept = kg.get_concept_by_name("测试用户")
            assert "小九" in concept["aliases"]
            assert "JJ" in concept["aliases"]
            
            # 通过别名查找
            concept_by_alias = kg.get_concept_by_name("小九")
            assert concept_by_alias is not None
            assert concept_by_alias["name"] == "测试用户"
        finally:
            kg.close()

    def test_add_edge_with_weight(self):
        """测试添加带权重的边"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            
            # 添加边（带权重）
            edge_id = kg.add_edge(
                from_concept="测试用户",
                to_concept="video game",
                relation="likes",
                weight=0.8
            )
            
            assert edge_id > 0
            
            # 验证边
            edges = kg.get_edges("测试用户")
            assert len(edges) > 0
            assert edges[0]["to_concept"] == "video game"
            # 允许时间衰减导致的微小差异
            assert abs(edges[0]["weight"] - 0.8) < 0.1
        finally:
            kg.close()

    def test_update_edge_weight(self):
        """测试更新边权重"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            
            # 初始权重
            kg.add_edge("测试用户", "video game", "likes", weight=0.5)
            
            # 更新权重
            kg.update_edge_weight("测试用户", "video game", 0.9)
            
            # 验证更新
            edges = kg.get_edges("测试用户")
            # 允许时间衰减导致的微小差异
            assert abs(edges[0]["weight"] - 0.9) < 0.1
        finally:
            kg.close()

    def test_get_related_concepts_weighted(self):
        """测试获取加权相关概念"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            kg.add_concept("测试角色", "character")
            kg.add_concept("loyal", "type")
            
            # 添加不同权重的边
            kg.add_edge("测试用户", "video game", "likes", weight=0.9)
            kg.add_edge("测试用户", "测试角色", "favorite", weight=0.7)
            kg.add_edge("测试用户", "loyal", "prefers", weight=0.5)
            
            # 获取相关概念（按权重排序）
            related = kg.get_related_concepts("测试用户", top_k=3)
            
            assert len(related) == 3
            # 验证按权重排序
            assert related[0]["concept"] == "video game"
            # 允许时间衰减导致的微小差异
            assert abs(related[0]["weight"] - 0.9) < 0.1
            assert related[1]["concept"] == "测试角色"
        finally:
            kg.close()

    def test_search_with_graph_expansion(self):
        """测试图谱扩展搜索"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            kg.add_concept("测试角色", "character")
            
            kg.add_edge("测试用户", "video game", "likes", weight=0.9)
            kg.add_edge("video game", "测试角色", "contains", weight=0.8)
            
            # 搜索"测试用户"，扩展到相关概念
            result = kg.search_with_expansion("测试用户", max_depth=2)
            
            assert result["found"] is True
            assert "video game" in result["expanded_concepts"]
            # 二层扩展
            assert "测试角色" in result["expanded_concepts"]
        finally:
            kg.close()

    def test_time_decay_weight(self):
        """测试时间衰减权重"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            
            # 添加边（带时间戳）
            import time
            old_time = time.time() - 86400 * 30  # 30 天前
            kg.add_edge("测试用户", "video game", "likes", weight=0.9, timestamp=old_time)
            
            # 获取衰减后的权重
            edges = kg.get_edges("测试用户")
            assert len(edges) > 0
            # 验证权重衰减（30 天后应该降低）
            assert edges[0]["weight"] < 0.9
        finally:
            kg.close()

    def test_get_stats(self):
        """测试获取统计信息"""
        kg = self.create_fresh_kg()
        try:
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            kg.add_edge("测试用户", "video game", "likes")
            
            stats = kg.get_stats()
            
            assert stats["concept_count"] == 2
            assert stats["edge_count"] == 1
            assert stats["avg_edges_per_concept"] > 0
        finally:
            kg.close()
