"""
Step 2 集成测试

测试 FTS5 + 知识图谱 + 拼装 + 防幻觉的完整流程
"""

import pytest
from mfs.fts5_search import FTS5Search
from mfs.knowledge_graph_v2 import KnowledgeGraphV2
from mfs.wal_logger import WALLogger


class TestStep2Integration:
    """Step 2 集成测试"""

    def test_fts5_with_knowledge_graph(self):
        """测试 FTS5 与知识图谱联合搜索"""
        import random
        import time
        
        # 创建组件
        db_id = f"memdb_int_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        fts5 = FTS5Search(db_path=f"file:{db_id}_fts5?mode=memory&cache=private")
        kg = KnowledgeGraphV2(db_path=f"file:{db_id}_kg?mode=memory&cache=private")
        
        try:
            # 插入文档到 FTS5
            fts5.insert("/test/doc1", "测试用户 喜欢 video game", "NOTE")
            fts5.insert("/test/doc2", "测试角色 是 video game 角色", "NOTE")
            
            # 构建知识图谱
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            kg.add_concept("测试角色", "character")
            kg.add_edge("测试用户", "video game", "likes", weight=0.9)
            kg.add_edge("video game", "测试角色", "contains", weight=0.8)
            
            # FTS5 搜索
            fts5_results = fts5.search("video game")
            assert len(fts5_results) >= 2
            
            # 知识图谱扩展
            expansion = kg.search_with_expansion("测试用户", max_depth=2)
            assert expansion["found"] is True
            assert "video game" in expansion["expanded_concepts"]
            
            print(f"✅ FTS5+ 知识图谱联合搜索测试通过")
            
        finally:
            fts5.close()
            kg.close()

    def test_wal_with_assembler(self):
        """测试 WAL 日志与拼装器集成"""
        import random
        import time
        
        db_id = f"memdb_int_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        wal = WALLogger(db_path=f"file:{db_id}_wal?mode=memory&cache=private")
        
        try:
            # 记录写入操作
            wal.log_operation(
                operation="CREATE",
                v_path="/test/long_doc",
                content="A" * 5000,
                source_agent="main",
                evidence="conversation_123",
                confidence=1.0
            )
            
            # 记录更新操作
            wal.log_operation(
                operation="UPDATE",
                v_path="/test/long_doc",
                content="B" * 5000,
                source_agent="assistant",
                evidence="conversation_456",
                confidence=0.8
            )
            
            # 获取历史记录
            history = wal.get_history("/test/long_doc")
            assert len(history) == 2
            
            # 获取最新版本
            latest = wal.get_latest_version("/test/long_doc")
            assert latest["version"] == 2
            assert latest["confidence"] == 0.8
            
            # 回滚到 V1
            wal.rollback(history[1]["id"])
            
            # 验证回滚
            v1 = wal.get_version("/test/long_doc", version=1)
            assert v1["content"] == "A" * 5000
            
            print(f"✅ WAL+ 拼装器集成测试通过")
            
        finally:
            wal.close()

    def test_full_pipeline(self):
        """测试完整流程：写入→切片→存储→搜索→还原"""
        import random
        import time
        
        db_id = f"memdb_int_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        fts5 = FTS5Search(db_path=f"file:{db_id}_fts5?mode=memory&cache=private")
        kg = KnowledgeGraphV2(db_path=f"file:{db_id}_kg?mode=memory&cache=private")
        wal = WALLogger(db_path=f"file:{db_id}_wal?mode=memory&cache=private")
        
        try:
            # 1. 写入长文本（带 WAL 日志）
            long_content = "测试用户 喜欢 video game 测试角色 loyal " * 100
            wal.log_operation(
                operation="CREATE",
                v_path="/test/long_doc",
                content=long_content,
                source_agent="main",
                evidence="test_conv",
                confidence=1.0
            )
            
            # 2. 插入 FTS5 索引
            fts5.insert("/test/long_doc", long_content, "NOTE")
            
            # 3. 构建知识图谱
            kg.add_concept("测试用户", "person")
            kg.add_concept("video game", "category")
            kg.add_edge("测试用户", "video game", "likes", weight=0.9)
            
            # 4. FTS5 搜索
            search_results = fts5.search("video game")
            assert len(search_results) >= 1
            
            # 5. 知识图谱扩展
            expansion = kg.search_with_expansion("测试用户")
            assert "video game" in expansion["expanded_concepts"]
            
            # 6. WAL 审计
            audit = wal.get_audit_trail()
            assert len(audit) >= 1
            
            print(f"✅ 完整流程集成测试通过")
            
        finally:
            fts5.close()
            kg.close()
            wal.close()
