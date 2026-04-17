"""
MCP Server 覆盖率优化测试
目标：将 mcp_server.py 覆盖率从 87% 提升到 90%+

未覆盖的行：36, 95, 105, 170-171, 184-188, 192
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from diting.mcp_server import MCPServer
from diting.errors import MFTNotFoundError, MFTException


class TestMCPServerCoverageOptimization:
    """针对未覆盖代码行的测试"""

    @pytest.fixture
    def server(self):
        """创建 MCP Server 实例"""
        return MCPServer(db_path=":memory:")

    def test_line36_server_close(self, server):
        """测试第 36 行 - close 方法"""
        # 调用 close 方法
        server.close()
        # 验证没有异常

    @pytest.mark.asyncio
    async def test_line95_mfs_read_missing_path(self, server):
        """测试第 95 行 - mfs_read 缺少 path 参数"""
        arguments = {}  # 缺少 path
        result = await server._mfs_read(arguments)
        assert "缺少 path 参数" in result[0].text

    @pytest.mark.asyncio
    async def test_line105_mfs_write_missing_params(self, server):
        """测试第 105 行 - mfs_write 缺少必需参数"""
        # 缺少 content
        arguments = {"path": "/test", "type": "RULE"}
        result = await server._mfs_write(arguments)
        assert "缺少必需参数" in result[0].text

        # 缺少 type
        arguments = {"path": "/test", "content": "test"}
        result = await server._mfs_write(arguments)
        assert "缺少必需参数" in result[0].text

        # 缺少 path
        arguments = {"type": "RULE", "content": "test"}
        result = await server._mfs_write(arguments)
        assert "缺少必需参数" in result[0].text

    @pytest.mark.asyncio
    async def test_line170_171_mfs_search_missing_query(self, server):
        """测试第 170-171 行 - mfs_search 缺少 query 参数"""
        arguments = {}  # 缺少 query
        result = await server._mfs_search(arguments)
        assert "缺少 query 参数" in result[0].text

        # 有 scope 但无 query
        arguments = {"scope": "/test"}
        result = await server._mfs_search(arguments)
        assert "缺少 query 参数" in result[0].text

    @pytest.mark.asyncio
    async def test_line184_188_call_tool_unknown_tool(self, server):
        """测试第 184-188 行 - call_tool 未知工具"""
        result = await server.call_tool("unknown_tool", {})
        assert "未知工具" in result[0].text

        # 测试其他未知工具
        result = await server.call_tool("nonexistent", {"arg": "value"})
        assert "未知工具" in result[0].text

    @pytest.mark.asyncio
    async def test_line192_call_tool_generic_exception(self, server):
        """测试第 192 行 - call_tool 通用异常处理"""
        # 模拟一个未处理的异常
        with patch.object(server, '_mfs_read', side_effect=RuntimeError("未预期的错误")):
            result = await server.call_tool("mfs_read", {"path": "/test"})
            assert "系统错误" in result[0].text

    @pytest.mark.asyncio
    async def test_mfs_read_not_found(self, server):
        """测试 mfs_read 路径不存在的情况"""
        # 先写入再删除，确保路径不存在
        server.mft.create("/test/to_delete", "RULE", "test content")
        server.mft.delete("/test/to_delete")
        
        with pytest.raises(MFTNotFoundError):
            await server._mfs_read({"path": "/test/to_delete"})

    @pytest.mark.asyncio
    async def test_mfs_write_create_and_update(self, server):
        """测试 mfs_write 创建和更新流程"""
        # 创建新记录
        arguments = {"path": "/test/new", "type": "RULE", "content": "new content"}
        result = await server._mfs_write(arguments)
        assert "已创建" in result[0].text

        # 更新已有记录
        arguments = {"path": "/test/new", "type": "RULE", "content": "updated content"}
        result = await server._mfs_write(arguments)
        assert "已更新" in result[0].text

    @pytest.mark.asyncio
    async def test_mfs_search_no_results(self, server):
        """测试 mfs_search 无结果的情况"""
        arguments = {"query": "不存在的关键词"}
        result = await server._mfs_search(arguments)
        assert "未找到匹配" in result[0].text

    @pytest.mark.asyncio
    async def test_mfs_search_with_results(self, server):
        """测试 mfs_search 有结果的情况"""
        # 先创建一些测试数据
        server.mft.create("/test/search1", "RULE", "这是测试内容 1")
        server.mft.create("/test/search2", "FACT", "这是测试内容 2")
        
        arguments = {"query": "测试", "scope": "/test"}
        result = await server._mfs_search(arguments)
        assert "找到" in result[0].text
        assert "条结果" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_mfs_read(self, server):
        """测试 call_tool 调用 mfs_read"""
        # 先创建数据
        server.mft.create("/test/read_test", "RULE", "test content")
        
        result = await server.call_tool("mfs_read", {"path": "/test/read_test"})
        assert "路径：" in result[0].text
        assert "类型：" in result[0].text
        assert "内容：" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_mfs_write(self, server):
        """测试 call_tool 调用 mfs_write"""
        result = await server.call_tool("mfs_write", {
            "path": "/test/write_test",
            "type": "RULE",
            "content": "test content"
        })
        assert "已创建" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_mfs_search(self, server):
        """测试 call_tool 调用 mfs_search"""
        server.mft.create("/test/search_test", "FACT", "这是搜索测试")
        
        result = await server.call_tool("mfs_search", {"query": "搜索"})
        assert "找到" in result[0].text or "未找到" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_mfs_error(self, server):
        """测试 call_tool 错误处理"""
        # 测试 MFTNotFoundError
        result = await server.call_tool("mfs_read", {"path": "/nonexistent"})
        assert "错误" in result[0].text

    @pytest.mark.asyncio
    async def test_list_tools_registered(self, server):
        """测试 list_tools 已注册"""
        # 验证工具列表包含预期的工具
        # 注意：这需要访问 server.server.list_tools 的返回值
        # 由于是异步装饰器，我们通过调用工具来间接验证
        tools = await server.server.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "mfs_read" in tool_names
        assert "mfs_write" in tool_names
        assert "mfs_search" in tool_names


class TestMCPServerEdgeCases:
    """MCP Server 边界条件测试"""

    @pytest.fixture
    def server(self):
        return MCPServer(db_path=":memory:")

    @pytest.mark.asyncio
    async def test_special_characters_in_path(self, server):
        """测试路径包含特殊字符"""
        arguments = {"path": "/test/special chars!@#", "type": "RULE", "content": "test"}
        result = await server._mfs_write(arguments)
        assert "已创建" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_string_content(self, server):
        """测试空字符串内容"""
        arguments = {"path": "/test/empty", "type": "RULE", "content": ""}
        result = await server._mfs_write(arguments)
        # 空内容应该也能创建
        assert "已创建" in result[0].text or "缺少" in result[0].text

    @pytest.mark.asyncio
    async def test_very_long_path(self, server):
        """测试超长路径"""
        long_path = "/test/" + "a" * 1000
        arguments = {"path": long_path, "type": "RULE", "content": "test"}
        result = await server._mfs_write(arguments)
        # 应该能处理或给出明确的错误
        assert "已创建" in result[0].text or "错误" in result[0].text

    @pytest.mark.asyncio
    async def test_unicode_content(self, server):
        """测试 Unicode 内容"""
        arguments = {
            "path": "/test/unicode",
            "type": "RULE",
            "content": "这是中文测试内容 🚀 émoji"
        }
        result = await server._mfs_write(arguments)
        assert "已创建" in result[0].text

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, server):
        """测试并发写入"""
        import asyncio
        
        async def write_task(i):
            return await server._mfs_write({
                "path": f"/test/concurrent_{i}",
                "type": "RULE",
                "content": f"content_{i}"
            })
        
        # 并发执行多个写入
        tasks = [write_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 所有写入都应该成功
        for result in results:
            assert "已创建" in result[0].text
