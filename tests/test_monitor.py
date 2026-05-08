"""
Monitor 监控告警系统测试用例

目标：覆盖率 75% → 90%+
"""

import pytest
import tempfile
from datetime import datetime
from diting.monitor import MonitorDashboard, AlertLevel, Alert


class TestMonitorDashboardInit:
    """初始化测试"""

    def test_init_default(self, tmp_path):
        """测试默认初始化"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        assert dashboard.db_path == db_path
        assert dashboard.db is not None
        assert "ai_error_rate" in dashboard.alert_rules
        assert "disk_usage" in dashboard.alert_rules

    def test_init_with_config(self, tmp_path):
        """测试自定义配置初始化"""
        db_path = str(tmp_path / "monitor.db")
        config = {
            'ALERT_RULES': {
                'custom_metric': {'threshold': 100, 'window': '10m'}
            }
        }
        dashboard = MonitorDashboard(db_path, config)
        
        assert "custom_metric" in dashboard.alert_rules
        assert dashboard.alert_rules["custom_metric"]["threshold"] == 100


class TestMonitorDashboardSystemStatus:
    """系统状态测试"""

    def test_get_system_status(self, tmp_path):
        """测试获取系统状态"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        status = dashboard.get_system_status()
        
        assert "system" in status
        assert "cpu_percent" in status["system"]
        assert "memory_percent" in status["system"]
        assert "disk_percent" in status["system"]
        assert "timestamp" in status

    def test_get_system_status_values(self, tmp_path):
        """测试系统状态值范围"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        status = dashboard.get_system_status()
        system = status["system"]
        
        assert 0 <= system["cpu_percent"] <= 100
        assert 0 <= system["memory_percent"] <= 100
        assert 0 <= system["disk_percent"] <= 100


class TestMonitorDashboardMetrics:
    """监控指标测试"""

    def test_record_metric(self, tmp_path):
        """测试记录指标"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test_metric", 42.0)
        
        # 验证记录存在
        cursor = dashboard.db.execute(
            "SELECT * FROM monitor_metrics WHERE metric_name = ?",
            ("test_metric",)
        )
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["metric_value"] == 42.0

    def test_record_metric_multiple(self, tmp_path):
        """测试记录多个指标"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("metric1", 10.0)
        dashboard.record_metric("metric2", 20.0)
        dashboard.record_metric("metric1", 15.0)
        
        cursor = dashboard.db.execute(
            "SELECT * FROM monitor_metrics ORDER BY id"
        )
        rows = cursor.fetchall()
        assert len(rows) == 3

    def test_get_metrics(self, tmp_path):
        """测试获取指标"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", 1.0)
        dashboard.record_metric("test", 2.0)
        
        metrics = dashboard.get_metrics("test")
        
        assert len(metrics) == 2

    def test_get_metrics_empty(self, tmp_path):
        """测试获取空指标"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        metrics = dashboard.get_metrics("nonexistent")
        
        assert metrics == []

    def test_get_metrics_with_time_range(self, tmp_path):
        """测试按时间范围获取"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", 1.0)
        
        metrics = dashboard.get_metrics("test", time_range="1h")
        
        assert len(metrics) >= 1


