"""
日志审计系统

完整记录系统操作，支持审计和故障排查
"""

import sqlite3
import json
import csv
import io
from typing import Dict, List
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class AuditLogger:
    """审计日志器"""
    
    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化审计日志器
        
        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}
        
        # 日志保留天数
        self.log_retention_days = self.config.get('LOG_RETENTION_DAYS', 30)
        
        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库表"""
        # 审计日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                success INTEGER DEFAULT 1
            )
        """)
        
        # 系统日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT,
                stack_trace TEXT
            )
        """)
        
        # 创建索引
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_system_time ON system_log(timestamp)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_system_level ON system_log(level)")
        
        self.db.commit()
    
    def log(self, user_id: str, action: str, resource: str = None, 
            details: Dict = None, ip_address: str = None, 
            user_agent: str = None, success: bool = True,
            level: str = 'INFO'):
        """
        记录审计日志
        
        Args:
            user_id: 用户 ID
            action: 操作类型
            resource: 资源标识
            details: 详细信息
            ip_address: IP 地址
            user_agent: 用户代理
            success: 是否成功
            level: 日志级别
        """
        self.db.execute("""
            INSERT INTO audit_log 
            (level, user_id, action, resource, details, ip_address, user_agent, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            level, user_id, action, resource,
            json.dumps(details) if details else None,
            ip_address, user_agent, 1 if success else 0
        ))
        self.db.commit()
    
    def log_system(self, component: str, message: str, 
                   level: str = 'INFO', stack_trace: str = None):
        """
        记录系统日志
        
        Args:
            component: 组件名称
            message: 日志消息
            level: 日志级别
            stack_trace: 堆栈跟踪
        """
        self.db.execute("""
            INSERT INTO system_log (level, component, message, stack_trace)
            VALUES (?, ?, ?, ?)
        """, (level, component, message, stack_trace))
        self.db.commit()
    
    def query(self, user_id: str = None, action: str = None, 
              time_range: str = '24h', level: str = None,
              success: bool = None) -> List[Dict]:
        """
        查询审计日志
        
        Args:
            user_id: 用户 ID
            action: 操作类型
            time_range: 时间范围（1h/24h/7d/30d）
            level: 日志级别
            success: 是否成功
        
        Returns:
            审计日志列表
        """
        # 解析时间范围
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            time_param = f'-{hours} hours'
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            time_param = f'-{days} days'
        else:
            time_param = '-24 hours'
        
        conditions = ["timestamp > datetime('now', ?)"]
        params = [time_param]
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if action:
            conditions.append("action = ?")
            params.append(action)
        
        if level:
            conditions.append("level = ?")
            params.append(level)
        
        if success is not None:
            conditions.append("success = ?")
            params.append(1 if success else 0)
        
        query = f"""
            SELECT * FROM audit_log
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
        """
        
        cursor = self.db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def query_system(self, component: str = None, level: str = None,
                     time_range: str = '24h') -> List[Dict]:
        """
        查询系统日志
        
        Args:
            component: 组件名称
            level: 日志级别
            time_range: 时间范围
        
        Returns:
            系统日志列表
        """
        # 解析时间范围
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            time_param = f'-{hours} hours'
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            time_param = f'-{days} days'
        else:
            time_param = '-24 hours'
        
        conditions = ["timestamp > datetime('now', ?)"]
        params = [time_param]
        
        if component:
            conditions.append("component = ?")
            params.append(component)
        
        if level:
            conditions.append("level = ?")
            params.append(level)
        
        query = f"""
            SELECT * FROM system_log
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
        """
        
        cursor = self.db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def export(self, time_range: str = '7d', format: str = 'csv',
               user_id: str = None) -> bytes:
        """
        导出审计日志
        
        Args:
            time_range: 时间范围
            format: 导出格式（csv/json）
            user_id: 用户 ID
        
        Returns:
            导出的文件字节
        """
        logs = self.query(user_id=user_id, time_range=time_range)
        
        if format == 'csv':
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            return output.getvalue().encode('utf-8')
        
        elif format == 'json':
            return json.dumps(logs, indent=2, default=str).encode('utf-8')
        
        return b''
    
    def get_statistics(self, time_range: str = '24h') -> Dict:
        """
        获取日志统计
        
        Args:
            time_range: 时间范围
        
        Returns:
            统计信息字典
        """
        # 解析时间范围
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            time_param = f'-{hours} hours'
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            time_param = f'-{days} days'
        else:
            time_param = '-24 hours'
        
        # 总日志数
        cursor = self.db.execute("""
            SELECT COUNT(*) as count FROM audit_log
            WHERE timestamp > datetime('now', ?)
        """, (time_param,))
        total = cursor.fetchone()['count']
        
        # 按级别统计
        cursor = self.db.execute("""
            SELECT level, COUNT(*) as count FROM audit_log
            WHERE timestamp > datetime('now', ?)
            GROUP BY level
        """, (f'-{time_range}',))
        by_level = {row['level']: row['count'] for row in cursor.fetchall()}
        
        # 按用户统计
        cursor = self.db.execute("""
            SELECT user_id, COUNT(*) as count FROM audit_log
            WHERE timestamp > datetime('now', ?)
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """, (f'-{time_range}',))
        by_user = {row['user_id'] or 'anonymous': row['count'] for row in cursor.fetchall()}
        
        # 按操作统计
        cursor = self.db.execute("""
            SELECT action, COUNT(*) as count FROM audit_log
            WHERE timestamp > datetime('now', ?)
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        """, (f'-{time_range}',))
        by_action = {row['action']: row['count'] for row in cursor.fetchall()}
        
        # 成功率
        cursor = self.db.execute("""
            SELECT 
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM audit_log
            WHERE timestamp > datetime('now', ?)
        """, (f'-{time_range}',))
        success_rate = cursor.fetchone()['success_rate'] or 0
        
        return {
            'total': total,
            'by_level': by_level,
            'by_user': by_user,
            'by_action': by_action,
            'success_rate': success_rate,
            'time_range': time_range
        }
    
    def cleanup_old_logs(self):
        """清理旧日志"""
        # 清理审计日志
        self.db.execute("""
            DELETE FROM audit_log
            WHERE timestamp < datetime('now', ?)
        """, (f'-{self.log_retention_days} days',))
        
        # 清理系统日志
        self.db.execute("""
            DELETE FROM system_log
            WHERE timestamp < datetime('now', ?)
        """, (f'-{self.log_retention_days} days',))
        
        self.db.commit()
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 使用示例
if __name__ == '__main__':
    import tempfile
    import os
    
    # 创建测试数据库
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # 创建审计日志器
    logger = AuditLogger(db_path)
    
    print("✅ 审计日志器初始化成功")
    
    # 记录审计日志
    logger.log('user_001', 'ai_call', 'slice_123', {'model': 'qwen-vl-max'})
    logger.log('user_001', 'storage_upload', 'file_456', {'size': 1024})
    
    # 记录系统日志
    logger.log_system('MFS', '系统启动', 'INFO')
    
    # 查询日志
    logs = logger.query('user_001', time_range='1h')
    print(f"审计日志：{len(logs)}条")
    
    # 获取统计
    stats = logger.get_statistics('1h')
    print(f"统计：{stats['total']}条，成功率 {stats['success_rate']:.1f}%")
    
    # 清理
    logger.close()
    os.close(db_fd)
