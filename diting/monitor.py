"""
监控告警系统

实时监控系统状态，异常时告警
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List

import psutil


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    CRITICAL = "critical"  # 严重


@dataclass
class Alert:
    """告警对象"""

    id: str
    level: AlertLevel
    metric: str
    message: str
    threshold: float
    current_value: float
    timestamp: datetime


class MonitorDashboard:
    """监控面板"""

    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化监控面板

        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}

        # 告警规则配置
        self.alert_rules = self.config.get(
            "ALERT_RULES",
            {
                # AI 错误率>10%
                "ai_error_rate": {"threshold": 0.1, "window": "5m"},
                "avg_latency": {"threshold": 1000, "window": "5m"},  # 延迟>1s
                "disk_usage": {"threshold": 0.9, "window": "1h"},  # 磁盘>90%
                "memory_usage": {"threshold": 0.9, "window": "1h"},  # 内存>90%
                "high_entropy_count": {"threshold": 50, "window": "1h"},  # 高熵记忆>50
            },
        )

        # 告警冷却记录
        self._alert_cooldowns: Dict[str, datetime] = {}

        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """初始化数据库表"""
        # 监控指标表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS monitor_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 告警记录表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                level TEXT NOT NULL,
                metric TEXT NOT NULL,
                message TEXT,
                threshold REAL,
                current_value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0
            )
        """)

        # 创建索引
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_time ON monitor_metrics(metric_name, timestamp)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_alert_time ON alert_log(timestamp)")

        self.db.commit()

    def get_system_status(self) -> Dict:
        """
        获取系统状态

        Returns:
            系统状态字典
        """
        # 系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # 数据库统计
        cursor = self.db.execute(
            "SELECT COUNT(*) FROM monitor_metrics WHERE timestamp > datetime('now', '-1 hour')"
        )
        metrics_count = cursor.fetchone()[0]

        cursor = self.db.execute("SELECT COUNT(*) FROM alert_log WHERE acknowledged = 0")
        active_alerts = cursor.fetchone()[0]

        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available / 1024 / 1024,  # MB
                "disk_percent": disk.percent,
                "disk_free": disk.free / 1024 / 1024 / 1024,  # GB
            },
            "metrics": {"count_last_hour": metrics_count},
            "alerts": {"active": active_alerts},
            "status": "healthy" if active_alerts == 0 else "warning",
            "timestamp": datetime.now().isoformat(),
        }

    def record_metric(self, metric_name: str, metric_value: float):
        """
        记录监控指标

        Args:
            metric_name: 指标名称
            metric_value: 指标值
        """
        self.db.execute(
            """
            INSERT INTO monitor_metrics (metric_name, metric_value)
            VALUES (?, ?)
        """,
            (metric_name, metric_value),
        )
        self.db.commit()

    def get_metrics(self, metric_name: str, time_range: str = "1h") -> List[Dict]:
        """
        获取指标数据

        Args:
            metric_name: 指标名称
            time_range: 时间范围（1h/24h/7d）

        Returns:
            指标数据列表
        """
        # 解析时间范围
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            sql = """
                SELECT metric_value, timestamp
                FROM monitor_metrics
                WHERE metric_name = ?
                  AND timestamp > datetime('now', ?)
                ORDER BY timestamp DESC
            """
            params = (metric_name, f"-{hours} hours")
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            sql = """
                SELECT metric_value, timestamp
                FROM monitor_metrics
                WHERE metric_name = ?
                  AND timestamp > datetime('now', ?)
                ORDER BY timestamp DESC
            """
            params = (metric_name, f"-{days} days")
        else:
            # 默认 1 小时
            sql = """
                SELECT metric_value, timestamp
                FROM monitor_metrics
                WHERE metric_name = ?
                  AND timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC
            """
            params = (metric_name,)

        cursor = self.db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def check_alerts(self) -> List[Alert]:
        """
        检查告警

        Returns:
            告警列表
        """
        alerts = []

        # 检查系统资源
        system_status = self.get_system_status()

        # 磁盘使用率
        if (
            system_status["system"]["disk_percent"] / 100
            > self.alert_rules["disk_usage"]["threshold"]
        ):
            alert = Alert(
                id=f"disk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                level=AlertLevel.WARNING,
                metric="disk_usage",
                message=f"磁盘使用率过高：{system_status['system']['disk_percent']:.1f}%",
                threshold=self.alert_rules["disk_usage"]["threshold"] * 100,
                current_value=system_status["system"]["disk_percent"],
                timestamp=datetime.now(),
            )
            alerts.append(alert)

        # 内存使用率
        if (
            system_status["system"]["memory_percent"] / 100
            > self.alert_rules["memory_usage"]["threshold"]
        ):
            alert = Alert(
                id=f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                level=AlertLevel.WARNING,
                metric="memory_usage",
                message=f"内存使用率过高：{system_status['system']['memory_percent']:.1f}%",
                threshold=self.alert_rules["memory_usage"]["threshold"] * 100,
                current_value=system_status["system"]["memory_percent"],
                timestamp=datetime.now(),
            )
            alerts.append(alert)

        # 记录告警
        for alert in alerts:
            self._record_alert(alert)

        return alerts

    def _is_in_cooldown(self, alert: Alert, cooldown_minutes: int = 30) -> bool:
        key = f"{alert.metric}:{alert.level.value}"
        if key not in self._alert_cooldowns:
            return False
        elapsed = (datetime.now() - self._alert_cooldowns[key]).total_seconds()
        return elapsed < cooldown_minutes * 60

    def _update_cooldown(self, alert: Alert):
        key = f"{alert.metric}:{alert.level.value}"
        self._alert_cooldowns[key] = datetime.now()

    def _record_alert(self, alert: Alert):
        """记录告警"""
        self.db.execute(
            """
            INSERT OR IGNORE INTO alert_log
            (alert_id, level, metric, message, threshold, current_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                alert.id,
                alert.level.value,
                alert.metric,
                alert.message,
                alert.threshold,
                alert.current_value,
            ),
        )
        self.db.commit()

    def send_alert(self, alert: Alert, channel: str = "log"):
        """
        发送告警

        Args:
            alert: 告警对象
            channel: 通知渠道（log/email/webhook）
        """
        if self._is_in_cooldown(alert):
            return

        if channel == "log":
            print(f"[ALERT] {alert.level.value.upper()}: {alert.message}")

        elif channel == "email":
            self._send_email(alert)

        elif channel == "webhook":
            self._send_webhook(alert)

        self._update_cooldown(alert)

    def _send_email(self, alert: Alert):
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        host = self.config.get("EMAIL_HOST")
        port = self.config.get("EMAIL_PORT")
        user = self.config.get("EMAIL_USER")
        password = self.config.get("EMAIL_PASSWORD")
        recipients = self.config.get("EMAIL_RECIPIENTS")

        if not all([host, port, user, password, recipients]):
            raise ValueError(
                "Email config incomplete. Required: EMAIL_HOST, EMAIL_PORT, "
                "EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS"
            )

        assert host is not None
        assert port is not None
        assert user is not None
        assert password is not None
        assert recipients is not None

        subject = f"[Diting Alert] {alert.level.value.upper()}: {alert.metric}"
        body = (
            f"Alert: {alert.message}\n"
            f"Metric: {alert.metric}\n"
            f"Level: {alert.level.value.upper()}\n"
            f"Threshold: {alert.threshold}\n"
            f"Current Value: {alert.current_value}\n"
            f"Timestamp: {alert.timestamp.isoformat()}\n"
        )

        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = ", ".join(recipients) if isinstance(recipients, list) else str(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, int(port), context=context) as server:
                server.login(user, password)
                server.sendmail(user, recipients, msg.as_string())
        except Exception as e:
            raise RuntimeError(f"Failed to send email alert: {e}") from e

    def _send_webhook(self, alert: Alert):
        import requests

        url = self.config.get("WEBHOOK_URL")
        if not url:
            raise ValueError("Webhook config incomplete. Required: WEBHOOK_URL")

        payload = {
            "alert_id": alert.id,
            "level": alert.level.value,
            "metric": alert.metric,
            "message": alert.message,
            "threshold": alert.threshold,
            "current_value": alert.current_value,
            "timestamp": alert.timestamp.isoformat(),
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Failed to send webhook alert: {e}") from e

    def acknowledge_alert(self, alert_id: str):
        """
        确认告警

        Args:
            alert_id: 告警 ID
        """
        self.db.execute(
            """
            UPDATE alert_log
            SET acknowledged = 1
            WHERE alert_id = ?
        """,
            (alert_id,),
        )
        self.db.commit()

    def get_active_alerts(self) -> List[Dict]:
        """获取活跃告警"""
        cursor = self.db.execute("""
            SELECT * FROM alert_log
            WHERE acknowledged = 0
            ORDER BY timestamp DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def archive_old_metrics(self, keep_days: int = 7):
        """归档旧指标数据（移动到 archived_monitor_metrics 表，不删除）"""
        cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS archived_monitor_metrics AS
            SELECT * FROM monitor_metrics WHERE 0
        """)

        self.db.execute(
            "INSERT INTO archived_monitor_metrics SELECT * FROM monitor_metrics WHERE timestamp < ?",
            (cutoff,)
        )
        self.db.execute(
            "DELETE FROM monitor_metrics WHERE timestamp < ?",
            (cutoff,)
        )

        self.db.commit()

    def cleanup_old_metrics(self, keep_days: int = 7):
        """兼容旧接口，内部调用 archive_old_metrics"""
        return self.archive_old_metrics(keep_days)

    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 使用示例
if __name__ == "__main__":
    import os
    import tempfile

    # 创建测试数据库
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # 创建监控面板
    monitor = MonitorDashboard(db_path)

    print("✅ 监控面板初始化成功")

    # 获取系统状态
    status = monitor.get_system_status()
    print(f"系统状态：{status['status']}")
    print(f"  CPU: {status['system']['cpu_percent']:.1f}%")
    print(f"  内存：{status['system']['memory_percent']:.1f}%")
    print(f"  磁盘：{status['system']['disk_percent']:.1f}%")

    # 记录指标
    monitor.record_metric("test_metric", 50.0)

    # 检查告警
    alerts = monitor.check_alerts()
    print(f"活跃告警：{len(alerts)}个")

    # 清理
    monitor.close()
    os.close(db_fd)
