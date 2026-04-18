"""
SQLite 连接管理模块
"""

import sqlite3
from typing import Optional
from contextlib import contextmanager

from .config import Config


class Database:
    """SQLite 数据库连接管理器"""

    def __init__(self, config: Optional[Config] = None):
        """
        初始化数据库连接

        Args:
            config: 配置对象，默认为 None (使用默认配置)
        """
        self.config = config or Config()
        self.db_path = self.config.db_path
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        建立数据库连接

        Returns:
            sqlite3.Connection 对象
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # 启用 WAL 模式以提高并发性能
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self):
        """关闭数据库连接"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器

        Usage:
            with db.get_connection() as conn:
                conn.execute("SELECT ...")
        """
        conn = self.connect()
        try:
            yield conn
        finally:
            pass  # 不自动关闭连接，保持连接池

    def init_schema(self, schema_sql: str):
        """
        初始化数据库模式

        Args:
            schema_sql: SQL DDL 语句
        """
        # 分割 SQL 语句并逐个执行（避免 executescript 的问题）
        with self.get_connection() as conn:
            # 按分号分割语句
            statements = [stmt.strip()
                          for stmt in schema_sql.split(';') if stmt.strip()]
            for statement in statements:
                conn.execute(statement)
            conn.commit()

    def __repr__(self) -> str:
        return f"Database(db_path='{self.db_path}')"