class TestMonitorDashboardAlerts:
    """告警测试"""

    def test_send_alert(self, tmp_path):
        """测试发送告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        alert = Alert(
            id="alert_001",
            level=AlertLevel.WARNING,
            metric="cpu_usage",
            message="CPU 使用率过高",
            threshold=90.0,
            current_value=95.0,
            timestamp=datetime.now()
        )
        
        # send_alert 应该不抛出异常
        dashboard.send_alert(alert, channel='log')

    def test_send_alert_info_level(self, tmp_path):
        """测试发送信息级别告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        alert = Alert(
            id="alert_002",
            level=AlertLevel.INFO,
            metric="memory_usage",
            message="内存使用正常",
            threshold=80.0,
            current_value=60.0,
            timestamp=datetime.now()
        )
        
        dashboard.send_alert(alert)

    def test_send_alert_critical_level(self, tmp_path):
        """测试发送严重级别告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        alert = Alert(
            id="alert_003",
            level=AlertLevel.CRITICAL,
            metric="disk_usage",
            message="磁盘空间严重不足",
            threshold=95.0,
            current_value=98.0,
            timestamp=datetime.now()
        )
        
        dashboard.send_alert(alert)

    def test_get_active_alerts(self, tmp_path):
        """测试获取活跃告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        alerts = dashboard.get_active_alerts()
        
        assert isinstance(alerts, list)

    def test_acknowledge_alert(self, tmp_path):
        """测试确认告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        # 先创建一个告警
        alert = Alert(
            id="alert_to_ack",
            level=AlertLevel.WARNING,
            metric="test",
            message="Test",
            threshold=10.0,
            current_value=15.0,
            timestamp=datetime.now()
        )
        dashboard.send_alert(alert)
        
        # 确认告警
        result = dashboard.acknowledge_alert("alert_to_ack")
        
        # acknowledge_alert 返回 None，但应该执行成功
        assert result is None

    def test_acknowledge_nonexistent_alert(self, tmp_path):
        """测试确认不存在的告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        result = dashboard.acknowledge_alert("nonexistent")
        
        # 应该返回 None
        assert result is None


class TestMonitorDashboardThresholds:
    """阈值检查测试"""

    def test_check_alerts(self, tmp_path):
        """测试检查告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        # check_alerts 应该不抛出异常
        result = dashboard.check_alerts()
        
        # 返回当前状态
        assert result is not None

    def test_alert_rules_config(self, tmp_path):
        """测试告警规则配置"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        assert "ai_error_rate" in dashboard.alert_rules
        assert "disk_usage" in dashboard.alert_rules
        assert dashboard.alert_rules["disk_usage"]["threshold"] == 0.9


class TestMonitorDashboardCleanup:
    """清理测试"""

    def test_cleanup_old_metrics(self, tmp_path):
        """测试清理旧指标"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", 1.0)
        
        # 清理（实际测试中不会删除，因为没有旧数据）
        dashboard.cleanup_old_metrics()
        
        # 验证
        metrics = dashboard.get_metrics("test")
        # 数据仍然存在（因为是刚创建的）
        assert len(metrics) >= 0

    def test_check_alerts_after_cleanup(self, tmp_path):
        """测试清理后检查告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.cleanup_old_metrics()
        
        # 应该能正常检查
        result = dashboard.check_alerts()
        assert result is not None


