"""
Audit Logger 审计日志器测试用例

目标：覆盖率 70% → 90%+
"""

import pytest
import json
from diting.audit_logger import AuditLogger, LogLevel


class TestAuditLoggerInit:
    """初始化测试"""

    def test_init_default(self, tmp_path):
        """测试默认初始化"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        assert logger.log_retention_days == 30
        assert logger.db is not None

    def test_init_with_config(self, tmp_path):
        """测试自定义配置初始化"""
        db_path = str(tmp_path / "audit.db")
        config = {'LOG_RETENTION_DAYS': 60}
        logger = AuditLogger(db_path, config)
        
        assert logger.log_retention_days == 60


class TestAuditLoggerLog:
    """日志记录测试"""

    def test_log_basic(self, tmp_path):
        """测试基本日志记录"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(
            user_id="user123",
            action="CREATE",
            resource="document/doc1",
            details={"key": "value"},
            success=True
        )
        
        logs = logger.query(user_id="user123")
        assert len(logs) == 1
        assert logs[0]["action"] == "CREATE"
        assert logs[0]["user_id"] == "user123"

    def test_log_with_all_fields(self, tmp_path):
        """测试完整字段日志记录"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(
            user_id="user123",
            action="UPDATE",
            resource="document/doc1",
            details={"field": "value"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
            level="INFO"
        )
        
        logs = logger.query()
        assert len(logs) == 1
        assert logs[0]["ip_address"] == "192.168.1.1"

    def test_log_failure(self, tmp_path):
        """测试失败操作日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user123", action="DELETE", success=False)
        
        logs = logger.query(success=False)
        assert len(logs) == 1
        assert logs[0]["success"] == 0


class TestAuditLoggerSystemLog:
    """系统日志测试"""

    def test_log_system_basic(self, tmp_path):
        """测试基本系统日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log_system("COMPONENT", "Test message")
        
        logs = logger.query_system()
        assert len(logs) == 1
        assert logs[0]["component"] == "COMPONENT"
        assert logs[0]["message"] == "Test message"

    def test_log_system_with_stack_trace(self, tmp_path):
        """测试带堆栈追踪的系统日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        stack = "Traceback: line 1"
        logger.log_system("COMPONENT", "Error occurred", stack_trace=stack, level="ERROR")
        
        logs = logger.query_system()
        assert len(logs) == 1
        assert logs[0]["stack_trace"] == stack
        assert logs[0]["level"] == "ERROR"


class TestAuditLoggerQueries:
    """查询功能测试"""

    def test_query_by_user(self, tmp_path):
        """测试按用户查询"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        logger.log(user_id="user2", action="UPDATE")
        logger.log(user_id="user1", action="DELETE")
        
        user1_logs = logger.query(user_id="user1")
        assert len(user1_logs) == 2

    def test_query_by_action(self, tmp_path):
        """测试按操作查询"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        logger.log(user_id="user2", action="CREATE")
        logger.log(user_id="user1", action="UPDATE")
        
        create_logs = logger.query(action="CREATE")
        assert len(create_logs) == 2

    def test_query_by_time_range(self, tmp_path):
        """测试按时间范围查询"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        
        # 查询最近 24 小时
        logs = logger.query(time_range="24h")
        assert len(logs) == 1
        
        # 查询最近 1 小时
        logs_1h = logger.query(time_range="1h")
        assert len(logs_1h) >= 0

    def test_query_system_by_component(self, tmp_path):
        """测试按组件查询系统日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log_system("COMP1", "Message 1")
        logger.log_system("COMP2", "Message 2")
        logger.log_system("COMP1", "Message 3")
        
        comp1_logs = logger.query_system(component="COMP1")
        assert len(comp1_logs) == 2

    def test_query_system_by_level(self, tmp_path):
        """测试按级别查询系统日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log_system("COMP", "Info", level="INFO")
        logger.log_system("COMP", "Error", level="ERROR")
        
        error_logs = logger.query_system(level="ERROR")
        assert len(error_logs) == 1


class TestAuditLoggerExport:
    """导出功能测试"""

    def test_export_csv(self, tmp_path):
        """测试导出为 CSV"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        logger.log(user_id="user2", action="UPDATE")
        
        csv_bytes = logger.export(format='csv')
        csv_str = csv_bytes.decode('utf-8')
        
        assert "user_id" in csv_str
        assert "action" in csv_str
        assert "user1" in csv_str

    def test_export_json(self, tmp_path):
        """测试导出为 JSON"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        
        json_str = logger.export(format='json')
        data = json.loads(json_str)
        
        assert isinstance(data, list)
        assert len(data) >= 1


class TestAuditLoggerStatistics:
    """统计功能测试"""

    def test_get_statistics(self, tmp_path):
        """测试获取统计信息"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        # 创建一些日志
        logger.log(user_id="user1", action="CREATE", level="INFO")
        logger.log(user_id="user1", action="UPDATE", level="INFO")
        logger.log(user_id="user2", action="DELETE", level="ERROR", success=False)
        
        stats = logger.get_statistics(time_range="24h")
        
        assert stats["total"] == 3
        assert "by_level" in stats
        assert "by_user" in stats
        assert "by_action" in stats
        assert "success_rate" in stats
        assert "time_range" in stats

    def test_get_statistics_with_days(self, tmp_path):
        """测试按天统计"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        
        stats = logger.get_statistics(time_range="7d")
        
        assert stats["total"] == 1

    def test_get_statistics_default(self, tmp_path):
        """测试默认时间范围"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE")
        
        stats = logger.get_statistics()  # 默认 24h
        
        assert stats["total"] == 1
        assert stats["time_range"] == "24h"


