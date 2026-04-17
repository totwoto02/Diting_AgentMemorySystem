# Diting 完整代码功能描述

**从 0 到 V1.0.0.0 的完整技术文档**

---

# Diting (Memory File System) - AI 记忆的 Git + NTFS

**为 Agent 时代打造的记忆管理系统**

---

## 🎯 项目愿景

将 NTFS 文件系统的严谨性引入 AI 记忆系统，成为 Agent 时代的基础设施级开源项目。

---

## 📁 核心架构

```
Diting V1.0.0.0
├── 文件系统概念
│   ├── 虚拟路径管理 (如：/person/用户朋友/preferences)
│   ├── 层级结构 (类似文件夹)
│   └── 类型系统 (NOTE/RULE/CODE/TASK/CONTACT/EVENT)
├── 自动切片还原
│   ├── 长文本自动切片 (>2000 字 → 500-2000 字切片)
│   ├── 读取时自动拼装
│   └── 重叠去重
├── 智能搜索
│   ├── FTS5 全文检索 (BM25 排序)
│   ├── 知识图谱扩展
│   └── 特殊字符支持
├── 防幻觉盾牌
│   ├── WAL 预写日志
│   ├── 证据链
│   ├── 版本控制
│   └── 置信度评分
├── 热力学四系统
│   ├── 内能 (U) - 记忆被访问总次数
│   ├── 温度 (T) - 与当前上下文关联度
│   ├── 熵 (S) - 记忆争议性/混乱度
│   └── 自由能 (G) - G = U - TS
└── 性能优化
    ├── LRU 缓存 (命中率>80%)
    ├── 连接池管理
    └── 并发安全
```

---

## 🔧 核心模块

### 1. MFT (Master File Table) - 元数据管理

**文件**: `mfs/mft.py`

**功能**:
- ✅ 记忆文件的 CRUD 操作
- ✅ 虚拟路径管理
- ✅ 类型约束 (NOTE/RULE/CODE/TASK/CONTACT/EVENT)
- ✅ LRU 缓存优化
- ✅ 并发写入支持
- ✅ 搜索功能 (LIKE 查询)

**核心方法**:
```python
class MFT:
    def create(self, v_path: str, type: str, content: str) -> int
    def read(self, v_path: str) -> Dict[str, Any]
    def update(self, v_path: str, content: str = None, status: str = None) -> bool
    def delete(self, v_path: str) -> bool
    def search(self, query: str, scope: str = None) -> List[Dict]
    def list_by_type(self, type: str) -> List[Dict]
    def get_stats(self) -> Dict[str, Any]
```

**数据库表结构**:
```sql
CREATE TABLE mft (
    inode INTEGER PRIMARY KEY AUTOINCREMENT,
    v_path TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    content TEXT,
    heat_score INTEGER DEFAULT 50,        -- 热度 (内能 U)
    temp_score REAL DEFAULT 0.0,          -- 温度 (关联度 T)
    entropy_score REAL DEFAULT 0.0,       -- 熵 (争议性 S)
    free_energy_score REAL DEFAULT 0.0,   -- 自由能 (G)
    deleted INTEGER DEFAULT 0,
    create_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_inode INTEGER,
    lcn_pointers TEXT DEFAULT NULL
);
```

---

### 2. FTS5 Search - 全文检索

**文件**: `mfs/fts5_search.py`

**功能**:
- ✅ FTS5 虚拟表管理
- ✅ BM25 排序算法
- ✅ 自动触发器同步
- ✅ 范围搜索
- ✅ 多关键词搜索

**核心方法**:
```python
class FTS5Search:
    def insert(self, v_path: str, content: str, type: str) -> int
    def search(self, query: str, scope: str = None, top_k: int = 20) -> List[Dict]
    def search_highlight(self, query: str, content: str) -> str
    def get_stats(self) -> Dict[str, Any]
    def rebuild_index(self) -> None
```

**FTS5 表结构**:
```sql
CREATE VIRTUAL TABLE mft_fts5 USING fts5(
    content,
    v_path,
    type,
    content='mft',
    content_rowid='inode'
);
```

