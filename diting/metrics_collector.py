"""
系统指标收集器

收集系统资源指标和数据库指标，存储到 SQLite 并提供历史查询。
"""

import os
import sqlite3
from typing import Dict, List, Optional

import psutil


class MetricsCollector:
    """系统指标收集器"""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS monitor_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_time ON monitor_metrics(metric_name, timestamp)"
        )
        self.db.commit()

    def collect_system_metrics(self) -> Dict:
        """
        收集系统资源指标

        Returns:
            包含 cpu_percent, memory_percent, memory_used_mb,
            memory_total_mb, disk_percent, disk_used_gb, disk_total_gb 的字典
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / 1024 / 1024,
            "memory_total_mb": memory.total / 1024 / 1024,
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / 1024 / 1024 / 1024,
            "disk_total_gb": disk.total / 1024 / 1024 / 1024,
        }

    def collect_db_metrics(self, target_db_path: Optional[str] = None) -> Dict:
        """
        收集数据库指标

        Args:
            target_db_path: 目标数据库路径，为 None 时使用 self.db_path

        Returns:
            包含 db_size_mb, table_count, db_path 的字典
        """
        db_path = target_db_path or self.db_path

        db_size_mb = os.path.getsize(db_path) / 1024 / 1024

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            )
            table_count = cursor.fetchone()[0]
        finally:
            conn.close()

        return {
            "db_size_mb": db_size_mb,
            "table_count": table_count,
            "db_path": db_path,
        }

    def store_metrics(self, metrics: Dict, category: str = "system") -> None:
        """
        存储指标到数据库

        每个键值对存储为一行，metric_name 格式为 "{category}.{key}"

        Args:
            metrics: 指标字典
            category: 指标类别前缀
        """
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_name = f"{category}.{key}"
                self.db.execute(
                    """
                    INSERT INTO monitor_metrics (metric_name, metric_value)
                    VALUES (?, ?)
                    """,
                    (metric_name, float(value)),
                )
        self.db.commit()

    def get_metrics_history(
        self, metric_name: str, hours: int = 24
    ) -> List[Dict]:
        """
        查询指标历史数据

        Args:
            metric_name: 指标名称
            hours: 回溯小时数

        Returns:
            按时间倒序排列的 {metric_value, timestamp} 列表
        """
        cursor = self.db.execute(
            """
            SELECT metric_value, timestamp
            FROM monitor_metrics
            WHERE metric_name = ?
              AND timestamp > datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (metric_name, f"-{hours} hours"),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """关闭数据库连接"""
        self.db.close()
