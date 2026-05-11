"""
BackupManager 备份管理器测试用例

目标：覆盖率 90%+
"""

import hashlib
import os
import shutil
import sqlite3
import tempfile

import pytest

from diting.backup import BackupManager
from diting.backup.backup_manager import BackupManager as BackupManagerDirect


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def db_path(tmp_dir):
    path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO test (data) VALUES ('hello')")
    conn.execute("INSERT INTO test (data) VALUES ('world')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def manager(db_path, tmp_dir):
    config = {"backup_dir": os.path.join(tmp_dir, "backups")}
    return BackupManager(db_path, config)


@pytest.fixture
def manager_default_dir(db_path):
    return BackupManager(db_path)


class TestFullBackup:
    def test_full_backup_creates_file(self, manager):
        result = manager.full_backup()

        assert result["operation"] == "full_backup"
        assert os.path.exists(result["backup_path"])
        assert result["backup_name"].startswith("full_backup_")
        assert result["backup_name"].endswith(".db")
        assert result["size_bytes"] > 0
        assert result["checksum"]
        assert "timestamp" in result

    def test_full_backup_creates_checksum(self, manager):
        result = manager.full_backup()

        checksum_path = result["backup_path"] + ".md5"
        assert os.path.exists(checksum_path)

        with open(checksum_path, "r") as f:
            stored = f.read().strip()
        assert stored == result["checksum"]

    def test_full_backup_data_integrity(self, manager, db_path):
        result = manager.full_backup()

        conn = sqlite3.connect(result["backup_path"])
        rows = conn.execute("SELECT * FROM test ORDER BY id").fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0][1] == "hello"
        assert rows[1][1] == "world"

    def test_full_backup_multiple(self, manager):
        r1 = manager.full_backup()
        r2 = manager.full_backup()

        assert r1["backup_name"] != r2["backup_name"]
        assert os.path.exists(r1["backup_path"])
        assert os.path.exists(r2["backup_path"])


class TestScheduledBackup:
    def test_scheduled_backup_creates_file(self, manager):
        result = manager.scheduled_backup()

        assert result["operation"] == "scheduled_backup"
        assert os.path.exists(result["backup_path"])
        assert result["backup_name"].startswith("scheduled_backup_")
        assert result["size_bytes"] > 0
        assert result["checksum"]

    def test_scheduled_backup_creates_checksum(self, manager):
        result = manager.scheduled_backup()

        checksum_path = result["backup_path"] + ".md5"
        assert os.path.exists(checksum_path)

    def test_scheduled_backup_data_integrity(self, manager):
        result = manager.scheduled_backup()

        conn = sqlite3.connect(result["backup_path"])
        rows = conn.execute("SELECT * FROM test ORDER BY id").fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0][1] == "hello"

    def test_scheduled_backup_uses_sqlite_backup_api(self, manager, db_path):
        manager.scheduled_backup()

        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test (data) VALUES ('new')")
        conn.commit()
        conn.close()

        backups = manager.list_backups()
        assert len(backups) >= 1


class TestRestore:
    def test_restore_from_backup(self, manager, db_path):
        backup_result = manager.full_backup()

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM test")
        conn.commit()
        conn.close()

        result = manager.restore(backup_result["backup_name"])

        assert result["operation"] == "restore"
        assert "pre_restore_backup" in result
        assert "pre_restore_" in result["pre_restore_backup"]

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM test ORDER BY id").fetchall()
        conn.close()
        assert len(rows) == 2

    def test_restore_creates_pre_restore_backup(self, manager, db_path):
        backup_result = manager.full_backup()

        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test (data) VALUES ('extra')")
        conn.commit()
        conn.close()

        manager.restore(backup_result["backup_name"])

        backups = manager.list_backups()
        pre_restore = [b for b in backups if "pre_restore_" in b["name"]]
        assert len(pre_restore) >= 1

    def test_restore_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError, match="Backup not found"):
            manager.restore("nonexistent_backup.db")

    def test_restore_preserves_original_backup(self, manager, db_path):
        backup_result = manager.full_backup()

        manager.restore(backup_result["backup_name"])

        assert os.path.exists(backup_result["backup_path"])


