"""
MCP Server 实现

暴露 3 个工具：mfs_read, mfs_write, mfs_search
"""

import asyncio
from typing import Any, Dict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .mft import MFT
from .errors import MFTNotFoundError, MFSException


class MCPServer:
    """MFS MCP Server"""

    def __init__(self, db_path: str | None = None):
        """
        初始化 MCP Server

        Args:
            db_path: SQLite 数据库路径
        """
        import os
        if db_path is None:
            db_path = os.environ.get('MFS_DB_PATH', None)
            if not db_path:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(base_dir, 'mfs.db')
        
        # KG 数据库路径
        kg_db_path = os.path.join(os.path.dirname(db_path), 'mfs_kg.db') if db_path != ':memory:' else None
        
        self.mft = MFT(db_path=db_path, kg_db_path=kg_db_path)
        self.server = Server("mfs-memory")
        self._register_tools()

    def _register_tools(self):
        """注册 MCP 工具"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="mfs_read",
                    description="读取记忆文件内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "虚拟路径 (如：/test/rules)"
                            }
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="mfs_write",
                    description="写入或更新记忆文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "虚拟路径 (如：/test/rules)"
                            },
                            "type": {
                                "type": "string",
                                "description": "文件类型 (如：RULE, NOTE, CODE)"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容"
                            }
                        },
                        "required": ["path", "type", "content"]
                    }
                ),
                Tool(
                    name="mfs_search",
                    description="搜索记忆文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "scope": {
                                "type": "string",
                                "description": "搜索范围 (路径前缀，可选)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                # Phase 2: 知识图谱工具
                Tool(
                    name="kg_search",
                    description="搜索知识图谱概念并获取关联扩展",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "最大扩展深度，默认 2"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="kg_get_related",
                    description="获取相关概念（按权重排序）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "concept": {
                                "type": "string",
                                "description": "概念名称"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回前 K 个，默认 5"
                            }
                        },
                        "required": ["concept"]
                    }
                ),
                Tool(
                    name="kg_stats",
                    description="获取知识图谱统计信息",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),

                Tool(
                    name="entropy_stats",
                    description="获取熵系统统计信息",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_project_entropy",
                    description="获取项目整体熵值",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "项目路径前缀"
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
                Tool(
                    name="entropy_anomaly",
                    description="检测熵值异常",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "slice_id": {
                                "type": "string",
                                "description": "切片 ID"
                            }
                        },
                        "required": ["slice_id"]
                    }
                )

            ]

        @self.server.call_tool()
        async def _handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """MCP 工具调用入口"""
        try:
            if name == "mfs_read":
                return await self._mfs_read(arguments)
            elif name == "mfs_write":
                return await self._mfs_write(arguments)
            elif name == "mfs_search":
                return await self._mfs_search(arguments)
            # Phase 2: KG 工具
            elif name == "kg_search":
                return await self._kg_search(arguments)
            elif name == "kg_get_related":
                return await self._kg_get_related(arguments)
            elif name == "kg_stats":
                return await self._kg_stats(arguments)
            # 熵系统工具
            elif name == "entropy_stats":
                return await self._entropy_stats(arguments)
            elif name == "get_project_entropy":
                return await self._get_project_entropy(arguments)
            elif name == "entropy_anomaly":
                return await self._entropy_anomaly(arguments)
            else:
                return [TextContent(type="text", text=f"未知工具：{name}")]
        except MFTNotFoundError as e:
            return [TextContent(type="text", text=f"错误：{str(e)}")]
        except MFSException as e:
            return [TextContent(type="text", text=f"MFS 错误：{str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"系统错误：{str(e)}")]

    async def _mfs_read(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """mfs_read 工具实现"""
        path = arguments.get("path")
        if not path:
            return [TextContent(type="text", text="错误：缺少 path 参数")]

        result = self.mft.read(path)
        if result:
            return [TextContent(
                type="text",
                text=f"路径：{result['v_path']}\n类型：{result['type']}\n内容：{result['content']}"
            )]
        else:
            raise MFTNotFoundError(f"未找到路径：{path}")

    async def _mfs_write(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """mfs_write 工具实现"""
        path = arguments.get("path")
        type_ = arguments.get("type")
        content = arguments.get("content")

        if not all([path, type_, content]):
            return [TextContent(type="text", text="错误：缺少必需参数 (path, type, content)")]

        # 检查是否已存在
        existing = self.mft.read(path)
        if existing:
            # 更新
            self.mft.update(path, content)
            return [TextContent(type="text", text=f"已更新：{path}")]
        else:
            # 创建
            inode = self.mft.create(path, type_, content)
            return [TextContent(type="text", text=f"已创建：{path} (inode={inode})")]

    async def _mfs_search(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """mfs_search 工具实现"""
        query = arguments.get("query")
        scope = arguments.get("scope")

        if not query:
            return [TextContent(type="text", text="错误：缺少 query 参数")]

        results = self.mft.search(query, scope)
        if not results:
            return [TextContent(type="text", text=f"未找到匹配 '{query}' 的结果")]

        output = f"找到 {len(results)} 条结果:\n\n"
        for r in results:
            output += f"- {r['v_path']} ({r['type']}): {r['content'][:50]}...\n"

        return [TextContent(type="text", text=output)]


    # ========== Phase 2: KG 工具实现 ==========
    
    async def _kg_search(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """kg_search 工具实现"""
        query = arguments.get("query")
        max_depth = arguments.get("max_depth", 2)
        
        if not query:
            return [TextContent(type="text", text="错误：缺少 query 参数")]
        
        if not self.mft.kg:
            return [TextContent(type="text", text="错误：知识图谱未启用")]
        
        result = self.mft.kg.search_with_expansion(query, max_depth)
        
        if not result["found"]:
            return [TextContent(type="text", text=f"未找到概念：'{query}'")]
        
        output = f"✅ 找到概念：{result.get('concept', query)}\n\n"
        if result.get("expanded_concepts"):
            output += f"🔗 关联概念 ({len(result['expanded_concepts'])} 个):\n"
            for concept in result['expanded_concepts'][:10]:
                output += f"  - {concept}\n"
        if result.get("suggestion"):
            output += f"\n💡 {result['suggestion']}"
        
        return [TextContent(type="text", text=output)]
    
    async def _kg_get_related(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """kg_get_related 工具实现"""
        concept = arguments.get("concept")
        top_k = arguments.get("top_k", 5)
        
        if not concept:
            return [TextContent(type="text", text="错误：缺少 concept 参数")]
        
        if not self.mft.kg:
            return [TextContent(type="text", text="错误：知识图谱未启用")]
        
        related = self.mft.kg.get_related_concepts(concept, top_k)
        
        if not related:
            return [TextContent(type="text", text=f"'{concept}' 没有关联概念")]
        
        output = f"🔗 '{concept}' 的关联概念:\n\n"
        for r in related:
            output += f"  - {r['concept']} (权重：{r['weight']:.2f})\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _kg_stats(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """kg_stats 工具实现"""
        if not self.mft.kg:
            return [TextContent(type="text", text="错误：知识图谱未启用")]
        
        stats = self.mft.kg.get_stats()
        
        output = "📊 知识图谱统计:\n\n"
        output += f"  概念数：{stats['concept_count']:,}\n"
        output += f"  边数：{stats['edge_count']:,}\n"
        output += f"  平均每概念边数：{stats['avg_edges_per_concept']:.2f}\n"
        
        return [TextContent(type="text", text=output)]

    async def run(self):
        """运行 MCP Server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


    async def _entropy_stats(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """entropy_stats 工具实现"""
        if not self.mft.entropy or not self.mft.entropy.is_enabled():
            return [TextContent(type="text", text="熵系统未启用")]
        
        stats = self.mft.entropy.recalculate_all()
        
        if 'error' in stats:
            return [TextContent(type="text", text=f"错误：{stats['error']}")]
        
        output = "📊 熵系统统计:\n\n"
        output += f"  高熵记忆：{stats.get('high', 0)}\n"
        output += f"  中熵记忆：{stats.get('medium', 0)}\n"
        output += f"  低熵记忆：{stats.get('low', 0)}\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _get_project_entropy(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """get_project_entropy 工具实现"""
        if not self.mft.entropy or not self.mft.entropy.is_enabled():
            return [TextContent(type="text", text="熵系统未启用")]
        
        project_path = arguments.get("project_path")
        if not project_path:
            return [TextContent(type="text", text="错误：缺少 project_path 参数")]
        
        result = self.mft.entropy.get_project_entropy(project_path)
        
        if 'error' in result:
            return [TextContent(type="text", text=f"错误：{result['error']}")]
        
        output = f"📊 项目熵值：{project_path}\n\n"
        output += f"  平均熵值：{result['avg_entropy']:.1f}\n"
        output += f"  熵级：{result['level']}\n"
        output += f"  记忆数：{result['memory_count']}\n"
        output += f"  趋势：{result.get('trend', 'stable')}\n"
        
        if result.get('high_entropy_ratio', 0) > 0.5:
            output += "\n⚠️ 警告：超过 50% 的记忆处于高熵状态，建议尽快决策"
        
        return [TextContent(type="text", text=output)]
    
    async def _entropy_anomaly(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """entropy_anomaly 工具实现"""
        if not self.mft.entropy or not self.mft.entropy.is_enabled():
            return [TextContent(type="text", text="熵系统未启用")]
        
        slice_id = arguments.get("slice_id")
        if not slice_id:
            return [TextContent(type="text", text="错误：缺少 slice_id 参数")]
        
        result = self.mft.entropy.detect_entropy_anomaly(slice_id)
        
        if 'error' in result:
            return [TextContent(type="text", text=f"错误：{result['error']}")]
        
        if not result['has_anomaly']:
            return [TextContent(type="text", text="✅ 未检测到熵值异常")]
        
        output = "⚠️ 检测到熵值异常:\n\n"
        for anomaly in result['anomalies']:
            output += f"  - {anomaly['type']}: {anomaly['message']}\n"
        
        return [TextContent(type="text", text=output)]


    def close(self):
        """关闭服务器"""
        self.mft.close()


async def main():
    """入口函数"""
    server = MCPServer()
    try:
        await server.run()
    finally:
        server.close()


if __name__ == "__main__":
    asyncio.run(main())
