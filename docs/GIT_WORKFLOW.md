# Git 版本管理指南

**项目**: Diting (Memory File System)  
**版本**: v1.0  
**创建时间**: 2026-04-13  

---

## 一、分支策略

### 1.1 分支结构

```
main              - 主分支（稳定版本，受保护）
  └── develop         - 开发分支（日常开发）
       ├── feature/mft        - MFT 功能分支
       ├── feature/mcp        - MCP 功能分支
       ├── feature/integration - 集成测试分支
       └── hotfix/xxx         - 紧急修复分支
```

### 1.2 分支规则

| 分支 | 保护级别 | 合并规则 | 用途 |
|------|---------|---------|------|
| `main` | 🔒 受保护 | 只能 PR 合并 | 稳定版本，每次合并必须打 tag |
| `develop` | ⚠️ 部分保护 | PR 合并 | 日常开发分支 |
| `feature/*` | ❌ 无保护 | 直接提交 | 功能开发，完成后合并回 develop |
| `hotfix/*` | ⚠️ 部分保护 | PR 合并 | 紧急修复，从 main 分出 |

### 1.3 分支命名规范

```bash
# 功能分支
git checkout -b feature/mft-crud
git checkout -b feature/mcp-server
git checkout -b feature/integration-test

# 修复分支
git checkout -b fix/mft-read-error
git checkout -b fix/mcp-timeout

# 紧急修复（从 main 分出）
git checkout -b hotfix/critical-bug
```

---

## 二、提交规范 (Commit Convention)

### 2.1 提交格式

```bash
<type>(<scope>): <subject>

# 示例
feat(mft): 添加 MFT 创建功能
fix(mcp): 修复 mfs_read 工具的错误处理
docs(readme): 更新快速开始指南
test(mft): 添加 MFT 单元测试
chore(git): 添加 Git 分支保护规则
```

### 2.2 类型说明

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(mft): 添加 MFT 创建功能` |
| `fix` | 修复 bug | `fix(mcp): 修复读取超时问题` |
| `docs` | 文档更新 | `docs(readme): 更新安装指南` |
| `style` | 代码格式（不影响运行） | `style(mft): 格式化代码` |
| `refactor` | 重构 | `refactor(database): 优化连接池` |
| `test` | 测试相关 | `test(mft): 添加单元测试` |
| `chore` | 构建/工具变动 | `chore(git): 添加分支保护` |
| `devops` | CI/CD 相关 | `devops(github): 添加 Actions 配置` |

### 2.3 提交信息模板

```bash
# <type>(<scope>): <subject>
# |<----  50 characters  ---->|

# 详细说明（可选）
# - 为什么要做这个改动
# - 改动的主要内容
# - 可能的影响

# 关联 Issue（可选）
# Closes #123
# See also #456
```

---

## 三、版本标签 (Tagging)

### 3.1 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ 向后兼容的 bug 修复
  │     └─────── 向后兼容的新功能
  └───────────── 不兼容的 API 变更
```

### 3.2 Phase 1 版本计划

```bash
# v0.1.0 - Phase 1 MVP 发布
git tag -a v0.1.0 -m "Phase 1 MVP: SQLite + MCP"
git push origin v0.1.0

# v0.1.1 - Bug 修复
git tag -a v0.1.1 -m "Bug fixes for MCP server"
git push origin v0.1.1

# v0.2.0 - Phase 2 向量 + 拼装
git tag -a v0.2.0 -m "Phase 2: Vector + Assembler"
git push origin v0.2.0

# v1.0.0 - Phase 3 日志 + 防幻觉
git tag -a v1.0.0 -m "Phase 3: WAL + Anti-Hallucination"
git push origin v1.0.0
```

### 3.3 查看版本

```bash
# 查看所有 tag
git tag -l

# 查看特定 tag 信息
git show v0.1.0

# 查看版本历史
git log --oneline --decorate --graph
```

---

## 四、回滚策略

### 4.1 安全回滚（推荐）

```bash
# 回滚最后一次提交
git revert HEAD

# 回滚特定提交
git revert <commit-hash>

# 回滚后会创建新的提交，历史记录清晰
```

### 4.2 回滚到 tag

```bash
# 查看历史 tag
git tag -l

# 切换到特定 tag（只读）
git checkout v0.1.0

# 基于 tag 创建新分支进行修复
git checkout -b hotfix/from-v0.1.0 v0.1.0
```

### 4.3 紧急回滚（慎用）

```bash
# 警告：会丢失提交历史！
# 仅用于本地开发环境

# 回滚到特定 tag
git reset --hard v0.1.0

# 回滚到上一个提交
git reset --hard HEAD~1
```

### 4.4 回滚流程图

```
正常流程：
main: [v0.1.0] → [v0.1.1] → [v0.2.0]
              ↑
         发现问题
              ↓
回滚流程：
git revert HEAD  # 创建回滚提交
git push origin main
```

---

## 五、GitHub Actions CI/CD

### 5.1 CI 配置文件

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
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest --cov=mfs --cov-report=xml --cov-fail-under=80
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  lint:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install flake8
        run: pip install flake8
      
      - name: Run flake8
        run: flake8 mfs/ --max-line-length=100
```

### 5.2 分支保护规则

在 GitHub 仓库设置中配置：

```
Settings → Branches → Add branch protection rule

