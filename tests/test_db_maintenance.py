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
