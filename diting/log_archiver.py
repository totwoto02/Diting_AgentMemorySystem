import gzip
import logging
import os
import shutil
from datetime import datetime
from typing import Optional


class LogArchiver:
    def __init__(
        self,
        max_size_mb: float = 100,
        max_files: int = 10,
        archive_dir: str = "logs/archive",
        compress: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_files = max_files
        self.archive_dir = archive_dir
        self.compress = compress
        self.logger = logger or logging.getLogger(__name__)

    def rotate(self, log_dir: str) -> list:
        archived = []
        if not os.path.isdir(log_dir):
            self.logger.warning(f"Log directory does not exist: {log_dir}")
            return archived

        log_files = self._get_log_files(log_dir)
        if not log_files:
            return archived

        total_size = sum(f["size"] for f in log_files)

        if total_size <= self.max_size_bytes and len(log_files) <= self.max_files:
            return archived

        os.makedirs(self.archive_dir, exist_ok=True)

        while len(log_files) > self.max_files and log_files:
            oldest = log_files.pop(0)
            dest = self._archive_file(oldest["path"])
            if dest:
                archived.append(dest)

        if not archived:
            remaining_size = sum(f["size"] for f in log_files)
            if remaining_size > self.max_size_bytes and log_files:
                oldest = log_files.pop(0)
                dest = self._archive_file(oldest["path"])
                if dest:
                    archived.append(dest)

        return archived

    def _get_log_files(self, log_dir: str) -> list:
        files = []
        for name in os.listdir(log_dir):
            if not name.endswith(".log"):
                continue
            path = os.path.join(log_dir, name)
            if not os.path.isfile(path):
                continue
            stat = os.stat(path)
            files.append({
                "path": path,
                "name": name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            })
        files.sort(key=lambda f: f["mtime"])
        return files

    def _archive_file(self, src_path: str) -> Optional[str]:
        basename = os.path.basename(src_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{basename}"

        if self.compress:
            return self._compress_and_move(src_path, archive_name)
        else:
            return self._move_file(src_path, archive_name)

    def _compress_and_move(self, src_path: str, archive_name: str) -> Optional[str]:
        gz_name = f"{archive_name}.gz"
        dest_path = os.path.join(self.archive_dir, gz_name)

        try:
            with open(src_path, "rb") as f_in:
                with gzip.open(dest_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            self.logger.info(f"Archived (compressed): {src_path} -> {dest_path}")
            return dest_path
        except Exception as e:
            self.logger.error(f"Failed to compress {src_path}: {e}")
            return None

    def _move_file(self, src_path: str, archive_name: str) -> Optional[str]:
        dest_path = os.path.join(self.archive_dir, archive_name)

        try:
            shutil.copy2(src_path, dest_path)
            self.logger.info(f"Archived (moved): {src_path} -> {dest_path}")
            return dest_path
        except Exception as e:
            self.logger.error(f"Failed to archive {src_path}: {e}")
            return None

    def get_archive_info(self) -> dict:
        if not os.path.isdir(self.archive_dir):
            return {"total_files": 0, "total_size_bytes": 0, "files": []}

        files = []
        total_size = 0
        for name in os.listdir(self.archive_dir):
            path = os.path.join(self.archive_dir, name)
            if not os.path.isfile(path):
                continue
            size = os.path.getsize(path)
            total_size += size
            files.append({
                "name": name,
                "path": path,
                "size_bytes": size,
                "archived_at": datetime.fromtimestamp(
                    os.path.getmtime(path)
                ).isoformat(),
            })

        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "files": files,
        }
