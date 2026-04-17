"""
缓存和连接池模块（性能优化）

提供 LRU 缓存和 SQLite 连接池管理
"""

import sqlite3
import threading
from typing import Any, Optional, Dict, List
from collections import OrderedDict
from contextlib import contextmanager
from queue import Queue, Empty


class LRUCache:
    """
    LRU 缓存实现
    
    用于缓存频繁访问的数据
    """

    def __init__(self, capacity: int = 100):
        """
        初始化 LRU 缓存

        Args:
            capacity: 缓存容量
        """
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            key: 缓存键

        Returns:
            缓存的值，不存在返回 None
        """
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """
        向缓存添加数据

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
                self.cache[key] = value

    def delete(self, key: str) -> None:
        """
        从缓存删除数据

        Args:
            key: 缓存键
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hits + self.misses
            return {
                "capacity": self.capacity,
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{(self.hits / total * 100) if total > 0 else 0:.2f}%"
            }


class ConnectionPool:
    """
    SQLite 连接池
    
    复用数据库连接，减少连接开销
    """

    def __init__(self, db_path: str, max_connections: int = 10):
        """
        初始化连接池

        Args:
            db_path: SQLite 数据库路径
            max_connections: 最大连接数
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.available: Queue = Queue(maxsize=max_connections)
        self.active: List[sqlite3.Connection] = []
        self.lock = threading.Lock()
        self.total_acquired = 0
        self.total_released = 0

        # 预创建连接
        for _ in range(max_connections):
            conn = self._create_connection()
            self.available.put(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def acquire(self, timeout: float = 5.0) -> Optional[sqlite3.Connection]:
        """
        获取连接

        Args:
            timeout: 超时时间（秒）

        Returns:
            数据库连接，超时返回 None
        """
        try:
            conn = self.available.get(timeout=timeout)
            with self.lock:
                self.active.append(conn)
                self.total_acquired += 1
            return conn
        except Empty:
            return None

    def release(self, conn: sqlite3.Connection) -> None:
        """
        释放连接回池

        Args:
            conn: 数据库连接
        """
        with self.lock:
            if conn in self.active:
                self.active.remove(conn)
                self.total_released += 1
        
        # 放回池
        try:
            self.available.put_nowait(conn)
        except Exception:
            # 池已满，关闭连接
            conn.close()

    @contextmanager
    def get_connection(self):
        """
        获取连接的上下文管理器
        
        Usage:
            with pool.get_connection() as conn:
                conn.execute("SELECT ...")
        """
        conn = self.acquire()
        if conn is None:
            raise RuntimeError("无法获取数据库连接（池已满或超时）")
        try:
            yield conn
        finally:
            self.release(conn)

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self.lock:
            return {
                "max_connections": self.max_connections,
                "active_connections": len(self.active),
                "available_connections": self.available.qsize(),
                "total_acquired": self.total_acquired,
                "total_released": self.total_released
            }

    def close(self) -> None:
        """关闭连接池"""
        # 关闭所有连接
        while not self.available.empty():
            conn = self.available.get()
            conn.close()
        
        with self.lock:
            self.active.clear()