**触发器**:
```sql
-- INSERT 触发器
CREATE TRIGGER mft_ai AFTER INSERT ON mft BEGIN
    INSERT INTO mft_fts5(rowid, content, v_path, type)
    VALUES (new.inode, new.content, new.v_path, new.type);
END;

-- UPDATE 触发器
CREATE TRIGGER mft_au AFTER UPDATE ON mft BEGIN
    INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
    VALUES ('delete', old.inode, old.content, old.v_path, old.type);
    INSERT INTO mft_fts5(rowid, content, v_path, type)
    VALUES (new.inode, new.content, new.v_path, new.type);
END;

-- DELETE 触发器
CREATE TRIGGER mft_ad AFTER DELETE ON mft BEGIN
    INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
    VALUES ('delete', old.inode, old.content, old.v_path, old.type);
END;
```

---

### 3. Knowledge Graph V2 - 知识图谱

**文件**: `mfs/knowledge_graph_v2.py`

**功能**:
- ✅ 概念管理
- ✅ 别名映射
- ✅ 边关系管理
- ✅ 智能权重计算
- ✅ 时间衰减
- ✅ 多层级关联

**核心方法**:
```python
class KnowledgeGraphV2:
    def add_concept(self, name: str, type: str, aliases: List[str] = None) -> int
    def add_alias(self, concept_name: str, alias: str) -> bool
    def get_concept_by_name(self, name: str) -> Optional[Dict]
    def add_edge(self, from_concept: str, to_concept: str, relation: str, 
                 weight: float = 1.0) -> int
    def update_edge_weight(self, from_concept: str, to_concept: str, 
                           new_weight: float) -> bool
    def get_related_concepts(self, concept_name: str, top_k: int = 5, 
                             max_depth: int = 2) -> List[Dict]
    def get_stats(self) -> Dict[str, Any]
```

**数据库表结构**:
```sql
CREATE TABLE kg_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE kg_aliases (
    alias TEXT PRIMARY KEY,
    concept_id INTEGER NOT NULL,
    FOREIGN KEY (concept_id) REFERENCES kg_concepts(id)
);

CREATE TABLE kg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_concept TEXT NOT NULL,
    to_concept TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    timestamp REAL DEFAULT (strftime('%s', 'now')),
    UNIQUE(from_concept, to_concept)
);
```

---

### 4. WAL Logger - 防幻觉盾牌

**文件**: `mfs/wal_logger.py`

**功能**:
- ✅ 预写日志记录
- ✅ 证据链追踪
- ✅ 版本控制
- ✅ 回滚支持
- ✅ 审计追踪
- ✅ 置信度评分

**核心方法**:
```python
class WALLogger:
    def log_operation(self, operation: str, v_path: str, content: str,
                      source_agent: str, evidence: str = "", 
                      confidence: float = 1.0) -> int
    def get_history(self, v_path: str) -> List[Dict]
    def rollback(self, record_id: int) -> bool
    def get_version(self, v_path: str, version: int) -> Optional[Dict]
    def get_latest_version(self, v_path: str) -> Optional[Dict]
    def get_audit_trail(self, limit: int = 100) -> List[Dict]
```

**数据库表结构**:
```sql
CREATE TABLE wal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    v_path TEXT NOT NULL,
    content TEXT,
    source_agent TEXT,
    evidence TEXT,
    confidence REAL,
    timestamp REAL,
    version INTEGER,
    status TEXT DEFAULT 'COMMITTED'
);
```

---

### 5. Heat Manager - 热度系统 (内能 U)

**文件**: `mfs/heat_manager.py`

**功能**:
- ✅ 记忆热度计算
- ✅ 时间衰减
- ✅ 轮次衰减
- ✅ 用户主动升温
- ✅ 死灰复燃检测

**核心方法**:
```python
class HeatManager:
    def calculate_heat(self, slice_id: str, current_round: int = None) -> Dict
    def heat(self, slice_id: str, reason: str = "用户主动提及", 
             changed_by: str = "user") -> Dict
    def cool(self, slice_id: str, reason: str = "时间衰减",
             changed_by: str = "system") -> Dict
    def freeze(self, slice_id: str, reason: str,
               changed_by: str = "user") -> Dict
    def thaw(self, slice_id: str, reason: str = "用户解冻",
             changed_by: str = "user") -> Dict
    def detect_zombie_revival(self, slice_id: str, 
                              current_round: int) -> Optional[Dict]
```

