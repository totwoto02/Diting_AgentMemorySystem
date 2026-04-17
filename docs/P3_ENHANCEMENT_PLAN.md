# P3 完善增强计划

**总耗时**: 5 小时  
**优先级**: P1（生产就绪必需）  
**更新时间**: 2026-04-16 00:33

---

## 📊 任务清单

| 编号 | 任务 | 预计耗时 | 优先级 | 状态 |
|------|------|---------|--------|------|
| ~~**T043**~~ | ~~配额管理系统~~ | ~~1h~~ | ~~P1~~ | ❌ 已移除 |
| **T044** | 对象存储集成 | 2h | P2 | 🔲 |
| **T045** | 监控告警系统 | 1h | P1 | 🔲 |
| **T046** | 日志审计 | 1h | P2 | 🔲 |
| **T047** | 批量处理优化 | 1h | P3 | 🔲 |

---

## ❌ T043: 配额管理系统（已移除）

**移除原因**: Diting 是面向 OpenClaw 等个人智能体的基于 SQLite 的记忆增强组件，单用户使用，不存在多用户配额管理需求。

**替代方案**: 个人用户可通过 SQLite 数据库大小或文件系统配额自行控制存储使用。

---

## 🗄️ T044: 对象存储集成（2h）

### 设计目标

支持 S3/OSS 对象存储，避免单机存储限制

### 功能设计

**存储后端**:
- 本地文件系统（默认）
- AWS S3
- 阿里云 OSS
- 腾讯云 COS

**配置设计**:
```python
STORAGE_CONFIG = {
    'backend': 'local',  # local/s3/oss/cos
    'local': {
        'root_path': '/data/mfs-storage'
    },
    's3': {
        'bucket': 'mfs-storage',
        'region': 'us-east-1',
        'access_key': 'xxx',
        'secret_key': 'xxx'
    },
    'oss': {
        'bucket': 'mfs-storage',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'access_key_id': 'xxx',
        'access_key_secret': 'xxx'
    }
}
```

**文件存储管理器**:
```python
class StorageBackend:
    def save(self, file_path: str, data: bytes) -> str:
        """保存文件，返回访问 URL"""
    
    def load(self, file_path: str) -> bytes:
        """加载文件"""
    
    def delete(self, file_path: str):
        """删除文件"""
    
    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
```

### 验收标准

- ✅ 本地存储正常
- ✅ S3 集成正常
- ✅ OSS 集成正常
- ✅ 配置切换方便

---

## 📊 T045: 监控告警系统（1h）

### 设计目标

实时监控系统状态，异常时告警

### 功能设计

**监控指标**:
- AI 调用成功率
- 平均响应时间
- 队列长度
- 磁盘使用率
- 内存使用率
- 熵值异常数量
- 温度异常数量

**告警规则**:
```python
ALERT_RULES = {
    'ai_error_rate': {'threshold': 0.1, 'window': '5m'},  # AI 错误率>10%
    'avg_latency': {'threshold': 1000, 'window': '5m'},   # 延迟>1s
    'queue_length': {'threshold': 100, 'window': '1m'},   # 队列>100
    'disk_usage': {'threshold': 0.9, 'window': '1h'},     # 磁盘>90%
    'high_entropy_count': {'threshold': 50, 'window': '1h'}  # 高熵记忆>50
}
```

**告警渠道**:
- 邮件通知
- Webhook（钉钉/企业微信）
- 系统日志

**监控面板**:
```python
class MonitorDashboard:
    def get_system_status(self) -> Dict:
        """获取系统状态"""
    
    def get_metrics(self, metric_name: str, time_range: str) -> List:
        """获取指标数据"""
    
    def check_alerts(self) -> List[Alert]:
        """检查告警"""
    
    def send_alert(self, alert: Alert):
        """发送告警"""
```

### 验收标准

- ✅ 指标采集正常
- ✅ 告警规则生效
- ✅ 告警通知发送
- ✅ 监控面板可用

---

## 📝 T046: 日志审计（1h）

### 设计目标

