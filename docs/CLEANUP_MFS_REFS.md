# 遗留 mfs 引用清理清单

**生成时间**: 2026-04-18 11:25

---

## 🔴 高优先级（必须修复）

### 1. 构建产物（应该被 .gitignore 忽略）

```
build/lib/diting/
mfs_memory.egg-info/
```

**处理**: 添加到 `.gitignore` 或删除

---

### 2. 配置文件

#### `config/mcporter.json`
```json
"mfs-memory": {
  "command": "python3 -m diting.mcp_server",
```
**修复**: 改为 `diting` 和 `python3 -m diting.mcp_server`

---

### 3. 脚本文件

#### `scripts/build_wheel.py`
```python
os.chdir("/root/.openclaw/workspace/projects/mfs-memory")
```
**修复**: 改为 `diting`

#### `scripts/release.py`
```python
os.chdir("/root/.openclaw/workspace/projects/mfs-memory")
```
**修复**: 改为 `diting`

#### `scripts/migrate_memory.py`
```python
sys.path.insert(0, '/root/.openclaw/workspace/projects/mfs-memory')
mfs_db = "/root/.openclaw/workspace/projects/Diting/diting.db"
```
**修复**: 改为 `diting`

#### `scripts/configure_mcp.py`
```python
"args": ["-m", "diting.mcp_server"],
```
**修复**: 改为 `diting.mcp_server`

---

### 4. MCP 配置文件

#### `mcp-configs/*.json` (4 个文件)
```json
"mfs-memory": {
  "args": ["-m", "diting.mcp_server"],
  "cwd": "/root/.openclaw/workspace/projects/mfs-memory",
```
**修复**: 改为 `diting` 和 `diting.mcp_server`

---

### 5. 文档中的路径引用

#### `docs/AI_AGENT_SETUP_GUIDE.md`
```python
from diting.mft import MFT
python3 -m py_compile /root/.openclaw/workspace/projects/diting/diting/mcp_server.py
```
**修复**: 导入改为 `diting`，路径删除 `mfs/`

#### `docs/DEPLOY.md`
```bash
pytest --cov=diting
python -m diting.mcp_server
```
**修复**: 改为 `diting`

#### `docs/DEVELOPER.md`
```
mfs/
from diting import MFT
pytest --cov=diting
flake8 diting/
```
**修复**: 改为 `diting`

#### `docs/其他文档`
大量 `mfs/` 路径引用需要改为 `diting/`

---

## 🟡 中优先级（建议修复）

### 6. 测试文件中的变量名

#### `tests/test_memory_correctness.py`
```python
def mfs_system(self):
    mft = mfs_system["mft"]
```
**建议**: 变量名改为 `diting_system`（不影响功能）

#### `tests/test_mock_conversations.py`
```python
def mfs_system(self):
```
**建议**: 变量名改为 `diting_system`

#### `tests/test_ultra_long_stress.py`
```python
def mfs_system(self):
```
**建议**: 变量名改为 `diting_system`

---

## 🟢 低优先级（保留不动）

### 7. MCP 工具名称（保留）

```python
diting_read, diting_write, diting_search
```
**保留原因**: 这是公开的 API 名称，更改会破坏现有集成

### 8. 数据库文件名（保留）

```
diting.db, diting_kg.db
```
**保留原因**: 向后兼容，避免迁移成本

### 9. 默认存储路径（保留）

```
~/.diting/memory.db
/tmp/mfs-storage
```
**保留原因**: 向后兼容

### 10. 包名引用（保留）

```python
from diting import __version__  # 在 install_check.py 中用于兼容检查
```
**保留原因**: 用于检查旧版本是否安装

---

## 📋 修复步骤

1. **清理构建产物**
   ```bash
   rm -rf build/ mfs_memory.egg-info/
   ```

2. **更新 .gitignore**
   ```
   build/
   *.egg-info/
   ```

3. **修复配置文件**
   - `config/mcporter.json`
   - `mcp-configs/*.json`

4. **修复脚本**
   - `scripts/*.py`

5. **修复文档**
   - `docs/*.md`

6. **运行全局搜索验证**
   ```bash
   grep -r "mfs/" --include="*.py" --include="*.md" --include="*.json" . | grep -v "__pycache__" | grep -v "build/"
   ```

---

## ✅ 修复后验证

```bash
# 应该只剩下合理的 mfs 引用（工具名、数据库名）
grep -r "mfs" --include="*.py" --include="*.md" --include="*.json" . \
  | grep -v "__pycache__" \
  | grep -v "build/" \
  | grep -v ".egg-info"
```

**预期结果**: 只包含 `diting_read`, `diting_write`, `diting_search`, `diting.db` 等合理引用
