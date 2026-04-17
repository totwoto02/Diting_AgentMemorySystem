"""
WAL 日志模块（防幻觉盾牌）

记录所有修改操作，支持证据链、回滚、审计追踪
"""

import sqlite3
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class WALRecord:
    """WAL 记录数据结构"""
    id: int
    operation: str
    v_path: str
    content: str
    source_agent: str
    evidence: str
    confidence: float
    timestamp: float
    status: str


class WALLogger:
    """
    WAL 日志记录器
    
    防幻觉盾牌核心组件
    """

    def __init__(self, db_path: str):
        """
        初始化 WAL 日志

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        """初始化 WAL 表结构"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS wal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                v_path TEXT NOT NULL,
                content TEXT NOT NULL,
                source_agent TEXT NOT NULL,
                evidence TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                status TEXT DEFAULT 'COMMITTED',
                version INTEGER DEFAULT 1
            )
        """)
        
        # 索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_wal_path ON wal_log(v_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_wal_timestamp ON wal_log(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_wal_status ON wal_log(status)")
        
        self.conn.commit()

    @contextmanager
    def get_cursor(self):
        """获取游标上下文管理器"""
        cursor = self.conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def log_operation(
        self,
        operation: str,
        v_path: str,
        content: str,
        source_agent: str,
        evidence: str,
        confidence: float = 1.0
    ) -> int:
        """
        记录操作到 WAL 日志

        Args:
            operation: 操作类型（CREATE/UPDATE/DELETE/ARCHIVE）
            v_path: 虚拟路径
            content: 内容
            source_agent: 来源 Agent
            evidence: 证据（对话 ID 等）
            confidence: 置信度（0-1）

        Returns:
            record_id: 记录 ID
        """
        with self.get_cursor() as cursor:
            # 获取当前版本号
            cursor.execute("""
                SELECT COALESCE(MAX(version), 0) FROM wal_log WHERE v_path = ?
            """, (v_path,))
            current_version = cursor.fetchone()[0]
            new_version = current_version + 1
            
            # 插入 WAL 记录
            cursor.execute("""
                INSERT INTO wal_log 
                (operation, v_path, content, source_agent, evidence, confidence, timestamp, version, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMMITTED')
            """, (
                operation, v_path, content, source_agent, evidence,
                confidence, time.time(), new_version
            ))
            
            self.conn.commit()
            return cursor.lastrowid

    def get_history(self, v_path: str) -> List[Dict[str, Any]]:
        """
        获取指定路径的历史记录

        Args:
            v_path: 虚拟路径

        Returns:
            历史记录列表
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, operation, v_path, content, source_agent, evidence,
                       confidence, timestamp, status, version
                FROM wal_log
                WHERE v_path = ?
                ORDER BY version ASC
            """, (v_path,))
            
            return [
                {
                    "id": row[0],
                    "operation": row[1],
                    "v_path": row[2],
                    "content": row[3],
                    "source_agent": row[4],
                    "evidence": row[5],
                    "confidence": row[6],
                    "timestamp": row[7],
                    "status": row[8],
                    "version": row[9]
                }
                for row in cursor.fetchall()
            ]

    def rollback(self, record_id: int) -> bool:
        """
        回滚指定记录

        Args:
            record_id: 记录 ID

        Returns:
            True 如果回滚成功
        """
        with self.get_cursor() as cursor:
            # 标记为回滚
            cursor.execute("""
                UPDATE wal_log
                SET status = 'ROLLED_BACK'
                WHERE id = ?
            """, (record_id,))
            
            self.conn.commit()
            return cursor.rowcount > 0

    def get_version(self, v_path: str, version: int) -> Optional[Dict[str, Any]]:
        """
        获取指定版本

        Args:
            v_path: 虚拟路径
            version: 版本号

        Returns:
            版本信息，未找到返回 None
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, operation, v_path, content, source_agent, evidence,
                       confidence, timestamp, status, version
                FROM wal_log
                WHERE v_path = ? AND version = ?
            """, (v_path, version))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "operation": row[1],
                    "v_path": row[2],
                    "content": row[3],
                    "source_agent": row[4],
                    "evidence": row[5],
                    "confidence": row[6],
                    "timestamp": row[7],
                    "status": row[8],
                    "version": row[9]
                }
            return None

    def get_latest_version(self, v_path: str) -> Optional[Dict[str, Any]]:
        """
        获取最新版本

        Args:
            v_path: 虚拟路径

        Returns:
            最新版本信息，未找到返回 None
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, operation, v_path, content, source_agent, evidence,
                       confidence, timestamp, status, version
                FROM wal_log
                WHERE v_path = ?
                ORDER BY version DESC
                LIMIT 1
            """, (v_path,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "operation": row[1],
                    "v_path": row[2],
                    "content": row[3],
                    "source_agent": row[4],
                    "evidence": row[5],
                    "confidence": row[6],
                    "timestamp": row[7],
                    "status": row[8],
                    "version": row[9]
                }
            return None

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取审计追踪

        Args:
            limit: 返回记录数限制

        Returns:
            审计追踪列表
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, operation, v_path, content, source_agent, evidence,
                       confidence, timestamp, status, version
                FROM wal_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "id": row[0],
                    "operation": row[1],
                    "v_path": row[2],
                    "content": row[3],
                    "source_agent": row[4],
                    "evidence": row[5],
                    "confidence": row[6],
                    "timestamp": row[7],
                    "status": row[8],
                    "version": row[9]
                }
                for row in cursor.fetchall()
            ]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def log_batch(self, operations: List[Dict]) -> List[int]:
        """
        批量记录操作（使用事务，性能提升 5-10 倍）
        
        Args:
            operations: 操作列表，每项包含：
                - operation: 操作类型
                - v_path: 虚拟路径
                - content: 内容
                - source_agent: 来源 Agent
                - evidence: 证据（可选）
                - confidence: 置信度（可选，默认 1.0）
        
        Returns:
            记录 ID 列表
        """
        if not operations:
            return []
        
        # 使用事务批量写入
        self.conn.execute("BEGIN TRANSACTION")
        try:
            ids = []
            for op in operations:
                cursor = self.conn.execute("""
                    INSERT INTO wal_log 
                    (operation, v_path, content, source_agent, evidence, confidence, timestamp, version, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMMITTED')
                """, (
                    op['operation'],
                    op['v_path'],
                    op['content'],
                    op['source_agent'],
                    op.get('evidence', ''),
                    op.get('confidence', 1.0),
                    time.time(),
                    1  # 版本号（简化处理）
                ))
                ids.append(cursor.lastrowid)
            
            self.conn.commit()
            return ids
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    @contextmanager
    def batch_context(self):
        """
        批量写入上下文管理器
        
        Usage:
            with wal_logger.batch_context() as batch:
                batch.add('CREATE', '/path', 'content', 'agent')
                batch.add('UPDATE', '/path', 'new content', 'agent')
        """
        batch = BatchWriter(self)
        yield batch
        batch.commit()


class BatchWriter:
    """
    批量写入器（配合 batch_context 使用）
    """
    
    def __init__(self, wal_logger: WALLogger):
        self.wal_logger = wal_logger
        self.operations = []
    
    def add(self, operation: str, v_path: str, content: str,
            source_agent: str, evidence: str = "", confidence: float = 1.0):
        """
        添加一个操作到批量队列
        
        Args:
            operation: 操作类型
            v_path: 虚拟路径
            content: 内容
            source_agent: 来源 Agent
            evidence: 证据（可选）
            confidence: 置信度（可选）
        """
        self.operations.append({
            'operation': operation,
            'v_path': v_path,
            'content': content,
            'source_agent': source_agent,
            'evidence': evidence,
            'confidence': confidence
        })
    
    def commit(self) -> List[int]:
        """
        提交批量写入
        
        Returns:
            记录 ID 列表
        """
        return self.wal_logger.log_batch(self.operations)
