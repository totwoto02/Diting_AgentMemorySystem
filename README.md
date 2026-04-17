# Diting (谛听)

**DitingFS** - A Thermodynamics-Inspired Memory File System for AI Agents

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 300 passed](https://img.shields.io/badge/tests-300%20passed-green.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-66%25-green.svg)]()

---

## 🦄 命名由来

**谛听**是地藏王菩萨的坐骑，能**听辨万物、识别真伪**。

### 神兽特性与技术映射

| 谛听能力 | 技术实现 | 说明 |
|----------|---------|------|
| **听** | FTS5 全文检索 | 聆听用户查询，快速检索记忆 |
| **辨** | 熵值计算 | 辨别记忆争议性（熵值高低） |
| **真** | WAL 审计日志 | 真实记录，防止 AI 幻觉 |
| **伪** | 矛盾检测 | 识别冲突记忆，标记高熵 |

**寓意：** 如谛听般辨别记忆真伪，如热力学般管理记忆能量。

---

## 🎯 概述

谛听 (DitingFS) 是一个为 AI 代理设计的复杂记忆管理系统，融合三大核心概念：

1. **热力学四系统** - 能量 (U)、热度 (H)、温度 (T)、熵 (S)、自由能 (G)
2. **NTFS 文件系统架构** - MFT 主文件表、inode、虚拟路径
3. **防幻觉机制** - WAL 日志审计、矛盾检测、熵值判断

### 核心特性

- 🔥 **热力学四系统** - 完整的能量/热度/温度/熵/自由能计算
- 📁 **MFT 架构** - NTFS 式主文件表，支持虚拟路径管理
- 🔍 **SQLite FTS5** - 全文检索，类 BM25 评分
- 🕸️ **知识图谱** - 自动概念提取和关系映射
- 🛡️ **防幻觉机制** - WAL 日志、审计追踪、回滚能力
- 🖼️ **多模态支持** - 图片、语音、文本，AI 生成摘要
- 🔒 **并发安全** - 线程安全操作，适当锁定

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/totwoto02/Diting.git
cd Diting

# 安装依赖
pip install -e .

# 运行测试
pytest tests/ -v
```

### 基础用法

```python
from mfs.mft import MFT

# 初始化 MFT（主文件表）
mft = MFT(db_path="diting.db")

# 创建记忆
inode = mft.create(
    path="/user/preferences",
    type="NOTE",
    content="User prefers dark mode and concise responses"
)

# 读取记忆
result = mft.read("/user/preferences")
print(result["content"])

# 搜索记忆
results = mft.search("preferences", scope="all")
for r in results:
    print(f"Path: {r['v_path']}, Content: {r['content']}")

# 更新记忆
mft.update("/user/preferences", content="Updated preferences...")

# 删除记忆
mft.delete("/user/preferences")
```

---

## 📚 核心概念

### 热力学类比

| 热力学 | 谛听记忆系统 | 说明 |
|--------|------------|------|
| **能量 (U)** | 访问次数 | 记忆被访问的总次数 |
| **热度 (H)** | 热度评分 | 近期访问频率 (0-100) |
| **温度 (T)** | 关联度 | 与当前上下文的关联程度 |
| **熵 (S)** | 争议性 | 矛盾/不确定性水平 |
| **自由能 (G)** | 有效性 | G = U - TS，决定记忆能否被提取 |

### 记忆状态

| 状态 | 热度评分 | 说明 |
|------|---------|------|
| 🔥 **热** | 70-100 | 频繁访问，高优先级 |
| 🌤️ **温** | 40-69 | 中等访问频率 |
| ❄️ **冷** | 10-39 | 很少访问 |
| 🧊 **冻** | 0-9 | 明确废弃/低有效性 |

---

## 🔧 架构

```
Diting/
├── mfs/
│   ├── mft.py              # 主文件表（核心）
│   ├── fts5_search.py      # 全文检索
│   ├── heat_manager.py     # 热度/温度系统
│   ├── entropy_manager.py  # 熵系统
│   ├── free_energy_manager.py  # 自由能计算
│   ├── knowledge_graph.py  # 知识图谱 V2
│   ├── wal_logger.py       # WAL 日志（防幻觉）
│   ├── integrity_tracker.py  # 完整性追踪
│   └── ...
├── tests/
│   ├── test_mft.py
│   ├── test_fts5.py
│   ├── test_knowledge_graph.py
│   └── ...
├── docs/
│   ├── API.md
│   ├── DEVELOPER.md
│   └── ...
└── README.md
```

---

## 🧪 测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 测试覆盖率

```bash
pytest tests/ --cov=mfs --cov-report=html
```

### 预期结果

- ✅ **300 个测试** 通过
- ✅ **66% 覆盖率** (达到 65% 要求)
- ✅ **0 警告**

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [API.md](docs/API.md) | 完整 API 参考 |
| [DEVELOPER.md](docs/DEVELOPER.md) | 开发者指南 |
| [INSTALL.md](docs/INSTALL.md) | 安装指南 |
| [QUICKSTART.md](docs/QUICKSTART.md) | 快速入门 |

---

## 🔒 隐私与安全

**重要**: 本项目仅用于**技术演示**。

- ✅ 代码库中不包含个人数据
- ✅ 所有测试数据使用通用示例（如"用户 A"、"测试朋友"）
- ✅ 配置文件（`.env`、凭证）已加入 gitignore
- ✅ 敏感操作需要用户明确确认

**部署到 GitHub 前：**
1. 审查所有文档中的个人信息
2. 从测试文件中删除真实用户数据
3. 确保 `.gitignore` 包含敏感文件
4. 使用环境变量存储凭证

---

## 🤝 MCP 集成

谛听提供 MCP（Model Context Protocol）服务器用于 AI 代理集成：

```json
{
  "mcpServers": {
    "diting": {
      "command": "python3",
      "args": ["-m", "mfs.mcp_server"],
      "cwd": "/path/to/Diting",
      "env": {
        "Diting_DB_PATH": "/path/to/diting.db"
      }
    }
  }
}
```

### 可用工具

- `mfs_read` - 按路径读取记忆
- `mfs_write` - 创建或更新记忆
- `mfs_search` - 按关键词搜索记忆
- `mfs_list` - 按类型列出记忆

---

## 📊 性能

| 操作 | 延迟 | 吞吐量 |
|------|------|--------|
| **读取** | ~0.00ms | ~10,000 ops/s |
| **写入** | ~0.28ms | ~3,500 ops/s |
| **搜索** | ~50ms | ~20 ops/s |

*在标准硬件上测量，10K+ 记忆*

---

## 🛠️ 开发

### 代码质量

```bash
# 运行 linter
ruff check mfs/

# 格式化代码
black mfs/

# 运行测试
pytest tests/ -v
```

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/your-feature

# 提交变更
git add .
git commit -m "feat: add new feature"

# 推送并创建 PR
git push origin feature/your-feature
```

---

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE)。

---

## 🙏 致谢

- 灵感来源于 NTFS 文件系统设计
- 热力学原理应用于信息管理
- 为 OpenClaw AI 代理框架构建

---

**版本**: 1.0.0.0  
**最后更新**: 2026-04-17  
**维护者**: [@totwoto02](https://github.com/totwoto02)
