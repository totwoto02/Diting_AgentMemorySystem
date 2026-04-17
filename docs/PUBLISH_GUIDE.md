# GitHub + PyPI 发布准备指南

**创建时间**: 2026-04-13 21:32  
**目的**: 指导 Diting Phase 1 MVP 发布到 GitHub 和 PyPI

---

## 一、GitHub 发布准备

### 1.1 账号要求

**必需**:
- ✅ **GitHub 账号** (免费注册：https://github.com/signup)
- ✅ 已验证邮箱地址
- ✅ 已启用双因素认证 (2FA) ⚠️ **重要**

**推荐**:
- ⭐ 完善个人资料 (头像、简介)
- ⭐ 添加 SSH 密钥 (方便 push 代码)

### 1.2 仓库准备

**已有** (Task 6 已准备):
- ✅ README.md
- ✅ LICENSE (MIT)
- ✅ .github/workflows/ci.yml
- ✅ setup.py
- ✅ CHANGELOG.md

**需要操作**:
1. 创建 GitHub 仓库
2. 上传代码
3. 配置仓库描述
4. 添加主题标签

### 1.3 发布步骤

#### Step 1: 创建 GitHub 仓库

```bash
# 方法 A: 使用 GitHub CLI (推荐)
gh repo create diting --public --description "Memory File System - AI 记忆的 Git + NTFS" --source=. --remote=origin --push

# 方法 B: 网页创建
# 1. 访问 https://github.com/new
# 2. 仓库名：diting
# 3. 描述：Memory File System - AI 记忆的 Git + NTFS
# 4. 公开仓库 (Public)
# 5. 不要初始化 (已有代码)
# 6. 点击 "Create repository"
```

#### Step 2: 推送代码到 GitHub

```bash
# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/diting.git

# 推送到 main 分支
git branch -M main
git push -u origin main

# 推送所有 tag
git push --tags
```

#### Step 3: 创建 GitHub Release

**方法 A: 网页创建**
```
1. 访问 https://github.com/YOUR_USERNAME/diting/releases/new
2. Tag version: v0.1.0
3. Release title: Diting Phase 1 MVP Release
4. 发布说明：复制 CHANGELOG.md 内容
5. 点击 "Publish release"
```

**方法 B: 使用 GitHub CLI**
```bash
gh release create v0.1.0 \
  --title "Diting Phase 1 MVP Release" \
  --notes-file CHANGELOG.md \
  --generate-notes
```

#### Step 4: 配置仓库设置

```
1. 访问 Settings
2. About 区域:
   - Website: https://github.com/YOUR_USERNAME/diting
   - Description: Memory File System - AI 记忆的 Git + NTFS
3. Topics:
   - memory-system
   - ai-agent
   - mcp
   - sqlite
   - python
4. Save changes
```

---

## 二、PyPI 发布准备

### 2.1 账号要求

**必需**:
- ✅ **PyPI 账号** (免费注册：https://pypi.org/account/register/)
- ✅ 已验证邮箱地址
- ✅ 已启用双因素认证 (2FA) ⚠️ **重要**

**推荐**:
- ⭐ 完善个人资料
- ⭐ 添加 API Token (不要直接用密码)

### 2.2 环境准备

**安装工具**:
```bash
# 安装构建和发布工具
pip install build twine

# 验证安装
python -m build --version
twine --version
```

### 2.3 配置 API Token

**推荐方式** (不要直接用密码):

#### 方法 A: 使用 .pypirc 文件

```bash
# 创建 ~/.pypirc 文件
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # 你的 API Token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # 你的 API Token
EOF

# 设置权限
chmod 600 ~/.pypirc
```

#### 方法 B: 使用 twine 命令行

```bash
# 发布时输入 Token
twine upload dist/* -u __token__
# 然后粘贴 API Token
```

### 2.4 获取 API Token

```
1. 访问 https://pypi.org/manage/account/token/
2. 点击 "Add API token"
3. Token name: diting
4. Scope: Entire account (或指定项目)
5. 点击 "Create token"
6. **复制 Token** (只显示一次！)
7. 保存到 ~/.pypirc 或密码管理器
```

### 2.5 发布步骤

#### Step 1: 构建分发包

```bash
# 清理旧构建
rm -rf build/ dist/ *.egg-info

# 构建源码包和 wheel
python -m build

# 验证构建产物
ls -lh dist/
# 应该看到:
# mfs_memory-0.1.0.tar.gz
# mfs_memory-0.1.0-py3-none-any.whl
```

#### Step 2: 测试上传 (强烈推荐)

```bash
# 上传到 TestPyPI (测试环境)
twine upload --repository testpypi dist/*

# 验证上传
# 访问 https://test.pypi.org/project/diting/
```

#### Step 3: 正式上传

```bash
# 上传到 PyPI
twine upload dist/*

# 验证上传
# 访问 https://pypi.org/project/diting/
```

#### Step 4: 验证安装

```bash
# 等待 5-10 分钟 (PyPI 索引更新)

# 测试安装
pip install diting

# 验证版本
python -c "import mfs; print(mfs.__version__)"
```

---

## 三、发布前检查清单

### 3.1 代码检查

```bash
# ✅ 所有测试通过
pytest tests/ -v

# ✅ 覆盖率达标 (>90%)
pytest --cov=mfs --cov-fail-under=90

# ✅ 代码风格检查
flake8 mfs/ --max-line-length=100

# ✅ 版本号正确
grep "version=" setup.py  # 应该是 0.1.0
```

### 3.2 文档检查

```bash
# ✅ README.md 存在
ls -la README.md

# ✅ LICENSE 存在
ls -la LICENSE

# ✅ CHANGELOG.md 存在
ls -la CHANGELOG.md

# ✅ 文档齐全
ls -la docs/*.md
```

### 3.3 Git 检查

```bash
# ✅ 所有变更已提交
git status  # 应该是 clean

# ✅ 已打 tag
git tag -l v0.1.0

# ✅ 远程仓库配置
git remote -v
```

### 3.4 账号检查

```bash
# ✅ GitHub 账号
gh auth status

# ✅ PyPI 账号
cat ~/.pypirc  # 检查配置

# ✅ 双因素认证
# GitHub: https://github.com/settings/security
# PyPI: https://pypi.org/manage/account/
```

---

## 四、常见问题

### Q1: GitHub 2FA 如何启用？

**步骤**:
```
1. 访问 https://github.com/settings/security
2. 点击 "Enable two-factor authentication"
3. 选择验证方式 (推荐 Authenticator App)
4. 使用手机 App 扫描二维码 (如 Google Authenticator)
5. 输入验证码
6. 保存恢复代码 (重要！)
```

### Q2: PyPI 2FA 如何启用？

**步骤**:
```
1. 访问 https://pypi.org/manage/account/
2. 点击 "Add two-factor authentication"
3. 选择验证方式 (推荐 TOTP App)
4. 使用手机 App 扫描二维码
5. 输入验证码
6. 保存恢复代码 (重要！)
```

### Q3: 忘记 PyPI 密码怎么办？

**解决方案**:
```
1. 使用 API Token 代替密码 (推荐)
2. 或者重置密码：https://pypi.org/help/#forgot-password
```

### Q4: GitHub push 被拒绝怎么办？

**解决方案**:
```bash
# 使用 Personal Access Token 代替密码
# https://github.com/settings/tokens

git push https://YOUR_TOKEN@github.com/YOUR_USERNAME/diting.git main
```

### Q5: PyPI 上传失败 "File already exists"

**解决方案**:
```bash
# 版本号重复，需要升级版本号
# 编辑 setup.py，修改 version="0.1.1"

# 重新构建
rm -rf build/ dist/
python -m build

# 重新上传
twine upload dist/*
```

### Q6: 如何发布到 TestPyPI?

**步骤**:
```bash
# 1. 注册 TestPyPI 账号
# https://test.pypi.org/account/register/

# 2. 获取 TestPyPI API Token
# https://test.pypi.org/manage/account/token/

# 3. 添加到 ~/.pypirc
[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...

# 4. 上传测试
twine upload --repository testpypi dist/*
```

---

## 五、发布后验证

### 5.1 GitHub 验证

```bash
# ✅ 访问仓库页面
# https://github.com/YOUR_USERNAME/diting

# ✅ 检查 README 渲染
# 应该正常显示 Markdown

# ✅ 检查 CI/CD
# https://github.com/YOUR_USERNAME/diting/actions
# 应该看到绿色的勾

# ✅ 检查 Release
# https://github.com/YOUR_USERNAME/diting/releases
# 应该看到 v0.1.0
```

### 5.2 PyPI 验证

```bash
# ✅ 访问项目页面
# https://pypi.org/project/diting/

# ✅ 检查项目信息
# - 版本号：0.1.0
# - 许可证：MIT
# - Python 版本：>=3.11
# - 作者：Diting Team

# ✅ 测试安装
pip install diting
python -c "import mfs; print(mfs.__version__)"

# ✅ 检查 CI/CD
# 访问 Actions 页面，确认测试通过
```

---

## 六、快速发布脚本

创建 `scripts/release.sh`:

```bash
#!/bin/bash
set -e

echo "=== Diting Release Script ==="
echo "Version: 0.1.0"
echo ""

# 1. 运行测试
echo "1. Running tests..."
pytest tests/ -v --cov=mfs --cov-fail-under=90

# 2. 代码风格检查
echo "2. Checking code style..."
flake8 mfs/ --max-line-length=100

# 3. 构建分发包
echo "3. Building distribution..."
rm -rf build/ dist/
python -m build

# 4. 上传到 PyPI
echo "4. Uploading to PyPI..."
twine upload dist/*

# 5. 创建 GitHub Release
echo "5. Creating GitHub Release..."
gh release create v0.1.0 \
  --title "Diting Phase 1 MVP Release" \
  --notes-file CHANGELOG.md \
  --generate-notes

# 6. 推送 tag
echo "6. Pushing tags..."
git push --tags

echo ""
echo "=== Release Complete! ==="
echo "GitHub: https://github.com/YOUR_USERNAME/diting"
echo "PyPI: https://pypi.org/project/diting/"
```

使用:
```bash
chmod +x scripts/release.sh
./scripts/release.sh
```

---

## 七、总结

### 必需账号

| 平台 | 账号 | 注册链接 | 2FA 必需 |
|------|------|---------|---------|
| **GitHub** | GitHub 账号 | https://github.com/signup | ✅ 是 |
| **PyPI** | PyPI 账号 | https://pypi.org/account/register/ | ✅ 是 |
| **TestPyPI** | TestPyPI 账号 | https://test.pypi.org/account/register/ | ❌ 否 (推荐) |

### 必需工具

```bash
# Python 工具
pip install build twine

# GitHub 工具 (可选)
brew install gh  # macOS
# 或 https://cli.github.com/
```

### 预计时间

| 步骤 | 预计时间 |
|------|---------|
| 注册账号 | 10 分钟 |
| 启用 2FA | 5 分钟 |
| 配置 API Token | 5 分钟 |
| 构建分发包 | 2 分钟 |
| 上传到 PyPI | 2 分钟 |
| 创建 GitHub Release | 5 分钟 |
| **总计** | **~30 分钟** |

---

**维护人**: Diting Team  
**最后更新**: 2026-04-13 21:32  
**版本**: v0.1.0
