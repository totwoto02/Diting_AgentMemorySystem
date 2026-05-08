"""Tests for diting.backup_manager - BackupManager class."""

import json
import os
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta

import pytest

from diting.backup_manager import BackupManager


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for the entire test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def db_path(tmp_dir):
    """Create a temporary SQLite database with some data."""
    db_path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO kv VALUES (?, ?)", ("hello", "world"))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def backup_dir(tmp_dir):
    """Return a backup directory path inside tmp_dir."""
    return os.path.join(tmp_dir, "backups")


@pytest.fixture
def manager(db_path, backup_dir):
    """Create a BackupManager instance."""
    return BackupManager({
        "db_path": db_path,
        "backup_dir": backup_dir,
        "max_backups": 5,
        "retention_days": 30,
    })


class TestCreateFullBackup:
    def test_creates_backup_directory_and_files(self, manager, backup_dir):
        metadata = manager.create_full_backup("test_full")

        assert metadata["name"] == "test_full"
        assert metadata["type"] == "full"
        assert "timestamp" in metadata
        assert "checksum" in metadata
        assert "db_size_mb" in metadata

        backup_path = os.path.join(backup_dir, "test_full")
        assert os.path.isdir(backup_path)
        assert os.path.isfile(os.path.join(backup_path, "diting.db"))
        assert os.path.isfile(os.path.join(backup_path, "metadata.json"))

    def test_auto_generates_name(self, manager):
        metadata = manager.create_full_backup()
        assert metadata["name"].startswith("full_")

    def test_backup_contains_correct_data(self, manager, backup_dir):
        metadata = manager.create_full_backup("data_check")
        backup_db = os.path.join(backup_dir, "data_check", "diting.db")

        conn = sqlite3.connect(backup_db)
        row = conn.execute("SELECT value FROM kv WHERE key='hello'").fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "world"

    def test_creates_wal_file_backup(self, manager, db_path, backup_dir):
        """WAL file is copied when it exists."""
        wal_path = db_path + "-wal"
        with open(wal_path, "wb") as f:
            f.write(b"fake wal data")

        metadata = manager.create_full_backup("wal_test")
        backup_wal = os.path.join(backup_dir, "wal_test", "diting.db-wal")
        assert os.path.isfile(backup_wal)

        os.unlink(wal_path)

    def test_skips_wal_when_absent(self, manager, backup_dir):
        metadata = manager.create_full_backup("no_wal")
        backup_wal = os.path.join(backup_dir, "no_wal", "diting.db-wal")
        assert not os.path.exists(backup_wal)


class TestCreateScheduledBackup:
    def test_creates_backup_via_sqlite_api(self, manager, backup_dir):
        metadata = manager.create_scheduled_backup("test_sched")

        assert metadata["name"] == "test_sched"
        assert metadata["type"] == "scheduled"
        assert "timestamp" in metadata
        assert "checksum" in metadata

        backup_path = os.path.join(backup_dir, "test_sched")
        assert os.path.isdir(backup_path)
        assert os.path.isfile(os.path.join(backup_path, "diting.db"))
        assert os.path.isfile(os.path.join(backup_path, "metadata.json"))

    def test_auto_generates_name(self, manager):
        metadata = manager.create_scheduled_backup()
        assert metadata["name"].startswith("scheduled_")

    def test_backup_contains_correct_data(self, manager, backup_dir):
        metadata = manager.create_scheduled_backup("sched_data")
        backup_db = os.path.join(backup_dir, "sched_data", "diting.db")

        conn = sqlite3.connect(backup_db)
        row = conn.execute("SELECT value FROM kv WHERE key='hello'").fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "world"


class TestVerifyBackup:
    def test_valid_backup_passes_verification(self, manager):
        manager.create_full_backup("verify_ok")
        assert manager.verify_backup("verify_ok") is True

    def test_corrupted_backup_fails_verification(self, manager, backup_dir):
        manager.create_full_backup("verify_corrupt")

        corrupt_path = os.path.join(backup_dir, "verify_corrupt", "extra_file.txt")
        with open(corrupt_path, "w") as f:
            f.write("corruption")

        assert manager.verify_backup("verify_corrupt") is False

    def test_missing_metadata_fails_verification(self, manager, backup_dir):
        os.makedirs(os.path.join(backup_dir, "no_meta"))
        assert manager.verify_backup("no_meta") is False

    def test_nonexistent_backup_fails_verification(self, manager):
        assert manager.verify_backup("does_not_exist") is False


