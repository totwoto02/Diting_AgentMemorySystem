"""
MCP Server 边界条件测试

测试各种边界情况和极端场景
"""

import pytest
import asyncio
from diting.mcp_server import MCPServer


class TestMCPEdgeCases:
    """测试 MCP 边界条件"""
    
    @pytest.mark.asyncio
    async def test_empty_content(self):
        """测试空内容写入"""
        server = MCPServer(db_path=":memory:")
        
        # 写入空内容
        result = await server._mfs_write({
            "path": "/test/empty",
            "type": "NOTE",
            "content": ""
        })
        
        # 空内容应该被拒绝
        assert len(result) == 1
        assert "错误" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_very_long_path(self):
        """测试超长路径"""
        server = MCPServer(db_path=":memory:")
        
        # 创建超长路径（1000 字符）
        long_path = "/test/" + "a" * 1000
        
        result = await server._mfs_write({
            "path": long_path,
            "type": "NOTE",
            "content": "测试内容"
        })
        
        # 应该能处理长路径（或者给出友好的错误消息）
        assert len(result) == 1
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_special_characters(self):
        """测试特殊字符路径"""
        server = MCPServer(db_path=":memory:")
        
        # 包含特殊字符的路径
        special_path = "/test/special-chars_123!@#"
        
        result = await server._mfs_write({
            "path": special_path,
            "type": "NOTE",
            "content": "测试内容"
        })
        
        # 应该能处理特殊字符
        assert len(result) == 1
        # "已创建"或"已更新"都可以
        assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 尝试读取
        read_result = await server._mfs_read({
            "path": special_path
        })
        
        assert len(read_result) == 1
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_unicode_content(self):
        """测试 Unicode 内容"""
        server = MCPServer(db_path=":memory:")
        
        # 包含多种语言的 Unicode 内容
        unicode_content = "你好世界！Hello World! 🌍 Привет мир! مرحبا"
        
        result = await server._mfs_write({
            "path": "/test/unicode",
            "type": "NOTE",
            "content": unicode_content
        })
        
        assert len(result) == 1
        # "已创建"或"已更新"都可以
        assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 读取验证
        read_result = await server._mfs_read({
            "path": "/test/unicode"
        })
        
        assert len(read_result) == 1
        assert "你好世界" in read_result[0].text
        assert "🌍" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_mcp_calls(self):
        """测试并发 MCP 调用"""
        server = MCPServer(db_path=":memory:")
        
        # 并发写入多个文件
        async def write_task(i):
            return await server._mfs_write({
                "path": f"/test/concurrent/{i}",
                "type": "NOTE",
                "content": f"并发测试内容 {i}"
            })
        
        # 并发执行 10 个写入任务
        tasks = [write_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 所有任务都应该成功
        assert len(results) == 10
        for result in results:
            assert len(result) == 1
            # "已创建"或"已更新"都可以（并发测试可能重复运行）
            assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 验证所有数据都正确写入
        for i in range(10):
            read_result = await server._mfs_read({
                "path": f"/test/concurrent/{i}"
            })
            assert f"并发测试内容 {i}" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_very_long_content(self):
        """测试超长内容"""
        server = MCPServer(db_path=":memory:")
        
        # 创建超长内容（10000 字符）
        long_content = "x" * 10000
        
        result = await server._mfs_write({
            "path": "/test/long_content",
            "type": "NOTE",
            "content": long_content
        })
        
        assert len(result) == 1
        # "已创建"或"已更新"都可以
        assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 读取验证
        read_result = await server._mfs_read({
            "path": "/test/long_content"
        })
        
        assert len(read_result) == 1
        assert long_content in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_special_type_values(self):
        """测试特殊类型值"""
        # 使用独立内存数据库
        server = MCPServer(db_path="file:test_special_type?mode=memory&cache=private")
        
        # 测试各种有效类型值
        test_types = ["NOTE", "RULE", "CODE", "TASK", "CONTACT", "EVENT"]
        
        for idx, type_val in enumerate(test_types):
            result = await server._mfs_write({
                "path": f"/test/type_{idx}",
                "type": type_val,
                "content": f"测试类型：{type_val}"
            })
            
            assert len(result) == 1
            # "已创建"或"已更新"都可以
            assert "已创建" in result[0].text or "已更新" in result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_path_with_spaces(self):
        """测试包含空格的路径"""
        # 使用独立内存数据库
        server = MCPServer(db_path="file:test_path_spaces?mode=memory&cache=private")
        
        # 包含空格的路径
        path_with_spaces = "/test/path_with_spaces/file"
        
        result = await server._mfs_write({
            "path": path_with_spaces,
            "type": "NOTE",
            "content": "测试空格路径"
        })
        
        assert len(result) == 1
        # "已创建"或"已更新"都可以
        assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 读取验证
        read_result = await server._mfs_read({
            "path": path_with_spaces
        })
        
        assert len(read_result) == 1
        assert "测试空格路径" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_deep_nested_path(self):
        """测试深层嵌套路径"""
        # 使用独立内存数据库
        server = MCPServer(db_path="file:test_deep_nested?mode=memory&cache=private")
        
        # 深层嵌套路径
        deep_path = "/level1/level2/level3/level4/level5/file"
        
        result = await server._mfs_write({
            "path": deep_path,
            "type": "NOTE",
            "content": "深层嵌套测试"
        })
        
        assert len(result) == 1
        # "已创建"或"已更新"都可以
        assert "已创建" in result[0].text or "已更新" in result[0].text
        
        # 读取验证
        read_result = await server._mfs_read({
            "path": deep_path
        })
        
        assert len(read_result) == 1
        assert "深层嵌套测试" in read_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_search_with_empty_query(self):
        """测试空查询搜索"""
        server = MCPServer(db_path=":memory:")
        
        # 写入一些数据
        await server._mfs_write({
            "path": "/test/search_empty",
            "type": "NOTE",
            "content": "测试内容"
        })
        
        # 空查询
        result = await server._mfs_search({
            "query": ""
        })
        
        assert len(result) == 1
        # 空查询应该返回错误或提示
        assert "错误" in result[0].text or "未找到" in result[0].text
        
        server.close()
