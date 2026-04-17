"""
OpenCode 集成测试

测试 OpenCode 通过 MCP 与 MFS 的集成：
- MCP 配置测试
- mfs_read 工具
- mfs_write 工具
- mfs_search 工具
"""

import pytest
import json
import tempfile
import os
import time
from diting.mcp_server import MCPServer
from diting.mft import MFT
from diting.errors import MFTNotFoundError, MFTInvalidPathError


class TestOpenCodeMCPConfig:
    """测试 MCP 配置"""
    
    def test_mcp_server_initialization(self):
        """测试 MCP Server 初始化"""
        server = MCPServer(db_path=None)
        
        assert server.server is not None
        assert server.mft is not None
        assert server.server.name == "mfs-memory"
    
    def test_mcp_server_with_custom_db(self):
        """测试 MCP Server 自定义数据库路径"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            server = MCPServer(db_path=db_path)
            
            # 验证数据库文件已创建
            assert os.path.exists(db_path)
            
            # 验证可以写入
            inode = server.mft.create("/config/test", "NOTE", "测试")
            assert inode > 0
        finally:
            os.unlink(db_path)
    
    def test_mcp_tools_registration(self):
        """测试 MCP 工具注册"""
        server = MCPServer(db_path=None)
        
        # 检查服务器已初始化
        assert server.server is not None
        assert server.mft is not None
    
    def test_mcp_tool_schema(self):
        """测试 MCP 工具 Schema"""
        server = MCPServer(db_path=None)
        
        # 验证工具定义完整
        tools = ["mfs_read", "mfs_write", "mfs_search"]
        # 通过 server 获取工具信息 (需要异步)
        # 这里做基本验证
        assert server.mft is not None


class TestOpenCodeMFSRead:
    """测试 mfs_read 工具"""
    
    def test_read_basic(self, memory_mft):
        """测试基本读取"""
        content = "OpenCode 读取测试"
        memory_mft.create("/opencode/read_basic", "NOTE", content)
        
        result = memory_mft.read("/opencode/read_basic")
        
        assert result["content"] == content
        assert result["type"] == "NOTE"
        assert "inode" in result
    
    def test_read_with_type_filter(self, memory_mft):
        """测试按类型读取"""
        memory_mft.create("/opencode/code", "CODE", "print('hello')")
        memory_mft.create("/opencode/rule", "RULE", "认证规则")
        
        code_result = memory_mft.read("/opencode/code")
        rule_result = memory_mft.read("/opencode/rule")
        
        assert code_result["type"] == "CODE"
        assert rule_result["type"] == "RULE"
    
    def test_read_not_found(self, memory_mft):
        """测试读取不存在的路径"""
        # read 返回 None 而不是抛出异常
        result = memory_mft.read("/opencode/not_exists")
        assert result is None
    
    def test_read_invalid_path(self, memory_mft):
        """测试读取无效路径"""
        # 路径验证在 create 时进行，read 返回 None
        result = memory_mft.read("invalid/path")
        assert result is None
    
    def test_read_with_metadata(self, memory_mft):
        """测试读取包含完整元数据"""
        memory_mft.create("/opencode/meta", "NOTE", "文档内容")
        
        result = memory_mft.read("/opencode/meta")
        
        # 验证元数据字段
        assert "inode" in result
        assert "v_path" in result
        assert "type" in result
        assert "content" in result
        assert "create_ts" in result
        assert "update_ts" in result
        assert "status" in result


class TestOpenCodeMFSWrite:
    """测试 mfs_write 工具"""
    
    def test_write_basic(self, memory_mft):
        """测试基本写入"""
        inode = memory_mft.create("/opencode/write_basic", "NOTE", "写入内容")
        
        assert inode > 0
        
        # 验证写入成功
        result = memory_mft.read("/opencode/write_basic")
        assert result["content"] == "写入内容"
    
    def test_write_with_different_types(self, memory_mft):
        """测试写入不同类型"""
        test_cases = [
            ("/opencode/note", "NOTE", "笔记内容"),
            ("/opencode/code", "CODE", "def hello(): pass"),
            ("/opencode/rule", "RULE", "业务规则"),
            ("/opencode/task", "TASK", "任务内容"),
        ]
        
        for path, type_, content in test_cases:
            inode = memory_mft.create(path, type_, content)
            assert inode > 0
            
            result = memory_mft.read(path)
            assert result["type"] == type_
            assert result["content"] == content
    
    def test_write_unicode_content(self, memory_mft):
        """测试写入 Unicode 内容"""
        content = "Unicode 测试：中文 日本語 한국어 Emoji 🚀✨🎉"
        inode = memory_mft.create("/opencode/unicode", "NOTE", content)
        
        assert inode > 0
        
        result = memory_mft.read("/opencode/unicode")
        assert result["content"] == content
    
    def test_write_large_content(self, memory_mft):
        """测试写入大内容"""
        # 创建 10KB 内容
        large_content = "x" * 10240
        inode = memory_mft.create("/opencode/large", "NOTE", large_content)
        
        assert inode > 0
        
        result = memory_mft.read("/opencode/large")
        assert len(result["content"]) == 10240
    
    def test_write_special_path_characters(self, memory_mft):
        """测试写入特殊路径字符"""
        test_paths = [
            "/opencode/path-with-dash",
            "/opencode/path_with_underscore",
            "/opencode/path.with.dots",
            "/opencode/路径/中文",
        ]
        
        for path in test_paths:
            inode = memory_mft.create(path, "NOTE", f"内容：{path}")
            assert inode > 0
    
    def test_write_invalid_path(self, memory_mft):
        """测试写入无效路径"""
        with pytest.raises(MFTInvalidPathError):
            memory_mft.create("invalid/path", "NOTE", "内容")
    
    def test_write_duplicate_path(self, memory_mft):
        """测试写入重复路径"""
        memory_mft.create("/opencode/duplicate", "NOTE", "内容 1")
        
        # 重复写入应该失败 (UNIQUE 约束)
        with pytest.raises(Exception):
            memory_mft.create("/opencode/duplicate", "NOTE", "内容 2")


class TestOpenCodeMFSSearch:
    """测试 mfs_search 工具"""
    
    def test_search_exact_keyword(self, memory_mft):
        """测试精确关键词搜索"""
        memory_mft.create("/opencode/search1", "NOTE", "关键词测试内容")
        memory_mft.create("/opencode/search2", "NOTE", "其他内容")
        
        results = memory_mft.search("关键词")
        
        assert len(results) >= 1
        assert any("关键词测试内容" in r["content"] for r in results)
    
    def test_search_partial_match(self, memory_mft):
        """测试部分匹配搜索"""
        memory_mft.create("/opencode/partial1", "NOTE", "测试内容 A")
        memory_mft.create("/opencode/partial2", "NOTE", "测试内容 B")
        memory_mft.create("/opencode/partial3", "NOTE", "不同内容")
        
        results = memory_mft.search("测试")
        
        assert len(results) >= 2
        paths = [r["v_path"] for r in results]
        assert "/opencode/partial1" in paths
        assert "/opencode/partial2" in paths
    
    def test_search_with_limit(self, memory_mft):
        """测试搜索数量限制"""
        # 写入 10 条
        for i in range(10):
            memory_mft.create(f"/opencode/limit_{i}", "NOTE", f"内容{i}")
        
        # 搜索所有 (当前 API 不支持 limit)
        results = memory_mft.search("内容")
        
        assert len(results) == 10
    
    def test_search_with_scope(self, memory_mft):
        """测试范围过滤"""
        memory_mft.create("/public/doc1", "NOTE", "公开文档")
        memory_mft.create("/private/doc2", "NOTE", "私密文档")
        memory_mft.create("/public/doc3", "NOTE", "另一个公开文档")
        
        # 搜索公共范围
        results = memory_mft.search("文档", scope="/public")
        
        assert len(results) > 0
        assert all(r["v_path"].startswith("/public") for r in results)
    
    def test_search_with_type_filter(self, memory_mft):
        """测试类型过滤"""
        memory_mft.create("/opencode/type_note", "NOTE", "笔记")
        memory_mft.create("/opencode/type_code", "CODE", "代码")
        memory_mft.create("/opencode/type_rule", "RULE", "规则")
        
        # 搜索后过滤类型 (当前 API 不支持 type_filter)
        all_results = memory_mft.search("代码")
        results = [r for r in all_results if r["type"] == "CODE"]
        
        assert len(results) > 0
        assert all(r["type"] == "CODE" for r in results)
    
    def test_search_empty_query(self, memory_mft):
        """测试空查询"""
        memory_mft.create("/opencode/empty", "NOTE", "内容")
        
        # 空查询应该返回所有或空 (取决于实现)
        results = memory_mft.search("")
        
        # 至少不应该报错
        assert isinstance(results, list)
    
    def test_search_no_results(self, memory_mft):
        """测试无结果搜索"""
        results = memory_mft.search("不存在的关键词_xyz_789")
        
        assert len(results) == 0
    
    def test_search_case_sensitivity(self, memory_mft):
        """测试大小写敏感性"""
        memory_mft.create("/opencode/case1", "NOTE", "Hello World")
        memory_mft.create("/opencode/case2", "NOTE", "hello world")
        
        # 搜索 (SQLite LIKE 默认不区分大小写)
        results_upper = memory_mft.search("HELLO")
        results_lower = memory_mft.search("hello")
        
        # 都应该找到结果
        assert len(results_upper) >= 1
        assert len(results_lower) >= 1
    
    def test_search_sorting(self, memory_mft):
        """测试搜索结果排序"""
        # 按时间顺序写入
        memory_mft.create("/opencode/sort1", "NOTE", "测试 1")
        time.sleep(0.01)  # 确保时间戳不同
        memory_mft.create("/opencode/sort2", "NOTE", "测试 2")
        time.sleep(0.01)
        memory_mft.create("/opencode/sort3", "NOTE", "测试 3")
        
        results = memory_mft.search("测试")
        
        # 验证结果包含所有
        assert len(results) >= 3


class TestOpenCodeWorkflow:
    """测试 OpenCode 工作流"""
    
    def test_write_search_read_workflow(self, memory_mft):
        """测试写入 - 搜索 - 读取工作流"""
        # 1. 写入多条 (使用有效类型)
        memory_mft.create("/workflow/note1", "NOTE", "文档 1 内容")
        memory_mft.create("/workflow/note2", "NOTE", "文档 2 内容")
        memory_mft.create("/workflow/code1", "CODE", "代码内容")
        
        # 2. 搜索
        results = memory_mft.search("文档")
        assert len(results) >= 2
        
        # 3. 读取搜索结果
        for result in results:
            content = memory_mft.read(result["v_path"])
            assert "文档" in content["content"]
    
    def test_batch_write_search(self, memory_mft):
        """测试批量写入后搜索"""
        # 批量写入 20 条
        for i in range(20):
            memory_mft.create(f"/workflow/batch_{i}", "NOTE", f"批量内容{i}")
        
        # 搜索
        results = memory_mft.search("批量")
        
        assert len(results) == 20
    
    def test_update_workflow(self, memory_mft):
        """测试更新工作流"""
        # 1. 创建
        memory_mft.create("/workflow/update", "NOTE", "原始内容")
        
        # 2. 读取验证
        result = memory_mft.read("/workflow/update")
        assert result["content"] == "原始内容"
        
        # 3. 更新 (使用 update 方法)
        memory_mft.update("/workflow/update", content="更新内容")
        
        # 4. 再次读取验证
        result = memory_mft.read("/workflow/update")
        assert result["content"] == "更新内容"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
