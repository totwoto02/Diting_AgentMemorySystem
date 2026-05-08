import os
import gzip
import json
import logging

import pytest

from diting.log_archiver import LogArchiver


@pytest.fixture
def log_dir(tmp_path):
    d = tmp_path / "logs"
    d.mkdir()
    return str(d)


@pytest.fixture
def archive_dir(tmp_path):
    d = tmp_path / "archive"
    d.mkdir()
    return str(d)


def _write_log_file(path: str, size_bytes: int = 100):
    with open(path, "wb") as f:
        f.write(b"A" * size_bytes)
    return path


class TestLogArchiverInit:
    def test_default_config(self):
        archiver = LogArchiver()
        assert archiver.max_size_bytes == 100 * 1024 * 1024
        assert archiver.max_files == 10
        assert archiver.compress is True

    def test_custom_config(self):
        archiver = LogArchiver(max_size_mb=50, max_files=5, compress=False)
        assert archiver.max_size_bytes == 50 * 1024 * 1024
        assert archiver.max_files == 5
        assert archiver.compress is False


class TestLogArchiverRotate:
    def test_rotate_no_files(self, log_dir, archive_dir):
        archiver = LogArchiver(archive_dir=archive_dir)
        result = archiver.rotate(log_dir)
        assert result == []

    def test_rotate_under_limits(self, log_dir, archive_dir):
        archiver = LogArchiver(max_size_mb=10, max_files=10, archive_dir=archive_dir)
        _write_log_file(os.path.join(log_dir, "app.log"), 100)
        result = archiver.rotate(log_dir)
        assert result == []

    def test_rotate_excess_files_archives_oldest(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=2, archive_dir=archive_dir, compress=False)

        f1 = os.path.join(log_dir, "a.log")
        f2 = os.path.join(log_dir, "b.log")
        f3 = os.path.join(log_dir, "c.log")

        _write_log_file(f1, 50)
        os.utime(f1, (1000, 1000))
        _write_log_file(f2, 50)
        os.utime(f2, (2000, 2000))
        _write_log_file(f3, 50)
        os.utime(f3, (3000, 3000))

        result = archiver.rotate(log_dir)

        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]).endswith("_a.log")

        assert os.path.exists(f1)
        assert os.path.exists(f2)
        assert os.path.exists(f3)

    def test_rotate_compress_creates_gz(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=True)

        f1 = os.path.join(log_dir, "old.log")
        f2 = os.path.join(log_dir, "new.log")

        _write_log_file(f1, 200)
        os.utime(f1, (1000, 1000))
        _write_log_file(f2, 200)
        os.utime(f2, (2000, 2000))

        result = archiver.rotate(log_dir)

        assert len(result) == 1
        assert result[0].endswith(".gz")
        assert os.path.exists(result[0])

        with gzip.open(result[0], "rb") as f:
            content = f.read()
        assert content == b"A" * 200

    def test_rotate_size_exceeded_archives_oldest(self, log_dir, archive_dir):
        archiver = LogArchiver(
            max_size_mb=0.0001, max_files=100, archive_dir=archive_dir, compress=False
        )

        f1 = os.path.join(log_dir, "big.log")
        _write_log_file(f1, 200)
        os.utime(f1, (1000, 1000))

        result = archiver.rotate(log_dir)

        assert len(result) == 1
        assert os.path.exists(result[0])

    def test_rotate_nonexistent_dir(self, archive_dir):
        archiver = LogArchiver(archive_dir=archive_dir)
        result = archiver.rotate("/nonexistent/path")
        assert result == []

    def test_rotate_ignores_non_log_files(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=False)

        _write_log_file(os.path.join(log_dir, "data.txt"), 50)
        f1 = os.path.join(log_dir, "a.log")
        f2 = os.path.join(log_dir, "b.log")
        _write_log_file(f1, 50)
        os.utime(f1, (1000, 1000))
        _write_log_file(f2, 50)
        os.utime(f2, (2000, 2000))

        result = archiver.rotate(log_dir)
        assert len(result) == 1

    def test_rotate_preserves_original_file(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=True)

        f1 = os.path.join(log_dir, "orig.log")
        _write_log_file(f1, 100)
        os.utime(f1, (1000, 1000))
        f2 = os.path.join(log_dir, "new.log")
        _write_log_file(f2, 100)
        os.utime(f2, (2000, 2000))

        archiver.rotate(log_dir)

        assert os.path.exists(f1)
        assert os.path.getsize(f1) == 100


class TestLogArchiverArchiveInfo:
    def test_get_archive_info_empty(self, archive_dir):
        archiver = LogArchiver(archive_dir=archive_dir)
        info = archiver.get_archive_info()
        assert info["total_files"] == 0
        assert info["total_size_bytes"] == 0

    def test_get_archive_info_with_files(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=False)

        f1 = os.path.join(log_dir, "old.log")
        f2 = os.path.join(log_dir, "new.log")
        _write_log_file(f1, 100)
        os.utime(f1, (1000, 1000))
        _write_log_file(f2, 100)
        os.utime(f2, (2000, 2000))

        archiver.rotate(log_dir)

        info = archiver.get_archive_info()
        assert info["total_files"] == 1
        assert info["total_size_bytes"] > 0
        assert len(info["files"]) == 1
        assert "archived_at" in info["files"][0]

    def test_get_archive_info_nonexistent_dir(self):
        archiver = LogArchiver(archive_dir="/nonexistent")
        info = archiver.get_archive_info()
        assert info["total_files"] == 0


class TestLogArchiverEdgeCases:
    def test_rotate_empty_log_file(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=False)

        f1 = os.path.join(log_dir, "empty.log")
        open(f1, "w").close()
        os.utime(f1, (1000, 1000))

        f2 = os.path.join(log_dir, "new.log")
        _write_log_file(f2, 50)
        os.utime(f2, (2000, 2000))

        result = archiver.rotate(log_dir)
        assert len(result) == 1

    def test_rotate_multiple_archives(self, log_dir, archive_dir):
        archiver = LogArchiver(max_files=1, archive_dir=archive_dir, compress=False)

        files = []
        for i in range(4):
            f = os.path.join(log_dir, f"log{i}.log")
            _write_log_file(f, 50)
            os.utime(f, (1000 * (i + 1), 1000 * (i + 1)))
            files.append(f)

        result = archiver.rotate(log_dir)

        assert len(result) == 3
        for r in result:
            assert os.path.exists(r)
