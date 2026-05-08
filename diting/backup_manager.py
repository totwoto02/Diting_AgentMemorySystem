"""
备份管理器

统一管理全量备份、定期备份、恢复、完整性校验和备份列表。

核心原则：只归档不删除。旧备份移动到 backups/archive/ 目录，不删除任何文件。
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional

from .backup.full_backup import FullBackup
from .backup.incremental import ScheduledBackup
from .backup.integrity import IntegrityChecker
from .backup.restore import RestoreManager


class BackupManager:
    """备份管理器"""

    def __init__(self, config: dict):
        self.db_path = config["db_path"]
        self.backup_dir = config.get("backup_dir", "backups")
        self.max_backups = config.get("max_backups", 10)
        self.retention_days = config.get("retention_days", 30)

        os.makedirs(self.backup_dir, exist_ok=True)

        self._full_backup = FullBackup(self.db_path, self.backup_dir)
        self._scheduled_backup = ScheduledBackup(self.db_path, self.backup_dir)
        self._integrity_checker = IntegrityChecker()
        self._restore_manager = RestoreManager(self.db_path, self.backup_dir)

    def create_full_backup(self, name: Optional[str] = None) -> dict:
        """创建全量备份"""
        metadata = self._full_backup.execute(name)
        self._cleanup_old_backups()
        return metadata

    def create_scheduled_backup(self, name: Optional[str] = None) -> dict:
        """创建定期备份（SQLite backup API，每次都是完整数据库副本）"""
        metadata = self._scheduled_backup.execute(name)
        return metadata

    def restore(self, backup_name: str) -> dict:
        """从备份恢复"""
        backup_path = os.path.join(self.backup_dir, backup_name)

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        if not self.verify_backup(backup_name):
            raise ValueError("Backup integrity check failed")

        return self._restore_manager.restore(backup_path)

    def verify_backup(self, backup_name: str) -> bool:
        """验证备份完整性"""
        backup_path = os.path.join(self.backup_dir, backup_name)
        return self._integrity_checker.verify(backup_path)

    def list_backups(self) -> List[dict]:
        """列出所有备份"""
        if not os.path.isdir(self.backup_dir):
            return []

        backups = []
        for name in os.listdir(self.backup_dir):
            metadata_path = os.path.join(self.backup_dir, name, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path) as f:
                    backups.append(json.load(f))
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

    def _cleanup_old_backups(self):
        """归档旧备份（移动到 archive 目录，不删除）"""
        backups = self.list_backups()
        archive_dir = os.path.join(self.backup_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for backup in backups:
            backup_time = datetime.fromisoformat(backup["timestamp"])
            if backup_time < cutoff:
                backup_path = os.path.join(self.backup_dir, backup["name"])
                archive_path = os.path.join(archive_dir, backup["name"])
                if os.path.exists(backup_path):
                    shutil.move(backup_path, archive_path)

        backups = self.list_backups()
        if len(backups) > self.max_backups:
            for backup in backups[self.max_backups:]:
                backup_path = os.path.join(self.backup_dir, backup["name"])
                archive_path = os.path.join(archive_dir, backup["name"])
                if os.path.exists(backup_path):
                    shutil.move(backup_path, archive_path)
