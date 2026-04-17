"""
MFT 性能测试

测试 LRU 缓存和搜索性能优化
"""

import pytest
import time
from diting.mft import MFT, LRUCache


class TestLRUCache:
    """测试 LRU 缓存实现"""
    
    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        cache = LRUCache(capacity=3)
        
        # 添加数据
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # 获取数据
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # 获取不存在的数据
        assert cache.get("key4") is None
    
    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰机制"""
        cache = LRUCache(capacity=3)
        
        # 添加 3 个数据
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # 添加第 4 个数据，应该淘汰 key1
        cache.put("key4", "value4")
        
        # key1 应该被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_lru_order_update(self):
        """测试访问时更新 LRU 顺序"""
        cache = LRUCache(capacity=3)
        
        # 添加数据
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # 访问 key1，使其成为最近使用
        cache.get("key1")
        
        # 添加新数据，应该淘汰 key2（最久未使用）
        cache.put("key4", "value4")
        
        # key2 应该被淘汰，key1 还在
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_update_existing(self):
        """测试更新已存在的键"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # 更新 key1
        cache.put("key1", "updated_value1")
        
        assert cache.get("key1") == "updated_value1"
        assert cache.get("key2") == "value2"
    
    def test_cache_delete(self):
        """测试删除操作"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # 删除 key1
        cache.delete("key1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_cache_clear(self):
        """测试清空操作"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # 清空缓存
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
    
    def test_cache_stats(self):
        """测试统计信息"""
        cache = LRUCache(capacity=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # 命中
        cache.get("key1")
        cache.get("key2")
        
        # 未命中
        cache.get("key3")
        cache.get("key4")
        
        stats = cache.get_stats()
        
        assert stats["capacity"] == 3
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert "hit_rate" in stats


class TestMFTCacheIntegration:
    """测试 MFT 与 LRU 缓存的集成"""
    
    def test_mft_read_caching(self, memory_mft):
        """测试 MFT 读取缓存"""
        # 创建数据
        memory_mft.create("/cache/test", "NOTE", "Cached content")
        
        # 第一次读取（缓存未命中）
        result1 = memory_mft.read("/cache/test")
        assert result1 is not None
        assert result1["content"] == "Cached content"
        
        # 第二次读取（缓存命中）
        result2 = memory_mft.read("/cache/test")
        assert result2 is not None
        assert result2["content"] == "Cached content"
        
        # 验证缓存统计
        stats = memory_mft.get_cache_stats()
        assert stats["hits"] >= 1  # 至少有一次命中
    
    def test_mft_write_cache_invalidation(self, memory_mft):
        """测试 MFT 写入时缓存失效"""
        # 创建数据
        memory_mft.create("/cache/update_test", "NOTE", "Original content")
        
        # 读取以填充缓存
        result1 = memory_mft.read("/cache/update_test")
        assert result1["content"] == "Original content"
        
        # 更新数据
        memory_mft.update("/cache/update_test", "Updated content")
        
        # 再次读取，应该看到更新后的内容
        result2 = memory_mft.read("/cache/update_test")
        assert result2 is not None
        assert result2["content"] == "Updated content"
    
    def test_mft_delete_cache_invalidation(self, memory_mft):
        """测试 MFT 删除时缓存失效"""
        # 创建数据
        memory_mft.create("/cache/delete_test", "NOTE", "To be deleted")
        
        # 读取以填充缓存
        result1 = memory_mft.read("/cache/delete_test")
        assert result1 is not None
        
        # 删除数据
        memory_mft.delete("/cache/delete_test")
        
        # 再次读取，应该返回 None
        result2 = memory_mft.read("/cache/delete_test")
        assert result2 is None
    
    def test_mft_cache_stats(self, memory_mft):
        """测试 MFT 缓存统计"""
        # 创建多个数据
        for i in range(5):
            memory_mft.create(f"/cache/item{i}", "NOTE", f"Content {i}")
        
        # 读取部分数据
        for i in range(3):
            memory_mft.read(f"/cache/item{i}")
        
        # 获取缓存统计
        stats = memory_mft.get_cache_stats()
        
        # 注意：create 操作也会预填充缓存，所以实际缓存大小是 5
        assert stats["size"] >= 3  # 至少缓存了 3 个条目
        assert stats["hits"] >= 3  # 至少 3 次命中
        assert stats["capacity"] == 100  # 默认容量
    
    def test_mft_cache_clear(self, memory_mft):
        """测试 MFT 清空缓存"""
        # 创建并读取数据
        memory_mft.create("/cache/clear_test", "NOTE", "Content")
        memory_mft.read("/cache/clear_test")
        
        # 验证缓存有数据
        stats1 = memory_mft.get_cache_stats()
        assert stats1["size"] > 0
        
        # 清空缓存
        memory_mft.clear_cache()
        
        # 验证缓存已清空
        stats2 = memory_mft.get_cache_stats()
        assert stats2["size"] == 0


class TestSearchPerformance:
    """测试搜索性能"""
    
    def test_search_with_cache(self, temp_db):
        """测试带缓存的搜索性能"""
        mft = MFT(temp_db)
        
        # 创建大量数据
        num_items = 100
        for i in range(num_items):
            mft.create(f"/perf/item{i}", "NOTE", f"Searchable content {i}")
        
        # 第一次搜索（无缓存）
        start_time = time.time()
        results1 = mft.search("Searchable content 50")
        time1 = time.time() - start_time
        
        assert len(results1) == 1
        
        # 读取结果以填充缓存
        for result in results1:
            mft.read(result["v_path"])
        
        # 第二次搜索（有缓存）
        start_time = time.time()
        results2 = mft.search("Searchable content 50")
        time2 = time.time() - start_time
        
        assert len(results2) == 1
        
        # 验证缓存命中率提升
        stats = mft.get_cache_stats()
        assert stats["hits"] > 0
        
        mft.close()
    
    def test_search_by_type_performance(self, temp_db):
        """测试按类型搜索的性能"""
        mft = MFT(temp_db)
        
        # 创建不同类型的数据
        for i in range(50):
            mft.create(f"/perf/note{i}", "NOTE", f"Note content {i}")
        
        for i in range(50):
            mft.create(f"/perf/rule{i}", "RULE", f"Rule content {i}")
        
        for i in range(50):
            mft.create(f"/perf/code{i}", "CODE", f"Code content {i}")
        
        # 按类型搜索
        start_time = time.time()
        notes = mft.search_by_type("NOTE")
        time_note = time.time() - start_time
        
        start_time = time.time()
        rules = mft.search_by_type("RULE")
        time_rule = time.time() - start_time
        
        assert len(notes) == 50
        assert len(rules) == 50
        
        mft.close()
    
    def test_list_by_status_performance(self, temp_db):
        """测试按状态列出的性能"""
        mft = MFT(temp_db)
        
        # 创建不同状态的数据
        for i in range(30):
            mft.create(f"/status/active{i}", "NOTE", f"Active {i}", status="active")
        
        for i in range(20):
            mft.create(f"/status/archived{i}", "NOTE", f"Archived {i}", status="archived")
        
        # 按状态列出
        active_items = mft.list_by_status("active")
        archived_items = mft.list_by_status("archived")
        
        assert len(active_items) == 30
        assert len(archived_items) == 20
        
        mft.close()


class TestMFTStats:
    """测试 MFT 统计功能"""
    
    def test_get_stats(self, memory_mft):
        """测试获取统计信息"""
        # 创建不同类型的数据
        for i in range(5):
            memory_mft.create(f"/stats/note{i}", "NOTE", f"Note {i}")
        
        for i in range(3):
            memory_mft.create(f"/stats/rule{i}", "RULE", f"Rule {i}")
        
        for i in range(2):
            memory_mft.create(f"/stats/code{i}", "CODE", f"Code {i}")
        
        # 获取统计
        stats = memory_mft.get_stats()
        
        assert stats["total"] == 10
        assert stats["by_type"]["NOTE"] == 5
        assert stats["by_type"]["RULE"] == 3
        assert stats["by_type"]["CODE"] == 2
        assert "active" in stats["by_status"]
