"""
批量处理优化

优化批量操作性能，降低 API 成本
"""

import collections
import json
import math
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from queue import PriorityQueue
from typing import Callable, Dict, List, Optional


@dataclass
class BatchTask:
    """批量任务"""

    id: str
    task_type: str
    priority: int
    data: Dict
    created_at: datetime
    callback: Optional[Callable] = None

    def __lt__(self, other):
        """支持优先级比较"""
        return self.priority > other.priority  # 优先级高的先处理


class BatchProcessor:
    """批量处理器"""

    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化批量处理器

        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}

        # 批量配置
        self.batch_size = self.config.get("BATCH_SIZE", 50)
        self.process_interval = self.config.get("PROCESS_INTERVAL", 300)  # 5 分钟

        # 任务队列
        self.task_queue = PriorityQueue()

        # 线程锁：保护所有 DB 操作
        self._db_lock = threading.Lock()

        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

        # 启动后台处理线程
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _init_schema(self):
        """初始化数据库表"""
        # 批量任务表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                data TEXT,
                result TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # 批量处理日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS batch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                task_count INTEGER,
                success_count INTEGER,
                failed_count INTEGER,
                duration_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON batch_tasks(status)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_priority ON batch_tasks(priority)")

        self.db.commit()

    def enqueue(
        self, task_id: str, task_type: str, data: Dict, priority: int = 0, callback: Callable = None
    ):
        """
        添加任务到队列

        Args:
            task_id: 任务 ID
            task_type: 任务类型
            data: 任务数据
            priority: 优先级（0-10，越高越优先）
            callback: 完成回调
        """
        task = BatchTask(
            id=task_id,
            task_type=task_type,
            priority=priority,
            data=data,
            created_at=datetime.now(),
            callback=callback,
        )

        with self._db_lock:
            self.db.execute(
                """
                INSERT OR REPLACE INTO batch_tasks
                (id, task_type, priority, data, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """,
                (task_id, task_type, priority, json.dumps(data), datetime.now().isoformat()),
            )
            self.db.commit()

        # 添加到队列
        self.task_queue.put((-priority, task))

    def dequeue_batch(self, batch_size: int = None) -> List[BatchTask]:
        """
        从队列获取一批任务

        Args:
            batch_size: 批量大小

        Returns:
            任务列表
        """
        batch_size = batch_size or self.batch_size
        tasks = []

        while len(tasks) < batch_size and not self.task_queue.empty():
            try:
                _, task = self.task_queue.get_nowait()
                tasks.append(task)

                with self._db_lock:
                    self.db.execute(
                        """
                        UPDATE batch_tasks
                        SET status = 'processing', started_at = ?
                        WHERE id = ?
                    """,
                        (datetime.now().isoformat(), task.id),
                    )

            except Exception:
                break

        with self._db_lock:
            self.db.commit()
        return tasks

    def complete_task(self, task_id: str, result: Dict = None, error: str = None):
        """
        完成任务

        Args:
            task_id: 任务 ID
            result: 处理结果
            error: 错误信息
        """
        with self._db_lock:
            self.db.execute(
                """
                UPDATE batch_tasks
                SET status = ?, result = ?, error_message = ?, completed_at = ?
                WHERE id = ?
            """,
                (
                    "completed" if not error else "failed",
                    json.dumps(result) if result else None,
                    error,
                    datetime.now().isoformat(),
                    task_id,
                ),
            )
            self.db.commit()

    def process_batch(self, tasks: List[BatchTask], processor: Callable) -> Dict:
        """
        处理批量任务

        Args:
            tasks: 任务列表
            processor: 处理函数

        Returns:
            处理统计
        """
        start_time = time.time()
        success_count = 0
        failed_count = 0

        for task in tasks:
            try:
                # 执行处理
                result = processor(task)
                self.complete_task(task.id, result)
                success_count += 1

                # 调用回调
                if task.callback:
                    task.callback(task.id, result)

            except Exception as e:
                self.complete_task(task.id, error=str(e))
                failed_count += 1

        duration = time.time() - start_time

        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with self._db_lock:
            self.db.execute(
                """
                INSERT INTO batch_log
                (batch_id, task_count, success_count, failed_count, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            """,
                (batch_id, len(tasks), success_count, failed_count, duration),
            )
            self.db.commit()

        return {
            "batch_id": batch_id,
            "total": len(tasks),
            "success": success_count,
            "failed": failed_count,
            "duration": duration,
        }

    def _worker_loop(self):
        """后台工作线程"""
        while self.running:
            try:
                # 获取一批任务
                tasks = self.dequeue_batch()

                if tasks:
                    # 处理任务（默认处理器）
                    self.process_batch(tasks, self._default_processor)
                else:
                    # 无任务，等待
                    time.sleep(self.process_interval)
            except Exception:
                # 捕获并发错误，避免线程崩溃
                time.sleep(0.1)

    def _default_processor(self, task: BatchTask) -> Dict:
        """默认处理器"""
        handlers = {
            "ai_summary": self._process_ai_summary,
            "entropy_calc": self._process_entropy_calc,
            "temp_calc": self._process_temp_calc,
            "file_cleanup": self._process_file_freeze,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return {"status": "unknown_task_type"}
        return self._retry_with_backoff(handler, task)

    def _retry_with_backoff(
        self, handler: Callable[[BatchTask], Dict], task: BatchTask, max_retries: int = 3
    ) -> Dict:
        backoff_seconds = [1, 2, 4]
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                return handler(task)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(backoff_seconds[attempt])
        if last_error is not None:
            raise last_error
        raise RuntimeError("retry_with_backoff: max_retries must be >= 1")

    def _process_ai_summary(self, task: BatchTask) -> Dict:
        content = task.data.get("content", "")
        if not content:
            return {"status": "no_content", "summary": ""}
        summary = content[:200] + "..." if len(content) > 200 else content
        return {"status": "processed", "summary": summary}

    def _process_entropy_calc(self, task: BatchTask) -> Dict:
        content = task.data.get("content", "")
        if not content:
            return {"status": "no_content", "entropy": 0.0}

        freq = collections.Counter(content)
        length = len(content)
        shannon_entropy = -sum(
            (count / length) * math.log2(count / length) for count in freq.values()
        )

        max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1.0
        normalized = shannon_entropy / max_entropy if max_entropy > 0 else 0.0
        normalized = max(0.0, min(1.0, normalized))

        return {"status": "processed", "entropy": round(normalized, 4)}

    def _process_temp_calc(self, task: BatchTask) -> Dict:
        access_count = task.data.get("access_count", 0)
        last_access_hours = task.data.get("last_access_hours", 0)
        round_count = task.data.get("round_count", 0)

        temperature = (
            (access_count / 1000)
            * math.exp(-last_access_hours / 168)
            * (1 / (1 + round_count))
        )
        temperature = max(0.0, min(1.0, temperature))

        return {"status": "processed", "temperature": round(temperature, 4)}

    def _process_file_freeze(self, task: BatchTask) -> Dict:
        file_status = task.data.get("status", "")
        if file_status != "archived":
            return {"status": "skipped", "reason": "not_archived"}

        file_id = task.data.get("file_id", "")
        with self._db_lock:
            self.db.execute(
                """
                UPDATE batch_tasks
                SET status = 'archived'
                WHERE id = ?
            """,
                (file_id,),
            )
            self.db.commit()

        return {"status": "frozen", "file_id": file_id}

    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        with self._db_lock:
            cursor = self.db.execute("""
                SELECT status, COUNT(*) as count
                FROM batch_tasks
                GROUP BY status
            """)

            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        return {
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
        }

    def get_batch_history(self, limit: int = 10) -> List[Dict]:
        """获取批量处理历史"""
        with self._db_lock:
            cursor = self.db.execute(
                """
                SELECT * FROM batch_log
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def stop(self):
        """停止处理器"""
        self.running = False
        self.worker_thread.join(timeout=5)

    def close(self):
        """关闭处理器"""
        self.stop()
        self.db.close()


# 使用示例
if __name__ == "__main__":
    import os
    import tempfile

    # 创建测试数据库
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # 创建批量处理器
    processor = BatchProcessor(db_path, {"BATCH_SIZE": 10})

    # 添加任务
    for i in range(5):
        processor.enqueue(f"task_{i}", "ai_summary", {"data": f"Test data {i}"}, priority=5)

    # 检查队列状态
    status = processor.get_queue_status()

    # 等待处理
    time.sleep(2)

    # 检查处理结果
    status = processor.get_queue_status()

    # 获取历史
    history = processor.get_batch_history()

    # 清理
    processor.close()
    os.close(db_fd)
