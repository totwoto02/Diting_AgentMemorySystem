"""
MCP Server KG 工具实现

添加到 mcp_server.py 中的 KG 工具方法
"""

from typing import Dict, Any
from mcp.types import TextContent

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
