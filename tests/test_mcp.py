"""
MCP Server 单元测试

TDD 流程：先写测试，再写实现
"""

import pytest
import asyncio
from diting.mcp_server import MCPServer


class TestMCPServerInit:
    """测试 MCP Server 初始化"""
    
    def test_init_default(self, temp_db):
        """测试默认初始化"""
        server = MCPServer(db_path=temp_db)
        assert server is not None
        assert server.server is not None
        server.close()
    
    def test_init_with_db_path(self, temp_db):
        """测试指定数据库路径初始化"""
        server = MCPServer(db_path=temp_db)
        assert server is not None
        server.close()


class TestMCPTools:
    """测试 MCP 工具"""
    
    @pytest.mark.asyncio
    async def test_list_tools(self, temp_db):
        """测试列出工具"""
        server = MCPServer(db_path=temp_db)
        # 验证 server 已正确初始化
        assert server.server is not None
        assert server.mft is not None
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_write_then_read(self, temp_db):
        """测试写入后读取"""
        server = MCPServer(db_path=temp_db)
        
        # 写入
        write_result = await server._diting_write({
            "path": "/test/mcp",
            "type": "NOTE",
            "content": "MCP 测试内容"
        })
        
        assert len(write_result) == 1
        assert "已创建" in write_result[0].text
        
        # 读取
        read_result = await server._diting_read({
            "path": "/test/mcp"
        })
        
        assert len(read_result) == 1
        assert "MCP 测试内容" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_read_not_found(self):
        """测试读取不存在的文件"""
        server = MCPServer(db_path=":memory:")
        
        with pytest.raises(Exception):
            await server._diting_read({
                "path": "/nonexistent"
            })
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_update_existing(self):
        """测试更新已存在的文件"""
        server = MCPServer(db_path=":memory:")
        
        # 先写入
        await server._diting_write({
            "path": "/test/update",
            "type": "NOTE",
            "content": "原始内容"
        })
        
        # 再更新
        write_result = await server._diting_write({
            "path": "/test/update",
            "type": "NOTE",
            "content": "更新后的内容"
        })
        
        assert "已更新" in write_result[0].text
        
        # 验证更新
        read_result = await server._diting_read({
            "path": "/test/update"
        })
        
        assert "更新后的内容" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_search(self):
        """测试搜索功能"""
        server = MCPServer(db_path=":memory:")
        
        # 写入多条数据
        await server._diting_write({
            "path": "/test/search1",
            "type": "NOTE",
            "content": "苹果很好吃"
        })
        await server._diting_write({
            "path": "/test/search2",
            "type": "NOTE",
            "content": "香蕉也很好吃"
        })
        await server._diting_write({
            "path": "/test/search3",
            "type": "NOTE",
            "content": "橙子一般般"
        })
        
        # 搜索
        search_result = await server._diting_search({
            "query": "好吃"
        })
        
        assert len(search_result) == 1
        assert "2 条结果" in search_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_search_no_results(self):
        """测试搜索无结果"""
        server = MCPServer(db_path=":memory:")
        
        search_result = await server._diting_search({
            "query": "不存在的关键词"
        })
        
        assert len(search_result) == 1
        assert "未找到" in search_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_search_with_scope(self):
        """测试带范围的搜索"""
        server = MCPServer(db_path=":memory:")
        
        # 写入数据
        await server._diting_write({
            "path": "/scope1/item",
            "type": "NOTE",
            "content": "内容 1"
        })
        await server._diting_write({
            "path": "/scope2/item",
            "type": "NOTE",
            "content": "内容 2"
        })
        
        # 带范围搜索
        search_result = await server._diting_search({
            "query": "1",
            "scope": "/scope1"
        })
        
        assert len(search_result) == 1
        assert "1 条结果" in search_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, temp_db):
        """测试调用未知工具"""
        server = MCPServer(db_path=temp_db)
        
        # 通过 server 的 call_tool 方法调用（在 mcp_server.py 中定义）
        result = await server.call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert "未知工具" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_diting_write_missing_params(self):
        """测试写入缺少参数"""
        server = MCPServer(db_path=":memory:")
        
        result = await server._diting_write({
            "path": "/test/missing"
            # 缺少 type 和 content
        })
        
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()


class TestMCPServerIntegration:
    """MCP Server 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_db):
        """测试完整工作流：写入 -> 读取 -> 搜索 -> 更新"""
        server = MCPServer(db_path=temp_db)
        
        # 1. 写入
        write_result = await server._diting_write({
            "path": "/workflow/test",
            "type": "RULE",
            "content": "初始规则内容"
        })
        assert "已创建" in write_result[0].text
        
        # 2. 读取
        read_result = await server._diting_read({
            "path": "/workflow/test"
        })
        assert "初始规则内容" in read_result[0].text
        
        # 3. 搜索
        search_result = await server._diting_search({
            "query": "规则"
        })
        assert len(search_result) == 1
        
        # 4. 更新
        update_result = await server._diting_write({
            "path": "/workflow/test",
            "type": "RULE",
            "content": "更新后的规则内容"
        })
        assert "已更新" in update_result[0].text
        
        # 5. 验证更新
        final_read = await server._diting_read({
            "path": "/workflow/test"
        })
        assert "更新后的规则内容" in final_read[0].text
        
        server.close()
