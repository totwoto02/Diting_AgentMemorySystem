# Diting 发布指南

## 版本命名规范

遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)：

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ 向后兼容的 bug 修复
  │     └─────── 向后兼容的新功能
  └───────────── 不兼容的 API 变更
```

**示例**:
- `0.1.0` - Phase 1 MVP 发布
- `0.2.0` - Phase 2 向量 + 拼装
- `1.0.0` - Phase 3 日志 + 防幻觉 (稳定版)

---

## 发布流程

### 1. 发布前检查清单

```bash
# 所有测试通过
pytest tests/ -v

# 覆盖率达标 (>90%)
pytest --cov=mfs --cov-fail-under=90

# 代码风格检查
flake8 mfs/ --max-line-length=100

# 文档齐全
ls -la README.md docs/*.md
```

### 2. 更新版本号

编辑 `setup.py`:
```python
version="0.1.0"  # 更新版本号
```

### 3. 更新 CHANGELOG.md

```markdown
## [0.1.0] - 2026-04-13

### Added
- MFT 核心管理器
- MCP Server 实现
- 集成测试 (OpenClaw/OpenCode)
- 完整文档

### Changed
- 无

### Fixed
- 无
```

### 4. Git 提交和打 tag

```bash
# 提交所有变更
git add -A
git commit -m "release: v0.1.0 - Phase 1 MVP"

# 打 tag
git tag -a v0.1.0 -m "Diting Phase 1 MVP Release"

# 推送到远程
git push origin main
git push origin v0.1.0
```

### 5. PyPI 发布

```bash
# 安装构建工具
pip install build twine

# 构建分发包
python -m build

# 上传到 PyPI
twine upload dist/*
```

### 6. GitHub Release

1. 访问 https://github.com/yourusername/diting/releases/new
2. 选择 tag: `v0.1.0`
3. 填写发布说明 (复制 CHANGELOG.md 内容)
4. 点击 "Publish release"

---

## CHANGELOG.md 模板

```markdown
# 更新日志

## [0.1.0] - 2026-04-13

### Added
- MFT 核心管理器
  - 支持 CRUD 操作
  - 支持类型约束 (NOTE/RULE/CODE/TASK/CONTACT/EVENT)
  - 支持 LRU 缓存优化
- MCP Server 实现
  - mfs_read/mfs_write/mfs_search 工具
  - 错误处理和异常传播
- 测试套件
  - 单元测试 (101 个)
  - 集成测试 (77 个)
  - 性能基准测试
  - 测试覆盖率 93.71%
- 文档
  - README.md
  - API 文档
  - 部署指南
  - 开发者文档

### Changed
- 无

### Fixed
- 无

### Security
- 无
```

---

## 发布清单

### Phase 1 MVP (v0.1.0)

- [x] 核心功能完成
  - [x] MFT 管理器
  - [x] MCP Server
  - [x] 数据库连接
- [x] 测试完成
  - [x] 单元测试 (>100 个)
  - [x] 集成测试 (>70 个)
  - [x] 覆盖率 >90%
- [x] 文档完成
  - [x] README.md
  - [x] API 文档
  - [x] 部署指南
  - [x] 开发者文档
- [x] CI/CD 配置
  - [x] GitHub Actions
  - [x] 自动测试
  - [x] 覆盖率检查
- [x] PyPI 配置
  - [x] setup.py
  - [x] 版本号设置
- [ ] GitHub Release
- [ ] PyPI 发布

---

## 运维指南

### 日志

日志文件位置：`~/.mfs/logs/`

```bash
# 查看最新日志
tail -f ~/.mfs/logs/mfs.log

# 清理旧日志
find ~/.mfs/logs/ -name "*.log" -mtime +7 -delete
```

### 备份

```bash
# 备份 Diting 数据库
cp ~/.mfs/mfs.db ~/.mfs/backup/mfs_$(date +%Y%m%d).db

# 定期备份 (cron)
0 2 * * * cp ~/.mfs/mfs.db ~/.mfs/backup/mfs_$(date +\%Y\%m\%d).db
```

### 监控

```bash
# 检查 Diting 进程
ps aux | grep mfs

# 检查数据库大小
du -sh ~/.mfs/mfs.db

# 检查测试覆盖率
pytest --cov=mfs --cov-report=term
```

---

## 故障排除

### 常见问题

**Q: 测试失败怎么办？**

A: 运行 `pytest tests/ -v` 查看详细错误，根据错误信息修复。

**Q: 覆盖率不达标怎么办？**

A: 运行 `pytest --cov=mfs --cov-report=html` 查看覆盖率报告，针对未覆盖的代码添加测试。

**Q: PyPI 上传失败怎么办？**

A: 检查版本号是否重复，确保 `setup.py` 配置正确。

**Q: GitHub Actions 失败怎么办？**

A: 查看 Actions 日志，根据错误信息修复代码或配置。

---

**维护人**: Diting Team  
**最后更新**: 2026-04-13  
**版本**: v0.1.0
