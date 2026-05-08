"""
全量备份模块

使用 shutil.copy2 直接复制数据库文件和 WAL 文件。
"""

import json
import os
import shutil
from datetime import datetime
from typing import Optional

from .integrity import IntegrityChecker


class FullBackup:
    """全量备份执行器"""

    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.integrity_checker = IntegrityChecker()

    def execute(self, name: Optional[str] = None) -> dict:
        """
        执行全量备份

        Args:
            name: 备份名称，默认使用 full_{timestamp} 格式

        Returns:
            备份元数据字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"full_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)

        os.makedirs(backup_path, exist_ok=True)

        shutil.copy2(self.db_path, os.path.join(backup_path, "diting.db"))

        wal_path = self.db_path + "-wal"
        if os.path.exists(wal_path):
            shutil.copy2(wal_path, os.path.join(backup_path, "diting.db-wal"))

        checksum = self.integrity_checker.calculate_checksum(backup_path)

        metadata = {
            "name": backup_name,
            "type": "full",
            "timestamp": datetime.now().isoformat(),
            "checksum": checksum,
            "db_size_mb": os.path.getsize(self.db_path) / (1024 * 1024),
        }

        with open(os.path.join(backup_path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata
