"""
备份管理器

提供 SQLite 数据库的全量备份、定期备份、恢复、完整性校验和归档清理功能。

核心原则：
- 不删除任何备份，只归档（移动到 archive 目录）
- MD5 校验确保备份完整性
- 恢复前自动创建 pre-restore 备份
- 归档时跳过 archive 目录本身
"""

import hashlib
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class BackupManager:
    """备份管理器"""

    def __init__(self, db_path: str, config: Optional[Dict] = None):
        """
        初始化备份管理器

        Args:
            db_path: SQLite 数据库文件路径
            config: 可选配置字典，支持 backup_dir
        """
        self.db_path = db_path
        config = config or {}
        self.backup_dir = config.get(
            "backup_dir", os.path.join(os.path.dirname(db_path), "backups")
        )
        self.archive_dir = os.path.join(self.archive_dir_path(), "archive")

    def _ensure_backup_dir(self) -> None:
        """确保备份目录存在"""
        os.makedirs(self.backup_dir, exist_ok=True)

    def archive_dir_path(self) -> str:
        """返回归档目录路径"""
        return self.backup_dir

    def _generate_backup_name(self, backup_type: str = "full") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        short_id = uuid.uuid4().hex[:8]
        return f"{backup_type}_backup_{timestamp}_{short_id}.db"

    def _calculate_md5(self, file_path: str) -> str:
        """计算文件的 MD5 校验和"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _save_checksum(self, backup_path: str, checksum: str) -> str:
        """保存 MD5 校验和文件"""
        checksum_path = backup_path + ".md5"
        with open(checksum_path, "w") as f:
            f.write(checksum)
        return checksum_path

    def _load_checksum(self, backup_path: str) -> Optional[str]:
        """加载 MD5 校验和"""
        checksum_path = backup_path + ".md5"
        if not os.path.exists(checksum_path):
            return None
        with open(checksum_path, "r") as f:
            return f.read().strip()

    def full_backup(self) -> Dict:
        """
        全量备份（使用 shutil.copy2）

        Returns:
            包含备份信息的字典
        """
        self._ensure_backup_dir()
        backup_name = self._generate_backup_name("full")
        backup_path = os.path.join(self.backup_dir, backup_name)

        shutil.copy2(self.db_path, backup_path)

        checksum = self._calculate_md5(backup_path)
        self._save_checksum(backup_path, checksum)

        return {
            "operation": "full_backup",
            "backup_name": backup_name,
            "backup_path": backup_path,
            "db_path": self.db_path,
            "checksum": checksum,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": os.path.getsize(backup_path),
        }

    def scheduled_backup(self) -> Dict:
        """
        定期备份（使用 SQLite backup API）

        Returns:
            包含备份信息的字典
        """
        self._ensure_backup_dir()
        backup_name = self._generate_backup_name("scheduled")
        backup_path = os.path.join(self.backup_dir, backup_name)

        source = sqlite3.connect(self.db_path)
        try:
            target = sqlite3.connect(backup_path)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()

        checksum = self._calculate_md5(backup_path)
        self._save_checksum(backup_path, checksum)

        return {
            "operation": "scheduled_backup",
            "backup_name": backup_name,
            "backup_path": backup_path,
            "db_path": self.db_path,
            "checksum": checksum,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": os.path.getsize(backup_path),
        }

    def restore(self, backup_name: str) -> Dict:
        backup_path = os.path.join(self.backup_dir, backup_name)

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        pre_restore_backup = self.full_backup()
        original_path = pre_restore_backup["backup_path"]
        pre_restore_name = "pre_restore_" + pre_restore_backup["backup_name"]
        renamed_path = os.path.join(self.backup_dir, pre_restore_name)

        shutil.move(original_path, renamed_path)
        md5_original = original_path + ".md5"
        if os.path.exists(md5_original):
            shutil.move(md5_original, renamed_path + ".md5")

        backup_conn = sqlite3.connect(backup_path)
        try:
            target_conn = sqlite3.connect(self.db_path)
            try:
                backup_conn.backup(target_conn)
            finally:
                target_conn.close()
        finally:
            backup_conn.close()

        return {
            "operation": "restore",
            "backup_name": backup_name,
            "backup_path": backup_path,
            "db_path": self.db_path,
            "pre_restore_backup": pre_restore_name,
            "timestamp": datetime.now().isoformat(),
        }

    def verify(self, backup_name: str) -> Dict:
        """
        MD5 校验备份完整性

        Args:
            backup_name: 备份文件名

        Returns:
            包含校验结果的字典
        """
        backup_path = os.path.join(self.backup_dir, backup_name)

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        stored_checksum = self._load_checksum(backup_path)
        actual_checksum = self._calculate_md5(backup_path)

        if stored_checksum is None:
            return {
                "operation": "verify",
                "backup_name": backup_name,
                "valid": False,
                "error": "No checksum file found",
                "actual_checksum": actual_checksum,
            }

        return {
            "operation": "verify",
            "backup_name": backup_name,
            "valid": stored_checksum == actual_checksum,
            "stored_checksum": stored_checksum,
            "actual_checksum": actual_checksum,
        }

    def cleanup(
        self, max_backups: int = 10, retention_days: int = 30
    ) -> Dict:
        """
        归档旧备份（移动到 archive 目录，不删除）

        Args:
            max_backups: 最大保留备份数量
            retention_days: 保留天数

        Returns:
            包含归档信息的字典
        """
        os.makedirs(self.archive_dir, exist_ok=True)

        backups = self.list_backups()
        archived = []

        cutoff = datetime.now() - timedelta(days=retention_days)

        for i, backup in enumerate(backups):
            should_archive = False

            if i >= max_backups:
                should_archive = True

            try:
                backup_time = datetime.fromisoformat(backup["timestamp"])
                if backup_time < cutoff:
                    should_archive = True
            except (ValueError, KeyError):
                pass

            if should_archive:
                src_path = backup["path"]
                if os.path.exists(src_path):
                    dest_path = os.path.join(
                        self.archive_dir, os.path.basename(src_path)
                    )
                    shutil.move(src_path, dest_path)
                    archived.append(os.path.basename(src_path))

                    md5_path = src_path + ".md5"
                    if os.path.exists(md5_path):
                        dest_md5 = dest_path + ".md5"
                        shutil.move(md5_path, dest_md5)

        return {
            "operation": "cleanup",
            "max_backups": max_backups,
            "retention_days": retention_days,
            "archived_count": len(archived),
            "archived_files": archived,
        }

    def list_backups(self) -> List[Dict]:
        """
        列出所有备份

        Returns:
            备份信息列表，按时间降序排列
        """
        if not os.path.isdir(self.backup_dir):
            return []

        backups = []
        for name in os.listdir(self.backup_dir):
            if not name.endswith(".db") or name.endswith(".md5"):
                continue

            path = os.path.join(self.backup_dir, name)
            if not os.path.isfile(path):
                continue

            stat = os.stat(path)
            backups.append({
                "name": name,
                "path": path,
                "size_bytes": stat.st_size,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        backups.sort(key=lambda b: b["timestamp"], reverse=True)
        return backups
