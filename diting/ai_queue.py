"""
异步 AI 调用队列

实现外卖平台模式：用户上传 → 立即返回 → 后台处理 → 完成通知
"""

import os
import json
import uuid
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    PENDING = 'pending'       # 队列中
    PROCESSING = 'processing' # 处理中
    DONE = 'done'            # 完成
    FAILED = 'failed'        # 失败
    RETRY = 'retry'          # 重试中


@dataclass
class AITask:
    """AI 任务"""
    task_id: str
    file_path: str
    file_type: str
    memory_path: str
    user_id: str
    status: TaskStatus
    priority: int = 0         # 优先级 0-10，越高越优先
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    result: Dict = None
    error_message: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AIQueueManager:
    """AI 队列管理器"""
    
    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化队列管理器
        
        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}
        
        # 队列配置
        self.max_concurrent = self.config.get('AI_MAX_CONCURRENT', 3)  # 最大并发数
        self.task_timeout = self.config.get('AI_TASK_TIMEOUT', 300)    # 任务超时（秒）
        self.poll_interval = self.config.get('AI_POLL_INTERVAL', 2)    # 轮询间隔（秒）
        
        # 回调函数
        self.on_task_complete: Optional[Callable] = None
        self.on_task_failed: Optional[Callable] = None
        
        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        
        # 工作线程
        self.workers = []
        self.running = False
        
        # 锁
        self.lock = threading.Lock()
    
    def _init_schema(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ai_tasks (
                task_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                memory_path TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                error_message TEXT
            )
        """)
        
        # 创建索引
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_status ON ai_tasks(status)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_priority ON ai_tasks(priority DESC)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_user ON ai_tasks(user_id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_created ON ai_tasks(created_at)")
        self.db.commit()
    
    def enqueue(self, file_path: str, file_type: str, memory_path: str,
                user_id: str = 'default', priority: int = 0) -> str:
        """
        添加任务到队列
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（image/audio）
            memory_path: 记忆路径
            user_id: 用户 ID
            priority: 优先级 0-10
        
        Returns:
            task_id: 任务 ID
        """
        task_id = str(uuid.uuid4())
        
        with self.lock:
            self.db.execute("""
                INSERT INTO ai_tasks (
                    task_id, file_path, file_type, memory_path, user_id,
                    status, priority, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, file_path, file_type, memory_path, user_id,
                TaskStatus.PENDING.value, priority, datetime.now().isoformat()
            ))
            self.db.commit()
        
        return task_id
    
    def dequeue(self) -> Optional[AITask]:
        """
        从队列获取下一个任务（优先级高的优先）
        
        Returns:
            任务对象，队列为空返回 None
        """
        with self.lock:
            cursor = self.db.execute("""
                SELECT * FROM ai_tasks
                WHERE status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """, (TaskStatus.PENDING.value,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            task_id = row['task_id']
            
            # 更新状态为处理中
            self.db.execute("""
                UPDATE ai_tasks
                SET status = ?, started_at = ?
                WHERE task_id = ?
            """, (TaskStatus.PROCESSING.value, datetime.now().isoformat(), task_id))
            self.db.commit()
            
            # 重新获取更新后的任务
            cursor = self.db.execute(
                "SELECT * FROM ai_tasks WHERE task_id = ?", (task_id,)
            )
            updated_row = cursor.fetchone()
            
            return self._row_to_task(updated_row)
    
    def complete_task(self, task_id: str, result: Dict):
        """
        标记任务完成
        
        Args:
            task_id: 任务 ID
            result: AI 处理结果
        """
        with self.lock:
            self.db.execute("""
                UPDATE ai_tasks
                SET status = ?, completed_at = ?, result = ?
                WHERE task_id = ?
            """, (
                TaskStatus.DONE.value, datetime.now().isoformat(),
                json.dumps(result), task_id
            ))
            self.db.commit()
            
            # 触发回调
            if self.on_task_complete:
                task = self.get_task(task_id)
                self.on_task_complete(task)
    
    def fail_task(self, task_id: str, error_message: str):
        """
        标记任务失败
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
        """
        with self.lock:
            # 检查重试次数
            task = self.get_task(task_id)
            
            if task.retry_count < task.max_retries:
                # 重试
                self.db.execute("""
                    UPDATE ai_tasks
                    SET status = ?, retry_count = retry_count + 1, error_message = ?
                    WHERE task_id = ?
                """, (TaskStatus.PENDING.value, error_message, task_id))
            else:
                # 超过最大重试次数，标记失败
                self.db.execute("""
                    UPDATE ai_tasks
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE task_id = ?
                """, (TaskStatus.FAILED.value, datetime.now().isoformat(), error_message, task_id))
                
                # 触发回调
                if self.on_task_failed:
                    self.on_task_failed(task)
            
            self.db.commit()
    
    def get_task(self, task_id: str) -> Optional[AITask]:
        """获取任务状态"""
        cursor = self.db.execute(
            "SELECT * FROM ai_tasks WHERE task_id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return self._row_to_task(row)
        return None
    
    def get_user_tasks(self, user_id: str, limit: int = 20) -> List[AITask]:
        """获取用户的任务列表"""
        cursor = self.db.execute("""
            SELECT * FROM ai_tasks
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        return [self._row_to_task(row) for row in cursor.fetchall()]
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        cursor = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM ai_tasks
            GROUP BY status
        """)
        
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        return {
            'pending': status_counts.get('pending', 0),
            'processing': status_counts.get('processing', 0),
            'done': status_counts.get('done', 0),
            'failed': status_counts.get('failed', 0),
            'retry': status_counts.get('retry', 0)
        }
    
    def cleanup_timeout_tasks(self):
        """清理超时任务"""
        timeout_threshold = datetime.now() - timedelta(seconds=self.task_timeout)
        
        with self.lock:
            self.db.execute("""
                UPDATE ai_tasks
                SET status = ?, error_message = ?
                WHERE status = ? AND started_at < ?
            """, (
                TaskStatus.PENDING.value,
                'Task timeout',
                TaskStatus.PROCESSING.value,
                timeout_threshold
            ))
            self.db.commit()
    
    def start_workers(self, worker_count: int = None):
        """启动工作线程"""
        if self.running:
            return
        
        self.running = True
        worker_count = worker_count or self.max_concurrent
        
        for i in range(worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"AIWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
    
    def stop_workers(self):
        """停止工作线程"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers.clear()
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.running:
            # 获取任务
            task = self.dequeue()
            
            if task:
                try:
                    # 处理任务（调用 AI）
                    result = self._process_task(task)
                    self.complete_task(task.task_id, result)
                except Exception as e:
                    self.fail_task(task.task_id, str(e))
            else:
                # 队列为空，等待
                time.sleep(self.poll_interval)
            
            # 定期清理超时任务
            self.cleanup_timeout_tasks()
    
    def _process_task(self, task: AITask) -> Dict:
        """
        处理任务（调用 AI）
        
        TODO: 集成实际 AI 调用
        目前返回模拟结果
        """
        # 模拟 AI 处理延迟
        time.sleep(2)
        
        # 模拟 AI 结果
        return {
            'summary': f'{task.file_type} 文件处理完成',
            'keywords': ['测试', 'AI'],
            'confidence': 0.8
        }
    
    def _row_to_task(self, row: sqlite3.Row) -> AITask:
        """数据库行转任务对象"""
        return AITask(
            task_id=row['task_id'],
            file_path=row['file_path'],
            file_type=row['file_type'],
            memory_path=row['memory_path'],
            user_id=row['user_id'],
            status=TaskStatus(row['status']),
            priority=row['priority'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            created_at=datetime.fromisoformat(row['created_at']),
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            result=json.loads(row['result']) if row['result'] else None,
            error_message=row['error_message']
        )
    
    def close(self):
        """关闭队列管理器"""
        self.stop_workers()
        self.db.close()


# 使用示例
if __name__ == '__main__':
    import tempfile
    
    # 创建队列
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    queue = AIQueueManager(db_path, {
        'AI_MAX_CONCURRENT': 2,
        'AI_TASK_TIMEOUT': 60
    })
    
    # 添加任务
    task1_id = queue.enqueue(
        file_path='/storage/image1.jpg',
        file_type='image',
        memory_path='/test/image1',
        user_id='user_001',
        priority=5
    )
    
    task2_id = queue.enqueue(
        file_path='/storage/audio1.ogg',
        file_type='audio',
        memory_path='/test/audio1',
        user_id='user_001',
        priority=8  # 高优先级
    )
    
    # 查看队列状态
    status = queue.get_queue_status()
    
    # 启动工作线程
    queue.start_workers()
    
    # 等待处理
    time.sleep(5)
    
    # 查看任务结果
    task1 = queue.get_task(task1_id)
    
    # 清理
    queue.close()
    os.close(db_fd)
