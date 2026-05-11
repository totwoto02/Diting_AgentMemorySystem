"""
备份恢复模块

提供 SQLite 数据库的全量备份、定期备份、恢复、完整性校验和归档清理功能。
"""

from .backup_manager import BackupManager

__all__ = ["BackupManager"]
