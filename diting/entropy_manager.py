"""
记忆熵系统管理器

评估长期任务/计划的不确定性和混乱性
随着方案确定，应该熵减
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class EntropyLevel(Enum):
    """熵级"""
    HIGH = 'high'     # 🌪️ 高熵 (>=70): 混乱/不确定/讨论初期
    MEDIUM = 'medium' # 🌊 中熵 (40-69): 收敛中/有方向未决策
    LOW = 'low'       # 📐 低熵 (<40): 确定/已决策/执行中


class EntropyManager:
    """熵管理器"""
    
    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化熵管理器
        
        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}
        
        # 熵系统开关
        self.enabled = self.config.get('ENABLE_ENTROPY', False)
        
        # 熵值阈值
        self.high_threshold = 70
        self.medium_threshold = 40
        
        # 熵增因素
        self.option_increase = 15      # 每多一个方案 +15
        self.disagreement_increase = 20  # 检测到分歧 +20
        self.time_open_increase = 0.5   # 每天未决 +0.5
        
        # 熵减因素
        self.decision_decrease = 30    # 做出决策 -30
        self.version_increase_decrease = 10  # 版本迭代 -10
        self.execution_decrease = 40   # 开始执行 -40
        
        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._ensure_schema()
    
    def _ensure_schema(self):
        """确保数据库表结构存在"""
        # 检查 entropy 字段是否存在
        cursor = self.db.execute("PRAGMA table_info(multimodal_slices)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'entropy' not in columns:
            # 添加熵字段
            self.db.execute("""
                ALTER TABLE multimodal_slices ADD COLUMN entropy INTEGER DEFAULT NULL
            """)
            self.db.execute("""
                ALTER TABLE multimodal_slices ADD COLUMN entropy_level TEXT DEFAULT NULL
            """)
            self.db.execute("""
                ALTER TABLE multimodal_slices ADD COLUMN last_entropy_change TIMESTAMP
            """)
            self.db.execute("""
                ALTER TABLE multimodal_slices ADD COLUMN entropy_trend TEXT DEFAULT NULL
            """)
            self.db.commit()
        
        # 创建熵变日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS entropy_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slice_id INTEGER NOT NULL,
                old_entropy INTEGER,
                new_entropy INTEGER,
                old_level TEXT,
                new_level TEXT,
                change_reason TEXT,
                triggered_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_entropy_log_slice ON entropy_log(slice_id)")
        self.db.commit()
    
    def calculate_entropy(self, slice_id: str) -> Dict:
        """
        计算记忆熵值
        
        Args:
            slice_id: 切片 ID
        
        Returns:
            熵计算结果
        """
        if not self.enabled:
            return {'error': '熵系统未启用'}
        
        # 获取记忆信息
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}
        
        # 基础熵值
        entropy = 50
        
        content = memory.get('content', '') + ' ' + (memory.get('ai_summary', '') or '')
        
        # 1. 方案数量（越多越混乱）
        option_count = self._count_options(content)
        entropy += option_count * self.option_increase
        
        # 2. 决策状态
        if self._has_decision_keywords(content):
            entropy -= self.decision_decrease
        if self._has_execution_keywords(content):
            entropy -= self.execution_decrease
        if self._has_uncertainty_keywords(content):
            entropy += 15
        
        # 3. 版本迭代（版本越高熵越低）
        version = self._parse_version(memory.get('iteration_version', ''))
        if version > 1:
            entropy -= (version - 1) * self.version_increase_decrease
        
        # 4. 关键词多样性
        keywords = memory.get('ai_keywords', '[]')
        try:
            keyword_list = json.loads(keywords)
            if len(keyword_list) > 10:
                entropy += 15
            elif len(keyword_list) < 3:
                entropy -= 10
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 5. 检测分歧
        if self._detect_disagreement(content):
            entropy += self.disagreement_increase
        
        # 6. 时间进展（讨论越久未决熵增）
        created_at = datetime.fromisoformat(memory['created_at'])
        days_open = (datetime.now() - created_at).days
        if days_open > 30 and memory.get('iteration_status') == 'active':
            entropy += days_open * self.time_open_increase
        
        # 限制在 0-100 范围
        entropy = max(0, min(100, int(entropy)))
        
        # 确定熵级
        new_level = self._entropy_to_level(entropy)
        old_level = memory.get('entropy_level')
        old_entropy = memory.get('entropy')
        
        # 确定趋势
        if old_entropy is not None:
            if entropy > old_entropy + 10:
                trend = 'increasing'
            elif entropy < old_entropy - 10:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # 更新数据库
        self._update_entropy(slice_id, entropy, new_level, trend)
        
        # 记录日志
        if old_entropy is not None:
            self._log_change(
                slice_id, old_entropy, entropy,
                old_level, new_level,
                '自动熵计算', 'system'
            )
        
        return {
            'slice_id': slice_id,
            'old_entropy': old_entropy,
            'new_entropy': entropy,
            'old_level': old_level,
            'new_level': new_level,
            'trend': trend,
            'factors': {
                'option_count': option_count,
                'version': version,
                'days_open': days_open
            }
        }
    
    def recalculate_all(self) -> Dict:
        """
        重新计算所有记忆的熵值
        
        Returns:
            统计信息
        """
        if not self.enabled:
            return {'error': '熵系统未启用'}
        
        cursor = self.db.execute("""
            SELECT slice_id FROM multimodal_slices
            WHERE entropy IS NOT NULL
        """)
        
        stats = {'high': 0, 'medium': 0, 'low': 0}
        
        for row in cursor.fetchall():
            result = self.calculate_entropy(row['slice_id'])
            if 'new_level' in result:
                stats[result['new_level']] += 1
        
        return stats
    
    def get_project_entropy(self, project_path: str) -> Dict:
        """
        获取项目整体熵值
        
        Args:
            project_path: 项目路径前缀
        
        Returns:
            项目熵值统计
        """
        if not self.enabled:
            return {'error': '熵系统未启用'}
        
        cursor = self.db.execute("""
            SELECT entropy, entropy_level, entropy_trend
            FROM multimodal_slices
            WHERE memory_path LIKE ?
            AND entropy IS NOT NULL
        """, (f'{project_path}%',))
        
        rows = cursor.fetchall()
        
        if not rows:
            return {
                'avg_entropy': 0,
                'level': 'unknown',
                'memory_count': 0
            }
        
        # 计算平均熵值
        avg_entropy = sum(row['entropy'] for row in rows) / len(rows)
        
        # 确定整体熵级
        high_count = sum(1 for row in rows if row['entropy_level'] == 'high')
        if high_count > len(rows) / 2:
            overall_level = 'high'
        elif avg_entropy >= self.high_threshold:
            overall_level = 'high'
        elif avg_entropy >= self.medium_threshold:
            overall_level = 'medium'
        else:
            overall_level = 'low'
        
        # 确定趋势
        increasing_count = sum(1 for row in rows if row['entropy_trend'] == 'increasing')
        if increasing_count > len(rows) / 2:
            overall_trend = 'increasing'
        else:
            overall_trend = 'stable'
        
        return {
            'avg_entropy': avg_entropy,
            'level': overall_level,
            'memory_count': len(rows),
            'high_entropy_ratio': high_count / len(rows),
            'trend': overall_trend
        }
    
    def alert_high_entropy(self, slice_id: str, threshold: int = None) -> Dict:
        """
        高熵预警
        
        Args:
            slice_id: 切片 ID
            threshold: 阈值（默认 80）
        
        Returns:
            预警信息
        """
        if not self.enabled:
            return {'alert': False, 'reason': '熵系统未启用'}
        
        threshold = threshold or 80
        
        memory = self._get_memory(slice_id)
        if not memory:
            return {'alert': False, 'reason': '记忆不存在'}
        
        entropy = memory.get('entropy', 50)
        
        if entropy >= threshold:
            days_open = (datetime.now() - datetime.fromisoformat(memory['created_at'])).days
            return {
                'alert': True,
                'message': f"⚠️ 高熵预警：{memory['memory_path']}",
                'entropy': entropy,
                'level': memory.get('entropy_level'),
                'days_open': days_open,
                'suggestion': "讨论时间过长，建议尽快做出决策"
            }
        
        return {'alert': False}
    
    def detect_entropy_anomaly(self, slice_id: str) -> Dict:
        """
        检测熵值异常
        
        Args:
            slice_id: 切片 ID
        
        Returns:
            异常检测结果
        """
        if not self.enabled:
            return {'has_anomaly': False, 'reason': '熵系统未启用'}
        
        memory = self._get_memory(slice_id)
        if not memory:
            return {'has_anomaly': False, 'reason': '记忆不存在'}
        
        anomalies = []
        
        entropy = memory.get('entropy', 50)
        level = memory.get('entropy_level', 'medium')
        trend = memory.get('entropy_trend', 'stable')
        
        # 异常 1: 低熵方案熵值突然升高（可能有人翻旧账）
        if level == 'low' and trend == 'increasing':
            anomalies.append({
                'type': 'decision_reversed',
                'message': "已决策方案熵值升高，可能有人翻旧账"
            })
        
        # 异常 2: 执行中方案熵值升高（可能执行受阻）
        if '执行' in memory.get('content', '') and entropy > 50:
            anomalies.append({
                'type': 'execution_blocked',
                'message': "执行中方案熵值升高，可能执行受阻"
            })
        
        # 异常 3: 高熵 + 低温（混乱但被遗忘，危险）
        temp = memory.get('temperature', 'warm')
        if entropy >= 70 and temp == 'cold':
            anomalies.append({
                'type': 'chaotic_forgotten',
                'message': "高熵低温：混乱但被遗忘，幻觉高危"
            })
        
        return {
            'has_anomaly': len(anomalies) > 0,
            'anomalies': anomalies
        }
    
    def _get_memory(self, slice_id: str) -> Optional[Dict]:
        """获取记忆信息"""
        cursor = self.db.execute(
            "SELECT * FROM multimodal_slices WHERE slice_id = ?",
            (slice_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _entropy_to_level(self, entropy: int) -> str:
        """熵值转熵级"""
        if entropy >= self.high_threshold:
            return EntropyLevel.HIGH.value
        elif entropy >= self.medium_threshold:
            return EntropyLevel.MEDIUM.value
        else:
            return EntropyLevel.LOW.value
    
    def _update_entropy(self, slice_id: str, entropy: int, level: str, trend: str):
        """更新熵值"""
        self.db.execute("""
            UPDATE multimodal_slices 
            SET entropy = ?, entropy_level = ?, entropy_trend = ?,
                last_entropy_change = ?
            WHERE slice_id = ?
        """, (entropy, level, trend, datetime.now().isoformat(), slice_id))
        self.db.commit()
    
    def _log_change(self, slice_id: str, old_entropy: int, new_entropy: int,
                   old_level: str, new_level: str, reason: str, triggered_by: str):
        """记录熵变日志"""
        self.db.execute("""
            INSERT INTO entropy_log 
            (slice_id, old_entropy, new_entropy, old_level, new_level, change_reason, triggered_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (slice_id, old_entropy, new_entropy, old_level, new_level, reason, triggered_by))
        self.db.commit()
    
    def _count_options(self, content: str) -> int:
        """统计方案数量"""
        patterns = [r'方案 [A-Z]', r'方案\d+', r'Option\s*\d+', r'Plan\s*\d+']
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content))
        return count
    
    def _has_decision_keywords(self, content: str) -> bool:
        """检测决策关键词"""
        keywords = ['已确定', '就这么定了', '决定', '确定', '就这么办', 'final', 'decided']
        return any(kw in content for kw in keywords)
    
    def _has_execution_keywords(self, content: str) -> bool:
        """检测执行关键词"""
        keywords = ['开始执行', '实施', '进行中', 'executing', 'implementing']
        return any(kw in content for kw in keywords)
    
    def _has_uncertainty_keywords(self, content: str) -> bool:
        """检测不确定关键词"""
        keywords = ['待定', '再讨论', '再研究', '不确定', ' TBD ', 'pending', 'discuss']
        return any(kw in content for kw in keywords)
    
    def _parse_version(self, version_str: str) -> int:
        """解析版本号"""
        if not version_str:
            return 1
        match = re.search(r'v?(\d+)', version_str)
        return int(match.group(1)) if match else 1
    
    def _detect_disagreement(self, content: str) -> bool:
        """检测分歧"""
        keywords = [
            '但是', '不过', '然而', '反对', '不同意',
            '有问题', '风险', '担心', '疑虑', 'disagree'
        ]
        return any(kw in content for kw in keywords)
    
    def get_entropy_history(self, slice_id: str, limit: int = 10) -> List[Dict]:
        """获取熵变历史"""
        cursor = self.db.execute("""
            SELECT old_entropy, new_entropy, old_level, new_level, 
                   change_reason, triggered_by, changed_at
            FROM entropy_log
            WHERE slice_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (slice_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def enable(self):
        """启用熵系统"""
        self.enabled = True
    
    def disable(self):
        """禁用熵系统"""
        self.enabled = False
    
    def is_enabled(self) -> bool:
        """检查熵系统是否启用"""
        return self.enabled
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 使用示例
if __name__ == '__main__':
    import tempfile
    import os
    
    # 创建测试数据库
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # 创建熵管理器
    entropy_mgr = EntropyManager(db_path, {'ENABLE_ENTROPY': True})
    
    print("✅ 熵管理器初始化成功")
    print(f"   熵系统状态：{'已启用' if entropy_mgr.is_enabled() else '未启用'}")
    
    # 清理
    entropy_mgr.close()
    os.close(db_fd)