**热度等级**:
- 🔥 **高热度区**: 70-100 (活跃/重要/当前)
- 🌤️ **中热度区**: 40-69 (最近使用/一般重要)
- ❄️ **低热度区**: 10-39 (历史归档/较少使用)
- 🧊 **冻结区**: 0-9 (明确废弃/幻觉源)

---

### 6. Entropy Manager - 熵系统 (S)

**文件**: `mfs/entropy_manager.py`

**功能**:
- ✅ 记忆混乱度评估
- ✅ 争议性检测
- ✅ 熵增因素追踪
- ✅ 熵减因素追踪
- ✅ 熵级分类

**核心方法**:
```python
class EntropyManager:
    def calculate_entropy(self, slice_id: str) -> Dict
    def track_options(self, slice_id: str, option_count: int) -> Dict
    def track_disagreement(self, slice_id: str, disagreement_level: int) -> Dict
    def track_decision(self, slice_id: str) -> Dict
    def get_entropy_level(self, entropy_score: float) -> str
```

**熵级分类**:
- 🌪️ **高熵**: >=70 (混乱/不确定/讨论初期)
- 🌊 **中熵**: 40-69 (收敛中/有方向未决策)
- 📐 **低熵**: <40 (确定/已决策/执行中)

---

### 7. Free Energy Manager - 自由能系统 (G)

**文件**: `mfs/free_energy_manager.py`

**功能**:
- ✅ 自由能计算 (G = U - TS)
- ✅ 记忆有效性判定
- ✅ 关联度计算 (温度 T)
- ✅ 可提取记忆筛选
- ✅ 系统状态分析

**核心方法**:
```python
class FreeEnergyManager:
    def calculate_free_energy(self, slice_id: str, 
                              heat_score: float = None,
                              temp_score: float = None,
                              entropy_score: float = None) -> Dict
    def batch_calculate(self, slice_ids: List[str], 
                        current_context: str = None) -> Dict
    def get_extractable_memories(self, context: str = None, 
                                 limit: int = 20) -> List[Dict]
    def analyze_system_state(self) -> Dict
```

**核心公式**:
```
G = U - TS

其中:
G = 自由能 (记忆有效性)
U = 内能 (热度评分 0-100)
T = 温度 (关联度评分 0-1)
S = 熵 (争议性评分 0-1)

物理意义:
- G > 0: 记忆可被提取并影响决策
- G < 0: 记忆虽存在但被抑制
- G = 0: 临界状态
```

---

### 8. Assembler V2 - 切片拼装

**文件**: `mfs/assembler_v2.py`

**功能**:
- ✅ 智能去重
- ✅ 重叠检测
- ✅ 质量评分
- ✅ 完整性验证

**核心方法**:
```python
class AssemblerV2:
    def assemble_with_dedup(self, slices: List[Dict]) -> Tuple[str, Dict]
    def assemble_with_quality(self, slices: List[Dict], 
                              expected_length: int = None) -> Dict
    def verify_integrity(self, assembled: str, original: str) -> Dict
```

---

### 9. Cache - LRU 缓存

**文件**: `mfs/cache.py`

**功能**:
- ✅ LRU 缓存管理
- ✅ 连接池管理
- ✅ 缓存统计
- ✅ 并发安全

**核心类**:
```python
class LRUCache:
    def get(self, key: str) -> Optional[Any]
    def put(self, key: str, value: Any) -> None
    def delete(self, key: str) -> bool
    def clear(self) -> None
    def get_stats(self) -> Dict

class ConnectionPool:
    def acquire(self) -> sqlite3.Connection
    def release(self, conn: sqlite3.Connection) -> None
    def get_stats(self) -> Dict
```

---

### 10. MCP Server - MCP 协议支持

**文件**: `mfs/mcp_server.py`

**功能**:
- ✅ MCP 协议实现
- ✅ 工具暴露 (mfs_read, mfs_write, mfs_search)
- ✅ 错误处理
- ✅ 多客户端支持

**工具列表**:
```python
[
    Tool(name="mfs_read", description="读取记忆文件内容"),
    Tool(name="mfs_write", description="写入或更新记忆文件"),
    Tool(name="mfs_search", description="搜索记忆文件")
]
```

