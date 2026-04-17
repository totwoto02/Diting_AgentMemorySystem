"""
测试 FTS5 全文检索模块

TDD 第一步：先写测试
"""

import pytest
import sqlite3
from mfs.fts5_search import FTS5Search


class TestFTS5Search:
    """测试 FTS5Search"""

    def create_fresh_fts5(self):
        """创建新的 FTS5 实例（带 MFT 表依赖）"""
        import random
        import time
        db_id = f"memdb_fts5_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        conn = sqlite3.connect(f"file:{db_id}?mode=memory&cache=private")
        
        # 先创建 MFT 表（FTS5 触发器依赖）
        conn.execute("""
            CREATE TABLE mft (
                inode INTEGER PRIMARY KEY AUTOINCREMENT,
                v_path TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                content TEXT,
                create_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        
        return FTS5Search(db_path=f"file:{db_id}?mode=memory&cache=private")

    def test_create_fts5_table(self):
        """测试创建 FTS5 表"""
        fts5 = self.create_fresh_fts5()
        try:
            # 验证表已创建
            stats = fts5.get_stats()
            assert stats["table_exists"] is True
            assert stats["doc_count"] == 0
        finally:
            fts5.close()

    def test_insert_document(self):
        """测试插入文档"""
        fts5 = self.create_fresh_fts5()
        try:
            # 插入文档
            doc_id = fts5.insert(
                v_path="/test/doc1",
                content="测试用户喜欢video game",
                type="NOTE"
            )
            
            assert doc_id > 0
            
            # 验证统计
            stats = fts5.get_stats()
            assert stats["doc_count"] == 1
        finally:
            fts5.close()

    def test_search_basic(self):
        """测试基本搜索"""
        fts5 = self.create_fresh_fts5()
        try:
            # 插入多个文档（使用空格分词）
            fts5.insert("/test/doc1", "测试用户 喜欢 乙女 游戏", "NOTE")
            fts5.insert("/test/doc2", "测试角色 是 乙女 游戏 角色", "NOTE")
            fts5.insert("/test/doc3", "loyal 类型 很 受欢迎", "NOTE")
            
            # 搜索"乙女"
            results = fts5.search("乙女")
            
            assert len(results) >= 2
            # 验证 BM25 排序（相关性高的在前）
            assert results[0]["v_path"] in ["/test/doc1", "/test/doc2"]
        finally:
            fts5.close()

    def test_search_phrase(self):
        """测试短语搜索"""
        fts5 = self.create_fresh_fts5()
        try:
            fts5.insert("/test/doc1", "测试用户 乙女 游戏 爱好者", "NOTE")
            fts5.insert("/test/doc2", "测试用户 喜欢 乙女 游戏", "NOTE")
            
            # 搜索多个词
            results = fts5.search("乙女 游戏")
            
            # 应该匹配包含两个词的文档
            assert len(results) >= 1
        finally:
            fts5.close()

    def test_search_multi_keywords(self):
        """测试多关键词搜索"""
        fts5 = self.create_fresh_fts5()
        try:
            fts5.insert("/test/doc1", "测试用户 video game 测试角色", "NOTE")
            fts5.insert("/test/doc2", "测试用户 loyal", "NOTE")
            fts5.insert("/test/doc3", "测试角色 loyal", "NOTE")
            
            # 多关键词搜索（AND）
            results = fts5.search("测试用户 loyal")
            
            # 应该匹配包含两个词的文档
            assert len(results) >= 1
        finally:
            fts5.close()

    def test_search_with_scope(self):
        """测试范围搜索"""
        fts5 = self.create_fresh_fts5()
        try:
            fts5.insert("/person/测试用户/doc1", "测试用户的资料", "CONTACT")
            fts5.insert("/person/测试用户/doc2", "测试用户的偏好", "NOTE")
            fts5.insert("/work/project/doc1", "项目文档", "CODE")
            
            # 范围搜索（只搜索/person 路径）
            results = fts5.search("测试用户", scope="/person")
            
            # 应该只返回/person 下的结果
            for r in results:
                assert r["v_path"].startswith("/person")
        finally:
            fts5.close()

    def test_search_no_results(self):
        """测试无结果搜索"""
        fts5 = self.create_fresh_fts5()
        try:
            fts5.insert("/test/doc1", "测试内容", "NOTE")
            
            # 搜索不存在的词
            results = fts5.search("不存在的词")
            
            assert len(results) == 0
        finally:
            fts5.close()

    def test_delete_document(self):
        """测试删除文档"""
        fts5 = self.create_fresh_fts5()
        try:
            doc_id = fts5.insert("/test/doc1", "测试内容", "NOTE")
            
            # 删除
            success = fts5.delete("/test/doc1")
            assert success is True
            
            # 验证删除后搜索不到
            results = fts5.search("测试")
            assert len(results) == 0
        finally:
            fts5.close()

    def test_bm25_ranking(self):
        """测试 BM25 排序"""
        fts5 = self.create_fresh_fts5()
        try:
            # 插入不同相关度的文档
            fts5.insert("/test/doc1", "video game video game video game", "NOTE")  # 高频
            fts5.insert("/test/doc2", "video game", "NOTE")  # 低频
            
            results = fts5.search("video game")
            
            # 验证 BM25 排序（高频在前）
            assert len(results) == 2
            assert results[0]["v_path"] == "/test/doc1"
        finally:
            fts5.close()
