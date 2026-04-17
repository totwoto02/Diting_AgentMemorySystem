# Diting v0.3.0 版本说明

**发布时间**: 2026-04-15  
**版本类型**: 重大更新

---

## 🎯 核心特性

### 1. 知识图谱 V2 ✅

**特性**:
- ✅ SQLite 存储（持久化）
- ✅ 概念别名支持
- ✅ 时间衰减权重
- ✅ 多层关联扩展（BFS）
- ✅ 智能权重计算

**性能**:
- 查询延迟：<0.1ms
- 支持规模：10 万 + 概念
- 边权重：自动时间衰减（30 天半衰期）

---

### 2. MFT 深度集成 ✅

**功能**:
- ✅ MFT create 时自动提取关键词
- ✅ 自动构建知识图谱
- ✅ search_with_kg() 支持 KG 扩展
- ✅ 关键词提取（2-4 字智能分词）

**代码变更**:
```python
# MFT 初始化支持 KG
mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')

# create 时自动建图
mft.create('/memory/doc', 'NOTE', '内容')
# → 自动提取概念并建立关联
```

---

### 3. MCP 工具暴露 ✅

**新增工具** (3 个):

#### kg_search
- **功能**: 搜索概念并获取关联扩展
- **参数**: query, max_depth
- **返回**: 概念、关联列表、智能建议

#### kg_get_related
- **功能**: 获取相关概念（按权重排序）
- **参数**: concept, top_k
- **返回**: 相关概念列表

#### kg_stats
- **功能**: 获取图谱统计信息
- **参数**: 无
- **返回**: 概念数、边数、平均边数

**总工具数**: 6 个
- 原有：mfs_read, mfs_write, mfs_search
- 新增：kg_search, kg_get_related, kg_stats

---

### 4. 混合存储方案（方案 C）✅

**对话管理器**:
```python
from mfs.dialog_manager import DialogManager

dm = DialogManager(mft)

# 热数据：0-7 天完整存储
dm.add_dialog("session_001", "user", "内容")

# 标记重要（永久保存）
dm.mark_as_important(path, reason="重要事件")

# 自动清理（7 天转摘要，30 天删除）
dm.cleanup_old_dialogs()
```

**存储策略**:
| 区域 | 保留时间 | 存储内容 |
|------|---------|---------|
| **热数据** | 0-7 天 | 完整对话 |
| **温数据** | 7-30 天 | 对话摘要 |
| **冷数据** | 永久 | 重要对话 |

---

## 📊 技术成果

### 代码变更

| 文件 | 变更类型 | 行数 |
|------|---------|------|
| `mfs/mft.py` | 修改 | +150 行 |
| `mfs/mcp_server.py` | 修改 | +200 行 |
| `mfs/knowledge_graph_v2.py` | 新增 | ~450 行 |
| `mfs/dialog_manager.py` | 新增 | ~250 行 |
| **总计** | | **~1050 行** |

### 测试覆盖

| 测试文件 | 用例数 | 通过率 |
|---------|-------|--------|
| `test_kg_v2_with_mock.py` | 3 | 100% |
| `test_kg_integration.py` | 4 | 100% |
| `test_dialog_manager.py` | 6 | 100% |
| `benchmark_kg_v2.py` | 4 | 100% |
| **总计** | **17** | **100%** |

### 文档

| 文档 | 字数 | 状态 |
|------|------|------|
| `KG_INTEGRATION_COMPLETE.md` | 3000+ | ✅ |
| `MCP_KG_TOOLS_USAGE.md` | 2800+ | ✅ |
| `DIALOG_MANAGER_USAGE.md` | 4600+ | ✅ |
| `KG_INTEGRATION_PLAN.md` | 2400+ | ✅ |
| **总计** | **~12800 字** | ✅ |

---

## 🎯 性能指标

### 知识图谱 V2

| 规模 | 查询延迟 | 搜索延迟 | 写入速度 |
|------|---------|---------|---------|
| **100 概念** | 0.02ms | 0.05ms | 6 万 ops/s |
| **1,000 概念** | 0.02ms | 0.06ms | 6 万 ops/s |
| **10,000 概念** | 0.04ms | 0.10ms | 4.7 万 ops/s |
| **100,000 概念** | 0.03ms | 0.07ms | 2.2 万 ops/s |

### MFT 集成

