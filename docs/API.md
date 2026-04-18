# Diting API 文档

本文档详细说明 Diting (Memory File System) 提供的所有接口和工具。

---

## 📋 目录

- [diting_read](#diting_read) - 读取记忆
- [diting_write](#diting_write) - 写入/更新记忆
- [diting_search](#diting_search) - 搜索记忆
- [MCP 配置](#mcp-配置) - MCP Server 配置说明
- [错误码](#错误码) - 错误码说明
- [使用示例](#使用示例) - 完整使用示例

---

## diting_read

读取指定路径的记忆内容。

### 接口说明

| 属性 | 说明 |
|------|------|
| **工具名称** | `diting_read` |
| **功能** | 读取记忆文件内容 |
| **输入** | 路径 (path) |
| **输出** | 记忆内容 + 元数据 |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 记忆的虚拟路径，如 `/rules/coding` |

### 响应格式

**成功响应**:
```json
{
  "v_path": "/rules/coding",
  "type": "RULE",
  "content": "代码必须经过测试才能提交",
  "inode": 1,
  "created_at": "2026-04-13T12:00:00Z",
  "updated_at": "2026-04-13T12:00:00Z",
  "is_deleted": false
}
```

**失败响应**:
```json
{
  "error": "PATH_NOT_FOUND",
  "message": "路径 '/rules/coding' 不存在",
  "path": "/rules/coding"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `v_path` | string | 虚拟路径 (唯一标识) |
| `type` | string | 记忆类型 (NOTE/RULE/TASK/CODE/CONTACT/EVENT) |
| `content` | string | 记忆内容 |
| `inode` | integer | 内部节点 ID |
| `created_at` | string | 创建时间 (ISO 8601) |
| `updated_at` | string | 更新时间 (ISO 8601) |
| `is_deleted` | boolean | 是否已删除 (软删除标记) |

### 使用示例

#### Python API

```python
from diting import MFT

mft = MFT("file:diting_memory.db?mode=rwc")

# 读取记忆
result = mft.read("/rules/coding")
print(result["content"])
```

#### MCP 工具调用

```json
{
  "name": "diting_read",
  "arguments": {
    "path": "/rules/coding"
  }
}
```

---

## diting_write

写入新记忆或更新已有记忆。

### 接口说明

| 属性 | 说明 |
|------|------|
| **工具名称** | `diting_write` |
| **功能** | 写入或更新记忆文件 |
| **输入** | 路径 (path) + 类型 (type) + 内容 (content) |
| **输出** | 操作结果 + inode |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 记忆的虚拟路径，如 `/rules/coding` |
| `type` | string | ✅ | 记忆类型 (NOTE/RULE/TASK/CODE/CONTACT/EVENT) |
| `content` | string | ✅ | 记忆内容 |

### 响应格式

**成功响应 (创建)**:
```json
{
  "success": true,
  "inode": 1,
  "operation": "create",
  "v_path": "/rules/coding"
}
```

**成功响应 (更新)**:
```json
{
  "success": true,
  "inode": 1,
  "operation": "update",
  "v_path": "/rules/coding"
}
```

**失败响应**:
```json
{
  "success": false,
  "error": "INVALID_TYPE",
  "message": "无效的记忆类型 'UNKNOWN'"
}
```

### 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `NOTE` | 普通笔记 | 会议记录、想法 |
| `RULE` | 规则/约束 | 编码规范、行为准则 |
| `TASK` | 任务/待办 | 待办事项、项目任务 |
| `CODE` | 代码片段 | 函数、配置片段 |
| `CONTACT` | 联系人 | 人员信息、角色 |
| `EVENT` | 事件 | 日程、重要日期 |

### 使用示例

#### Python API

```python
from diting import MFT

mft = MFT("file:diting_memory.db?mode=rwc")

# 创建新记忆
inode = mft.create("/rules/coding", "RULE", "代码必须经过测试才能提交")
print(f"创建成功，inode={inode}")

# 更新已有记忆
mft.update("/rules/coding", "代码必须经过测试和代码审查才能提交")
```

#### MCP 工具调用

**创建新记忆**:
```json
{
  "name": "diting_write",
  "arguments": {
    "path": "/rules/coding",
    "type": "RULE",
    "content": "代码必须经过测试才能提交"
  }
}
```

**更新已有记忆**:
```json
{
  "name": "diting_write",
  "arguments": {
    "path": "/rules/coding",
    "type": "RULE",
    "content": "代码必须经过测试和代码审查才能提交"
  }
}
```

---

## diting_search

搜索记忆，支持关键词匹配和范围过滤。

### 接口说明

| 属性 | 说明 |
|------|------|
| **工具名称** | `diting_search` |
| **功能** | 搜索记忆文件 |
| **输入** | 查询词 (query) + 可选参数 |
| **输出** | 匹配的记忆列表 |

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 搜索关键词 |
| `scope` | string | ❌ | `/` | 搜索范围 (路径前缀) |
| `type` | string | ❌ | - | 记忆类型过滤 |
| `limit` | integer | ❌ | 100 | 最大返回数量 |

### 响应格式

**成功响应**:
```json
[
  {
    "v_path": "/rules/coding",
    "type": "RULE",
    "content": "代码必须经过测试才能提交",
    "inode": 1,
    "score": 1.0
  },
  {
    "v_path": "/notes/meeting",
    "type": "NOTE",
    "content": "会议记录：讨论代码质量",
    "inode": 2,
    "score": 0.5
  }
]
```

**空结果**:
```json
[]
```

### 搜索规则

1. **关键词匹配**: 使用 SQL LIKE 进行模糊匹配
2. **范围过滤**: `scope` 参数限制搜索路径前缀
3. **类型过滤**: `type` 参数过滤特定类型
4. **结果排序**: 按匹配度降序排列
5. **数量限制**: `limit` 参数限制最大返回数量

### 使用示例

#### Python API

```python
from diting import MFT

mft = MFT("file:diting_memory.db?mode=rwc")

# 基本搜索
results = mft.search("代码")
for r in results:
    print(f"{r['v_path']}: {r['content']}")

# 范围搜索 (只搜索 /rules 路径下)
results = mft.search("测试", scope="/rules")

# 类型过滤 (只搜索 RULE 类型)
results = mft.search("规范", type="RULE")

# 限制结果数量
results = mft.search("会议", limit=5)
```

#### MCP 工具调用

**基本搜索**:
```json
{
  "name": "diting_search",
  "arguments": {
    "query": "代码"
  }
}
```

**范围搜索**:
```json
{
  "name": "diting_search",
  "arguments": {
    "query": "测试",
    "scope": "/rules"
  }
}
```

**类型过滤**:
```json
{
  "name": "diting_search",
  "arguments": {
    "query": "规范",
    "type": "RULE",
    "limit": 10
  }
}
```

---

## MCP 配置

### OpenClaw 配置

在 OpenClaw 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "diting": {
      "command": "python",
      "args": ["-m", "diting.mcp_server"],
      "cwd": "/path/to/diting",
      "env": {
        "Diting_DB_PATH": "file:/path/to/diting_memory.db?mode=rwc"
      }
    }
  }
}
```

### OpenCode 配置

在 OpenCode 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "diting": {
      "command": "python",
      "args": ["-m", "diting.mcp_server"],
      "cwd": "/path/to/diting"
    }
  }
}
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `Diting_DB_PATH` | 数据库路径 | `file:memdb?mode=memory&cache=private` |
| `Diting_CACHE_SIZE` | LRU 缓存大小 | `1000` |
| `Diting_LOG_LEVEL` | 日志级别 | `INFO` |

### 启动 MCP Server

```bash
# 使用默认配置 (内存数据库)
python -m diting.mcp_server

# 使用文件数据库 (持久化)
Diting_DB_PATH="file:/path/to/diting_memory.db?mode=rwc" python -m diting.mcp_server

# 自定义日志级别
Diting_LOG_LEVEL=DEBUG python -m diting.mcp_server
```

---

## 错误码

### 错误类型

| 错误码 | HTTP 状态 | 说明 |
|--------|---------|------|
| `PATH_NOT_FOUND` | 404 | 路径不存在 |
| `INVALID_PATH` | 400 | 路径格式无效 |
| `INVALID_TYPE` | 400 | 记忆类型无效 |
| `CONTENT_TOO_LARGE` | 413 | 内容过大 |
| `DATABASE_ERROR` | 500 | 数据库错误 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `DUPLICATE_PATH` | 409 | 路径已存在 (创建时) |

### 错误响应格式

```json
{
  "error": "ERROR_CODE",
  "message": "人类可读的错误描述",
  "details": {
    "path": "/rules/coding",
    "type": "RULE"
  }
}
```

### 错误处理示例

#### Python API

```python
from diting import MFT, DitingPathNotFoundError, DitingError

mft = MFT("file:diting_memory.db?mode=rwc")

try:
    result = mft.read("/nonexistent/path")
except DitingPathNotFoundError as e:
    print(f"路径不存在：{e.path}")
except DitingError as e:
    print(f"Diting 错误：{e.message}")
```

#### MCP 工具

```json
// 请求
{
  "name": "diting_read",
  "arguments": {
    "path": "/nonexistent/path"
  }
}

// 响应
{
  "error": "PATH_NOT_FOUND",
  "message": "路径 '/nonexistent/path' 不存在",
  "details": {
    "path": "/nonexistent/path"
  }
}
```

---

## 使用示例

### 完整工作流

```python
from diting import MFT

# 1. 初始化
mft = MFT("file:diting_memory.db?mode=rwc")

# 2. 创建记忆
print("=== 创建记忆 ===")
mft.create("/rules/coding", "RULE", "代码必须经过测试才能提交")
mft.create("/rules/review", "RULE", "代码必须经过代码审查")
mft.create("/tasks/todo", "TASK", "完成 Diting 开发")
mft.create("/notes/ideas", "NOTE", "实现向量搜索功能")

# 3. 读取记忆
print("\n=== 读取记忆 ===")
result = mft.read("/rules/coding")
print(f"{result['v_path']}: {result['content']}")

# 4. 更新记忆
print("\n=== 更新记忆 ===")
mft.update("/rules/coding", "代码必须经过测试和代码审查才能提交")
result = mft.read("/rules/coding")
print(f"{result['v_path']}: {result['content']}")

# 5. 搜索记忆
print("\n=== 搜索记忆 ===")
results = mft.search("代码")
for r in results:
    print(f"{r['v_path']}: {r['content']}")

# 6. 范围搜索
print("\n=== 范围搜索 (/rules) ===")
results = mft.search("测试", scope="/rules")
for r in results:
    print(f"{r['v_path']}: {r['content']}")

# 7. 按类型列出
print("\n=== 所有规则 ===")
rules = mft.list_by_type("RULE")
for r in rules:
    print(f"{r['v_path']}: {r['content']}")

# 8. 删除记忆
print("\n=== 删除记忆 ===")
mft.delete("/tasks/todo")
print("已删除 /tasks/todo")

# 9. 验证删除
try:
    result = mft.read("/tasks/todo")
except Exception as e:
    print(f"验证：路径已删除 - {e}")
```

### OpenClaw 集成示例

在 OpenClaw 会话中：

```
用户：帮我记住一条规则

AI: 好的，我来帮你保存。

[调用 diting_write 工具]
{
  "name": "diting_write",
  "arguments": {
    "path": "/rules/coding",
    "type": "RULE",
    "content": "代码必须经过测试才能提交"
  }
}

AI: ✅ 已保存规则到 `/rules/coding`

---

用户：我刚才保存的规则是什么？

AI: 让我帮你查询。

[调用 diting_read 工具]
{
  "name": "diting_read",
  "arguments": {
    "path": "/rules/coding"
  }
}

AI: 你保存的规则是：**代码必须经过测试才能提交**

---

用户：搜索所有关于"代码"的记忆

AI: 好的，我来搜索。

[调用 diting_search 工具]
{
  "name": "diting_search",
  "arguments": {
    "query": "代码"
  }
}

AI: 找到以下相关记忆：
1. `/rules/coding`: 代码必须经过测试才能提交
2. `/rules/review`: 代码必须经过代码审查
```

---

## 性能提示

### 最佳实践

1. **使用范围搜索**: 当知道记忆大致位置时，使用 `scope` 参数提高搜索效率
2. **批量写入**: 多条记忆连续写入比分散写入性能更好
3. **合理使用缓存**: LRU 缓存会自动优化频繁访问的记忆
4. **避免过大内容**: 单条记忆内容建议 < 1MB

### 性能基准

| 操作 | 延迟 | 说明 |
|------|------|------|
| 读取 | <0.01ms | 缓存命中 |
| 写入 | 0.28ms | 单条写入 |
| 搜索 (100 条) | <0.01ms | 小数据集 |
| 搜索 (10000 条) | 50.44ms | 大数据集 |

---

*Last updated: 2026-04-13*