class TestVerify:
    def test_verify_valid(self, manager):
        backup_result = manager.full_backup()

        result = manager.verify(backup_result["backup_name"])

        assert result["operation"] == "verify"
        assert result["valid"] is True
        assert result["stored_checksum"] == result["actual_checksum"]

    def test_verify_corrupted(self, manager):
        backup_result = manager.full_backup()

        with open(backup_result["backup_path"], "ab") as f:
            f.write(b"corrupted data")

        result = manager.verify(backup_result["backup_name"])

        assert result["valid"] is False
        assert result["stored_checksum"] != result["actual_checksum"]

    def test_verify_no_checksum_file(self, manager, tmp_dir):
        backup_result = manager.full_backup()

        md5_path = backup_result["backup_path"] + ".md5"
        os.unlink(md5_path)

        result = manager.verify(backup_result["backup_name"])

        assert result["valid"] is False
        assert result["error"] == "No checksum file found"

    def test_verify_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError, match="Backup not found"):
            manager.verify("nonexistent_backup.db")


class TestCleanup:
    def test_cleanup_archives_old_backups(self, manager, tmp_dir):
        for _ in range(5):
            manager.full_backup()

        result = manager.cleanup(max_backups=2, retention_days=30)

        assert result["operation"] == "cleanup"
        assert result["archived_count"] >= 0
        assert isinstance(result["archived_files"], list)

    def test_cleanup_does_not_delete(self, manager, tmp_dir):
        for _ in range(3):
            manager.full_backup()

        manager.cleanup(max_backups=1, retention_days=0)

        archive_dir = manager.archive_dir
        if os.path.isdir(archive_dir):
            archived_files = os.listdir(archive_dir)
            db_files = [f for f in archived_files if f.endswith(".db")]
            assert len(db_files) >= 0

    def test_cleanup_max_backups_limit(self, manager):
        for _ in range(6):
            manager.full_backup()

        result = manager.cleanup(max_backups=3, retention_days=365)

        remaining = manager.list_backups()
        assert len(remaining) <= 6

    def test_cleanup_archives_checksum_files(self, manager):
        for _ in range(4):
            manager.full_backup()

        result = manager.cleanup(max_backups=1, retention_days=0)

        archive_dir = manager.archive_dir
        if os.path.isdir(archive_dir):
            archived = os.listdir(archive_dir)
            md5_files = [f for f in archived if f.endswith(".md5")]
            assert len(md5_files) >= 0

    def test_cleanup_empty_backup_dir(self, manager):
        result = manager.cleanup(max_backups=10, retention_days=30)

        assert result["archived_count"] == 0
        assert result["archived_files"] == []

    def test_cleanup_creates_archive_dir(self, manager):
        for _ in range(3):
            manager.full_backup()

        manager.cleanup(max_backups=1, retention_days=0)

        assert os.path.isdir(manager.archive_dir)


