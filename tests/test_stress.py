"""
暴力测试模块

大数据量、高并发、边界条件、压力测试
"""

import pytest
import asyncio
import threading
import time
import random
import string
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

from diting.fts5_search import FTS5Search
from diting.knowledge_graph_v2 import KnowledgeGraphV2
from diting.assembler_v2 import AssemblerV2
from diting.wal_logger import WALLogger
from diting.cache import LRUCache, ConnectionPool
from diting.mft import MFT

# Slice 类已在 assembler_v2 中定义
from diting.assembler_v2 import Slice
from tests.test_unified_db import create_unified_db


class TestStressFTS5:
    """FTS5 压力测试"""

    def test_large_dataset_insert(self):
        """测试大数据量插入（10000 条记录）"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        
        # 创建统一数据库
        db_path = create_unified_db(db_id)
        fts5 = FTS5Search(db_path=db_path)
        
        try:
            start_time = time.time()
            
            # 插入 10000 条记录
            for i in range(10000):
                fts5.insert(f"/test/doc{i}", f"内容_{i} " * 10, "NOTE")
            
            elapsed = time.time() - start_time
            stats = fts5.get_stats()
            
            assert stats["doc_count"] == 10000
            print(f"✅ 10000 条记录插入完成，耗时：{elapsed:.2f}s，平均：{elapsed/10000*1000:.2f}ms/条")
            
        finally:
            fts5.close()

    def test_large_dataset_search(self):
        """测试大数据量搜索性能"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        
        # 创建统一数据库
        db_path = create_unified_db(db_id)
        fts5 = FTS5Search(db_path=db_path)
        
        try:
            # 插入 5000 条记录
            for i in range(5000):
                fts5.insert(f"/test/doc{i}", f"内容_{i} 测试 搜索", "NOTE")
            
            # 执行 100 次搜索
            start_time = time.time()
            for _ in range(100):
                fts5.search("测试")
            
            elapsed = time.time() - start_time
            avg_latency = elapsed / 100 * 1000
            
            assert avg_latency < 100  # 平均延迟应小于 100ms
            print(f"✅ 100 次搜索完成，平均延迟：{avg_latency:.2f}ms")
            
        finally:
            fts5.close()

    def test_concurrent_search(self):
        """测试并发搜索"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        fts5 = FTS5Search(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            # 插入数据
            for i in range(1000):
                fts5.insert(f"/test/doc{i}", f"内容_{i} 并发 测试", "NOTE")
            
            # 并发搜索
            def search_task():
                for _ in range(10):
                    fts5.search("并发")
            
            threads = []
            for _ in range(10):
                t = threading.Thread(target=search_task)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            print(f"✅ 并发搜索测试完成（10 线程 × 10 次）")
            
        finally:
            fts5.close()


class TestStressKnowledgeGraph:
    """知识图谱压力测试"""

    def test_large_graph(self):
        """测试大型知识图谱（1000 个概念）"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        kg = KnowledgeGraphV2(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            start_time = time.time()
            
            # 添加 1000 个概念
            for i in range(1000):
                kg.add_concept(f"概念_{i}", "category", aliases=[f"别名_{i}"])
            
            # 添加 5000 条边
            for i in range(5000):
                from_concept = f"概念_{random.randint(0, 999)}"
                to_concept = f"概念_{random.randint(0, 999)}"
                kg.add_edge(from_concept, to_concept, "related", weight=random.random())
            
            elapsed = time.time() - start_time
            stats = kg.get_stats()
            
            assert stats["concept_count"] == 1000
            # 由于 UNIQUE 约束，重复的边会被合并，所以边数可能略少于 5000
            assert stats["edge_count"] >= 4000
            print(f"✅ 大型图谱构建完成：1000 概念 + {stats['edge_count']} 边，耗时：{elapsed:.2f}s")
            
        finally:
            kg.close()

    def test_deep_expansion(self):
        """测试深层扩展（max_depth=5）"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        kg = KnowledgeGraphV2(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            # 构建链式结构
            for i in range(100):
                kg.add_concept(f"概念_{i}", "category")
                if i > 0:
                    kg.add_edge(f"概念_{i-1}", f"概念_{i}", "next", weight=0.9)
            
            # 深层扩展
            result = kg.search_with_expansion("概念_0", max_depth=5)
            
            assert result["found"] is True
            assert len(result["expanded_concepts"]) >= 5
            print(f"✅ 深层扩展测试完成，扩展到 {len(result['expanded_concepts'])} 个概念")
            
        finally:
            kg.close()


class TestStressAssembler:
    """拼装器压力测试"""

    def test_many_slices(self):
        """测试多切片拼装（100 个切片）"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        assembler = AssemblerV2()
        
        try:
            # 创建 100 个切片
            slices = []
            for i in range(100):
                slices.append(Slice(
                    chunk_id=i+1,
                    offset=i*500,
                    length=500,
                    content=f"切片_{i} " * 50
                ))
            
            # 拼装
            start_time = time.time()
            result = assembler.assemble_with_dedup(slices)
            elapsed = time.time() - start_time
            
            assert len(result) > 0
            print(f"✅ 100 个切片拼装完成，耗时：{elapsed*1000:.2f}ms，总长度：{len(result)}")
            
        finally:
            assembler.close()

    def test_cache_performance(self):
        """测试缓存性能"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        assembler = AssemblerV2()
        
        try:
            # 填充缓存
            for i in range(500):
                slice_obj = Slice(chunk_id=i, offset=0, length=100, content=f"内容_{i}")
                assembler.cache_slice(f"path_{i}", slice_obj)
            
            # 随机访问
            hits = 0
            for _ in range(1000):
                key = f"path_{random.randint(0, 499)}"
                if assembler.get_cached_slice(key) is not None:
                    hits += 1
            
            stats = assembler.get_cache_stats()
            hit_rate = hits / 1000 * 100
            
            assert hit_rate > 90  # 命中率应大于 90%
            print(f"✅ 缓存性能测试完成，命中率：{hit_rate:.2f}%")
            
        finally:
            assembler.close()


class TestStressWAL:
    """WAL 日志压力测试"""

    def test_many_operations(self):
        """测试大量操作记录（10000 条）"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        wal = WALLogger(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            start_time = time.time()
            
            # 记录 10000 条操作
            for i in range(10000):
                wal.log_operation(
                    operation="UPDATE",
                    v_path=f"/test/doc{i % 1000}",
                    content=f"内容_{i}",
                    source_agent="test",
                    evidence=f"conv_{i}",
                    confidence=random.random()
                )
            
            elapsed = time.time() - start_time
            
            # 获取历史
            history = wal.get_history("/test/doc0")
            
            assert len(history) == 10  # 10000/1000 = 10
            print(f"✅ 10000 条操作记录完成，耗时：{elapsed:.2f}s，平均：{elapsed/10000*1000:.2f}ms/条")
            
        finally:
            wal.close()

    def test_rollback_many(self):
        """测试多次回滚"""
        import random
        db_id = f"memdb_stress_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        wal = WALLogger(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            # 创建 100 条记录
            record_ids = []
            for i in range(100):
                record_id = wal.log_operation("CREATE", f"/test/doc{i}", f"内容_{i}", "main", f"conv_{i}")
                record_ids.append(record_id)
            
            # 回滚 50 条
            for i in range(0, 100, 2):
                wal.rollback(record_ids[i])
            
            # 验证
            history = wal.get_history("/test/doc0")
            assert history[0]["status"] == "ROLLED_BACK"
            
            print(f"✅ 多次回滚测试完成（50 次回滚）")
            
        finally:
            wal.close()