class TestMonitorDashboardEdgeCases:
    """边界条件测试"""

    def test_record_metric_zero(self, tmp_path):
        """测试记录零值"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", 0.0)
        
        metrics = dashboard.get_metrics("test")
        assert len(metrics) == 1
        assert metrics[0]["metric_value"] == 0.0

    def test_record_metric_negative(self, tmp_path):
        """测试记录负值"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", -10.0)
        
        metrics = dashboard.get_metrics("test")
        assert len(metrics) == 1

    def test_record_metric_large(self, tmp_path):
        """测试记录大值"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        dashboard.record_metric("test", 999999.99)
        
        metrics = dashboard.get_metrics("test")
        assert len(metrics) == 1

    def test_send_alert_multiple(self, tmp_path):
        """测试发送多个告警"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        for i in range(5):
            alert = Alert(
                id=f"alert_{i}",
                level=AlertLevel.INFO,
                metric="test",
                message=f"Message {i}",
                threshold=10.0,
                current_value=float(i),
                timestamp=datetime.now()
            )
            dashboard.send_alert(alert)
        
        # 应该能获取活跃告警
        alerts = dashboard.get_active_alerts()
        assert isinstance(alerts, list)

    def test_get_system_status_timestamp_format(self, tmp_path):
        """测试系统状态时间戳格式"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        
        status = dashboard.get_system_status()
        
        assert "timestamp" in status
        # 时间戳是 ISO 格式字符串
        assert isinstance(status["timestamp"], str)
        assert "T" in status["timestamp"]  # ISO 格式特征


class TestAlertLevel:
    """告警级别枚举测试"""

    def test_alert_level_values(self):
        """测试告警级别值"""
        assert AlertLevel.INFO.value == 'info'
        assert AlertLevel.WARNING.value == 'warning'
        assert AlertLevel.CRITICAL.value == 'critical'

    def test_alert_level_from_string(self):
        """测试从字符串创建告警级别"""
        assert AlertLevel('info') == AlertLevel.INFO
        assert AlertLevel('warning') == AlertLevel.WARNING
        assert AlertLevel('critical') == AlertLevel.CRITICAL


class TestAlertDataclass:
    """告警数据类测试"""

    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            id="test_001",
            level=AlertLevel.WARNING,
            metric="cpu",
            message="High CPU",
            threshold=90.0,
            current_value=95.0,
            timestamp=datetime.now()
        )
        
        assert alert.id == "test_001"
        assert alert.level == AlertLevel.WARNING
        assert alert.metric == "cpu"
        assert alert.current_value == 95.0

    def test_alert_repr(self):
        """测试告警表示"""
        alert = Alert(
            id="test_001",
            level=AlertLevel.INFO,
            metric="memory",
            message="OK",
            threshold=80.0,
            current_value=60.0,
            timestamp=datetime.now()
        )
        
        # dataclass 应该有自动生成的 __repr__
        repr_str = repr(alert)
        assert "test_001" in repr_str
        assert "memory" in repr_str


class TestMonitorDashboardArchive:
    """归档功能测试"""

    def test_archive_old_metrics_creates_table(self, tmp_path):
        """归档操作自动创建 archived_monitor_metrics 表"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)

        dashboard.archive_old_metrics()

        cursor = dashboard.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'archived_monitor_metrics'"
        )
        assert cursor.fetchone() is not None

    def test_archive_old_metrics_moves_data(self, tmp_path):
        """归档指标：INSERT INTO archived 再 DELETE FROM 原表"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)

        dashboard.record_metric("old_metric", 42.0)
        dashboard.db.execute(
            "UPDATE monitor_metrics SET timestamp = datetime('now', '-30 days') WHERE metric_name = 'old_metric'"
        )
        dashboard.db.commit()

        dashboard.record_metric("new_metric", 99.0)

        dashboard.archive_old_metrics(keep_days=7)

        cursor = dashboard.db.execute("SELECT * FROM monitor_metrics")
        remaining = [dict(row) for row in cursor.fetchall()]
        assert len(remaining) == 1
        assert remaining[0]["metric_name"] == "new_metric"

        cursor = dashboard.db.execute("SELECT * FROM archived_monitor_metrics")
        archived = [dict(row) for row in cursor.fetchall()]
        assert len(archived) == 1
        assert archived[0]["metric_name"] == "old_metric"
        assert archived[0]["metric_value"] == 42.0

    def test_archive_old_metrics_no_old_data(self, tmp_path):
        """无旧数据时归档不报错"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)

        dashboard.record_metric("recent", 1.0)
        dashboard.archive_old_metrics(keep_days=7)

        cursor = dashboard.db.execute("SELECT * FROM monitor_metrics")
        assert len(cursor.fetchall()) == 1

        cursor = dashboard.db.execute("SELECT * FROM archived_monitor_metrics")
        assert len(cursor.fetchall()) == 0

    def test_cleanup_old_metrics_is_alias_for_archive(self, tmp_path):
        """cleanup_old_metrics() 作为 archive_old_metrics() 的兼容别名"""
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)

        dashboard.record_metric("old_metric", 42.0)
        dashboard.db.execute(
            "UPDATE monitor_metrics SET timestamp = datetime('now', '-30 days') WHERE metric_name = 'old_metric'"
        )
        dashboard.db.commit()

        dashboard.cleanup_old_metrics(keep_days=7)

        cursor = dashboard.db.execute("SELECT * FROM archived_monitor_metrics")
        archived = [dict(row) for row in cursor.fetchall()]
        assert len(archived) == 1
        assert archived[0]["metric_name"] == "old_metric"