class TestAuditLoggerCleanup:
    """清理功能测试"""

    def test_cleanup_old_logs(self, tmp_path):
        """测试清理旧日志"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})
        
        logger.log(user_id="user1", action="CREATE")
        
        # 清理（实际测试中不会真的删除，因为没有旧日志）
        logger.cleanup_old_logs()
        
        # 验证日志仍然存在（因为没有超过 7 天）
        logs = logger.query()
        assert len(logs) == 1

    def test_cleanup_short_retention(self, tmp_path):
        """测试短保留期清理"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 1})
        
        logger.log(user_id="user1", action="CREATE")
        logger.cleanup_old_logs()
        
        # 日志仍然存在（因为是刚刚创建的）
        logs = logger.query()
        assert len(logs) == 1

    def test_close(self, tmp_path):
        """测试关闭数据库"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.close()


class TestAuditLoggerEdgeCases:
    """边界条件测试"""

    def test_log_with_none_details(self, tmp_path):
        """测试 None 详情"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE", details=None)
        
        logs = logger.query()
        assert len(logs) == 1

    def test_log_with_empty_details(self, tmp_path):
        """测试空详情"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(user_id="user1", action="CREATE", details={})
        
        logs = logger.query()
        assert len(logs) == 1

    def test_log_with_complex_details(self, tmp_path):
        """测试复杂详情"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        details = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        logger.log(user_id="user1", action="CREATE", details=details)
        
        logs = logger.query()
        assert len(logs) == 1

    def test_log_with_unicode(self, tmp_path):
        """测试 Unicode 字符"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logger.log(
            user_id="用户 123",
            action="创建",
            resource="文档/测试",
            details={"内容": "中文测试"}
        )
        
        logs = logger.query()
        assert len(logs) == 1
        assert logs[0]["user_id"] == "用户 123"

    def test_query_empty_results(self, tmp_path):
        """测试查询空结果"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        logs = logger.query(user_id="nonexistent")
        assert logs == []

    def test_log_with_very_long_strings(self, tmp_path):
        """测试超长字符串"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path)
        
        long_string = "A" * 10000
        logger.log(user_id="user1", action="CREATE", details={"long": long_string})
        
        logs = logger.query()
        assert len(logs) == 1


class TestAuditLoggerArchive:
    """归档功能测试"""

    def test_archive_old_logs_creates_tables(self, tmp_path):
        """归档操作自动创建 archived_* 表"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.archive_old_logs()

        cursor = logger.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'archived_%'"
        )
        table_names = {row[0] for row in cursor.fetchall()}
        assert "archived_audit_log" in table_names
        assert "archived_system_log" in table_names

    def test_archive_old_logs_moves_audit_data(self, tmp_path):
        """归档审计日志：INSERT INTO archived 再 DELETE FROM 原表"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log(user_id="user1", action="OLD_ACTION")

        logger.db.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-30 days') WHERE action = 'OLD_ACTION'"
        )
        logger.db.commit()

        logger.log(user_id="user1", action="NEW_ACTION")

        logger.archive_old_logs()

        cursor = logger.db.execute("SELECT * FROM audit_log")
        remaining = [dict(row) for row in cursor.fetchall()]
        assert len(remaining) == 1
        assert remaining[0]["action"] == "NEW_ACTION"

        cursor = logger.db.execute("SELECT * FROM archived_audit_log")
        archived = [dict(row) for row in cursor.fetchall()]
        assert len(archived) == 1
        assert archived[0]["action"] == "OLD_ACTION"

    def test_archive_old_logs_moves_system_data(self, tmp_path):
        """归档系统日志：INSERT INTO archived 再 DELETE FROM 原表"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log_system("OLD_COMP", "old message")

        logger.db.execute(
            "UPDATE system_log SET timestamp = datetime('now', '-30 days') WHERE component = 'OLD_COMP'"
        )
        logger.db.commit()

        logger.log_system("NEW_COMP", "new message")

        logger.archive_old_logs()

        cursor = logger.db.execute("SELECT * FROM system_log")
        remaining = [dict(row) for row in cursor.fetchall()]
        assert len(remaining) == 1
        assert remaining[0]["component"] == "NEW_COMP"

        cursor = logger.db.execute("SELECT * FROM archived_system_log")
        archived = [dict(row) for row in cursor.fetchall()]
        assert len(archived) == 1
        assert archived[0]["component"] == "OLD_COMP"

    def test_archive_old_logs_no_old_data(self, tmp_path):
        """无旧数据时归档不报错"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log(user_id="user1", action="RECENT")
        logger.archive_old_logs()

        cursor = logger.db.execute("SELECT * FROM audit_log")
        assert len(cursor.fetchall()) == 1

        cursor = logger.db.execute("SELECT * FROM archived_audit_log")
        assert len(cursor.fetchall()) == 0

    def test_cleanup_old_logs_is_alias_for_archive(self, tmp_path):
        """cleanup_old_logs() 作为 archive_old_logs() 的兼容别名"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log(user_id="user1", action="OLD_ACTION")
        logger.db.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-30 days') WHERE action = 'OLD_ACTION'"
        )
        logger.db.commit()

        logger.cleanup_old_logs()

        cursor = logger.db.execute("SELECT * FROM archived_audit_log")
        archived = [dict(row) for row in cursor.fetchall()]
        assert len(archived) == 1
        assert archived[0]["action"] == "OLD_ACTION"
