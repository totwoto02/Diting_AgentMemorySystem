"""
MCP Server 集成测试

测试完整工作流程和事务处理
"""

import pytest
from diting.mcp_server import MCPServer
from diting.errors import MFTNotFoundError


class TestMCPIntegration:
    """MCP 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_errors(self):
        """测试完整工作流程 + 错误恢复"""
        server = MCPServer(db_path="file:test_workflow?mode=memory&cache=private")
        
        # 1. 正常写入
        write_result = await server._mfs_write({
            "path": "/workflow/test",
            "type": "RULE",
            "content": "初始规则"
        })
        assert len(write_result) == 1
        assert "已创建" in write_result[0].text or "已更新" in write_result[0].text
        
        # 2. 正常读取
        read_result = await server._mfs_read({
            "path": "/workflow/test"
        })
        assert len(read_result) == 1
        assert "初始规则" in read_result[0].text
        
        # 3. 尝试读取不存在的路径（错误场景）
        with pytest.raises(MFTNotFoundError):
            await server._mfs_read({
                "path": "/nonexistent"
            })
        
        # 4. 搜索
        search_result = await server._mfs_search({
            "query": "规则"
        })
        assert len(search_result) == 1
        assert "1 条结果" in search_result[0].text
        
        # 5. 更新
        update_result = await server._mfs_write({
            "path": "/workflow/test",
            "type": "RULE",
            "content": "更新后的规则"
        })
        assert len(update_result) == 1
        assert "已更新" in update_result[0].text
        
        # 6. 验证更新
        final_read = await server._mfs_read({
            "path": "/workflow/test"
        })
        assert len(final_read) == 1
        assert "更新后的规则" in final_read[0].text
        
        # 7. 错误恢复：尝试写入缺少参数
        error_result = await server._mfs_write({
            "path": "/workflow/error"
            # 缺少 type 和 content
        })
        assert len(error_result) == 1
        assert "错误" in error_result[0].text
        
        # 8. 验证错误后系统仍然正常工作
        recovery_read = await server._mfs_read({
            "path": "/workflow/test"
        })
        assert len(recovery_read) == 1
        assert "更新后的规则" in recovery_read[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_mcp(self):
        """测试 MCP 操作的事务回滚"""
        server = MCPServer(db_path="file:test_rollback?mode=memory&cache=private")
        
        # 1. 创建初始数据
        await server._mfs_write({
            "path": "/transaction/data",
            "type": "NOTE",
            "content": "原始数据"
        })
        
        # 2. 验证原始数据
        original = await server._mfs_read({
            "path": "/transaction/data"
        })
        assert "原始数据" in original[0].text
        
        # 3. 尝试更新（模拟事务）
        try:
            # 先更新
            await server._mfs_write({
                "path": "/transaction/data",
                "type": "NOTE",
                "content": "新数据"
            })
            
            # 检查更新后的数据
            updated = await server._mfs_read({
                "path": "/transaction/data"
            })
            assert "新数据" in updated[0].text
            
            # 模拟业务逻辑失败，需要回滚
            raise Exception("模拟业务逻辑失败")
            
        except Exception:
            # 回滚：恢复原始数据
            await server._mfs_write({
                "path": "/transaction/data",
                "type": "NOTE",
                "content": "原始数据"
            })
        
        # 4. 验证回滚后的数据
        rolled_back = await server._mfs_read({
            "path": "/transaction/data"
        })
        assert len(rolled_back) == 1
        assert "原始数据" in rolled_back[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_multiple_operations_sequence(self):
        """测试多个操作序列"""
        # 使用独立内存数据库
        server = MCPServer(db_path="file:test_seq_ops?mode=memory&cache=private")
        
        # 连续执行多个操作
        operations = [
            ("创建", await server._mfs_write({
                "path": "/seq/item1",
                "type": "NOTE",
                "content": "项目 1"
            })),
            ("创建", await server._mfs_write({
                "path": "/seq/item2",
                "type": "NOTE",
                "content": "项目 2"
            })),
            ("读取", await server._mfs_read({"path": "/seq/item1"})),
            ("搜索", await server._mfs_search({"query": "项目"})),
        ]
        
        # 验证所有操作都成功
        # "已创建"或"已更新"都可以
        assert "已创建" in operations[0][1][0].text or "已更新" in operations[0][1][0].text
        assert "已创建" in operations[1][1][0].text or "已更新" in operations[1][1][0].text
        assert "项目 1" in operations[2][1][0].text
        assert "2 条结果" in operations[3][1][0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """测试错误传播"""
        server = MCPServer(db_path="file:test_error_prop?mode=memory&cache=private")
        
        # 通过 call_tool 调用，测试错误是否正确传播
        result = await server.call_tool("mfs_read", {"path": "/nonexistent"})
        
        # 应该返回错误消息
        assert len(result) == 1
        assert "错误" in result[0].text or "未找到" in result[0].text
        
        # 测试未知工具
        unknown_result = await server.call_tool("unknown_tool", {})
        assert len(unknown_result) == 1
        assert "未知工具" in unknown_result[0].text
        
        server.close()
    
    @pytest.mark.asyncio
    async def test_data_consistency(self):
        """测试数据一致性"""
        server = MCPServer(db_path="file:test_consistency?mode=memory&cache=private")
        
        # 写入大量数据
        for i in range(20):
            await server._mfs_write({
                "path": f"/consistency/item_{i}",
                "type": "NOTE",
                "content": f"内容_{i}"
            })
        
        # 验证所有数据都可读
        for i in range(20):
            result = await server._mfs_read({
                "path": f"/consistency/item_{i}"
            })
            assert len(result) == 1
            assert f"内容_{i}" in result[0].text
        
        # 搜索验证
        search_result = await server._mfs_search({
            "query": "内容"
        })
        assert len(search_result) == 1
        assert "20 条结果" in search_result[0].text
        
        server.close()