完整记录系统操作，支持审计和故障排查

### 功能设计

**日志类型**:
- 操作日志（用户操作）
- 系统日志（系统事件）
- 错误日志（异常信息）
- 审计日志（敏感操作）

**日志格式**:
```json
{
    "timestamp": "2026-04-16T00:00:00Z",
    "level": "INFO",
    "user_id": "user_001",
    "action": "ai_call",
    "resource": "slice_abc123",
    "details": {"model": "qwen-vl-max", "cost": 0.01},
    "ip_address": "192.168.1.1",
    "user_agent": "Diting-Client/1.0"
}
```

**日志存储**:
- 数据库存储（结构化）
- 文件存储（原始日志）
- 日志轮转（按天/大小）

**审计查询**:
```python
class AuditLogger:
    def log(self, user_id: str, action: str, resource: str, details: Dict):
        """记录审计日志"""
    
    def query(self, user_id: str = None, action: str = None, 
              time_range: str = None) -> List[Dict]:
        """查询审计日志"""
    
    def export(self, time_range: str, format: str = 'csv') -> bytes:
        """导出审计日志"""
```

### 验收标准

- ✅ 日志记录完整
- ✅ 查询功能正常
- ✅ 导出功能正常
- ✅ 日志轮转正常

---

## ⚡ T047: 批量处理优化（1h）

### 设计目标

优化批量操作性能，降低 API 成本

### 功能设计

**批量场景**:
- 批量 AI 调用（闲时处理）
- 批量熵计算（定期重算）
- 批量温度计算（定期重算）
- 批量文件清理（过期文件）

**队列设计**:
```python
BATCH_QUEUE = {
    'ai_summary': {'priority': 1, 'batch_size': 50},
    'entropy_calc': {'priority': 2, 'batch_size': 100},
    'temp_calc': {'priority': 2, 'batch_size': 100},
    'file_cleanup': {'priority': 3, 'batch_size': 200}
}
```

**定时任务**:
```python
CRON_JOBS = [
    {'schedule': '0 2 * * *', 'task': 'batch_ai_summary'},    # 凌晨 2 点
    {'schedule': '0 3 * * 0', 'task': 'batch_entropy_calc'},  # 每周日凌晨 3 点
    {'schedule': '0 4 * * 0', 'task': 'batch_temp_calc'},     # 每周日凌晨 4 点
    {'schedule': '0 5 * * *', 'task': 'batch_file_cleanup'}   # 每天凌晨 5 点
]
```

**优化策略**:
- 闲时处理（凌晨 2-5 点）
- 批量 API 调用（降低成本）
- 失败重试（保证成功率）
- 进度追踪（可视化）

### 验收标准

- ✅ 批量队列正常
- ✅ 定时任务执行
- ✅ 失败重试正常
- ✅ 进度可追踪

---

## 📅 执行计划

### 第 1 小时：监控告警
- [ ] 设计监控指标
- [ ] 实现指标采集
- [ ] 实现告警规则
- [ ] 集成通知渠道

### 第 2 小时：日志审计
- [ ] 设计日志格式
- [ ] 实现 AuditLogger
- [ ] 实现查询功能
- [ ] 实现导出功能

### 第 3-4 小时：对象存储
- [ ] 设计 StorageBackend 接口
- [ ] 实现本地存储
- [ ] 实现 S3 集成
- [ ] 实现 OSS 集成
- [ ] 编写测试

### 第 5 小时：批量优化
- [ ] 设计批量队列
- [ ] 实现定时任务
- [ ] 实现失败重试
- [ ] 编写测试

---

## ✅ 验收清单

| 任务 | 验收标准 | 状态 |
|------|---------|------|
| ~~T043 配额管理~~ | ~~已移除~~ | ❌ |
| T044 对象存储 | 4 项标准 | 🔲 |
| T045 监控告警 | 4 项标准 | 🔲 |
| T046 日志审计 | 4 项标准 | 🔲 |
| T047 批量优化 | 4 项标准 | 🔲 |

---

**开始执行 P3 完善增强！** 🚀
