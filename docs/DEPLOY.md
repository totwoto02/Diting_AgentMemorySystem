# Diting 部署指南

本文档提供 Diting (Memory File System) 的完整部署说明，包括环境要求、安装步骤、MCP 配置和常见问题。

---

## 📋 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [配置 MCP](#配置-mcp)
- [OpenClaw 集成](#openclaw-集成)
- [OpenCode 集成](#opencode-集成)
- [常见问题](#常见问题)

---

## 环境要求

### 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 单核 | 双核+ |
| 内存 | 512 MB | 1 GB+ |
| 磁盘 | 100 MB | 1 GB+ (取决于数据量) |
| 网络 | 无需联网 | - |

### 软件要求

| 组件 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.11+ | 必需 |
| **pip** | 最新 | Python 包管理器 |
| **SQLite** | 3.35+ | Python 内置 (无需单独安装) |
| **Git** | 任意版本 | 可选，用于版本管理 |

### 操作系统支持

- ✅ Linux (Ubuntu 20.04+, CentOS 7+, OpenCloudOS)
- ✅ macOS (10.15+)
- ✅ Windows (10+)
- ✅ WSL2 (Windows Subsystem for Linux)

### 验证环境

```bash
# 检查 Python 版本
python --version  # 应 >= 3.11

# 检查 pip
pip --version

# 检查 SQLite (Python 内置，无需单独检查)
python -c "import sqlite3; print(sqlite3.sqlite_version)"

# 检查 Git (可选)
git --version
```

---

## 安装步骤

### 1. 获取源代码

#### 方式一：Git 克隆 (推荐)

```bash
git clone https://github.com/xxx/diting.git
cd diting
```

#### 方式二：下载 ZIP

```bash
wget https://github.com/xxx/diting/archive/refs/heads/main.zip
unzip main.zip
cd diting-main
```

### 2. 创建虚拟环境 (推荐)

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖列表**:
```txt
mcp>=1.0.0        # MCP 协议
pytest>=7.0.0     # 测试框架
pytest-cov>=4.0.0 # 覆盖率
```

### 4. 验证安装

```bash
# 运行测试
pytest -v

# 查看覆盖率
pytest --cov=mfs --cov-report=term-missing

# 预期输出：所有测试通过，覆盖率 > 80%
```

### 5. 初始化数据库

Diting 会在首次运行时自动创建数据库。

**内存数据库** (临时，重启后数据丢失):
```bash
# 默认配置，无需额外设置
python -m mfs.mcp_server
```

**文件数据库** (持久化，推荐):
```bash
# 设置环境变量
export Diting_DB_PATH="file:/path/to/mfs_memory.db?mode=rwc"

# 或使用绝对路径
export Diting_DB_PATH="/absolute/path/to/mfs_memory.db"

# 启动 MCP Server
python -m mfs.mcp_server
```

### 6. 启动 MCP Server

```bash
# 前台运行 (开发调试)
python -m mfs.mcp_server

# 后台运行 (生产环境)
nohup python -m mfs.mcp_server > mfs.log 2>&1 &

# 使用 systemd (Linux 生产环境)
# 创建 /etc/systemd/system/mfs.service
[Unit]
Description=Diting MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/diting
Environment=Diting_DB_PATH=/path/to/mfs_memory.db
ExecStart=/path/to/venv/bin/python -m mfs.mcp_server
Restart=always

[Install]
WantedBy=multi-user.target

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable mfs
sudo systemctl start mfs
sudo systemctl status mfs
```

---

## 配置 MCP

### MCP Server 配置

Diting 通过 MCP (Model Context Protocol) 暴露工具给 AI Agent。

#### 环境变量配置

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `Diting_DB_PATH` | 数据库路径 | `:memory:` | `file:/path/to/mfs.db` |
| `Diting_CACHE_SIZE` | LRU 缓存大小 | `1000` | `2000` |
| `Diting_LOG_LEVEL` | 日志级别 | `INFO` | `DEBUG` |
| `Diting_LOG_FILE` | 日志文件路径 | `None` | `/var/log/mfs.log` |

#### 配置文件 (可选)

创建 `mfs_config.json`:

```json
{
  "database": {
    "path": "file:/path/to/mfs_memory.db?mode=rwc",
    "wal_mode": true,
    "timeout": 30
  },
  "cache": {
    "size": 1000,
    "ttl": 3600
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/mfs.log",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

启动时指定配置文件:

```bash
Diting_CONFIG=/path/to/mfs_config.json python -m mfs.mcp_server
```

---

## OpenClaw 集成

### 配置步骤

1. **找到 OpenClaw 配置文件**

通常位于 `~/.openclaw/config.json` 或项目根目录的 `.openclaw.json`。

2. **添加 MCP Server 配置**

```json
{
  "mcpServers": {
    "mfs": {
      "command": "python",
      "args": ["-m", "mfs.mcp_server"],
      "cwd": "/root/.openclaw/workspace/projects/diting",
      "env": {
        "Diting_DB_PATH": "file:/root/.openclaw/workspace/projects/diting/mfs_memory.db?mode=rwc"
      }
    }
  }
}
```

3. **重启 OpenClaw Gateway**

```bash
openclaw gateway restart
```

4. **验证集成**

在 OpenClaw 会话中测试：

```
用户：帮我记住一条规则：代码必须经过测试

AI: [调用 mfs_write 工具]
✅ 已保存规则到 `/rules/coding`
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `command` | 启动命令 (python) |
| `args` | 命令参数 (运行 mcp_server 模块) |
| `cwd` | 工作目录 (Diting 项目路径) |
| `env` | 环境变量 (数据库路径等) |

---

## OpenCode 集成

### 配置步骤

1. **找到 OpenCode 配置文件**

通常位于 `~/.opencode/config.json` 或项目根目录的 `.opencode.json`。

2. **添加 MCP Server 配置**

```json
{
  "mcp": {
    "servers": {
      "mfs": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mfs.mcp_server"],
        "cwd": "/root/.openclaw/workspace/projects/diting",
        "env": {
          "Diting_DB_PATH": "file:/root/.openclaw/workspace/projects/diting/mfs_memory.db?mode=rwc"
        }
      }
    }
  }
}
```

3. **重启 OpenCode**

```bash
# 如果使用 CLI
opencode restart

# 或者重新打开终端会话
```

4. **验证集成**

在 OpenCode 会话中测试：

```
用户：保存这条规则：所有代码必须有单元测试

AI: [调用 mfs_write 工具]
✅ 规则已保存到 `/rules/testing`
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `type` | 连接类型 (stdio 或 sse) |
| `command` | 启动命令 |
| `args` | 命令参数 |
| `cwd` | 工作目录 |
| `env` | 环境变量 |

---

## 常见问题

### Q1: Python 版本过低

**错误**: `SyntaxError: invalid syntax` 或 `ModuleNotFoundError`

**解决**:
```bash
# 检查 Python 版本
python --version  # 需要 >= 3.11

# 安装 Python 3.11+
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# CentOS/RHEL:
sudo yum install python3.11

# macOS (使用 Homebrew):
brew install python@3.11

# 验证安装
python3.11 --version
```

### Q2: 依赖安装失败

**错误**: `ERROR: Could not find a version that satisfies the requirement`

**解决**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像 (中国大陆)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者使用阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### Q3: 数据库锁定

**错误**: `sqlite3.OperationalError: database is locked`

**解决**:
1. 检查是否有其他进程占用数据库
2. 使用 WAL 模式提高并发性能
3. 减少并发写入频率

```bash
# 检查占用进程
lsof mfs_memory.db

# 杀死占用进程
kill -9 <PID>

# 或删除数据库文件重新创建 (数据会丢失)
rm mfs_memory.db
```

### Q4: MCP Server 无法启动

**错误**: `ModuleNotFoundError: No module named 'mfs'`

**解决**:
```bash
# 确保在项目根目录运行
cd /path/to/diting

# 或者将项目添加到 PYTHONPATH
export PYTHONPATH=/path/to/diting:$PYTHONPATH

# 或者使用 -m 参数运行
python -m mfs.mcp_server
```

### Q5: OpenClaw/OpenCode 无法连接 MCP

**错误**: `MCP server not responding`

**解决**:
1. 检查 MCP Server 是否运行
2. 检查配置文件路径是否正确
3. 检查环境变量是否设置

```bash
# 手动测试 MCP Server
cd /path/to/diting
python -m mfs.mcp_server

# 检查日志
tail -f mfs.log

# 验证配置文件
cat ~/.openclaw/config.json | jq .mcpServers
```

### Q6: 性能问题

**现象**: 读写延迟高，搜索慢

**解决**:
```bash
# 1. 增加缓存大小
export Diting_CACHE_SIZE=2000

# 2. 使用 SSD 存储数据库
export Diting_DB_PATH="/path/to/ssd/mfs_memory.db"

# 3. 启用 WAL 模式 (已在代码中默认启用)
# 4. 定期清理已删除的记忆
python -c "from mfs import MFT; mft = MFT('file:mfs.db'); mft.vacuum()"
```

### Q7: 数据丢失

**现象**: 重启后数据不见

**解决**:
1. 确保使用文件数据库，而非内存数据库
2. 检查数据库路径是否正确
3. 检查文件权限

```bash
# 检查数据库文件
ls -la mfs_memory.db

# 确保使用文件数据库
export Diting_DB_PATH="file:/absolute/path/to/mfs_memory.db?mode=rwc"

# 检查文件权限
chmod 644 mfs_memory.db
```

### Q8: 测试失败

**错误**: `pytest` 运行失败

**解决**:
```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行特定测试
pytest tests/test_mft.py -v

# 查看详细错误
pytest tests/test_mft.py -v -s

# 检查覆盖率
pytest --cov=mfs --cov-report=term-missing
```

---

## 运维指南

### 日志管理

```bash
# 查看日志
tail -f mfs.log

# 日志轮转 (使用 logrotate)
# /etc/logrotate.d/mfs
/var/log/mfs.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 your_user your_group
}
```

### 备份策略

```bash
# 每日备份脚本
#!/bin/bash
DB_PATH="/path/to/mfs_memory.db"
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份
cp "$DB_PATH" "$BACKUP_DIR/mfs_memory_$DATE.db"

# 删除 7 天前的备份
find "$BACKUP_DIR" -name "mfs_memory_*.db" -mtime +7 -delete
```

### 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 数据库大小 | 监控数据增长 | > 1GB |
| 读写延迟 | 性能指标 | > 100ms |
| 错误率 | 错误请求占比 | > 1% |
| 缓存命中率 | 缓存效率 | < 80% |

---

## 故障排除

### 诊断命令

```bash
# 检查 Python 环境
python --version
pip list | grep -E "mcp|pytest"

# 检查数据库文件
ls -lh mfs_memory.db
file mfs_memory.db

# 检查进程
ps aux | grep mcp_server

# 检查端口 (如果使用网络模式)
netstat -tlnp | grep mfs

# 查看系统资源
top -p $(pgrep -f mcp_server)
```

### 恢复流程

1. **停止服务**
   ```bash
   sudo systemctl stop mfs
   # 或
   kill $(pgrep -f mcp_server)
   ```

2. **备份当前状态**
   ```bash
   cp mfs_memory.db mfs_memory.db.backup
   ```

3. **诊断问题**
   ```bash
   python -c "from mfs import MFT; mft = MFT('file:mfs_memory.db'); print(mft.search(''))"
   ```

4. **修复或恢复**
   ```bash
   # 从备份恢复
   cp mfs_memory.db.backup mfs_memory.db
   
   # 或重建数据库
   rm mfs_memory.db
   python -m mfs.mcp_server  # 会自动创建新数据库
   ```

5. **重启服务**
   ```bash
   sudo systemctl start mfs
   ```

---

*Last updated: 2026-04-13*
