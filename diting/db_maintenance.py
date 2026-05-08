"""
数据库维护工具

提供 VACUUM 压缩、过期数据归档、FTS 索引重建、数据库健康检查等功能。

核心原则：只归档不删除。归档后的数据保留在 archived_* 表，可随时查询。
如需释放磁盘空间，由用户通过 VACUUM 命令手动触发清理。
"""

import os
import sqlite3
from datetime import datetime, timedelta


class DatabaseMaintenance:
    """数据库维护工具"""

    def __init__(self, db_path: str):
        """
        初始化数据库维护工具

        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path

    def vacuum(self) -> dict:
        """
        执行 VACUUM 压缩数据库

        Returns:
            包含压缩前后大小和节省空间的字典
        """
        size_before = os.path.getsize(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()

        size_after = os.path.getsize(self.db_path)
        saved_mb = (size_before - size_after) / (1024 * 1024)

        return {
            "operation": "vacuum",
            "size_before_mb": size_before / (1024 * 1024),
            "size_after_mb": size_after / (1024 * 1024),
            "saved_mb": saved_mb,
            "saved_percent": (saved_mb / (size_before / (1024 * 1024))) * 100 if size_before > 0 else 0,
        }

    def analyze(self) -> dict:
        """
        分析数据库统计信息

        Returns:
            包含各表记录数、索引信息、总记录数和数据库大小的字典
        """
        conn = sqlite3.connect(self.db_path)
        try:
            tables = {}
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            for (table_name,) in cursor.fetchall():
                count = conn.execute(
                    f"SELECT COUNT(*) FROM [{table_name}]"
                ).fetchone()[0]
                tables[table_name] = count

            indexes = {}
            cursor = conn.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
            )
            for index_name, table_name in cursor.fetchall():
                if table_name not in indexes:
                    indexes[table_name] = []
                indexes[table_name].append(index_name)

            db_size = os.path.getsize(self.db_path)

            return {
                "tables": tables,
                "indexes": indexes,
                "total_records": sum(tables.values()),
                "db_size_mb": db_size / (1024 * 1024),
                "file_count": len(tables),
            }
        finally:
            conn.close()

    def archive_expired(self, retention_days: int = 90) -> dict:
        """
        归档过期数据（移动到 archived_* 表，不删除）

        先 INSERT INTO archived_* SELECT ... 再 DELETE FROM 原表。

        Args:
            retention_days: 保留天数，默认 90 天

        Returns:
            包含各表归档记录数的字典
        """
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            archive_targets = [
                ("audit_log", "timestamp"),
                ("temperature_log", "changed_at"),
                ("entropy_log", "changed_at"),
            ]

            results = {}

            for table_name, time_col in archive_targets:
                table_exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                ).fetchone()

                if table_exists is None:
                    results[f"{table_name}_archived"] = 0
                    continue

                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS [archived_{table_name}] AS "
                    f"SELECT * FROM [{table_name}] WHERE 0"
                )

                # Archive safety: INSERT INTO archived_* BEFORE DELETE FROM source
                cursor = conn.execute(
                    f"INSERT INTO [archived_{table_name}] "
                    f"SELECT * FROM [{table_name}] WHERE [{time_col}] < ?",
                    (cutoff,),
                )
                archived_count = cursor.rowcount

                conn.execute(
                    f"DELETE FROM [{table_name}] WHERE [{time_col}] < ?",
                    (cutoff,),
                )

                results[f"{table_name}_archived"] = archived_count

            conn.commit()

            return {
                "operation": "archive_expired",
                "retention_days": retention_days,
                **results,
                "total_archived": sum(results.values()),
            }
        finally:
            conn.close()

    def archive_orphaned(self) -> dict:
        """
        归档孤立数据（移动到 archived_* 表，不删除）

        检测逻辑：
        - temperature_log / entropy_log / heat_log 中 slice_id 不存在于 multimodal_slices 的记录
        - kg_aliases 中 concept_id 不存在于 kg_concepts 的记录

        Returns:
            包含各表归档记录数的字典
        """
        conn = sqlite3.connect(self.db_path)
        try:
            results = {}

            # (child_table, fk_col, parent_table, pk_col)
            orphan_targets = [
                ("temperature_log", "slice_id", "multimodal_slices", "slice_id"),
                ("entropy_log", "slice_id", "multimodal_slices", "slice_id"),
                ("heat_log", "slice_id", "multimodal_slices", "slice_id"),
                ("kg_aliases", "concept_id", "kg_concepts", "id"),
            ]

            for child_table, fk_col, parent_table, pk_col in orphan_targets:
                child_exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (child_table,),
                ).fetchone()

                if child_exists is None:
                    results[f"orphaned_{child_table}_archived"] = 0
                    continue

                parent_exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (parent_table,),
                ).fetchone()

                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS [archived_{child_table}] AS "
                    f"SELECT * FROM [{child_table}] WHERE 0"
                )

                if parent_exists is None:
                    cursor = conn.execute(
                        f"INSERT INTO [archived_{child_table}] SELECT * FROM [{child_table}]"
                    )
                    archived_count = cursor.rowcount
                    conn.execute(f"DELETE FROM [{child_table}]")
                else:
                    # Archive safety: INSERT INTO archived_* BEFORE DELETE FROM source
                    cursor = conn.execute(
                        f"INSERT INTO [archived_{child_table}] "
                        f"SELECT * FROM [{child_table}] "
                        f"WHERE [{fk_col}] NOT IN (SELECT [{pk_col}] FROM [{parent_table}])"
                    )
                    archived_count = cursor.rowcount

                    conn.execute(
                        f"DELETE FROM [{child_table}] "
                        f"WHERE [{fk_col}] NOT IN (SELECT [{pk_col}] FROM [{parent_table}])"
                    )

                results[f"orphaned_{child_table}_archived"] = archived_count

            conn.commit()

            return {
                "operation": "archive_orphaned",
                **results,
                "total_archived": sum(results.values()),
            }
        finally:
            conn.close()

    def rebuild_fts_index(self) -> dict:
        """
        重建 FTS5 全文检索索引

        Returns:
            包含重建的 FTS 表列表和数量的字典
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts%'"
            )
            fts_tables = [row[0] for row in cursor.fetchall()]

            rebuilt = []
            for table in fts_tables:
                conn.execute(f"INSERT INTO [{table}]([{table}]) VALUES('rebuild')")
                rebuilt.append(table)

            conn.commit()

            return {
                "operation": "rebuild_fts_index",
                "rebuilt_tables": rebuilt,
                "table_count": len(rebuilt),
            }
        finally:
            conn.close()

    def health_check(self) -> dict:
        """
        数据库健康检查

        检查项：
        - 完整性检查（PRAGMA integrity_check）
        - WAL 文件大小
        - 数据库文件大小
        - 表数量

        Returns:
            包含健康状态、问题列表和统计信息的字典
        """
        issues = []

        conn = sqlite3.connect(self.db_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                issues.append(f"Integrity check failed: {result[0]}")

            wal_path = self.db_path + "-wal"
            if os.path.exists(wal_path):
                wal_size = os.path.getsize(wal_path)
                if wal_size > 100 * 1024 * 1024:
                    issues.append(f"WAL file too large: {wal_size / (1024 * 1024):.1f}MB")

            db_size = os.path.getsize(self.db_path)
            if db_size > 1024 * 1024 * 1024:
                issues.append(f"Database too large: {db_size / (1024 * 1024 * 1024):.1f}GB")

            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            )
            table_count = cursor.fetchone()[0]

            return {
                "db_size_mb": db_size / (1024 * 1024),
                "table_count": table_count,
                "issues": issues,
                "healthy": len(issues) == 0,
            }
        finally:
            conn.close()