---

## 📊 性能指标

| 指标 | V1.0.0.0 | 说明 |
|------|---------|------|
| **搜索延迟** | <10ms | FTS5 BM25 |
| **写入延迟** | <1ms | 批量写入 |
| **读取延迟** | <1ms | LRU 缓存 |
| **并发连接** | 10 | 连接池 |
| **缓存命中率** | >80% | LRU 缓存 |
| **整体提升** | 30-50% | vs v0.3.0 |

---

## 🎯 使用示例

### 基础使用

```python
from mfs.mft import MFT
from mfs.fts5_search import FTS5Search
from mfs.knowledge_graph_v2 import KnowledgeGraphV2
from mfs.wal_logger import WALLogger

# 初始化
mft = MFT(db_path="mfs.db")
fts5 = FTS5Search(db_path="mfs.db")
kg = KnowledgeGraphV2(db_path="mfs_kg.db")
wal = WALLogger(db_path="mfs.db")

# CREATE - 写入记忆
mft.create("/person/用户朋友/preferences", "NOTE", "用户朋友喜欢游戏")
fts5.insert("/person/用户朋友/preferences", "用户朋友喜欢游戏", "NOTE")
wal.log_operation("CREATE", "/person/用户朋友/preferences", "用户朋友喜欢游戏", "main")

# READ - 读取记忆
result = mft.read("/person/用户朋友/preferences")
print(result["content"])

# UPDATE - 更新记忆
mft.update("/person/用户朋友/preferences", content="用户朋友喜欢游戏和拍照")

# SEARCH - 搜索记忆
results = fts5.search("游戏")
for r in results:
    print(f"- {r['v_path']}: {r['content']}")

# 知识图谱
kg.add_concept("用户朋友", "person")
kg.add_concept("游戏", "category")
kg.add_edge("用户朋友", "游戏", "likes", weight=0.9)

related = kg.get_related_concepts("用户朋友")
print(related)
```

### 热力学四系统

```python
from mfs.free_energy_manager import FreeEnergyManager

fe = FreeEnergyManager(db_path="mfs.db")

# 计算自由能 G = U - TS
result = fe.calculate_free_energy(
    slice_id="memory_001",
    heat_score=80,      # U (内能)
    temp_score=0.7,     # T (温度/关联度)
    entropy_score=0.3   # S (熵/争议性)
)

print(f"自由能 G = {result['free_energy']}")
print(f"可提取：{result['can_extract']}")
```

---

## 📁 项目结构

```
diting/
├── mfs/                      # 核心模块
│   ├── __init__.py           # V1.0.0.0 版本信息
│   ├── mft.py                # MFT 元数据管理
│   ├── database.py           # SQLite 连接管理
│   ├── fts5_search.py        # FTS5 全文检索
│   ├── knowledge_graph_v2.py # 知识图谱 V2
│   ├── wal_logger.py         # WAL 日志
│   ├── heat_manager.py       # 热度系统 (内能 U)
│   ├── entropy_manager.py    # 熵系统 (S)
│   ├── free_energy_manager.py# 自由能系统 (G)
│   ├── assembler_v2.py       # 切片拼装 V2
│   ├── cache.py              # LRU 缓存 + 连接池
│   ├── slicers/
│   │   └── length.py         # 按长度切片
│   └── cli/
│       └── install_check.py  # 安装验证工具
├── tests/                    # 测试套件 (102 个用例)
├── docs/                     # 文档
├── mcp-configs/              # MCP 配置模板
├── setup.py                  # 安装配置
├── requirements.txt          # 依赖列表
└── README.md                 # 项目说明
```

---

## 🎊 总结

**Diting V1.0.0.0** 是一个完整的 AI 记忆管理系统，包含：

- ✅ **10 个核心模块**
- ✅ **热力学四系统** (U/T/S/G)
- ✅ **FTS5 全文检索**
- ✅ **知识图谱**
- ✅ **WAL 防幻觉**
- ✅ **MCP 协议支持**
- ✅ **102 个测试用例**
- ✅ **30-50% 性能提升**

**可以开始使用了！** 🚀

---

**文档版本**: V1.0.0.0  
**创建时间**: 2026-04-17  
**维护人**: Diting Team
