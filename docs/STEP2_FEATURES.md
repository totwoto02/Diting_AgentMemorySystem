# MFS Step 2 功能说明

## Step 2: FTS5 + 知识图谱完善方案

**版本**: v0.3.0  
**发布时间**: 2026-04-14  

---

## 新增功能

### 1. FTS5 全文检索

**功能说明**：
- 基于 SQLite FTS5 扩展
- 支持 BM25 排序
- 支持短语搜索、多关键词搜索
- 支持范围搜索（按路径前缀）

**使用示例**：
```python
from mfs.fts5_search import FTS5Search

fts5 = FTS5Search(db_path=":memory:")

# 插入文档
fts5.insert("/test/doc1", "用户朋友 喜欢 游戏", "NOTE")
fts5.insert("/test/doc2", "游戏角色 是 游戏 角色", "NOTE")

# 搜索
results = fts5.search("游戏")
for r in results:
    print(f"- {r['v_path']}: {r['content']}")

# 范围搜索
results = fts5.search("用户朋友", scope="/test")
```

**性能指标**：
- 搜索延迟：<10ms（千级数据量）
- 内存占用：<10MB

---

### 2. 知识图谱 V2

**功能说明**：
- 多层级关联（概念→子概念→实例）
- 智能权重（TF-IDF + 共现频率 + 时间衰减）
- 概念别名支持
- 搜索扩展（BFS 扩展相关概念）

**使用示例**：
```python
from mfs.knowledge_graph_v2 import KnowledgeGraphV2

kg = KnowledgeGraphV2(db_path=":memory:")

# 添加概念
kg.add_concept("用户朋友", "person", aliases=["小九", "JJ"])
kg.add_concept("游戏", "category")
kg.add_concept("游戏角色", "character")

# 添加关联
kg.add_edge("用户朋友", "游戏", "likes", weight=0.9)
kg.add_edge("游戏", "游戏角色", "contains", weight=0.8)

# 获取相关概念
related = kg.get_related_concepts("用户朋友", top_k=3)
for r in related:
    print(f"- {r['concept']}: {r['weight']}")

# 搜索扩展
expansion = kg.search_with_expansion("用户朋友", max_depth=2)
print(expansion["expanded_concepts"])
```

**时间衰减**：
- 半衰期：30 天
- 公式：`decay_factor = 0.5 ^ (time_diff / 30 天)`

---

### 3. 拼装还原 V2

**功能说明**：
- 重叠去重（智能识别重叠部分）
- 语义连贯排序（按 chunk_id）
- LRU 缓存（缓存热点切片）
- 并行捞取（异步并发）

**使用示例**：
```python
from mfs.assembler_v2 import AssemblerV2, Slice

assembler = AssemblerV2(db_path=":memory:")

# 模拟切片
slices = [
    Slice(chunk_id=1, offset=0, length=1000, content="A" * 1000),
    Slice(chunk_id=2, offset=900, length=1000, content="B" * 100 + "C" * 900),
]

# 拼装（带重叠去重）
result = assembler.assemble_with_dedup(slices)

# LRU 缓存
assembler.cache_slice("/test/doc", slices[0])
cached = assembler.get_cached_slice("/test/doc")
```

**缓存统计**：
```python
stats = assembler.get_cache_stats()
print(f"命中率：{stats['hit_rate']}")
```

---

### 4. 防幻觉盾牌（WAL 日志）

**功能说明**：
- WAL 预写日志（记录所有修改）
- 证据链（记录来源 Agent、对话 ID）
- 回滚机制（支持版本回退）
- 置信度评分（AI 推断的记忆降低权重）

**使用示例**：
```python
from mfs.wal_logger import WALLogger

wal = WALLogger(db_path=":memory:")

# 记录操作
wal.log_operation(
    operation="CREATE",
    v_path="/test/doc",
    content="初始内容",
    source_agent="main",
    evidence="conversation_123",
    confidence=1.0
)

# 获取历史
history = wal.get_history("/test/doc")
for h in history:
    print(f"V{h['version']}: {h['operation']} by {h['source_agent']}")

# 回滚
wal.rollback(history[-1]["id"])

# 获取特定版本
v1 = wal.get_version("/test/doc", version=1)
```

**审计追踪**：
```python
audit = wal.get_audit_trail(limit=100)
for a in audit:
    print(f"{a['timestamp']}: {a['operation']} by {a['source_agent']}")
```

---

### 5. 性能优化

**LRU 缓存**：
```python
from mfs.cache import LRUCache

cache = LRUCache(capacity=100)
cache.put("key", "value")
value = cache.get("key")
stats = cache.get_stats()
```

**连接池**：
```python
from mfs.cache import ConnectionPool

pool = ConnectionPool(db_path=":memory:", max_connections=10)

# 使用上下文管理器
with pool.get_connection() as conn:
    conn.execute("SELECT ...")

stats = pool.get_stats()
```

---

## 性能指标

| 指标 | Phase 1 | Phase 2 | 提升 |
|------|---------|---------|------|
| 搜索延迟 | 50.44ms | <10ms | 5x |
| 拼装延迟 | - | <50ms | - |
| 缓存命中率 | - | >80% | - |
| 并发连接 | 1 | 10 | 10x |

---

## 兼容性

- **向后兼容**: Phase 1 API 保持不变
- **数据迁移**: 自动升级 schema
- **Python 版本**: 3.11+

---

## 下一步

**Step 3: 向量支持（预留）**
- 向量检索接口已预留
- 支持多模型兼容（m3e-small/base, BGE-M3）
- 支持远程 API（百度、阿里、OpenAI）
- 等 Step 2 稳定后执行

---

## 技术支持

- GitHub: https://github.com/yourusername/mfs-memory
- Issues: https://github.com/yourusername/mfs-memory/issues
- 文档：https://github.com/yourusername/mfs-memory/docs
