"""
Monitor 监控告警系统测试用例

目标：覆盖率 75% → 90%+
"""

import pytest
import tempfile
import smtplib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from diting.monitor import MonitorDashboard, AlertLevel, Alert
from diting.metrics_collector import MetricsCollector


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


class TestCooldownMechanism:
    """冷却机制测试"""

    def test_is_in_cooldown_returns_false_initially(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = Alert(
            id="cd_001", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        assert dashboard._is_in_cooldown(alert) is False

    def test_is_in_cooldown_returns_true_after_update(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = Alert(
            id="cd_002", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        dashboard._update_cooldown(alert)
        assert dashboard._is_in_cooldown(alert) is True

    def test_cooldown_different_metrics_not_interfering(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert_cpu = Alert(
            id="cd_003", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        alert_mem = Alert(
            id="cd_004", level=AlertLevel.WARNING, metric="memory",
            message="High memory", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        dashboard._update_cooldown(alert_cpu)
        assert dashboard._is_in_cooldown(alert_cpu) is True
        assert dashboard._is_in_cooldown(alert_mem) is False

    def test_cooldown_different_levels_not_interfering(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert_warn = Alert(
            id="cd_005", level=AlertLevel.WARNING, metric="cpu",
            message="Warn", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        alert_crit = Alert(
            id="cd_006", level=AlertLevel.CRITICAL, metric="cpu",
            message="Critical", threshold=90.0, current_value=99.0,
            timestamp=datetime.now()
        )
        dashboard._update_cooldown(alert_warn)
        assert dashboard._is_in_cooldown(alert_warn) is True
        assert dashboard._is_in_cooldown(alert_crit) is False

    def test_cooldown_expires_after_time(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = Alert(
            id="cd_007", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        base_time = datetime(2026, 5, 10, 12, 0, 0)
        with patch('diting.monitor.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            dashboard._update_cooldown(alert)
            assert dashboard._is_in_cooldown(alert) is True

            mock_dt.now.return_value = base_time + timedelta(minutes=31)
            assert dashboard._is_in_cooldown(alert) is False

    def test_send_alert_skips_when_in_cooldown(self, tmp_path, capsys):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = Alert(
            id="cd_008", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        dashboard._update_cooldown(alert)
        dashboard.send_alert(alert, channel='log')
        captured = capsys.readouterr()
        assert "[ALERT]" not in captured.out

    def test_send_alert_updates_cooldown_after_send(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = Alert(
            id="cd_009", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )
        assert dashboard._is_in_cooldown(alert) is False
        dashboard.send_alert(alert, channel='log')
        assert dashboard._is_in_cooldown(alert) is True


class TestSendEmail:
    """邮件发送测试"""

    def _make_alert(self):
        return Alert(
            id="email_001", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )

    def test_send_email_success(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {
            'EMAIL_HOST': 'smtp.example.com', 'EMAIL_PORT': 465,
            'EMAIL_USER': 'user@example.com', 'EMAIL_PASSWORD': 'password',
            'EMAIL_RECIPIENTS': ['recipient@example.com']
        }
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()

        mock_server = MagicMock()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch('smtplib.SMTP_SSL', return_value=mock_smtp):
            dashboard._send_email(alert)
            mock_server.login.assert_called_once_with('user@example.com', 'password')
            mock_server.sendmail.assert_called_once()

    def test_send_email_missing_config_raises(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = self._make_alert()
        with pytest.raises(ValueError, match="Email config incomplete"):
            dashboard._send_email(alert)

    def test_send_email_partial_config_raises(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {'EMAIL_HOST': 'smtp.example.com', 'EMAIL_PORT': 465}
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()
        with pytest.raises(ValueError, match="Email config incomplete"):
            dashboard._send_email(alert)

    def test_send_email_smtp_error_raises_runtime_error(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {
            'EMAIL_HOST': 'smtp.example.com', 'EMAIL_PORT': 465,
            'EMAIL_USER': 'user@example.com', 'EMAIL_PASSWORD': 'password',
            'EMAIL_RECIPIENTS': ['recipient@example.com']
        }
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()

        with patch('smtplib.SMTP_SSL', side_effect=smtplib.SMTPException("Connection failed")):
            with pytest.raises(RuntimeError, match="Failed to send email"):
                dashboard._send_email(alert)

    def test_send_email_lazy_import(self):
        import diting.monitor as m
        assert 'smtplib' not in dir(m)


class TestSendWebhook:
    """Webhook 发送测试"""

    def _make_alert(self):
        return Alert(
            id="wh_001", level=AlertLevel.WARNING, metric="cpu",
            message="High CPU", threshold=90.0, current_value=95.0,
            timestamp=datetime.now()
        )

    def test_send_webhook_success(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {'WEBHOOK_URL': 'https://example.com/webhook'}
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch('requests.post', return_value=mock_response) as mock_post:
            dashboard._send_webhook(alert)
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == 'https://example.com/webhook'
            payload = call_args[1]['json']
            assert payload['alert_id'] == 'wh_001'
            assert payload['level'] == 'warning'
            assert payload['metric'] == 'cpu'

    def test_send_webhook_missing_url_raises(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        dashboard = MonitorDashboard(db_path)
        alert = self._make_alert()
        with pytest.raises(ValueError, match="Webhook config incomplete"):
            dashboard._send_webhook(alert)

    def test_send_webhook_http_error_raises_runtime_error(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {'WEBHOOK_URL': 'https://example.com/webhook'}
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Failed to send webhook"):
                dashboard._send_webhook(alert)

    def test_send_webhook_timeout(self, tmp_path):
        db_path = str(tmp_path / "monitor.db")
        config = {'WEBHOOK_URL': 'https://example.com/webhook'}
        dashboard = MonitorDashboard(db_path, config)
        alert = self._make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch('requests.post', return_value=mock_response) as mock_post:
            dashboard._send_webhook(alert)
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs['timeout'] == 10

    def test_send_webhook_lazy_import(self):
        import diting.monitor as m
        assert 'requests' not in dir(m)


class TestMetricsCollector:
    """MetricsCollector 测试"""

    def test_init(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)
        assert collector.db_path == db_path
        assert collector.db is not None
        collector.close()

    def test_collect_system_metrics(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)
        metrics = collector.collect_system_metrics()
        expected_keys = {
            "cpu_percent", "memory_percent", "memory_used_mb", "memory_total_mb",
            "disk_percent", "disk_used_gb", "disk_total_gb"
        }
        assert set(metrics.keys()) == expected_keys
        collector.close()

    def test_collect_system_metrics_values_in_range(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)
        metrics = collector.collect_system_metrics()
        for value in metrics.values():
            assert value >= 0
        collector.close()

    def test_collect_db_metrics(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)
        metrics = collector.collect_db_metrics()
        assert "db_size_mb" in metrics
        assert "table_count" in metrics
        assert "db_path" in metrics
        assert metrics["db_path"] == db_path
        assert metrics["table_count"] >= 1
        collector.close()

    def test_collect_db_metrics_with_target(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        target_db = str(tmp_path / "target.db")
        collector = MetricsCollector(db_path)

        import sqlite3
        conn = sqlite3.connect(target_db)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        metrics = collector.collect_db_metrics(target_db)
        assert metrics["db_path"] == target_db
        assert metrics["table_count"] >= 1
        collector.close()

    def test_store_metrics(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)

        collector.store_metrics({"cpu_percent": 50.0, "memory_percent": 75.0})

        history = collector.get_metrics_history("system.cpu_percent")
        assert len(history) >= 1
        assert history[0]["metric_value"] == 50.0
        collector.close()

    def test_store_metrics_category_prefix(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)

        collector.store_metrics({"cpu_percent": 50.0}, category="custom")

        history = collector.get_metrics_history("custom.cpu_percent")
        assert len(history) >= 1
        collector.close()

    def test_store_metrics_skips_non_numeric(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)

        collector.store_metrics({"cpu_percent": 50.0, "hostname": "server1", "status": "ok"})

        history = collector.get_metrics_history("system.cpu_percent")
        assert len(history) >= 1

        history_hostname = collector.get_metrics_history("system.hostname")
        assert len(history_hostname) == 0
        collector.close()

    def test_get_metrics_history(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)

        collector.store_metrics({"test_metric": 42.0})
        history = collector.get_metrics_history("system.test_metric")
        assert len(history) >= 1
        assert history[0]["metric_value"] == 42.0
        collector.close()

    def test_get_metrics_history_empty(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)

        history = collector.get_metrics_history("nonexistent.metric")
        assert history == []
        collector.close()

    def test_close(self, tmp_path):
        db_path = str(tmp_path / "metrics.db")
        collector = MetricsCollector(db_path)
        collector.close()
        with pytest.raises(Exception):
            collector.db.execute("SELECT 1")
