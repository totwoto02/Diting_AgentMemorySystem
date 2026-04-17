"""
MCP Server 异常覆盖测试

专门用于提高覆盖率的测试
"""

import pytest
from unittest.mock import patch, MagicMock
from diting.mcp_server import MCPServer
from diting.errors import MFTNotFoundError, MFSException


class TestMCPExceptionCoverage:
    """测试异常处理覆盖率"""
    
    @pytest.mark.asyncio
    async def test_call_tool_mfs_exception(self):
        """测试 call_tool 捕获 MFSException"""
        server = MCPServer(db_path="file:test_mfs_exc?mode=memory&cache=private")
        
        # 模拟 MFT 抛出 MFSException
        with patch.object(server.mft, 'read', side_effect=MFSException("模拟 MFS 错误")):
            result = await server.call_tool("mfs_read", {"path": "/test"})
            
            assert len(result) == 1
            assert "MFS 错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_call_tool_generic_exception(self):
        """测试 call_tool 捕获通用 Exception"""
        server = MCPServer(db_path="file:test_gen_exc?mode=memory&cache=private")
        
        # 模拟抛出通用异常
        with patch.object(server.mft, 'read', side_effect=Exception("模拟系统错误")):
            result = await server.call_tool("mfs_read", {"path": "/test"})
            
            assert len(result) == 1
            assert "系统错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_read_path_is_none(self):
        """测试 mfs_read path 为 None"""
        server = MCPServer(db_path="file:test_none_path?mode=memory&cache=private")
        
        # path 为 None
        result = await server._mfs_read({"path": None})
        
        assert len(result) == 1
        assert "错误" in result[0].text
        assert "path" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_write_path_is_none(self):
        """测试 mfs_write path 为 None"""
        server = MCPServer(db_path="file:test_none_write?mode=memory&cache=private")
        
        # path 为 None
        result = await server._mfs_write({
            "path": None,
            "type": "NOTE",
            "content": "测试"
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_write_type_is_none(self):
        """测试 mfs_write type 为 None"""
        server = MCPServer(db_path="file:test_none_type?mode=memory&cache=private")
        
        # type 为 None
        result = await server._mfs_write({
            "path": "/test",
            "type": None,
            "content": "测试"
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_write_content_is_none(self):
        """测试 mfs_write content 为 None"""
        server = MCPServer(db_path="file:test_none_content?mode=memory&cache=private")
        
        # content 为 None
        result = await server._mfs_write({
            "path": "/test",
            "type": "NOTE",
            "content": None
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_search_query_is_none(self):
        """测试 mfs_search query 为 None"""
        server = MCPServer(db_path="file:test_none_query?mode=memory&cache=private")
        
        # query 为 None
        result = await server._mfs_search({"query": None})
        
        assert len(result) == 1
        assert "错误" in result[0].text
        assert "query" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_mfs_search_with_none_scope(self):
        """测试 mfs_search scope 为 None（应该正常工作）"""
        server = MCPServer(db_path="file:test_none_scope?mode=memory&cache=private")
        
        # 写入数据
        await server._mfs_write({
            "path": "/test/scope_none",
            "type": "NOTE",
            "content": "测试内容"
        })
        
        # scope 为 None（应该正常搜索）
        result = await server._mfs_search({
            "query": "测试",
            "scope": None
        })
        
        assert len(result) == 1
        assert "1 条结果" in result[0].text
        
        server.close()


class TestMCPServerLifecycle:
    """测试服务器生命周期"""
    
    def test_server_init_default(self):
        """测试服务器默认初始化"""
        # 使用默认参数（db_path=None）
        server = MCPServer()
        assert server is not None
        assert server.mft is not None
        server.close()
    
    def test_server_close(self):
        """测试服务器关闭"""
        server = MCPServer(db_path="file:test_close?mode=memory&cache=private")
        # 关闭不应该抛出异常
        server.close()
        # 再次关闭也不应该抛出异常
        server.close()
    
    @pytest.mark.asyncio
    async def test_run_method_exists(self):
        """测试 run 方法存在"""
        server = MCPServer(db_path="file:test_run?mode=memory&cache=private")
        # run 方法应该存在（虽然我们不实际运行它）
        assert hasattr(server, 'run')
        assert callable(server.run)
        server.close()