class TestRestore:
    def test_restores_from_backup(self, manager, db_path, backup_dir):
        manager.create_full_backup("restore_src")

        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("goodbye", "world"))
        conn.commit()
        conn.close()

        result = manager.restore("restore_src")

        assert "restored_from" in result
        assert "pre_restore_backup" in result
        assert "timestamp" in result
        assert result["restored_from"] == "restore_src"

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT value FROM kv WHERE key='goodbye'").fetchone()
        conn.close()
        assert row is None

    def test_creates_pre_restore_backup(self, manager, db_path, backup_dir):
        manager.create_full_backup("restore_src2")
        result = manager.restore("restore_src2")

        pre_backup = os.path.join(backup_dir, result["pre_restore_backup"])
        assert os.path.isdir(pre_backup)
        assert os.path.isfile(os.path.join(pre_backup, "metadata.json"))

    def test_restore_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError, match="Backup not found"):
            manager.restore("nonexistent_backup")

    def test_restore_corrupted_backup_raises(self, manager, backup_dir):
        manager.create_full_backup("corrupt_restore")

        corrupt_file = os.path.join(backup_dir, "corrupt_restore", "bad.bin")
        with open(corrupt_file, "wb") as f:
            f.write(b"corrupted")

        with pytest.raises(ValueError, match="integrity check failed"):
            manager.restore("corrupt_restore")


class TestListBackups:
    def test_lists_backups_sorted_by_time(self, manager):
        manager.create_full_backup("list_a")
        manager.create_full_backup("list_b")

        backups = manager.list_backups()
        assert len(backups) >= 2
        names = [b["name"] for b in backups]
        assert "list_a" in names
        assert "list_b" in names

    def test_empty_backup_dir(self, tmp_dir):
        empty_dir = os.path.join(tmp_dir, "empty_backups")
        mgr = BackupManager({
            "db_path": os.path.join(tmp_dir, "dummy.db"),
            "backup_dir": empty_dir,
        })
        assert mgr.list_backups() == []

    def test_includes_scheduled_backups(self, manager):
        manager.create_full_backup("list_full")
        manager.create_scheduled_backup("list_sched")

        backups = manager.list_backups()
        names = [b["name"] for b in backups]
        assert "list_full" in names
        assert "list_sched" in names


class TestCleanupOldBackups:
    def test_archives_by_retention_days(self, manager, backup_dir):
        old_name = "old_backup"
        old_path = os.path.join(backup_dir, old_name)
        os.makedirs(old_path)

        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        metadata = {
            "name": old_name,
            "type": "full",
            "timestamp": old_time,
            "checksum": "fake",
        }
        with open(os.path.join(old_path, "metadata.json"), "w") as f:
            json.dump(metadata, f)

        manager.create_full_backup("new_backup")

        archive_path = os.path.join(backup_dir, "archive", old_name)
        assert os.path.isdir(archive_path)

        original_path = os.path.join(backup_dir, old_name)
        assert not os.path.exists(original_path)

    def test_archives_excess_backups(self, manager, backup_dir):
        for i in range(7):
            name = f"excess_{i}"
            path = os.path.join(backup_dir, name)
            os.makedirs(path)
            ts = (datetime.now() - timedelta(seconds=7 - i)).isoformat()
            meta = {"name": name, "type": "full", "timestamp": ts, "checksum": "x"}
            with open(os.path.join(path, "metadata.json"), "w") as f:
                json.dump(meta, f)

            dummy_db = os.path.join(path, "diting.db")
            with open(dummy_db, "wb") as f:
                f.write(b"fake")

        manager.create_full_backup("trigger_cleanup")

        backups = manager.list_backups()
        assert len(backups) <= 5

    def test_archive_directory_created(self, manager, backup_dir):
        manager.create_full_backup("archive_test")
        archive_dir = os.path.join(backup_dir, "archive")
        assert os.path.isdir(archive_dir)


class TestEndToEnd:
    def test_full_backup_restore_cycle(self, manager, db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("key1", "val1"))
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("key2", "val2"))
        conn.commit()
        conn.close()

        metadata = manager.create_full_backup("e2e_backup")
        assert metadata["type"] == "full"
        assert manager.verify_backup("e2e_backup") is True

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM kv")
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
        conn.close()
        assert count == 0

        result = manager.restore("e2e_backup")

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT key, value FROM kv ORDER BY key").fetchall()
        conn.close()
        assert ("hello", "world") in rows
        assert ("key1", "val1") in rows
        assert ("key2", "val2") in rows
        assert len(rows) == 3

    def test_scheduled_backup_restore_cycle(self, manager, db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("s1", "v1"))
        conn.commit()
        conn.close()

        metadata = manager.create_scheduled_backup("e2e_sched")
        assert metadata["type"] == "scheduled"

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM kv")
        conn.commit()
        conn.close()

        result = manager.restore("e2e_sched")

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT value FROM kv WHERE key='s1'").fetchone()
        conn.close()
        assert row[0] == "v1"


class TestBackupModuleImports:
    def test_import_full_backup(self):
        from diting.backup.full_backup import FullBackup
        assert FullBackup is not None

    def test_import_scheduled_backup(self):
        from diting.backup.incremental import ScheduledBackup
        assert ScheduledBackup is not None

    def test_import_integrity_checker(self):
        from diting.backup.integrity import IntegrityChecker
        assert IntegrityChecker is not None

    def test_import_restore_manager(self):
        from diting.backup.restore import RestoreManager
        assert RestoreManager is not None

    def test_import_package(self):
        from diting.backup import FullBackup, ScheduledBackup, IntegrityChecker, RestoreManager
        assert FullBackup is not None
        assert ScheduledBackup is not None
        assert IntegrityChecker is not None
        assert RestoreManager is not None
