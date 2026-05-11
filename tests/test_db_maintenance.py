"""Tests for diting.db_maintenance - DatabaseMaintenance class."""

import os
import sqlite3
import tempfile

import pytest

from diting.db_maintenance import DatabaseMaintenance


@pytest.fixture
def tmp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def maintenance(tmp_db):
    """创建 DatabaseMaintenance 实例"""
    return DatabaseMaintenance(tmp_db)


@pytest.fixture
def db_with_tables(tmp_db):
    """创建带表结构的临时数据库"""
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, timestamp TEXT, message TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS temperature_log (id INTEGER PRIMARY KEY, slice_id INTEGER, changed_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS entropy_log (id INTEGER PRIMARY KEY, slice_id INTEGER, changed_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS heat_log (id INTEGER PRIMARY KEY, slice_id INTEGER, changed_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS multimodal_slices (slice_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS kg_concepts (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS kg_aliases (id INTEGER PRIMARY KEY, concept_id INTEGER)")
    conn.commit()
    conn.close()
    return tmp_db


class TestVacuum:
    def test_vacuum_reduces_size(self, maintenance, tmp_db):
        conn = sqlite3.connect(tmp_db)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        for i in range(1000):
            conn.execute("INSERT INTO test (data) VALUES (?)", (f"row_{i}",))
        conn.commit()
        conn.execute("DELETE FROM test WHERE id <= 500")
        conn.commit()
        conn.close()

        # VACUUM outside transaction (in maintenance.vacuum)
        result = maintenance.vacuum()

        assert result["operation"] == "vacuum"
        assert result["size_before_mb"] >= 0
        assert result["size_after_mb"] >= 0
        assert isinstance(result["saved_mb"], float)


class TestAnalyze:
    def test_analyze_returns_stats(self, maintenance, db_with_tables):
        conn = sqlite3.connect(db_with_tables)
        conn.execute("INSERT INTO audit_log (timestamp, message) VALUES (?, ?)", ("2024-01-01", "test"))
        conn.execute("INSERT INTO temperature_log (slice_id, changed_at) VALUES (?, ?)", (1, "2024-01-01"))
        conn.commit()
        conn.close()

        result = maintenance.analyze()

        assert "tables" in result
        assert "indexes" in result
        assert "total_records" in result
        assert "db_size_mb" in result
        assert result["total_records"] >= 2

    def test_analyze_empty_db(self, maintenance, tmp_db):
        result = maintenance.analyze()
        assert result["total_records"] == 0
        assert result["file_count"] >= 0


class TestArchiveExpired:
    def test_archive_expired_old_records(self, maintenance, db_with_tables):
        from datetime import datetime, timedelta

        old_cutoff = (datetime.now() - timedelta(days=100)).isoformat()
        conn = sqlite3.connect(db_with_tables)
        conn.execute("INSERT INTO audit_log (timestamp, message) VALUES (?, ?)", (old_cutoff, "old"))
        conn.execute("INSERT INTO temperature_log (slice_id, changed_at) VALUES (?, ?)", (1, old_cutoff))
        conn.commit()
        conn.close()

        result = maintenance.archive_expired(retention_days=90)

        assert result["operation"] == "archive_expired"
        assert result["total_archived"] >= 2

        conn = sqlite3.connect(db_with_tables)
        remaining = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        assert remaining == 0

        archived = conn.execute("SELECT COUNT(*) FROM archived_audit_log").fetchone()[0]
        assert archived == 1
        conn.close()

    def test_archive_expired_keeps_new_records(self, maintenance, db_with_tables):
        from datetime import datetime

        new_time = datetime.now().isoformat()
        conn = sqlite3.connect(db_with_tables)
        conn.execute("INSERT INTO audit_log (timestamp, message) VALUES (?, ?)", (new_time, "new"))
        conn.commit()
        conn.close()

        result = maintenance.archive_expired(retention_days=90)

        assert result["total_archived"] == 0

        conn = sqlite3.connect(db_with_tables)
        remaining = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        assert remaining == 1
        conn.close()

    def test_archive_expired_missing_table(self, maintenance, tmp_db):
        result = maintenance.archive_expired(retention_days=90)
        assert result["audit_log_archived"] == 0


class TestArchiveOrphaned:
    def test_archive_orphaned_records(self, maintenance, db_with_tables):
        conn = sqlite3.connect(db_with_tables)
        conn.execute("INSERT INTO multimodal_slices (slice_id) VALUES (1)")
        conn.execute("INSERT INTO temperature_log (slice_id, changed_at) VALUES (?, ?)", (1, "2024-01-01"))
        conn.execute("INSERT INTO temperature_log (slice_id, changed_at) VALUES (?, ?)", (999, "2024-01-01"))
        conn.commit()
        conn.close()

        result = maintenance.archive_orphaned()

        assert result["operation"] == "archive_orphaned"
        assert result.get("orphaned_temperature_log_archived", 0) == 1

    def test_archive_orphaned_missing_child_table(self, maintenance, tmp_db):
        result = maintenance.archive_orphaned()
        assert result["orphaned_temperature_log_archived"] == 0


class TestRebuildFtsIndex:
    def test_rebuild_fts_index(self, maintenance, db_with_tables):
        result = maintenance.rebuild_fts_index()

        assert result["operation"] == "rebuild_fts_index"
        assert isinstance(result["rebuilt_tables"], list)


class TestHealthCheck:
    def test_health_check_healthy(self, maintenance, tmp_db):
        result = maintenance.health_check()

        assert "db_size_mb" in result
        assert "table_count" in result
        assert "issues" in result
        assert "healthy" in result
        assert isinstance(result["healthy"], bool)

    def test_health_check_large_db_flag(self, maintenance, tmp_db):
        result = maintenance.health_check()
        assert "db_size_mb" in result


class TestEdgeCases:
    def test_nonexistent_db_vacuum(self):
        maintenance = DatabaseMaintenance("/tmp/nonexistent_test_db_12345.db")
        result = maintenance.vacuum()
        assert result["operation"] == "vacuum"

    def test_nonexistent_db_analyze(self):
        maintenance = DatabaseMaintenance("/tmp/nonexistent_test_db_12345.db")
        result = maintenance.analyze()
        assert result["total_records"] == 0
    
    def test_nonexistent_db_health_check(self):
        maintenance = DatabaseMaintenance("/tmp/nonexistent_test_db_12345.db")
        result = maintenance.health_check()
        assert "healthy" in result


class TestPreviewArchivedCleanup:
    """T049: 预览归档数据清理测试"""

    def test_preview_archived_cleanup_empty_db(self, maintenance, tmp_db):
        """T049: 空数据库预览返回零"""
        result = maintenance.preview_archived_cleanup(retention_days=365)

        assert result["operation"] == "preview_archived_cleanup"
        assert result["retention_days"] == 365
        assert "cutoff_date" in result
        assert result["total_to_cleanup"] == 0

    def test_preview_archived_cleanup_with_old_data(self, maintenance, db_with_tables):
        """T049: 预览包含旧归档数据"""
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(days=400)).isoformat()

        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE archived_audit_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (old_time, "old message"))
        conn.commit()
        conn.close()

        result = maintenance.preview_archived_cleanup(retention_days=365)

        assert result["total_to_cleanup"] == 1
        assert result["tables"]["archived_audit_log"] == 1

    def test_preview_archived_cleanup_keeps_recent(self, maintenance, db_with_tables):
        """T049: 保留近期归档数据"""
        from datetime import datetime

        recent_time = datetime.now().isoformat()

        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE archived_audit_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (recent_time, "recent message"))
        conn.commit()
        conn.close()

        result = maintenance.preview_archived_cleanup(retention_days=365)

        assert result["total_to_cleanup"] == 0


class TestCleanupArchivedData:
    """T049: 归档数据清理测试"""

    def test_cleanup_archived_data_blocks_openclaw(self, maintenance, db_with_tables, monkeypatch):
        """T049: OpenClaw 环境阻止执行"""
        monkeypatch.setenv("OPENCLAW_AGENT", "1")

        with pytest.raises(RuntimeError) as exc_info:
            maintenance.cleanup_archived_data(retention_days=365)

        assert "OPENCLAW_AGENT" in str(exc_info.value)
        assert "blocked" in str(exc_info.value).lower()

    def test_cleanup_archived_data_dry_run(self, maintenance, db_with_tables):
        """T049: --dry-run 模式仅预览不删除"""
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(days=400)).isoformat()

        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE archived_audit_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (old_time, "old message"))
        conn.commit()
        conn.close()

        result = maintenance.cleanup_archived_data(retention_days=365, dry_run=True)

        assert result["dry_run"] is True
        assert result["total_to_cleanup"] == 1

        # 验证数据未被删除
        conn = sqlite3.connect(db_with_tables)
        count = conn.execute("SELECT COUNT(*) FROM archived_audit_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_cleanup_archived_data_deletes_old(self, maintenance, db_with_tables):
        """T049: 清理超过保留期的归档数据"""
        import os
        from datetime import datetime, timedelta

        # 确保不在 OpenClaw 环境
        if "OPENCLAW_AGENT" in os.environ:
            del os.environ["OPENCLAW_AGENT"]

        old_time = (datetime.now() - timedelta(days=400)).isoformat()
        recent_time = datetime.now().isoformat()

        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE archived_audit_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (old_time, "old message"))
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (recent_time, "recent message"))
        conn.commit()
        conn.close()

        result = maintenance.cleanup_archived_data(retention_days=365, dry_run=False)

        assert result["dry_run"] is False
        assert result["deleted"] == 1
        assert result["details"]["archived_audit_log"] == 1

        # 验证旧数据被删除，新数据保留
        conn = sqlite3.connect(db_with_tables)
        count = conn.execute("SELECT COUNT(*) FROM archived_audit_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_cleanup_archived_data_no_data(self, maintenance, db_with_tables):
        """T049: 无归档数据时返回空结果"""
        import os

        # 确保不在 OpenClaw 环境
        if "OPENCLAW_AGENT" in os.environ:
            del os.environ["OPENCLAW_AGENT"]

        result = maintenance.cleanup_archived_data(retention_days=365, dry_run=False)

        assert result["deleted"] == 0
        assert "No archived data to cleanup" in result["message"]


class TestGetTimeColumn:
    """T049: _get_time_column 辅助方法测试"""

    def test_get_time_column_timestamp(self, maintenance, db_with_tables):
        """T049: 识别 timestamp 列"""
        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.commit()

        time_col = maintenance._get_time_column(conn, "test_table")
        assert time_col == "timestamp"
        conn.close()

    def test_get_time_column_changed_at(self, maintenance, db_with_tables):
        """T049: 识别 changed_at 列"""
        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                changed_at TEXT,
                message TEXT
            )
        """)
        conn.commit()

        time_col = maintenance._get_time_column(conn, "test_table")
        assert time_col == "changed_at"
        conn.close()

    def test_get_time_column_created_at(self, maintenance, db_with_tables):
        """T049: 识别 created_at 列"""
        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                created_at TEXT,
                message TEXT
            )
        """)
        conn.commit()

        time_col = maintenance._get_time_column(conn, "test_table")
        assert time_col == "created_at"
        conn.close()

    def test_get_time_column_none(self, maintenance, db_with_tables):
        """T049: 无时序列返回 None"""
        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                message TEXT
            )
        """)
        conn.commit()

        time_col = maintenance._get_time_column(conn, "test_table")
        assert time_col is None
        conn.close()


class TestPreviewArchivedCleanupWithVariousTables:
    """T049: 预览多种归档表测试"""

    def test_preview_multiple_archived_tables(self, maintenance, db_with_tables):
        """T049: 预览多种归档表"""
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(days=400)).isoformat()

        conn = sqlite3.connect(db_with_tables)
        # 创建多个归档表
        conn.execute("""
            CREATE TABLE archived_audit_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE archived_system_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                message TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE archived_heat_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                changed_at TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_audit_log (timestamp, message) VALUES (?, ?)",
                     (old_time, "old"))
        conn.execute("INSERT INTO archived_system_log (timestamp, message) VALUES (?, ?)",
                     (old_time, "old"))
        conn.execute("INSERT INTO archived_heat_log (timestamp, changed_at, message) VALUES (?, ?, ?)",
                     (old_time, old_time, "old"))
        conn.commit()
        conn.close()

        result = maintenance.preview_archived_cleanup(retention_days=365)

        assert result["total_to_cleanup"] == 3
        assert result["tables"]["archived_audit_log"] == 1
        assert result["tables"]["archived_system_log"] == 1
        assert result["tables"]["archived_heat_log"] == 1


class TestCleanupArchivedDataWithDifferentTimeColumns:
    """T049: 测试不同时间列的归档数据清理"""

    def test_cleanup_with_changed_at_column(self, maintenance, db_with_tables):
        """T049: 使用 changed_at 列清理归档数据"""
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(days=400)).isoformat()

        conn = sqlite3.connect(db_with_tables)
        conn.execute("""
            CREATE TABLE archived_temperature_log (
                id INTEGER PRIMARY KEY,
                changed_at TEXT,
                message TEXT
            )
        """)
        conn.execute("INSERT INTO archived_temperature_log (changed_at, message) VALUES (?, ?)",
                     (old_time, "old temp"))
        conn.commit()
        conn.close()

        result = maintenance.preview_archived_cleanup(retention_days=365)
        assert result["tables"]["archived_temperature_log"] == 1