Branch name pattern: main
✓ Require a pull request before merging
✓ Require approvals (1)
✓ Require status checks to pass before merging
  - test (ubuntu-latest)
  - lint (ubuntu-latest)
✓ Require branches to be up to date before merging
✓ Include administrators
```

---

## 六、日常开发流程

### 6.1 开始新功能

```bash
# 1. 从 develop 分支创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/mft-crud

# 2. 开发功能（TDD 流程）
# 写测试 → 写实现 → 重构 → 提交

# 3. 提交代码
git add tests/test_mft.py
git commit -m "test(mft): 添加 MFT CRUD 测试"

git add mfs/mft.py
git commit -m "feat(mft): 实现 MFT CRUD 功能"

# 4. 推送到远程
git push origin feature/mft-crud
```

### 6.2 合并到 develop

```bash
# 1. 在 GitHub 上创建 Pull Request
# 2. 等待 CI 通过
# 3. 获得审查批准
# 4. 合并到 develop

# 5. 本地更新
git checkout develop
git pull origin develop
git branch -d feature/mft-crud  # 删除本地分支
```

### 6.3 发布版本

```bash
# 1. 从 develop 合并到 main
git checkout main
git merge develop
git push origin main

# 2. 打 tag
git tag -a v0.1.0 -m "Phase 1 MVP: SQLite + MCP"
git push origin v0.1.0

# 3. 在 GitHub 上创建 Release
# https://github.com/xxx/diting/releases/new
```

---

## 七、常用 Git 命令速查

### 7.1 分支管理

```bash
# 查看分支
git branch           # 本地分支
git branch -a        # 所有分支
git branch -r        # 远程分支

# 创建分支
git checkout -b feature/xxx
git checkout -b feature/xxx develop  # 从 develop 创建

# 删除分支
git branch -d feature/xxx      # 删除本地
git push origin --delete xxx   # 删除远程
```

### 7.2 提交历史

```bash
# 查看提交历史
git log --oneline              # 简洁模式
git log --oneline --graph      # 图形模式
git log --oneline --decorate   # 显示 tag

# 查看特定文件历史
git log -- mfs/mft.py

# 查看提交详情
git show <commit-hash>
```

### 7.3 版本回滚

```bash
# 安全回滚
git revert HEAD
git revert <commit-hash>

# 查看回滚点
git reflog

# 紧急回滚（慎用）
git reset --hard <commit-hash>
```

### 7.4 Tag 管理

```bash
# 创建 tag
git tag -a v0.1.0 -m "Phase 1 MVP"

# 查看 tag
git tag -l

# 推送 tag
git push origin v0.1.0
git push origin --tags  # 推送所有 tag

# 删除 tag
git tag -d v0.1.0
git push origin --delete v0.1.0
```

---

## 八、Git 配置清单

### 8.1 .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# 测试
.pytest_cache/
.coverage
htmlcov/
.tox/

# 敏感文件
.env
.env.local
*.key
*.pem
secrets/

# 日志
*.log
logs/

# 临时文件
tmp/
temp/
*.tmp
```

### 8.2 .gitattributes

```gitattributes
# 行尾符统一
* text=auto

# Python 文件
*.py text eol=lf

# Shell 脚本
*.sh text eol=lf

# 配置文件
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.md text eol=lf
```

### 8.3 .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
```

---

## 九、检查清单

### 9.1 每日检查

```bash
# 上班后
git status              # 查看当前状态
git pull origin develop # 更新 develop 分支

# 下班前
git add .
git commit -m "chore: daily progress"
git push origin feature/xxx
```

### 9.2 提交前检查

```bash
# 运行测试
pytest tests/ -v

# 检查覆盖率
pytest --cov=mfs --cov-fail-under=80

# 代码风格
flake8 mfs/ --max-line-length=100

# 格式化
black mfs/ tests/
```

### 9.3 发布前检查

```bash
# 所有测试通过
pytest tests/ -v

# 覆盖率达标
pytest --cov=mfs --cov-fail-under=80

# 文档齐全
ls README.md docs/*.md

# Git 历史清晰
git log --oneline --graph

# Tag 已创建
git tag -l v0.1.0
```

---

## 十、常见问题

### Q1: 提交信息写错了怎么办？

```bash
# 最后一次提交
git commit --amend -m "正确的提交信息"

# 之前的提交（交互式）
git rebase -i HEAD~3
# 将 commit 改为 edit，然后 git commit --amend
```

### Q2: 不小心提交到 main 分支怎么办？

```bash
# 1. 创建新分支保存当前工作
git checkout -b feature/my-work

# 2. 重置 main 分支
git checkout main
git reset --hard origin/main

# 3. 在 feature 分支继续开发
git checkout feature/my-work
```

### Q3: 代码冲突怎么解决？

```bash
# 1. 更新 develop 分支
git checkout develop
git pull origin develop

# 2. 切换回功能分支
git checkout feature/xxx

# 3. 合并 develop
git merge develop

# 4. 解决冲突文件
# 编辑冲突文件，删除 <<<<<<< ======= >>>>>>>

# 5. 提交解决
git add .
git commit -m "fix: resolve merge conflicts"
```

---

**维护人**: main  
**最后更新**: 2026-04-13
