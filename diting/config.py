"""
配置管理模块
"""

from pathlib import Path
from typing import Optional


class Config:
    """MFS 配置类"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化配置

        Args:
            db_path: SQLite 数据库路径，默认为 ~/.mfs/memory.db
        """
        if db_path is None:
            home_dir = Path.home()
            mfs_dir = home_dir / ".mfs"
            mfs_dir.mkdir(exist_ok=True)
            self.db_path = str(mfs_dir / "memory.db")
        else:
            self.db_path = db_path

        # 确保数据库目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(exist_ok=True)

    def __repr__(self) -> str:
        return f"Config(db_path='{self.db_path}')"
