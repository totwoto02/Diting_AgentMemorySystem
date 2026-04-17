"""
测试性能优化模块（Phase 2）

TDD 第一步：先写测试
"""

import pytest
from diting.cache import LRUCache, ConnectionPool


class TestLRUCache:
    """测试 LRU 缓存"""

    def test_put_and_get(self):
        """测试放入和获取"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None

    def test_capacity_limit(self):
        """测试容量限制"""
        cache = LRUCache(capacity=2)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # 超出容量，key1 应该被淘汰
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = LRUCache(capacity=2)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # 访问 key1，使其成为最近使用
        cache.put("key3", "value3")  # key2 应该被淘汰
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_delete(self):
        """测试删除"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.delete("key1")
        
        assert cache.get("key1") is None

    def test_clear(self):
        """测试清空"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache.cache) == 0

    def test_stats(self):
        """测试统计信息"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.get("key1")
        cache.get("key2")  # miss
        
        stats = cache.get_stats()
        
        assert stats["capacity"] == 3
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert "hit_rate" in stats


class TestConnectionPool:
    """测试连接池"""

    def test_acquire_and_release(self):
        """测试获取和释放连接"""
        pool = ConnectionPool(db_path=":memory:", max_connections=3)
        try:
            conn = pool.acquire()
            assert conn is not None
            
            # 验证连接可用
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
            
            pool.release(conn)
        finally:
            pool.close()

    def test_max_connections(self):
        """测试最大连接数"""
        pool = ConnectionPool(db_path=":memory:", max_connections=2)
        try:
            conn1 = pool.acquire()
            conn2 = pool.acquire()
            
            # 第三个获取应该等待或返回 None（取决于实现）
            conn3 = pool.acquire(timeout=0.1)
            
            # 释放
            pool.release(conn1)
            pool.release(conn2)
            if conn3:
                pool.release(conn3)
        finally:
            pool.close()

    def test_context_manager(self):
        """测试上下文管理器"""
        pool = ConnectionPool(db_path=":memory:", max_connections=3)
        try:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
            
            # 连接应该已释放回池
            assert pool.available.qsize() == pool.max_connections
        finally:
            pool.close()

    def test_stats(self):
        """测试统计信息"""
        pool = ConnectionPool(db_path=":memory:", max_connections=3)
        try:
            conn = pool.acquire()
            pool.release(conn)
            
            stats = pool.get_stats()
            
            assert stats["max_connections"] == 3
            assert stats["active_connections"] == 0
            assert "total_acquired" in stats
        finally:
            pool.close()