class TestStressCache:
    """缓存压力测试"""

    def test_lru_large_capacity(self):
        """测试大容量 LRU 缓存（10000 容量）"""
        cache = LRUCache(capacity=10000)
        
        # 填充缓存
        for i in range(10000):
            cache.put(f"key_{i}", f"value_{i}")
        
        # 验证容量
        stats = cache.get_stats()
        assert stats["size"] == 10000
        
        # 触发淘汰
        cache.put("key_new", "value_new")
        stats = cache.get_stats()
        assert stats["size"] == 10000
        
        print(f"✅ 大容量 LRU 缓存测试完成（容量 10000）")

    def test_connection_pool_stress(self):
        """测试连接池压力"""
        pool = ConnectionPool(db_path=":memory:", max_connections=20)
        
        try:
            def use_connection():
                for _ in range(10):
                    with pool.get_connection() as conn:
                        conn.execute("SELECT 1")
            
            # 50 个线程并发使用连接池
            threads = []
            for _ in range(50):
                t = threading.Thread(target=use_connection)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            stats = pool.get_stats()
            print(f"✅ 连接池压力测试完成（50 线程 × 10 次，总获取：{stats['total_acquired']}）")
            
        finally:
            pool.close()


class TestBoundaryConditions:
    """边界条件测试"""

    def test_empty_inputs(self):
        """测试空输入"""
        # FTS5 空搜索
        import random
        db_id = f"memdb_boundary_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        db_path = create_unified_db(db_id)
        fts5 = FTS5Search(db_path=db_path)
        
        try:
            fts5.insert("/test/doc1", "内容", "NOTE")
            
            # 空搜索（应该处理异常）
            try:
                results = fts5.search("")
                # 如果返回结果，应该是空列表
                assert isinstance(results, list)
            except Exception:
                # 或者抛出异常，也是可以接受的行为
                pass
            
            # 搜索不存在的词
            results = fts5.search("不存在的词_xyz")
            assert len(results) == 0
            
            print(f"✅ 空输入测试完成")
            
        finally:
            fts5.close()

    def test_special_characters(self):
        """测试特殊字符"""
        import random
        db_id = f"memdb_boundary_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        db_path = create_unified_db(db_id)
        fts5 = FTS5Search(db_path=db_path)
        
        try:
            # 特殊字符内容
            special_content = "特殊字符：!@#$%^&*()_+-=[]{}|;':\",./<>?"
            fts5.insert("/test/special", special_content, "NOTE")
            
            results = fts5.search("特殊字符")
            assert len(results) >= 1
            
            print(f"✅ 特殊字符测试完成")
            
        finally:
            fts5.close()

    def test_unicode_content(self):
        """测试 Unicode 内容"""
        import random
        db_id = f"memdb_boundary_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        kg = KnowledgeGraphV2(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            # Unicode 概念名
            kg.add_concept("日本語概念", "category")
            kg.add_concept("한국어 개념", "category")
            kg.add_concept("العربية مفهوم", "category")
            
            stats = kg.get_stats()
            assert stats["concept_count"] == 3
            
            print(f"✅ Unicode 内容测试完成")
            
        finally:
            kg.close()

    def test_very_long_content(self):
        """测试超长内容"""
        import random
        db_id = f"memdb_boundary_{int(time.time()*1000)}_{random.randint(0, 10000)}"
        wal = WALLogger(db_path=f"file:{db_id}?mode=memory&cache=private")
        
        try:
            # 100 万字内容
            long_content = "A" * 1000000
            
            record_id = wal.log_operation(
                operation="CREATE",
                v_path="/test/long",
                content=long_content,
                source_agent="main",
                evidence="test"
            )
            
            assert record_id > 0
            
            latest = wal.get_latest_version("/test/long")
            assert len(latest["content"]) == 1000000
            
            print(f"✅ 超长内容测试完成（100 万字）")
            
        finally:
            wal.close()
