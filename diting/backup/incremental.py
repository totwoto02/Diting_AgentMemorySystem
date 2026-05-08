"""
定期备份模块

使用 SQLite backup API 做全量数据库复制（非真正增量）。
保留此模块名以区别于 full_backup（shutil 方式）。
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from .integrity import IntegrityChecker


class ScheduledBackup:
    """定期备份执行器（SQLite backup API）"""

    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.integrity_checker = IntegrityChecker()

    def execute(self, name: Optional[str] = None) -> dict:
        """
        执行定期备份（SQLite backup API）

        Args:
            name: 备份名称，默认使用 scheduled_{timestamp} 格式

        Returns:
            备份元数据字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"scheduled_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)

        os.makedirs(backup_path, exist_ok=True)

        target_db = os.path.join(backup_path, "diting.db")
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(target_db) as target:
                source.backup(target)

        checksum = self.integrity_checker.calculate_checksum(backup_path)

        metadata = {
            "name": backup_name,
            "type": "scheduled",
            "timestamp": datetime.now().isoformat(),
            "checksum": checksum,
        }

        with open(os.path.join(backup_path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata
