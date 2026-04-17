"""
测试 MCP Server Phase 2 增强功能
"""

import pytest
import asyncio
from diting.mcp_server import MCPServer


class TestMCPServerPhase2:
    """测试 MCP Server Phase 2 功能"""

    @pytest.fixture
    def server(self):
        """创建 MCP Server 实例"""
        server = MCPServer(db_path="file:memdb_mcp_test?mode=memory&cache=private")
        yield server
        server.close()

    def test_mfs_write_auto_slice(self, server):
        """测试 mfs_write 自动切片（长文本）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            import random
            path = f"/test/long_doc_{random.randint(0, 10000)}"
            
            # 长文本（>2000 字）
            long_content = "A" * 5000
            
            arguments = {
                "path": path,
                "type": "NOTE",
                "content": long_content
            }
            
            result = loop.run_until_complete(server._mfs_write(arguments))
            
            # 验证返回消息提到切片
            assert "自动切片" in result[0].text
            
            # 验证 MFT 中有切片指针
            pointers = server.mft.get_lcn_pointers(path)
            assert pointers is not None
            assert len(pointers) > 1
        finally:
            loop.close()

    def test_mfs_write_no_slice(self, server):
        """测试 mfs_write 不切片（短文本）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 短文本（<2000 字）
            short_content = "这是短文本"
            
            arguments = {
                "path": "/test/short_doc",
                "type": "NOTE",
                "content": short_content
            }
            
            result = loop.run_until_complete(server._mfs_write(arguments))
            
            # 验证返回消息没有提到切片
            assert "自动切片" not in result[0].text
            
            # 验证 MFT 中没有切片指针
            pointers = server.mft.get_lcn_pointers("/test/short_doc")
            assert pointers is None or len(pointers) == 0
        finally:
            loop.close()

    def test_mfs_read_auto_assemble(self, server):
        """测试 mfs_read 自动还原"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 先写入长文本
            long_content = "B" * 5000
            write_args = {
                "path": "/test/long_read",
                "type": "NOTE",
                "content": long_content
            }
            loop.run_until_complete(server._mfs_write(write_args))
            
            # 读取
            read_args = {"path": "/test/long_read"}
            result = loop.run_until_complete(server._mfs_read(read_args))
            
            # 验证返回完整内容
            assert f"内容：{long_content}" in result[0].text
        finally:
            loop.close()
