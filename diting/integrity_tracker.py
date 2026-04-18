"""
完整性追踪器 - 防幻觉机制

追踪所有修改，防止 AI 幻觉篡改记忆
"""

import hashlib
from datetime import datetime
from typing import Dict, Any, List
import sqlite3


class IntegrityTracker:
    """完整性追踪器"""

    def __init__(self, db_path: str):
        """
        初始化追踪器

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        """初始化追踪表"""
        # 修改历史表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS integrity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                v_path TEXT NOT NULL,
                action TEXT NOT NULL,
                old_content_hash TEXT,
                new_content_hash TEXT,
                old_content TEXT,
                new_content TEXT,
                reason TEXT,
                operator TEXT DEFAULT 'AI',
                timestamp REAL DEFAULT (strftime('%s', 'now'))
            )
        """)

        # 内容哈希表（用于快速验证）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS content_hashes (
                v_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                content_snapshot TEXT,
                last_verified REAL DEFAULT (strftime('%s', 'now'))
            )
        """)

        # 创建索引
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_path ON integrity_log(v_path)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_time ON integrity_log(timestamp)"
        )

        self.conn.commit()

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def track_update(self, v_path: str, old_content: str, new_content: str,
                     reason: str = "", operator: str = "AI") -> Dict[str, Any]:
        """
        追踪更新操作

        Args:
            v_path: 路径
            old_content: 旧内容
            new_content: 新内容
            reason: 修改原因
            operator: 操作者

        Returns:
            追踪记录
        """
        old_hash = self._compute_hash(old_content)
        new_hash = self._compute_hash(new_content)

        # 记录修改历史
        self.conn.execute("""
            INSERT INTO integrity_log
            (v_path, action, old_content_hash, new_content_hash,
             old_content, new_content, reason, operator)
            VALUES (?, 'UPDATE', ?, ?, ?, ?, ?, ?)
        """, (v_path, old_hash, new_hash, old_content[:1000],
              new_content[:1000], reason, operator))

        # 更新哈希表
        self.conn.execute("""
            INSERT OR REPLACE INTO content_hashes
            (v_path, content_hash, content_snapshot, last_verified)
            VALUES (?, ?, ?, strftime('%s', 'now'))
        """, (v_path, new_hash, new_content[:500]))

        self.conn.commit()

        # 计算变更统计
        diff_chars = sum(1 for a, b in zip(old_content, new_content) if a != b)
        diff_chars += abs(len(new_content) - len(old_content))

        return {
            "v_path": v_path,
            "action": "UPDATE",
            "old_hash": old_hash,
            "new_hash": new_hash,
            "diff_chars": diff_chars,
            "change_rate": f"{diff_chars/max(len(old_content),1)*100:.1f}%",
            "timestamp": datetime.now().isoformat()
        }

    def track_create(self, v_path: str, content: str,
                     operator: str = "AI") -> Dict[str, Any]:
        """
        追踪创建操作

        Args:
            v_path: 路径
            content: 内容
            operator: 操作者

        Returns:
            追踪记录
        """
        content_hash = self._compute_hash(content)

        # 记录创建历史
        self.conn.execute("""
            INSERT INTO integrity_log
            (v_path, action, new_content_hash, new_content, operator)
            VALUES (?, 'CREATE', ?, ?, ?)
        """, (v_path, content_hash, content[:1000], operator))

        # 更新哈希表
        self.conn.execute("""
            INSERT OR REPLACE INTO content_hashes
            (v_path, content_hash, content_snapshot, last_verified)
            VALUES (?, ?, ?, strftime('%s', 'now'))
        """, (v_path, content_hash, content[:500]))

        self.conn.commit()

        return {
            "v_path": v_path,
            "action": "CREATE",
            "content_hash": content_hash,
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        }

    def track_delete(self, v_path: str, old_content: str,
                     reason: str = "") -> Dict[str, Any]:
        """
        追踪删除操作

        Args:
            v_path: 路径
            old_content: 旧内容
            reason: 删除原因

        Returns:
            追踪记录
        """
        old_hash = self._compute_hash(old_content)

        self.conn.execute("""
            INSERT INTO integrity_log
            (v_path, action, old_content_hash, old_content, reason)
            VALUES (?, 'DELETE', ?, ?, ?)
        """, (v_path, old_hash, old_content[:1000], reason))

        # 从哈希表移除
        self.conn.execute(
            "DELETE FROM content_hashes WHERE v_path = ?",
            (v_path,)
        )

        self.conn.commit()

        return {
            "v_path": v_path,
            "action": "DELETE",
            "old_hash": old_hash,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

    def verify_integrity(
            self, v_path: str, current_content: str) -> Dict[str, Any]:
        """
        验证内容完整性

        Args:
            v_path: 路径
            current_content: 当前内容

        Returns:
            验证结果
        """
        # 获取存储的哈希
        cursor = self.conn.execute("""
            SELECT content_hash, content_snapshot, last_verified
            FROM content_hashes
            WHERE v_path = ?
        """, (v_path,))
        row = cursor.fetchone()

        if not row:
            return {
                "verified": False,
                "reason": "未找到哈希记录",
                "is_tampered": None
            }

        stored_hash = row[0]
        current_hash = self._compute_hash(current_content)

        is_tampered = stored_hash != current_hash

        return {
            "verified": True,
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "is_tampered": is_tampered,
            "last_verified": datetime.fromtimestamp(row[2]).isoformat(),
            "warning": "⚠️ 内容可能被篡改！" if is_tampered else "✅ 内容完整"
        }

    def get_history(self, v_path: str,
                    limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取修改历史

        Args:
            v_path: 路径
            limit: 返回记录数

        Returns:
            历史记录列表
        """
        cursor = self.conn.execute("""
            SELECT action, old_content_hash, new_content_hash,
                   reason, operator, timestamp
            FROM integrity_log
            WHERE v_path = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (v_path, limit))

        history = []
        for row in cursor.fetchall():
            history.append({
                "action": row[0],
                "old_hash": row[1],
                "new_hash": row[2],
                "reason": row[3],
                "operator": row[4],
                "timestamp": datetime.fromtimestamp(row[5]).isoformat()
            })

        return history

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM integrity_log"
        )
        total_logs = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM content_hashes"
        )
        tracked_files = cursor.fetchone()[0]

        cursor = self.conn.execute("""
            SELECT action, COUNT(*)
            FROM integrity_log
            GROUP BY action
        """)
        by_action = dict(cursor.fetchall())

        return {
            "total_logs": total_logs,
            "tracked_files": tracked_files,
            "by_action": by_action
        }

    def close(self):
        """关闭连接"""
        self.conn.close()
