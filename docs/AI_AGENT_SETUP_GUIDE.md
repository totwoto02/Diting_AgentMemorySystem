# AI Agent 安装与初始化引导文档

**版本**: v1.0  
**适用**: OpenClaw + Diting v0.3.0  
**最后更新**: 2026-04-15

---

## ⚠️ 重要提示

**开始之前请阅读**:

1. **备份优先** - 任何操作前先备份现有数据
2. **测试环境** - 首次安装建议在测试环境进行
3. **逐步验证** - 每步完成后验证再继续
4. **风险告知** - 本指南涉及数据迁移，存在潜在风险

---

## 📋 目录

1. [前置检查](#1-前置检查)
2. [备份现有数据](#2-备份现有数据)
3. [安装 Diting](#3-安装-mfs)
4. [初始化配置](#4-初始化配置)
5. [记忆迁移](#5-记忆迁移)
6. [验证测试](#6-验证测试)
7. [故障排查](#7-故障排查)
8. [最佳实践](#8-最佳实践)

---

## 1. 前置检查

### 1.1 系统要求

```bash
# 检查 Python 版本（需要 3.11+）
python3 --version
# 应该输出：Python 3.11.x 或更高

# 检查 pip
pip3 --version

# 检查 OpenClaw 状态
openclaw status
```

**要求**:
- ✅ Python >= 3.11
- ✅ pip 可用
- ✅ OpenClaw 正常运行
- ✅ 至少 100MB 可用磁盘空间

### 1.2 环境检查清单

```bash
# 创建工作目录检查脚本
cat > /tmp/check_env.sh << 'EOF'
#!/bin/bash
echo "=== 环境检查 ==="
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version | head -1)"
echo "可用空间：$(df -h /root | tail -1 | awk '{print $4}')"
echo "OpenClaw: $(which openclaw 2>/dev/null || echo '未找到')"
echo ""
echo "工作目录：/root/.openclaw/workspace"
echo "备份目录：/root/.openclaw/backups"
EOF

chmod +x /tmp/check_env.sh
/tmp/check_env.sh
```

---

## 2. 备份现有数据

### ⚠️ 警告：此步骤至关重要

**备份所有现有记忆和配置文件，避免数据丢失。**

### 2.1 自动备份脚本

```bash
#!/bin/bash
# 备份脚本：backup_agent.sh

BACKUP_DIR="/root/.openclaw/backups/agent_backup_$(date +%Y%m%d_%H%M%S)"
echo "=== 开始备份 AI Agent 数据 ==="
echo "备份目录：$BACKUP_DIR"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份记忆文件
echo "[1/5] 备份 MEMORY.md..."
cp /root/.openclaw/workspace/MEMORY.md "$BACKUP_DIR/" 2>/dev/null || echo "  不存在"

# 备份 memory 目录
echo "[2/5] 备份 memory/ 目录..."
cp -r /root/.openclaw/workspace/memory/ "$BACKUP_DIR/" 2>/dev/null || echo "  不存在"

# 备份配置文件
echo "[3/5] 备份配置文件..."
for file in SOUL.md USER.md TOOLS.md IDENTITY.md; do
    cp /root/.openclaw/workspace/$file "$BACKUP_DIR/" 2>/dev/null || echo "  $file 不存在"
done

# 备份 MCP 配置
echo "[4/5] 备份 MCP 配置..."
cp /root/.openclaw/workspace/config/mcporter.json "$BACKUP_DIR/" 2>/dev/null || echo "  不存在"

# 备份 Diting 数据库（如果已存在）
echo "[5/5] 备份 Diting 数据库..."
cp /root/.openclaw/workspace/projects/diting/*.db "$BACKUP_DIR/" 2>/dev/null || echo "  不存在"

echo ""
echo "=== 备份完成 ==="
echo "备份位置：$BACKUP_DIR"
echo ""
ls -lh "$BACKUP_DIR"
```

### 2.2 执行备份

```bash
# 运行备份脚本
bash /tmp/backup_agent.sh

# 验证备份
ls -lh /root/.openclaw/backups/
```

### 2.3 备份验证清单

- [ ] MEMORY.md 已备份
- [ ] memory/ 目录已备份
- [ ] SOUL.md, USER.md, TOOLS.md 已备份
- [ ] mcporter.json 已备份
- [ ] 备份文件大小合理（>1KB）

---

## 3. 安装 Diting

### 3.1 下载/准备 Diting

```bash
# 检查 Diting 项目目录
Diting_DIR="/root/.openclaw/workspace/projects/diting"

if [ -d "$Diting_DIR" ]; then
    echo "✅ Diting 项目已存在"
    cd "$Diting_DIR"
else
    echo "❌ Diting 项目不存在，需要克隆或创建"
    # 如果有 Git 仓库
    # git clone <repo_url> "$Diting_DIR"
fi
```

### 3.2 安装依赖

```bash
cd /root/.openclaw/workspace/projects/diting

# 检查 requirements.txt
if [ -f "requirements.txt" ]; then
    echo "安装依赖..."
    pip3 install -r requirements.txt
else
    echo "⚠️  requirements.txt 不存在，创建默认配置..."
    cat > requirements.txt << 'EOF'
# Diting Memory File System Dependencies
mcp>=1.0.0
pytest>=7.0
pytest-cov>=4.0
pytest-asyncio>=0.23
EOF
    pip3 install -r requirements.txt
fi
```

### 3.3 安装 Diting 包

```bash
cd /root/.openclaw/workspace/projects/diting

# 可编辑安装（推荐，便于开发）
pip3 install -e .

# 或者普通安装
# pip3 install .

# 验证安装
python3 -c "from mfs.mft import MFT; print('✅ Diting 安装成功')"
```

### 3.4 验证 MCP 配置

```bash
# 检查 MCP 服务器配置
cat /root/.openclaw/workspace/config/mcporter.json | grep -A 10 "diting"

# 如果没有配置，添加
python3 << 'EOF'
import json

config_path = '/root/.openclaw/workspace/config/mcporter.json'

# 读取现有配置
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 添加 Diting 配置（如果不存在）
if 'diting' not in config.get('mcpServers', {}):
    config['mcpServers']['diting'] = {
        "description": "Diting Memory File System - Local MCP Server",
        "command": "python3",
        "args": ["-m", "mfs.mcp_server"],
        "cwd": "/root/.openclaw/workspace/projects/diting",
        "env": {
            "PYTHONPATH": "/root/.openclaw/workspace/projects/diting"
        }
    }
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ Diting 配置已添加")
else:
    print("✅ Diting 配置已存在")
EOF
```

---

## 4. 初始化配置

### 4.1 创建 Diting 数据库

```bash
cd /root/.openclaw/workspace/projects/diting

# 初始化 MFT 和 KG
python3 << 'EOF'
from mfs.mft import MFT

# 创建数据库（会自动初始化 schema）
mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')

print("✅ Diting 数据库已创建")
print(f"   Diting 数据库：mfs.db")
print(f"   KG 数据库：mfs_kg.db")

# 验证
stats = mft.get_stats()
print(f"   初始记录数：{stats['total']}")

if mft.kg:
    kg_stats = mft.kg.get_stats()
    print(f"   KG 概念数：{kg_stats['concept_count']}")
EOF
```

### 4.2 配置 MCP Server

```bash
# 重启 MCP daemon（如果已运行）
mcporter daemon restart

# 验证 Diting 工具可用
mcporter list diting

# 应该显示 6 个工具：
# - mfs_read
# - mfs_write
# - mfs_search
# - kg_search
# - kg_get_related
# - kg_stats
```

### 4.3 初始化对话管理器

```bash
python3 << 'EOF'
from mfs.mft import MFT
from mfs.dialog_manager import DialogManager

# 初始化
mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')
dm = DialogManager(mft)

print("✅ 对话管理器已初始化")
print(f"   热数据路径：{dm.path_hot}")
print(f"   温数据路径：{dm.path_warm}")
print(f"   冷数据路径：{dm.path_cold}")
print(f"   热数据阈值：{dm.hot_days} 天")
print(f"   温数据阈值：{dm.warm_days} 天")
EOF
```

---

## 5. 记忆迁移

### ⚠️ 警告：此步骤有风险

**确保备份已完成并验证！**

### 5.1 迁移脚本

```bash
cd /root/.openclaw/workspace/projects/diting

# 运行迁移脚本（使用备份目录）
python3 scripts/migrate_memory.py
```

### 5.2 手动迁移（可选）

如果自动迁移失败，可以手动迁移重要记忆：

```bash
python3 << 'EOF'
from mfs.mft import MFT

mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')

# 手动迁移关键记忆
memories = [
    ("/agent/main/MEMORY.md", "长期记忆", "文件内容..."),
    ("/agent/main/config/SOUL.md", "身份配置", "文件内容..."),
    # 添加更多...
]

for path, desc, content in memories:
    try:
        mft.create(path, "NOTE", content)
        print(f"✅ {desc} 已迁移")
    except Exception as e:
        print(f"❌ {desc} 迁移失败：{e}")

print("\n迁移完成！")
EOF
```

### 5.3 迁移验证

```bash
# 验证迁移结果
mcporter call diting.kg_stats
mcporter call diting.mfs_search query="关键记忆"
```

---

## 6. 验证测试

### 6.1 基础功能测试

```bash
# 测试 1: 写入记忆
echo "=== 测试 1: 写入记忆 ==="
mcporter call diting.mfs_write \
  path="/test/setup_guide.md" \
  type="NOTE" \
  content="安装测试记忆"

# 测试 2: 读取记忆
echo "=== 测试 2: 读取记忆 ==="
mcporter call diting.mfs_read \
  path="/test/setup_guide.md"

# 测试 3: 搜索记忆
echo "=== 测试 3: 搜索记忆 ==="
mcporter call diting.mfs_search \
  query="安装测试"

# 测试 4: KG 统计
echo "=== 测试 4: KG 统计 ==="
mcporter call diting.kg_stats

# 测试 5: KG 搜索
echo "=== 测试 5: KG 搜索 ==="
mcporter call diting.kg_search \
  query="测试"
```

### 6.2 集成测试

```bash
# 运行完整测试套件
cd /root/.openclaw/workspace/projects/diting
python3 -m pytest tests/ -v
```

### 6.3 验证清单

- [ ] Diting 数据库创建成功
- [ ] MCP 工具全部可用（6 个）
- [ ] 写入记忆正常
- [ ] 读取记忆正常
- [ ] 搜索记忆正常
- [ ] KG 统计正常
- [ ] KG 搜索正常
- [ ] 记忆迁移完成
- [ ] 测试全部通过

---

## 7. 故障排查

### 7.1 常见问题

#### 问题 1: MCP 工具未找到

```
错误：未知工具：kg_stats
```

**解决**:
```bash
# 重启 MCP daemon
mcporter daemon restart

# 验证工具列表
mcporter list diting

# 如果仍无，检查 mcp_server.py 是否正确
python3 -m py_compile /root/.openclaw/workspace/projects/diting/mfs/mcp_server.py
```

#### 问题 2: 数据库路径错误

```
sqlite3.OperationalError: unable to open database file
```

**解决**:
```bash
# 检查目录权限
ls -la /root/.openclaw/workspace/projects/diting/

# 确保目录存在且可写
mkdir -p /root/.openclaw/workspace/projects/diting
chmod 755 /root/.openclaw/workspace/projects/diting
```

#### 问题 3: 记忆迁移失败

```
UNIQUE constraint failed: mft.v_path
```

**解决**:
```bash
# 路径冲突，清理测试数据
cd /root/.openclaw/workspace/projects/diting
rm -f mfs.db mfs_kg.db

# 重新运行迁移
python3 scripts/migrate_memory.py
```

#### 问题 4: KG 未启用

```
错误：知识图谱未启用
```

**解决**:
```bash
# 检查 MFT 初始化是否传入 kg_db_path
python3 << 'EOF'
from mfs.mft import MFT
mft = MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')
print(f"KG enabled: {mft.kg is not None}")
EOF
```

### 7.2 日志位置

```bash
# MCP 日志
tail -f /root/.openclaw/logs/mcp*.log

# OpenClaw 日志
tail -f /root/.openclaw/logs/openclaw.log

# Diting 调试
export DEBUG=1
python3 -m mfs.mcp_server
```

### 7.3 恢复备份

如果安装失败，恢复备份：

```bash
# 找到最新备份
BACKUP_DIR=$(ls -td /root/.openclaw/backups/agent_backup_* | head -1)
echo "恢复备份：$BACKUP_DIR"

# 恢复记忆文件
cp "$BACKUP_DIR/MEMORY.md" /root/.openclaw/workspace/
cp -r "$BACKUP_DIR/memory/" /root/.openclaw/workspace/

# 恢复配置文件
for file in SOUL.md USER.md TOOLS.md mcporter.json; do
    cp "$BACKUP_DIR/$file" /root/.openclaw/workspace/ 2>/dev/null
done

echo "✅ 备份恢复完成"
```

---

## 8. 最佳实践

### 8.1 安装建议

1. **测试环境先行** - 首次安装先在测试环境验证
2. **分步执行** - 每步完成后验证再继续
3. **保留备份** - 至少保留 3 份历史备份
4. **文档记录** - 记录所有自定义配置

### 8.2 使用建议

1. **重要记忆手动标记**
   ```python
   dm.mark_as_important(path, reason="重要事件")
   ```

2. **定期清理**
   ```bash
   # 每周运行一次清理
   python3 -c "from mfs.mft import MFT; from mfs.dialog_manager import DialogManager; dm = DialogManager(MFT(db_path='mfs.db', kg_db_path='mfs_kg.db')); dm.cleanup_old_dialogs()"
   ```

3. **定期备份**
   ```bash
   # 每天备份一次
   0 2 * * * bash /tmp/backup_agent.sh
   ```

### 8.3 性能优化

1. **KG 缓存** - 高频查询使用 LRU 缓存
2. **批量写入** - 使用事务批量插入
3. **定期清理** - 避免数据库膨胀

### 8.4 安全建议

1. **权限控制** - 数据库文件权限 644
2. **备份加密** - 敏感记忆加密备份
3. **访问日志** - 记录所有写入操作

---

## 📋 安装检查清单

### 安装前
- [ ] 系统要求检查通过
- [ ] 备份脚本准备就绪
- [ ] 备份目录空间充足

### 安装中
- [ ] 备份完成并验证
- [ ] Diting 安装成功
- [ ] MCP 配置正确
- [ ] 数据库初始化成功

### 安装后
- [ ] 6 个 MCP 工具全部可用
- [ ] 记忆迁移完成
- [ ] 所有测试通过
- [ ] 备份已更新

### 运行中
- [ ] 定期备份（每天）
- [ ] 定期清理（每周）
- [ ] 监控性能
- [ ] 记录问题

---

## 📞 获取帮助

**文档**:
- Diting 使用指南：`docs/DIALOG_MANAGER_USAGE.md`
- KG 集成文档：`docs/KG_INTEGRATION_COMPLETE.md`
- MCP 工具指南：`docs/MCP_KG_TOOLS_USAGE.md`

**日志**:
- `/root/.openclaw/logs/`

**备份**:
- `/root/.openclaw/backups/`

---

**最后更新**: 2026-04-15  
**维护人**: Diting Team  
**版本**: v1.0
