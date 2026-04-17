"""
MFT 单元测试

TDD 流程：先写测试，再写实现
"""

import pytest
from diting.mft import MFT
from diting.errors import MFTInvalidPathError, MFTNotFoundError


class TestMFTCreate:
    """测试 MFT 创建功能"""
    
    def test_create_basic(self, memory_mft):
        """测试基本创建功能"""
        inode = memory_mft.create("/test/rules", "RULE", "测试规则")
        assert inode > 0
    
    def test_create_with_different_types(self, memory_mft):
        """测试创建不同类型的记忆"""
        inode1 = memory_mft.create("/note/1", "NOTE", "笔记内容")
        inode2 = memory_mft.create("/code/main.py", "CODE", "print('hello')")
        inode3 = memory_mft.create("/rule/auth", "RULE", "认证规则")
        
        assert inode1 > 0
        assert inode2 > 0
        assert inode3 > 0
        assert inode1 != inode2 != inode3
    
    def test_create_invalid_path(self, memory_mft):
        """测试创建时路径必须以 / 开头"""
        with pytest.raises(MFTInvalidPathError):
            memory_mft.create("invalid/path", "NOTE", "内容")
    
    def test_create_duplicate_path(self, memory_mft):
        """测试创建重复路径应该失败"""
        memory_mft.create("/test/unique", "NOTE", "内容 1")
        with pytest.raises(Exception):  # SQLite UNIQUE constraint
            memory_mft.create("/test/unique", "NOTE", "内容 2")


class TestMFTRead:
    """测试 MFT 读取功能"""
    
    def test_read_existing(self, memory_mft):
        """测试读取已存在的记忆"""
        memory_mft.create("/test/readme", "NOTE", "测试内容")
        result = memory_mft.read("/test/readme")
        
        assert result is not None
        assert result["v_path"] == "/test/readme"
        assert result["type"] == "NOTE"
        assert result["content"] == "测试内容"
        assert "inode" in result
        assert "create_ts" in result
        assert "update_ts" in result
        assert "status" in result
    
    def test_read_nonexistent(self, memory_mft):
        """测试读取不存在的记忆"""
        result = memory_mft.read("/nonexistent")
        assert result is None
    
    def test_read_deleted(self, memory_mft):
        """测试读取已删除的记忆"""
        memory_mft.create("/test/todelete", "NOTE", "内容")
        memory_mft.delete("/test/todelete")
        result = memory_mft.read("/test/todelete")
        assert result is None


class TestMFTUpdate:
    """测试 MFT 更新功能"""
    
    def test_update_existing(self, memory_mft):
        """测试更新已存在的记忆"""
        memory_mft.create("/test/update", "NOTE", "原始内容")
        success = memory_mft.update("/test/update", "新内容")
        
        assert success is True
        result = memory_mft.read("/test/update")
        assert result["content"] == "新内容"
    
    def test_update_nonexistent(self, memory_mft):
        """测试更新不存在的记忆"""
        success = memory_mft.update("/nonexistent", "新内容")
        assert success is False


class TestMFTDelete:
    """测试 MFT 删除功能"""
    
    def test_delete_existing(self, memory_mft):
        """测试删除已存在的记忆"""
        memory_mft.create("/test/delete", "NOTE", "内容")
        success = memory_mft.delete("/test/delete")
        
        assert success is True
        result = memory_mft.read("/test/delete")
        assert result is None
    
    def test_delete_nonexistent(self, memory_mft):
        """测试删除不存在的记忆"""
        success = memory_mft.delete("/nonexistent")
        assert success is False
    
    def test_delete_twice(self, memory_mft):
        """测试重复删除"""
        memory_mft.create("/test/del2", "NOTE", "内容")
        memory_mft.delete("/test/del2")
        success = memory_mft.delete("/test/del2")
        assert success is False


class TestMFTSearch:
    """测试 MFT 搜索功能"""
    
    def test_search_exact(self, memory_mft):
        """测试精确搜索"""
        memory_mft.create("/test/search1", "NOTE", "苹果")
        memory_mft.create("/test/search2", "NOTE", "香蕉")
        memory_mft.create("/test/search3", "NOTE", "橙子")
        
        results = memory_mft.search("苹果")
        assert len(results) == 1
        assert results[0]["content"] == "苹果"
    
    def test_search_partial(self, memory_mft):
        """测试模糊搜索"""
        memory_mft.create("/test/partial1", "NOTE", "测试内容 A")
        memory_mft.create("/test/partial2", "NOTE", "测试内容 B")
        memory_mft.create("/test/other", "NOTE", "其他内容")
        
        results = memory_mft.search("测试")
        assert len(results) == 2
    
    def test_search_with_scope(self, memory_mft):
        """测试带范围的搜索"""
        memory_mft.create("/scope1/item", "NOTE", "内容 1")
        memory_mft.create("/scope2/item", "NOTE", "内容 2")
        memory_mft.create("/scope1/other", "NOTE", "内容 3")
        
        results = memory_mft.search("内容", scope="/scope1")
        assert len(results) == 2
        assert all(r["v_path"].startswith("/scope1") for r in results)
    
    def test_search_no_results(self, memory_mft):
        """测试搜索无结果"""
        results = memory_mft.search("不存在的关键词")
        assert len(results) == 0
    
    def test_search_excludes_deleted(self, memory_mft):
        """测试搜索排除已删除的记忆"""
        memory_mft.create("/test/tosearch", "NOTE", "关键词")
        memory_mft.create("/test/todelete", "NOTE", "关键词")
        memory_mft.delete("/test/todelete")
        
        results = memory_mft.search("关键词")
        assert len(results) == 1
        assert results[0]["v_path"] == "/test/tosearch"


class TestMFTListByType:
    """测试按类型列出功能"""
    
    def test_list_by_type(self, memory_mft):
        """测试按类型列出记忆"""
        memory_mft.create("/note/1", "NOTE", "笔记 1")
        memory_mft.create("/note/2", "NOTE", "笔记 2")
        memory_mft.create("/rule/1", "RULE", "规则 1")
        memory_mft.create("/code/1", "CODE", "代码 1")
        
        notes = memory_mft.list_by_type("NOTE")
        rules = memory_mft.list_by_type("RULE")
        codes = memory_mft.list_by_type("CODE")
        
        assert len(notes) == 2
        assert len(rules) == 1
        assert len(codes) == 1
    
    def test_list_by_type_empty(self, memory_mft):
        """测试列出不存在的类型"""
        results = memory_mft.list_by_type("NONEXISTENT")
        assert len(results) == 0


class TestMFTDatabasePersistence:
    """测试数据库持久化"""
    
    def test_persistence_with_file_db(self, temp_db):
        """测试文件数据库持久化"""
        # 创建 MFT 并写入数据
        mft1 = MFT(temp_db)
        inode = mft1.create("/persist/test", "NOTE", "持久化测试")
        mft1.close()
        
        # 重新打开数据库
        mft2 = MFT(temp_db)
        result = mft2.read("/persist/test")
        
        assert result is not None
        assert result["content"] == "持久化测试"
        mft2.close()
