"""
备份模块

提供全量备份、定期备份、完整性校验和恢复功能。

核心原则：只归档不删除。旧备份移动到 backups/archive/ 目录，不删除任何文件。
"""

from .full_backup import FullBackup
from .incremental import ScheduledBackup
from .integrity import IntegrityChecker
from .restore import RestoreManager

__all__ = ["FullBackup", "ScheduledBackup", "IntegrityChecker", "RestoreManager"]
