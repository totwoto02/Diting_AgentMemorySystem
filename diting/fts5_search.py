"""
FTS5 全文检索模块

提供高性能的全文搜索功能
"""

import sqlite3
from typing import List, Dict, Any, Optional


class FTS5Search:
    """FTS5 全文搜索引擎"""

    def __init__(self, db_path: str):
        """
        初始化 FTS5 搜索引擎

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        """初始化 FTS5 虚拟表"""
        # 创建 FTS5 虚拟表
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS mft_fts5 USING fts5(
                content,
                v_path,
                type,
                content='mft',
                content_rowid='inode'
            )
        """)

        # 创建触发器：自动同步 INSERT
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS mft_ai AFTER INSERT ON mft BEGIN
                INSERT INTO mft_fts5(rowid, content, v_path, type)
                VALUES (new.inode, new.content, new.v_path, new.type);
            END
        """)

        # 创建触发器：自动同步 DELETE
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS mft_ad AFTER DELETE ON mft BEGIN
                INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
                VALUES ('delete', old.inode, old.content, old.v_path, old.type);
            END
        """)

        # 创建触发器：自动同步 UPDATE
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS mft_au AFTER UPDATE ON mft BEGIN
                INSERT INTO mft_fts5(mft_fts5, rowid, content, v_path, type)
                VALUES ('delete', old.inode, old.content, old.v_path, old.type);
                INSERT INTO mft_fts5(rowid, content, v_path, type)
                VALUES (new.inode, new.content, new.v_path, new.type);
            END
        """)

        self.conn.commit()

    def search(self, query: str, scope: Optional[str] = None,
               top_k: int = 20) -> List[Dict[str, Any]]:
        """
        全文搜索

        Args:
            query: 搜索词
            scope: 路径前缀过滤（可选）
            top_k: 返回前 K 个结果

        Returns:
            搜索结果列表
        """
        # 构建查询
        if scope:
            sql = """
                SELECT m.inode, m.v_path, m.type, m.content,
                       m.create_ts, m.update_ts,
                       bm2d(mft_fts5) AS rank
                FROM mft_fts5 f
                JOIN mft m ON f.rowid = m.inode
                WHERE mft_fts5 MATCH ?
                  AND m.v_path LIKE ?
                  AND m.deleted = 0
                ORDER BY rank
                LIMIT ?
            """
            params = (query, f"{scope}%", top_k)
        else:
            sql = """
                SELECT m.inode, m.v_path, m.type, m.content,
                       m.create_ts, m.update_ts,
                       bm2d(mft_fts5) AS rank
                FROM mft_fts5 f
                JOIN mft m ON f.rowid = m.inode
                WHERE mft_fts5 MATCH ?
                  AND m.deleted = 0
                ORDER BY rank
                LIMIT ?
            """
            params = (query, top_k)

        try:
            cursor = self.conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    'inode': row[0],
                    'v_path': row[1],
                    'type': row[2],
                    'content': row[3],
                    'create_ts': row[4],
                    'update_ts': row[5],
                    'rank': row[6]
                })
        except sqlite3.OperationalError as e:
            if "bm2d" in str(e):
                # 回退到简单搜索（无 BM25 排序）
                if scope:
                    sql = """
                        SELECT inode, v_path, type, content, create_ts, update_ts
                        FROM mft
                        WHERE content LIKE ?
                          AND v_path LIKE ?
                          AND deleted = 0
                    """
                    params = (f"%{query}%", f"{scope}%")
                else:
                    sql = """
                        SELECT inode, v_path, type, content, create_ts, update_ts
                        FROM mft
                        WHERE content LIKE ?
                          AND deleted = 0
                    """
                    params = (f"%{query}%",)

                cursor = self.conn.execute(sql, params)
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'inode': row[0],
                        'v_path': row[1],
                        'type': row[2],
                        'content': row[3],
                        'create_ts': row[4],
                        'update_ts': row[5],
                        'rank': 0.0  # 无排序
                    })
            else:
                raise

        return results

    def search_highlight(self, query: str, content: str) -> str:
        """
        搜索并高亮匹配内容

        Args:
            query: 搜索词
            content: 原始内容

        Returns:
            带高亮标记的内容
        """
        # 使用 FTS5 snippet 函数
        sql = """
            SELECT snippet(mft_fts5, 0, '<mark>', '</mark>', '...', 10)
            FROM mft_fts5
            WHERE mft_fts5 MATCH ?
            LIMIT 1
        """
        cursor = self.conn.execute(sql, (query,))
        row = cursor.fetchone()
        return row[0] if row else content

    def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM mft_fts5"
        )
        total_docs = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM mft_fts5 WHERE content IS NOT NULL"
        )
        indexed_docs = cursor.fetchone()[0]

        return {
            'total_documents': total_docs,
            'indexed_documents': indexed_docs,
            'index_rate': f"{indexed_docs/total_docs*100:.1f}%" if total_docs > 0 else "0%"
        }

    def rebuild_index(self):
        """重建索引"""
        self.conn.execute("INSERT INTO mft_fts5(mft_fts5) VALUES('rebuild')")
        self.conn.commit()

    def insert(self, v_path: str, content: str, type: str = "NOTE") -> int:
        """
        插入文档到 FTS5 索引

        Args:
            v_path: 虚拟路径
            content: 内容
            type: 类型

        Returns:
            插入的文档 ID
        """
        # 先插入到 mft 表（触发器会自动同步到 FTS5）
        cursor = self.conn.execute("""
            INSERT INTO mft (v_path, type, content)
            VALUES (?, ?, ?)
        """, (v_path, type, content))
        self.conn.commit()
        return cursor.lastrowid

    def get_stats(self) -> Dict[str, Any]:
        """获取 FTS5 统计信息"""
        # 检查表是否存在
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='mft_fts5'
        """)
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            return {
                'table_exists': False,
                'doc_count': 0,
                'indexed_docs': 0
            }

        # 获取文档数量
        cursor = self.conn.execute("SELECT COUNT(*) FROM mft_fts5")
        doc_count = cursor.fetchone()[0]

        return {
            'table_exists': True,
            'doc_count': doc_count,
            'indexed_docs': doc_count
        }

    def delete(self, v_path: str) -> bool:
        """
        删除文档

        Args:
            v_path: 虚拟路径

        Returns:
            是否删除成功
        """
        # 从 mft 表删除（触发器会自动同步到 FTS5）
        cursor = self.conn.execute("""
            UPDATE mft SET deleted = 1 WHERE v_path = ?
        """, (v_path,))
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """关闭连接"""
        self.conn.close()
