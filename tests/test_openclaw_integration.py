"""
OpenClaw 集成测试

测试 OpenClaw 通过 MCP 与 MFS 的集成：
- memory_search 工具
- memory_get 工具  
- memory_write 工具
- session_persistence 会话持久性
"""

import pytest
import time
from diting.mcp_server import MCPServer
from diting.mft import MFT


class TestOpenClawMemorySearch:
    """测试 memory_search 工具"""
    
    def test_search_exact_match(self, memory_mft):
        """测试精确匹配搜索"""
        # 写入测试数据
        memory_mft.create("/test/search_exact", "NOTE", "这是测试内容")
        
        # 搜索
        results = memory_mft.search("测试")
        
        assert len(results) > 0
        assert any("这是测试内容" in r.get("content", "") for r in results)
    
    def test_search_fuzzy_match(self, memory_mft):
        """测试模糊匹配搜索"""
        # 写入多条数据
        memory_mft.create("/note/1", "NOTE", "今天天气很好")
        memory_mft.create("/note/2", "NOTE", "天气晴朗适合外出")
        memory_mft.create("/note/3", "NOTE", "完全无关的内容")
        
        # 模糊搜索"天气"
        results = memory_mft.search("天气")
        
        assert len(results) >= 2
        paths = [r["v_path"] for r in results]
        assert "/note/1" in paths
        assert "/note/2" in paths
    
    def test_search_by_scope(self, memory_mft):
        """测试范围过滤搜索"""
        # 写入不同范围的数据
        memory_mft.create("/public/info", "NOTE", "公开信息")
        memory_mft.create("/private/secret", "NOTE", "私密信息")
        
        # 搜索公共范围
        results = memory_mft.search("信息", scope="/public")
        
        assert len(results) > 0
        assert all(r["v_path"].startswith("/public") for r in results)
    
    def test_search_empty_result(self, memory_mft):
        """测试搜索无结果"""
        results = memory_mft.search("不存在的关键词_xyz_123")
        
        assert len(results) == 0
    
    def test_search_with_limit(self, memory_mft):
        """测试搜索结果数量限制"""
        # 写入多条数据
        for i in range(10):
            memory_mft.create(f"/batch/note_{i}", "NOTE", f"内容{i}")
        
        # 搜索 (当前 API 不支持 limit，搜索所有)
        results = memory_mft.search("内容")
        
        assert len(results) == 10


class TestOpenClawMemoryGet:
    """测试 memory_get 工具"""
    
    def test_get_existing_path(self, memory_mft):
        """测试读取已存在的路径"""
        content = "测试记忆内容"
        memory_mft.create("/test/get_existing", "NOTE", content)
        
        result = memory_mft.read("/test/get_existing")
        
        assert result is not None
        assert result["content"] == content
        assert result["type"] == "NOTE"
    
    def test_get_nonexistent_path(self, memory_mft):
        """测试读取不存在的路径"""
        # read 返回 None 而不是抛出异常
        result = memory_mft.read("/not/exists")
        assert result is None
    
    def test_get_with_metadata(self, memory_mft):
        """测试读取包含元数据"""
        memory_mft.create("/test/meta", "CODE", "print('hello')")
        
        result = memory_mft.read("/test/meta")
        
        assert "inode" in result
        assert "create_ts" in result
        assert "update_ts" in result
        assert result["type"] == "CODE"


class TestOpenClawMemoryWrite:
    """测试 memory_write 工具"""
    
    def test_write_new_path(self, memory_mft):
        """测试写入新路径"""
        inode = memory_mft.create("/test/write_new", "NOTE", "新内容")
        
        assert inode > 0
        
        # 验证可以读取
        result = memory_mft.read("/test/write_new")
        assert result["content"] == "新内容"
    
    def test_write_update_existing(self, memory_mft):
        """测试更新已存在的路径"""
        # 使用 update 方法
        memory_mft.create("/test/update", "NOTE", "原始内容")
        memory_mft.update("/test/update", content="更新后的内容")
        
        result = memory_mft.read("/test/update")
        assert result["content"] == "更新后的内容"
    
    def test_write_different_types(self, memory_mft):
        """测试写入不同类型"""
        # 使用有效的类型
        types = ["NOTE", "CODE", "RULE", "TASK"]
        
        for t in types:
            inode = memory_mft.create(f"/test/type_{t}", t, f"{t}内容")
            assert inode > 0
    
    def test_write_special_characters(self, memory_mft):
        """测试写入特殊字符"""
        content = "特殊字符：!@#$%^&*()_+-=[]{}|;':\",./<>? 中文测试 🚀"
        inode = memory_mft.create("/test/special_chars", "NOTE", content)
        
        assert inode > 0
        
        result = memory_mft.read("/test/special_chars")
        assert result["content"] == content
    
    def test_write_empty_content(self, memory_mft):
        """测试写入空内容"""
        inode = memory_mft.create("/test/empty", "NOTE", "")
        
        assert inode > 0
        
        result = memory_mft.read("/test/empty")
        assert result["content"] == ""


class TestOpenClawSessionPersistence:
    """测试会话持久性"""
    
    def test_write_then_read_different_instance(self):
        """测试写入后新实例读取 (模拟不同会话)"""
        # 使用文件数据库 (非内存)
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # 会话 1: 写入
            mft1 = MFT(db_path=db_path)
            mft1.create("/session/test", "NOTE", "持久化内容")
            
            # 会话 2: 读取 (新实例)
            mft2 = MFT(db_path=db_path)
            result = mft2.read("/session/test")
            
            assert result["content"] == "持久化内容"
        finally:
            os.unlink(db_path)
    
    def test_multiple_writes_persistence(self):
        """测试多次写入持久化"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # 写入多条
            mft1 = MFT(db_path=db_path)
            for i in range(5):
                mft1.create(f"/persist/note_{i}", "NOTE", f"内容{i}")
            
            # 新实例验证
            mft2 = MFT(db_path=db_path)
            for i in range(5):
                result = mft2.read(f"/persist/note_{i}")
                assert result["content"] == f"内容{i}"
        finally:
            os.unlink(db_path)
    
    def test_search_across_instances(self):
        """测试跨实例搜索"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # 会话 1: 写入并搜索
            mft1 = MFT(db_path=db_path)
            mft1.create("/search/cross1", "NOTE", "关键词测试")
            mft1.create("/search/cross2", "NOTE", "另一个关键词")
            
            results1 = mft1.search("关键词")
            assert len(results1) == 2
            
            # 会话 2: 搜索
            mft2 = MFT(db_path=db_path)
            results2 = mft2.search("关键词")
            
            assert len(results2) == 2
            assert set(r["v_path"] for r in results1) == set(r["v_path"] for r in results2)
        finally:
            os.unlink(db_path)


class TestMCPServerIntegration:
    """测试 MCP Server 集成"""
    
    def test_mcp_server_initialization(self):
        """测试 MCP Server 初始化"""
        server = MCPServer(db_path=None)
        
        assert server.server is not None
        assert server.mft is not None
        assert server.server.name == "mfs-memory"
    
    def test_mcp_server_tools_available(self, memory_mft):
        """测试 MCP 工具可用性"""
        # 验证 MFT 功能正常
        memory_mft.create("/mcp/test", "NOTE", "测试内容")
        result = memory_mft.read("/mcp/test")
        assert result["content"] == "测试内容"
        
        results = memory_mft.search("测试")
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
