# AI Agent 安装引导 / AI Agent Installation Guide

**复制以下内容给 AI Agent（OpenClaw、Hermes 等），即可完成完整安装和 MCP 配置**

**Copy the following content to AI Agent (OpenClaw, Hermes, etc.) to complete full installation and MCP configuration**

---

## 📋 任务：安装 Diting 记忆系统

你好！请帮我完成 Diting 记忆系统的安装和配置。以下是完整步骤：

Hello! Please help me complete the installation and configuration of Diting memory system. Here are the complete steps:

### 1️⃣ 克隆仓库 / Clone Repository

```bash
cd /root/.openclaw/workspace
git clone https://github.com/totwoto02/Diting.git
cd Diting
```

### 2️⃣ 安装依赖 / Install Dependencies

```bash
# 创建虚拟环境（可选）/ Create virtual environment (optional)
python3 -m venv .venv
source .venv/bin/activate

# 安装项目依赖 / Install project dependencies
pip install -e .

# 验证安装 / Verify installation
python3 -c "from diting import __version__; print(f'Diting v{__version__}')"
```

### 3️⃣ 运行测试 / Run Tests

```bash
# 运行完整测试套件 / Run full test suite
pytest tests/ -v --tb=short

# 检查覆盖率 / Check coverage
pytest tests/ --cov=diting --cov-report=term-missing
```

**预期结果 / Expected Results:**
- ✅ 425 个测试通过 / 425 tests passed
- ✅ 覆盖率 ≥80% / Coverage ≥80%
- ✅ 0 警告 / 0 warnings

### 4️⃣ 配置 MCP 服务器 / Configure MCP Server

**对于 OpenClaw 用户 / For OpenClaw Users:**

编辑 MCP 配置文件 / Edit MCP config file:
```bash
# OpenClaw MCP 配置路径 / OpenClaw MCP config path
~/.openclaw/mcp_config.json
```

添加 Diting MCP 服务器配置 / Add Diting MCP server configuration:
```json
{
  "mcpServers": {
    "diting": {
      "command": "python3",
      "args": ["-m", "diting.mcp_server"],
      "cwd": "/root/.openclaw/workspace/Diting",
      "env": {
        "DITING_DB_PATH": "/root/.openclaw/workspace/Diting/diting.db"
      }
    }
  }
}
```

**对于其他支持 MCP 的 Agent / For Other MCP-Supported Agents:**

将上述配置添加到你的 MCP 配置文件中 / Add the above configuration to your MCP config file.

### 5️⃣ 验证 MCP 连接 / Verify MCP Connection

```python
# 测试 MCP 连接 / Test MCP connection
from diting.mcp_server import main

# 或直接通过命令行测试 / Or test via command line
python3 -m diting.mcp_server --test
```

### 6️⃣ 基础功能测试 / Basic Functionality Test

```python
from diting.mft import MFT

# 初始化 / Initialize
mft = MFT(db_path="test.db")

# 创建记忆 / Create memory
inode = mft.create(
    path="/test/memory",
    type="NOTE",
    content="This is a test memory"
)

# 读取记忆 / Read memory
result = mft.read("/test/memory")
assert result["content"] == "This is a test memory"

# 搜索记忆 / Search memory
results = mft.search("test", scope="all")
assert len(results) > 0

# 清理 / Cleanup
import os
os.remove("test.db")

print("✅ Diting 安装成功！/ Diting installation successful!")
```

### 7️⃣ 可用工具 / Available Tools

安装完成后，AI Agent 可以使用以下工具：

After installation, AI Agent can use the following tools:

| 工具 / Tool | 功能 / Function | 示例 / Example |
|------|--------|------|
| `diting_read` | 读取记忆 / Read memory | `diting_read(path="/user/preferences")` |
| `diting_write` | 创建/更新记忆 / Create/Update memory | `diting_write(path="/user/name", content="Alice")` |
| `diting_search` | 搜索记忆 / Search memory | `diting_search(query="preferences")` |
| `diting_list` | 列出记忆 / List memories | `diting_list(type="NOTE")` |

### 8️⃣ 故障排除 / Troubleshooting

**问题 / Issue:** `ModuleNotFoundError: No module named 'diting'`

**解决 / Solution:**
```bash
cd /root/.openclaw/workspace/Diting
pip install -e .
```

**问题 / Issue:** MCP 服务器无法连接 / MCP server cannot connect

**解决 / Solution:**
1. 检查配置文件路径是否正确 / Check if config file path is correct
2. 验证 Python 路径 / Verify Python path
3. 确保工作目录存在 / Ensure working directory exists
4. 检查数据库文件权限 / Check database file permissions

**问题 / Issue:** 测试失败 / Tests fail

**解决 / Solution:**
```bash
# 重新安装依赖 / Reinstall dependencies
pip install -r requirements.txt

# 清除缓存 / Clear cache
rm -rf .pytest_cache __pycache__

# 重新运行测试 / Run tests again
pytest tests/ -v
```

---

## 🎯 完成标志 / Completion Checklist

- [ ] 仓库已克隆 / Repository cloned
- [ ] 依赖已安装 / Dependencies installed
- [ ] 测试通过（425/425） / Tests passed (425/425)
- [ ] 覆盖率 ≥80% / Coverage ≥80%
- [ ] MCP 配置已添加 / MCP configuration added
- [ ] MCP 连接验证成功 / MCP connection verified
- [ ] 基础功能测试通过 / Basic functionality test passed

---

## 📚 后续步骤 / Next Steps

1. 阅读 [QUICKSTART.md](QUICKSTART.md) 了解基础用法 / Read QUICKSTART.md for basic usage
2. 查看 [API.md](API.md) 了解完整 API / Check API.md for complete API reference
3. 参考 [DEVELOPER.md](DEVELOPER.md) 进行开发 / Refer to DEVELOPER.md for development

---

**版本 / Version**: 1.0.0.0  
**最后更新 / Last Updated**: 2026-04-18

---

## 🤖 AI Agent 快速指令 / AI Agent Quick Commands

**如果你是 AI Agent，收到此消息后请直接执行以下步骤：**

**If you are an AI Agent, please directly execute the following steps after receiving this message:**

1. 克隆仓库到 `/root/.openclaw/workspace/Diting`
2. 执行 `pip install -e .`
3. 运行 `pytest tests/ -v --tb=short` 验证
4. 将 MCP 配置添加到 `~/.openclaw/mcp_config.json`
5. 回复安装结果和测试状态

**开始执行 / Start Execution:**

```bash
cd /root/.openclaw/workspace && git clone https://github.com/totwoto02/Diting.git
```
