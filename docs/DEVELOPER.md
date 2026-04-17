# Diting 开发者文档

本文档为 Diting (Memory File System) 的开发者提供详细的开发指南，包括代码结构、TDD 开发流程、测试说明、贡献指南和 Git 工作流。

---

## 📋 目录

- [代码结构说明](#代码结构说明)
- [TDD 开发指南](#tdd-开发指南)
- [测试说明](#测试说明)
- [贡献指南](#贡献指南)
- [Git 工作流](#git-工作流)

---

## 代码结构说明

### 目录结构

```
diting/
├── mfs/                        # 核心模块
│   ├── __init__.py            # 包初始化 + 导出 MFT 类
│   ├── mft.py                 # MFT 管理器 (核心数据结构)
│   ├── database.py            # SQLite 连接管理
│   ├── mcp_server.py          # MCP Server 实现
│   ├── config.py              # 配置管理
│   └── errors.py              # 自定义异常
├── tests/                      # 测试套件
│   ├── __init__.py
│   ├── test_mft.py            # MFT 单元测试
│   ├── test_mcp.py            # MCP 集成测试
│   ├── test_openclaw_integration.py  # OpenClaw 集成测试
│   ├── test_opencode_integration.py  # OpenCode 集成测试
│   ├── test_session_persistence.py   # 会话持久性测试
│   ├── test_benchmark.py             # 性能基准测试
│   └── conftest.py            # pytest 配置
├── docs/                       # 文档目录
│   ├── API.md                 # API 接口文档
│   ├── DEPLOY.md              # 部署指南
│   ├── DEVELOPER.md           # 开发者文档
│   └── GIT_WORKFLOW.md        # Git 工作流
├── db/                         # 数据库脚本
├── requirements.txt            # Python 依赖
├── pytest.ini                 # pytest 配置
├── .pre-commit-config.yaml    # Git hooks 配置
└── README.md                  # 项目说明
```

### 核心模块说明

#### mfs/__init__.py

包初始化文件，导出主要类和函数。

```python
from .mft import MFT
from .errors import DitingError, DitingPathNotFoundError, DitingInvalidTypeError

__all__ = ['MFT', 'DitingError', 'DitingPathNotFoundError', 'DitingInvalidTypeError']
__version__ = '0.1.0'
```

#### mfs/mft.py

MFT (Master File Table) 管理器，核心数据结构。

**主要功能**:
- `create(v_path, type, content)` - 创建记忆
- `read(v_path)` - 读取记忆
- `update(v_path, content)` - 更新记忆
- `delete(v_path)` - 删除记忆 (软删除)
- `search(query, scope, type, limit)` - 搜索记忆
- `list_by_type(type)` - 按类型列出记忆

**关键实现**:
```python
class MFT:
    def __init__(self, db_path=":memory:"):
        self.db = get_connection(db_path)
        self.cache = LRUCache(capacity=1000)
        self._init_schema()
    
    def create(self, v_path, type, content):
        # 实现逻辑
        pass
    
    def read(self, v_path):
        # 实现逻辑
        pass
```

#### mfs/database.py

SQLite 连接管理。

**主要功能**:
- `get_connection(db_path)` - 获取数据库连接
- `_init_schema()` - 初始化数据库表结构
- 连接池管理
- WAL 模式配置

#### mfs/mcp_server.py

MCP Server 实现，暴露工具给 AI Agent。

**主要功能**:
- `mfs_read` 工具实现
- `mfs_write` 工具实现
- `mfs_search` 工具实现
- MCP 协议处理

#### mfs/config.py

配置管理。

**主要功能**:
- 环境变量读取
- 配置文件解析
- 默认值管理

#### mfs/errors.py

自定义异常。

**异常类型**:
- `DitingError` - 基础异常
- `DitingPathNotFoundError` - 路径不存在
- `DitingInvalidTypeError` - 类型无效
- `DitingContentTooLargeError` - 内容过大

---

## TDD 开发指南

### TDD 核心原则

```
1. Red     → 先写失败的测试
2. Green   → 写最少代码让测试通过
3. Refactor → 重构优化，保持测试通过
```

### TDD 开发流程

#### Step 1: 理解需求

在开始编码前，明确要实现的功能：

```
需求：实现 MFT 的 create 方法
- 输入：v_path (路径), type (类型), content (内容)
- 输出：inode (整数 ID)
- 约束：路径唯一，类型必须是有效类型
```

#### Step 2: 编写测试 (Red)

创建测试文件 `tests/test_mft.py`:

```python
import pytest
from mfs import MFT, DitingInvalidTypeError

def test_create_basic():
    """测试基本创建功能"""
    mft = MFT(':memory:')
    inode = mft.create('/test/rules', 'RULE', '测试规则')
    assert inode > 0

def test_create_duplicate_path():
    """测试重复路径"""
    mft = MFT(':memory:')
    mft.create('/test/rules', 'RULE', '规则 1')
    with pytest.raises(Exception):  # 应抛出异常
        mft.create('/test/rules', 'RULE', '规则 2')

def test_create_invalid_type():
    """测试无效类型"""
    mft = MFT(':memory:')
    with pytest.raises(DitingInvalidTypeError):
        mft.create('/test/rules', 'INVALID', '内容')
```

运行测试 (会失败):

```bash
pytest tests/test_mft.py::test_create_basic -v
# ❌ FAILED: AttributeError: 'MFT' object has no attribute 'create'
```

#### Step 3: 实现功能 (Green)

编写最少代码让测试通过：

```python
# mfs/mft.py
class MFT:
    VALID_TYPES = {'NOTE', 'RULE', 'TASK', 'CODE', 'CONTACT', 'EVENT'}
    
    def __init__(self, db_path=":memory:"):
        self.db = get_connection(db_path)
        self._init_schema()
    
    def create(self, v_path, type, content):
        if type not in self.VALID_TYPES:
            raise DitingInvalidTypeError(f"无效类型：{type}")
        
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO mft (v_path, type, content) VALUES (?, ?, ?)",
            (v_path, type, content)
        )
        self.db.commit()
        return cursor.lastrowid
```

运行测试 (通过):

```bash
pytest tests/test_mft.py::test_create_basic -v
# ✅ PASSED
```

#### Step 4: 重构 (Refactor)

优化代码质量，保持测试通过：

```python
# 改进：添加路径验证、错误处理、日志
def create(self, v_path, type, content):
    if not v_path or not v_path.startswith('/'):
        raise DitingInvalidPathError(f"无效路径：{v_path}")
    
    if type not in self.VALID_TYPES:
        raise DitingInvalidTypeError(f"无效类型：{type}")
    
    try:
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO mft (v_path, type, content, created_at) VALUES (?, ?, ?, ?)",
            (v_path, type, content, datetime.utcnow())
        )
        self.db.commit()
        logger.info(f"创建成功：{v_path}")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        raise DitingPathNotFoundError(f"路径已存在：{v_path}") from e
```

运行所有测试 (保持通过):

```bash
pytest tests/test_mft.py -v
# ✅ 全部通过
```

### TDD 最佳实践

1. **测试先行**: 永远先写测试，再写实现
2. **小步快跑**: 每次只实现一个小功能
3. **测试命名**: 使用描述性的测试函数名
4. **断言明确**: 每个测试只验证一个行为
5. **保持绿色**: 重构前确保所有测试通过

---

## 测试说明

### 测试分类

#### 单元测试 (Unit Tests)

测试单个模块的功能。

```bash
# 运行 MFT 单元测试
pytest tests/test_mft.py -v

# 运行 MCP 单元测试
pytest tests/test_mcp.py -v
```

**测试覆盖**:
- 正常流程 (Happy Path)
- 错误路径 (Error Path)
- 边界条件 (Edge Cases)

#### 集成测试 (Integration Tests)

测试模块间的集成。

```bash
# 运行 OpenClaw 集成测试
pytest tests/test_openclaw_integration.py -v

# 运行 OpenCode 集成测试
pytest tests/test_opencode_integration.py -v
```

**测试覆盖**:
- MCP Server 初始化
- 工具调用
- 端到端工作流

#### 性能测试 (Benchmark Tests)

测试性能指标。

```bash
# 运行性能基准测试
pytest tests/test_benchmark.py -v
```

**测试覆盖**:
- 读写延迟
- 搜索性能
- 并发性能

### 运行测试

```bash
# 运行所有测试
pytest -v

# 运行特定测试文件
pytest tests/test_mft.py -v

# 运行特定测试函数
pytest tests/test_mft.py::test_create_basic -v

# 运行测试并查看覆盖率
pytest --cov=mfs --cov-report=html

# 运行测试并查看终端覆盖率报告
pytest --cov=mfs --cov-report=term-missing

# 运行测试并生成 JUnit 报告
pytest --junitxml=test-results.xml

# 只运行失败的测试
pytest --lf

# 重新运行上次失败的测试 + 新增测试
pytest --ff
```

### 测试覆盖率

```bash
# 查看总体覆盖率
pytest --cov=mfs

# 查看每个模块的覆盖率
pytest --cov=mfs --cov-report=term-missing

# 生成 HTML 报告
pytest --cov=mfs --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# 覆盖率要求
pytest --cov=mfs --cov-fail-under=80
```

**覆盖率目标**:
- MFT 核心: > 80%
- MCP Server: > 70%
- Database: > 60%
- 总计: > 80%

### 测试数据

使用内存数据库进行测试，避免污染生产数据：

```python
import pytest
from mfs import MFT

@pytest.fixture
def mft():
    """创建内存数据库 MFT 实例"""
    return MFT(':memory:')

def test_create(mft):
    inode = mft.create('/test', 'NOTE', 'content')
    assert inode > 0
```

---

## 贡献指南

### 贡献流程

1. **Fork 项目**
   ```bash
   # 在 GitHub 上点击 Fork 按钮
   ```

2. **克隆 Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/diting.git
   cd diting
   ```

3. **添加上游仓库**
   ```bash
   git remote add upstream https://github.com/xxx/diting.git
   ```

4. **创建功能分支**
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```

5. **开发功能**
   ```bash
   # 遵循 TDD 流程
   # 1. 写测试
   # 2. 写实现
   # 3. 重构
   
   # 运行测试
   pytest -v
   
   # 检查覆盖率
   pytest --cov=mfs
   ```

6. **提交变更**
   ```bash
   git add .
   git commit -m "feat: add your feature name"
   ```

7. **同步上游**
   ```bash
   git fetch upstream
   git rebase upstream/develop
   ```

8. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

9. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 描述
   - 等待代码审查

### 代码风格

遵循 PEP 8 规范：

```bash
# 安装代码检查工具
pip install flake8 black isort

# 检查代码风格
flake8 mfs/ --max-line-length=100

# 自动格式化
black mfs/ tests/

# 排序导入
isort mfs/ tests/
```

**代码规范**:
- 行宽: 100 字符
- 缩进: 4 空格
- 导入排序: 标准库 → 第三方 → 本地
- 类型注解: 推荐使用

### 提交规范

遵循 Conventional Commits 规范：

```bash
# 格式：<type>(<scope>): <subject>

# 类型
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式 (不影响运行)
refactor: 重构
test:     测试相关
chore:    构建/工具

# 示例
feat(mft): 添加 MFT 创建功能
fix(mcp): 修复 mfs_read 的错误处理
docs(readme): 更新快速开始指南
test(mft): 添加 MFT 单元测试
refactor(database): 优化数据库连接管理
chore(git): 添加 .gitignore
```

### 代码审查清单

提交 PR 前自查：

- [ ] 代码通过所有测试
- [ ] 测试覆盖率 > 80%
- [ ] 代码通过 flake8 检查
- [ ] 提交信息符合规范
- [ ] 代码有适当的注释
- [ ] 更新了相关文档
- [ ] 无敏感信息泄露

---

## Git 工作流

### 分支模型

```
main         - 主分支 (稳定版本，受保护)
  └── develop    - 开发分支 (日常开发)
       ├── feature/mft       - MFT 功能分支
       ├── feature/mcp       - MCP 功能分支
       └── feature/integration - 集成测试分支
```

**分支规则**:
- `main`: 只能通过 PR 合并，每次合并必须打 tag
- `develop`: 日常开发分支，所有功能分支从此分出
- `feature/*`: 功能开发分支，开发完成后合并回 develop
- `hotfix/*`: 紧急修复分支，从 main 分出，合并回 main 和 develop

### 开发流程

#### 1. 开始新功能

```bash
# 切换到 develop 分支
git checkout develop

# 同步上游
git pull upstream develop

# 创建功能分支
git checkout -b feature/your-feature
```

#### 2. 开发功能

```bash
# TDD 流程
# 1. 写测试
# 2. 运行测试 (失败)
# 3. 写实现
# 4. 运行测试 (通过)
# 5. 重构

# 提交变更
git add .
git commit -m "feat(your-feature): implement feature"
```

#### 3. 完成功能

```bash
# 运行所有测试
pytest -v

# 检查覆盖率
pytest --cov=mfs --cov-fail-under=80

# 检查代码风格
flake8 mfs/

# 合并到 develop
git checkout develop
git merge --no-ff feature/your-feature

# 删除功能分支
git branch -d feature/your-feature
```

#### 4. 发布版本

```bash
# 从 develop 合并到 main
git checkout main
git merge --no-ff develop

# 打 tag
git tag -a v0.1.0 -m "Phase 1 MVP: SQLite + MCP"

# 推送
git push origin main
git push origin v0.1.0
```

### 提交历史

```bash
# 查看提交历史
git log --oneline --graph

# 查看某次提交详情
git show <commit-hash>

# 查看文件变更历史
git log --follow <file-path>
```

### 回滚操作

```bash
# 撤销工作区修改
git checkout <file>

# 撤销暂存区修改
git reset HEAD <file>

# 撤销最后一次提交
git reset --soft HEAD~1

# 回滚到特定提交
git revert <commit-hash>

# 紧急回滚 (慎用)
git reset --hard <commit-hash>
```

### 冲突解决

```bash
# 合并时遇到冲突
git merge feature/branch

# 编辑冲突文件，解决冲突标记
# <<<<<<< HEAD
# 当前分支内容
# =======
# 合并分支内容
# >>>>>>> feature/branch

# 标记为解决
git add <file>

# 完成合并
git commit
```

### GitHub Actions CI/CD

项目使用 GitHub Actions 自动运行测试：

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=mfs --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 开发环境配置

### 推荐工具

| 工具 | 用途 | 安装命令 |
|------|------|---------|
| VS Code | 代码编辑器 | - |
| Python Extension | Python 支持 | - |
| GitLens | Git 增强 | - |
| pytest | 测试框架 | `pip install pytest` |
| Coverage.py | 覆盖率 | `pip install pytest-cov` |
| black | 代码格式化 | `pip install black` |
| flake8 | 代码检查 | `pip install flake8` |

### VS Code 配置

`.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "--cov=mfs",
    "--cov-report=term-missing"
  ],
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "ms-python.black-formatter",
  "editor.rulers": [100]
}
```

### Pre-commit Hooks

安装 pre-commit hooks:

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 hooks
pre-commit install

# 运行所有 hooks
pre-commit run --all-files
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
```

---

## 调试技巧

### 日志调试

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def some_function():
    logger.debug("调试信息")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
```

### 断点调试

```python
# Python 3.7+
def some_function():
    breakpoint()  # 设置断点
    # ... 代码
```

### 性能分析

```bash
# 使用 cProfile
python -m cProfile -o profile.stats mfs/mcp_server.py

# 查看分析结果
python -m pstats profile.stats
```

---

*Last updated: 2026-04-13*
