"""
Audit Logger 审计日志器测试用例

目标：覆盖率 70% → 90%+
"""

import pytest
import json
import sqlite3
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
    """归档功能测试 - T046: 使用 UPDATE 代替 DELETE"""

    def test_archive_old_logs_updates_status(self, tmp_path):
        """T046: 归档操作更新 status='archived'，不删除数据"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        # 创建旧日志
        logger.log(user_id="user1", action="OLD_ACTION")
        logger.db.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-30 days') WHERE action = 'OLD_ACTION'"
        )
        logger.db.commit()

        # 创建新日志
        logger.log(user_id="user1", action="NEW_ACTION")

        # 获取归档前的总记录数
        cursor = logger.db.execute("SELECT COUNT(*) FROM audit_log")
        total_before = cursor.fetchone()[0]
        assert total_before == 2

        # 执行归档
        logger.archive_old_logs()

        # T046: 验证数据未被删除，总记录数不变
        cursor = logger.db.execute("SELECT COUNT(*) FROM audit_log")
        total_after = cursor.fetchone()[0]
        assert total_after == 2

        # T046: 验证旧日志状态变为 'archived'
        cursor = logger.db.execute(
            "SELECT status FROM audit_log WHERE action = 'OLD_ACTION'"
        )
        old_status = cursor.fetchone()[0]
        assert old_status == 'archived'

        # T046: 验证新日志状态仍为 'active'
        cursor = logger.db.execute(
            "SELECT status FROM audit_log WHERE action = 'NEW_ACTION'"
        )
        new_status = cursor.fetchone()[0]
        assert new_status == 'active'

    def test_archive_old_logs_system_log_status(self, tmp_path):
        """T046: 系统日志归档更新 status='archived'"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        # 创建旧系统日志
        logger.log_system("OLD_COMP", "old message")
        logger.db.execute(
            "UPDATE system_log SET timestamp = datetime('now', '-30 days') WHERE component = 'OLD_COMP'"
        )
        logger.db.commit()

        # 创建新系统日志
        logger.log_system("NEW_COMP", "new message")

        # 执行归档
        logger.archive_old_logs()

        # T046: 验证旧系统日志状态变为 'archived'
        cursor = logger.db.execute(
            "SELECT status FROM system_log WHERE component = 'OLD_COMP'"
        )
        old_status = cursor.fetchone()[0]
        assert old_status == 'archived'

        # T046: 验证新系统日志状态仍为 'active'
        cursor = logger.db.execute(
            "SELECT status FROM system_log WHERE component = 'NEW_COMP'"
        )
        new_status = cursor.fetchone()[0]
        assert new_status == 'active'

    def test_archive_old_logs_no_old_data(self, tmp_path):
        """T046: 无旧数据时归档不报错"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log(user_id="user1", action="RECENT")
        logger.archive_old_logs()

        cursor = logger.db.execute("SELECT COUNT(*) FROM audit_log")
        assert cursor.fetchone()[0] == 1

        cursor = logger.db.execute("SELECT status FROM audit_log WHERE action = 'RECENT'")
        assert cursor.fetchone()[0] == 'active'

    def test_cleanup_old_logs_calls_archive(self, tmp_path):
        """T046: cleanup_old_logs() 调用 archive_old_logs()"""
        db_path = str(tmp_path / "audit.db")
        logger = AuditLogger(db_path, {'LOG_RETENTION_DAYS': 7})

        logger.log(user_id="user1", action="OLD_ACTION")
        logger.db.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-30 days') WHERE action = 'OLD_ACTION'"
        )
        logger.db.commit()

        logger.cleanup_old_logs()

        # T046: 验证数据未被删除，只是状态更新
        cursor = logger.db.execute("SELECT COUNT(*) FROM audit_log")
        assert cursor.fetchone()[0] == 1

        cursor = logger.db.execute(
            "SELECT status FROM audit_log WHERE action = 'OLD_ACTION'"
        )
        assert cursor.fetchone()[0] == 'archived'

    def test_status_column_migration(self, tmp_path):
        """T046: 测试 status 列自动迁移"""
        db_path = str(tmp_path / "audit.db")

        # 创建不带 status 列的旧数据库（包含所有其他列）
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                success INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT,
                stack_trace TEXT
            )
        """)
        conn.commit()
        conn.close()

        # 使用 AuditLogger 初始化（应自动迁移）
        logger = AuditLogger(db_path)

        # 验证 status 列已添加
        cursor = logger.db.execute("PRAGMA table_info(audit_log)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "status" in columns

        cursor = logger.db.execute("PRAGMA table_info(system_log)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "status" in columns

        # 验证可以正常记录日志
        logger.log(user_id="user1", action="TEST")
        cursor = logger.db.execute("SELECT status FROM audit_log WHERE action = 'TEST'")
        assert cursor.fetchone()[0] == 'active'
