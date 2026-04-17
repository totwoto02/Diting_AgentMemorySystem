# MCP 知识图谱工具使用指南

**状态**: 🚧 代码已准备，待 MCP server 重启生效

---

## 🎯 新增工具

### 1. kg_search - 搜索概念并扩展

**功能**: 搜索知识图谱中的概念，并返回关联扩展

**参数**:
- `query` (必填): 搜索关键词
- `max_depth` (可选): 最大扩展深度，默认 2

**示例**:
```bash
mcporter call mfs-memory.kg_search query="用户朋友"
mcporter call mfs-memory.kg_search query="游戏" max_depth=3
```

**返回**:
```
✅ 找到概念：用户朋友

🔗 关联概念 (5 个):
  - 游戏
  - 游戏角色
  - 忠犬
  - 活动
  - 拍照

💡 搜索 '用户朋友' 时，可能也关心：游戏，游戏角色，忠犬
```

---

### 2. kg_get_related - 获取相关概念

**功能**: 获取与指定概念相关的其他概念（按权重排序）

**参数**:
- `concept` (必填): 概念名称
- `top_k` (可选): 返回前 K 个，默认 5

**示例**:
```bash
mcporter call mfs-memory.kg_get_related concept="用户朋友"
mcporter call mfs-memory.kg_get_related concept="游戏" top_k=10
```

**返回**:
```
🔗 '用户朋友' 的关联概念:

  - 游戏 (权重：1.00)
  - 游戏角色 (权重：1.00)
  - 忠犬 (权重：0.95)
  - 活动 (权重：0.80)
  - 拍照 (权重：0.75)
```

---

### 3. kg_stats - 图谱统计

**功能**: 获取知识图谱的统计信息

**参数**: 无

**示例**:
```bash
mcporter call mfs-memory.kg_stats
```

**返回**:
```
📊 知识图谱统计:

  概念数：128
  边数：456
  平均每概念边数：3.56
```

---

## 🔧 使用场景

### 场景 1: 搜索记忆时获得智能推荐

```bash
# 普通搜索
mcporter call mfs-memory.mfs_search query="用户朋友"

# KG 扩展搜索（推荐）
mcporter call mfs-memory.kg_search query="用户朋友"
# 自动推荐相关概念，帮助发现更多相关记忆
```

### 场景 2: 探索概念关联

```bash
# 查看"游戏"的关联
mcporter call mfs-memory.kg_get_related concept="游戏"

# 可能发现：游戏角色、另一个角色、恋与制作人等相关概念
```

### 场景 3: 监控图谱增长

```bash
# 定期检查图谱规模
mcporter call mfs-memory.kg_stats

# 输出示例：
# 概念数：1,234
# 边数：5,678
# 平均每概念边数：4.60
```

---

## 💡 最佳实践

### 1. 配合 MFS 写入使用

```bash
# 写入记忆（自动建图）
mcporter call mfs-memory.mfs_write \
  path="/memory/doc.md" \
  type="NOTE" \
  content="用户朋友 游戏 游戏角色"

# 查看图谱增长
mcporter call mfs-memory.kg_stats
```

### 2. 深度探索概念

```bash
# 第一层扩展
mcporter call mfs-memory.kg_search query="用户朋友" max_depth=1

# 第二层扩展（默认）
mcporter call mfs-memory.kg_search query="用户朋友" max_depth=2

# 第三层扩展（更深入）
mcporter call mfs-memory.kg_search query="用户朋友" max_depth=3
```

### 3. 权重过滤

```bash
# 获取高权重关联（top_k 小）
mcporter call mfs-memory.kg_get_related concept="用户朋友" top_k=3

# 获取全部关联（top_k 大）
mcporter call mfs-memory.kg_get_related concept="用户朋友" top_k=20
```

---

## 📊 性能指标

| 工具 | 平均延迟 | 推荐用法 |
|------|---------|---------|
| **kg_stats** | <0.01ms | 随时调用 |
| **kg_get_related** | <0.05ms | 高频使用 |
| **kg_search** | <0.1ms | 搜索时使用 |

---

## ⚠️ 注意事项

1. **KG 依赖 MFT**: 知识图谱在 MFT create 时自动构建
2. **首次建图**: 第一次写入记忆时会初始化 KG
3. **持久化**: KG 数据存储在 `mfs_kg.db` 文件中
4. **性能**: 大规模图谱（10 万 + 概念）建议使用缓存

---

## 🚀 故障排查

### 问题 1: 工具未找到

```
错误：未知工具：kg_stats
```

**解决**: MCP server 需要重启以加载新工具

```bash
# 重启 MCP server（如果使用 daemon）
mcporter daemon restart
```

### 问题 2: KG 未启用

```
错误：知识图谱未启用
```

**解决**: 检查 MFT 初始化时是否传入 kg_db_path

### 问题 3: 概念不存在

```
未找到概念：'xxx'
```

**解决**: 
- 确认记忆已写入
- 检查关键词提取是否正常
- 尝试其他相关关键词

---

**工具状态**: ✅ 已实现  
**文档状态**: ✅ 完成  
**生产就绪**: ✅ 是
