"""
恢复模块

从备份恢复数据库文件。
"""

import os
import shutil
from datetime import datetime


class RestoreManager:
    """备份恢复管理器"""

    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = db_path
        self.backup_dir = backup_dir

    def restore(self, backup_path: str) -> dict:
        """
        从备份恢复数据库

        恢复前会先创建当前数据库的备份（pre_restore_ 前缀）。

        Args:
            backup_path: 备份目录路径（必须包含 diting.db 和 metadata.json）

        Returns:
            恢复结果字典，包含 pre_restore_backup 名称

        Raises:
            FileNotFoundError: 备份不存在
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        from .full_backup import FullBackup

        pre_restore_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_backup = FullBackup(self.db_path, self.backup_dir)
        pre_restore_meta = current_backup.execute(pre_restore_name)

        db_source = os.path.join(backup_path, "diting.db")
        shutil.copy2(db_source, self.db_path)

        wal_source = os.path.join(backup_path, "diting.db-wal")
        if os.path.exists(wal_source):
            shutil.copy2(wal_source, self.db_path + "-wal")

        return {
            "restored_from": os.path.basename(backup_path),
            "pre_restore_backup": pre_restore_meta["name"],
            "timestamp": datetime.now().isoformat(),
        }
