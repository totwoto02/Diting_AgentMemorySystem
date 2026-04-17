"""
MFS (Memory File System) - AI 记忆的 Git + NTFS

V1.0.0.0 - 正式版（C/C++/SQLite 全面优化）

核心优化:
- FTS5 BM25 温度计算
- SQLite 事务批量写入
- GLOB 路径匹配
- JSON 扩展
- 递归 CTE 图遍历
- 热力学四系统（U/T/S/G）
"""

__version__ = "1.0.0.0"
__version_info__ = (1, 0, 0, 0)
__release_date__ = "2026-04-16"
__author__ = "main (管家)"
__description__ = "AI 记忆的 Git + NTFS - 全面优化版"

from .mft import MFT
from .database import Database
from .config import Config

__all__ = ["MFT", "Database", "Config"]
