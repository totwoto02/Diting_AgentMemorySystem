# 知识图谱 V2 集成计划

**时间**: 2026-04-15 11:42  
**状态**: 执行中

---

## 🎯 集成目标

1. **MFT 深度集成** - 写入时自动建图，搜索时智能扩展
2. **MCP 工具暴露** - 3 个新工具：diting_kg_search, diting_kg_get_related, diting_kg_stats
3. **性能保障** - 保持查询延迟 <1ms

---

## 📋 任务清单

### Task 1: MFT 集成

**修改文件**: `mfs/mft.py`

**功能**:
- ✅ 初始化时创建 KG V2 实例
- ✅ `create()` 时自动提取概念并建图
- ✅ `search()` 时支持 KG 扩展建议

**代码变更**:
```python
# 1. 导入 KG V2
from .knowledge_graph_v2 import KnowledgeGraphV2

# 2. 初始化 KG
self.kg = KnowledgeGraphV2(kg_db_path)

# 3. create 时自动建图
def create(self, v_path, type, content):
    # ... 现有逻辑 ...
    # 新增：提取概念并建图
    keywords = self.extract_keywords(content)
    for kw in keywords:
        self.kg.add_concept(kw, "keyword")
    # 建立概念间共现关系
    for i, kw1 in enumerate(keywords):
        for kw2 in keywords[i+1:]:
            self.kg.add_edge(kw1, kw2, "co_occurrence", 1.0)

# 4. search 时支持扩展
def search(self, query):
    # ... 现有逻辑 ...
    # 新增：KG 扩展建议
    kg_result = self.kg.search_with_expansion(query)
    if kg_result["found"]:
        result["related_concepts"] = kg_result["expanded_concepts"]
```

---

### Task 2: MCP 工具暴露

**修改文件**: `mfs/mcp_server.py`

**新增工具**:

#### 1. diting_kg_search
```python
@self.server.call_tool()
async def diting_kg_search(query, max_depth=2):
    """搜索概念并获取关联扩展"""
    result = self.kg.search_with_expansion(query, max_depth)
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

#### 2. diting_kg_get_related
```python
@self.server.call_tool()
async def diting_kg_get_related(concept, top_k=5):
    """获取相关概念"""
    related = self.kg.get_related_concepts(concept, top_k)
    return [TextContent(type="text", text=json.dumps(related, ensure_ascii=False))]
```

#### 3. diting_kg_stats
```python
@self.server.call_tool()
async def diting_kg_stats():
    """获取图谱统计信息"""
    stats = self.kg.get_stats()
    return [TextContent(type="text", text=json.dumps(stats, ensure_ascii=False))]
```

---

### Task 3: 测试验证

**测试文件**: `tests/test_kg_integration.py`

**测试用例**:
- ✅ MFT create 自动建图
- ✅ MFT search KG 扩展
- ✅ MCP diting_kg_search 工具
- ✅ MCP diting_kg_get_related 工具
- ✅ MCP diting_kg_stats 工具
- ✅ 集成性能测试

---

## 📊 验收标准

| 功能 | 验收标准 | 状态 |
|------|---------|------|
| MFT create 自动建图 | 写入后 KG 有对应概念 | ⏳ |
| MFT search KG 扩展 | 搜索结果包含相关概念 | ⏳ |
| MCP diting_kg_search | 工具可用，返回正确 | ⏳ |
| MCP diting_kg_get_related | 工具可用，按权重排序 | ⏳ |
| MCP diting_kg_stats | 工具可用，统计准确 | ⏳ |
| 性能 | 查询延迟 <1ms | ⏳ |

---

## 🚀 执行顺序

1. MFT 集成（核心功能）
2. MCP 工具暴露（接口层）
3. 集成测试验证
4. 性能基准测试

---

**预计完成时间**: 30-45 分钟