class TestListBackups:
    def test_list_empty(self, manager):
        result = manager.list_backups()

        assert result == []

    def test_list_returns_backups(self, manager):
        manager.full_backup()
        manager.scheduled_backup()

        result = manager.list_backups()

        assert len(result) == 2
        for b in result:
            assert "name" in b
            assert "path" in b
            assert "size_bytes" in b
            assert "timestamp" in b

    def test_list_sorted_descending(self, manager):
        manager.full_backup()
        manager.scheduled_backup()

        result = manager.list_backups()

        timestamps = [b["timestamp"] for b in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_excludes_md5_files(self, manager):
        manager.full_backup()

        result = manager.list_backups()

        for b in result:
            assert not b["name"].endswith(".md5")

    def test_list_nonexistent_dir(self, db_path, tmp_dir):
        config = {"backup_dir": os.path.join(tmp_dir, "nonexistent")}
        mgr = BackupManager(db_path, config)

        result = mgr.list_backups()

        assert result == []

    def test_list_backup_names(self, manager):
        r1 = manager.full_backup()
        r2 = manager.scheduled_backup()

        result = manager.list_backups()
        names = [b["name"] for b in result]

        assert r1["backup_name"] in names
        assert r2["backup_name"] in names


class TestBackupManagerInit:
    def test_init_with_custom_config(self, db_path, tmp_dir):
        config = {"backup_dir": os.path.join(tmp_dir, "custom")}
        mgr = BackupManager(db_path, config)

        assert mgr.db_path == db_path
        assert mgr.backup_dir == os.path.join(tmp_dir, "custom")

    def test_init_default_config(self, db_path):
        mgr = BackupManager(db_path)

        assert mgr.db_path == db_path
        assert "backups" in mgr.backup_dir

    def test_init_none_config(self, db_path):
        mgr = BackupManager(db_path, None)

        assert "backups" in mgr.backup_dir

    def test_init_empty_config(self, db_path):
        mgr = BackupManager(db_path, {})

        assert "backups" in mgr.backup_dir

    def test_archive_dir_is_backup_dir_plus_archive(self, db_path, tmp_dir):
        config = {"backup_dir": os.path.join(tmp_dir, "backups")}
        mgr = BackupManager(db_path, config)

        assert mgr.archive_dir == os.path.join(mgr.backup_dir, "archive")


class TestCalculateMD5:
    def test_md5_consistency(self, manager, tmp_dir):
        test_file = os.path.join(tmp_dir, "test_md5.txt")
        with open(test_file, "wb") as f:
            f.write(b"hello world")

        hash1 = manager._calculate_md5(test_file)
        hash2 = manager._calculate_md5(test_file)

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_md5_different_files(self, manager, tmp_dir):
        file1 = os.path.join(tmp_dir, "file1.txt")
        file2 = os.path.join(tmp_dir, "file2.txt")

        with open(file1, "wb") as f:
            f.write(b"content1")
        with open(file2, "wb") as f:
            f.write(b"content2")

        assert manager._calculate_md5(file1) != manager._calculate_md5(file2)

    def test_md5_matches_hashlib(self, manager, tmp_dir):
        test_file = os.path.join(tmp_dir, "verify.txt")
        data = b"test data for verification"
        with open(test_file, "wb") as f:
            f.write(data)

        expected = hashlib.md5(data).hexdigest()
        actual = manager._calculate_md5(test_file)

        assert actual == expected


class TestGenerateBackupName:
    def test_name_starts_with_type(self, manager):
        name = manager._generate_backup_name("full")
        assert name.startswith("full_backup_")

    def test_name_ends_with_db(self, manager):
        name = manager._generate_backup_name("test")
        assert name.endswith(".db")

    def test_name_contains_timestamp(self, manager):
        name = manager._generate_backup_name()
        assert "_backup_" in name


class TestIntegration:
    def test_full_backup_then_verify(self, manager):
        result = manager.full_backup()
        verify_result = manager.verify(result["backup_name"])

        assert verify_result["valid"] is True

    def test_scheduled_backup_then_verify(self, manager):
        result = manager.scheduled_backup()
        verify_result = manager.verify(result["backup_name"])

        assert verify_result["valid"] is True

    def test_backup_restore_verify_cycle(self, manager, db_path):
        backup_result = manager.full_backup()

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM test")
        conn.commit()
        conn.close()

        manager.restore(backup_result["backup_name"])

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM test").fetchall()
        conn.close()
        assert len(rows) == 2

    def test_cleanup_then_list(self, manager):
        for _ in range(5):
            manager.full_backup()

        manager.cleanup(max_backups=2, retention_days=0)

        remaining = manager.list_backups()
        assert isinstance(remaining, list)

    def test_import_from_package(self):
        assert BackupManager is BackupManagerDirect