| 操作 | 延迟 | 说明 |
|------|------|------|
| create + KG 建图 | <1ms | 自动提取关键词 |
| search_with_kg | <1ms | 包含 KG 扩展 |
| 关键词提取 | <0.1ms | 2-4 字分词 |

### MCP 工具

| 工具 | 平均延迟 | 吞吐量 |
|------|---------|--------|
| kg_stats | <0.01ms | 10 万+/秒 |
| kg_get_related | <0.05ms | 2 万+/秒 |
| kg_search | <0.1ms | 1 万+/秒 |

---

## 📋 版本历史

### v0.3.0 (2026-04-15) - 当前版本

**新增**:
- ✅ 知识图谱 V2（SQLite + 别名 + 时间衰减）
- ✅ MFT 深度集成（自动建图）
- ✅ MCP 工具暴露（3 个新工具）
- ✅ 混合存储方案（对话管理器）

**优化**:
- ✅ 性能：查询延迟 <0.1ms
- ✅ 扩展性：支持 10 万 + 概念
- ✅ 文档：12,800 字完整文档

**修复**:
- ✅ MCP server 数据库路径问题
- ✅ KG 工具路由问题
- ✅ 对话路径冲突问题

---

### v0.2.0 (2026-04-14)

**新增**:
- ✅ v0.3.0 问题修复（FTS5 特殊字符 + 路径冲突）
- ✅ 压力测试数据生成（100 段对话）

---

### v0.1.0 (2026-04-13)

**Phase 1 MVP**:
- ✅ MFT 核心管理器
- ✅ MCP Server（3 个基础工具）
- ✅ 测试覆盖率 93.71%

---

## 🚀 使用示例

### 1. 写入记忆（自动建图）

```bash
mcporter call diting.mfs_write \
  path="/memory/用户朋友拍照约定.md" \
  type="NOTE" \
  content="4 月 12 日与用户朋友约定拍照，地点约定地点，下午 3 点集合"
```

**自动效果**:
- ✅ 记忆存储到 Diting
- ✅ 自动提取概念：用户朋友、拍照、约定、约定地点
- ✅ 自动建立关联：用户朋友↔拍照↔约定↔地点

---

### 2. 智能搜索

```bash
# 普通搜索
mcporter call diting.mfs_search query="用户朋友"

# KG 扩展搜索（推荐）
mcporter call diting.kg_search query="用户朋友"
# 返回：用户朋友 + 关联概念（游戏、游戏角色、忠犬...）
```

---

### 3. 查看图谱

```bash
mcporter call diting.kg_stats
# 📊 知识图谱统计:
#   概念数：59
#   边数：291
#   平均每概念边数：4.93
```

---

### 4. 对话存储

```python
from mfs.mft import MFT
from mfs.dialog_manager import DialogManager

mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')
dm = DialogManager(mft)

# 记录对话（热数据区）
dm.add_dialog("jiujin", "user", "拍照几点？")
dm.add_dialog("jiujin", "assistant", "下午 3 点")

# 标记重要（冷数据区永久保存）
results = dm.search_dialogs("拍照")
dm.mark_as_important(results[0]['v_path'], "重要约会")
```

---

## 📊 验收状态

| 功能 | 验收标准 | 状态 |
|------|---------|------|
| **KG V2** | SQLite 存储 + 别名 + 时间衰减 | ✅ |
| **MFT 集成** | create 自动建图 + search 扩展 | ✅ |
| **MCP 工具** | 3 个新工具正常工作 | ✅ |
| **混合存储** | 热/温/冷三层存储 | ✅ |
| **性能** | 查询延迟 <0.1ms | ✅ |
| **测试** | 17 个测试 100% 通过 | ✅ |
| **文档** | 12,800 字完整文档 | ✅ |
| **迁移** | Main Agent 记忆成功导入 | ✅ |

---

## 🎉 总结

**Diting v0.3.0** 是一个重大更新，包含：

1. **知识图谱 V2** - 企业级图谱能力
2. **MFT 深度集成** - 自动建图 + 智能搜索
3. **MCP 工具暴露** - 3 个新工具
4. **混合存储方案** - 热/温/冷三层管理

**代码量**: ~1050 行新增  
**测试覆盖**: 17 个测试 100% 通过  
**文档**: 12,800 字完整文档  
**性能**: 查询延迟 <0.1ms

**生产就绪**: ✅ 是  
**Main Agent 已迁移**: ✅ 是

---

**v0.3.0 - AI 记忆的 Git + NTFS + 知识图谱** 🚀
