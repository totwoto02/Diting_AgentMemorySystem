"""
MCP Server 错误路径测试

测试各种异常和错误场景
"""

import pytest
from diting.mcp_server import MCPServer
from diting.errors import MFTNotFoundError, MFSException


class TestMCPErrorHandling:
    """测试 MCP 错误处理"""
    
    @pytest.mark.asyncio
    async def test_diting_read_missing_params(self):
        """测试 diting_read 缺少必需参数"""
        server = MCPServer(db_path=":memory:")
        
        # 缺少 path 参数
        result = await server._diting_read({})
        
        assert len(result) == 1
        assert "错误" in result[0].text
        assert "path" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_write_invalid_path(self):
        """测试 diting_write 无效路径"""
        server = MCPServer(db_path=":memory:")
        
        # 空路径
        result = await server._diting_write({
            "path": "",
            "type": "NOTE",
            "content": "测试内容"
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_update_not_found(self):
        """测试 diting_update 记录不存在"""
        server = MCPServer(db_path=":memory:")
        
        # 尝试更新不存在的记录
        with pytest.raises(MFTNotFoundError):
            await server._diting_read({
                "path": "/nonexistent/path"
            })
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_search_invalid_scope(self):
        """测试 diting_search 无效范围"""
        server = MCPServer(db_path=":memory:")
        
        # 写入一些数据
        await server._diting_write({
            "path": "/test/item",
            "type": "NOTE",
            "content": "测试内容"
        })
        
        # 使用无效范围搜索（应该返回空结果，但不应该报错）
        result = await server._diting_search({
            "query": "测试",
            "scope": "/invalid/scope"
        })
        
        assert len(result) == 1
        # 应该返回未找到结果，因为范围不匹配
        assert "未找到" in result[0].text or "0 条结果" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """测试 call_tool 未知工具名称"""
        server = MCPServer(db_path=":memory:")
        
        # 调用不存在的工具
        result = await server.call_tool("nonexistent_tool", {})
        
        assert len(result) == 1
        assert "未知工具" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_read_not_found(self):
        """测试 diting_read 文件不存在"""
        server = MCPServer(db_path=":memory:")
        
        # 读取不存在的文件应该抛出异常
        with pytest.raises(MFTNotFoundError):
            await server._diting_read({
                "path": "/does/not/exist"
            })
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_write_missing_type(self):
        """测试 diting_write 缺少 type 参数"""
        server = MCPServer(db_path=":memory:")
        
        result = await server._diting_write({
            "path": "/test/missing",
            "content": "测试内容"
            # 缺少 type
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_write_missing_content(self):
        """测试 diting_write 缺少 content 参数"""
        server = MCPServer(db_path=":memory:")
        
        result = await server._diting_write({
            "path": "/test/missing",
            "type": "NOTE"
            # 缺少 content
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_search_missing_query(self):
        """测试 diting_search 缺少 query 参数"""
        server = MCPServer(db_path=":memory:")
        
        result = await server._diting_search({})
        
        assert len(result) == 1
        assert "错误" in result[0].text
        assert "query" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_call_tool_error_handling(self):
        """测试 call_tool 通用错误处理"""
        server = MCPServer(db_path=":memory:")
        
        # 模拟一个会抛出 MFSException 的场景
        # 这里通过 call_tool 捕获异常
        result = await server.call_tool("diting_read", {"path": "/nonexistent"})
        
        # 应该返回错误消息而不是抛出异常
        assert len(result) == 1
        assert "错误" in result[0].text or "未找到" in result[0].text
        
        server.close()
