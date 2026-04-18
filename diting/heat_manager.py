"""
记忆热度管理器（四系统架构 - 热度模块）

热力学四系统类比：
- 内能（U）：记忆被访问的总次数（积累的能量）
- 温度（T）：记忆与当前上下文的关联度/激活梯度
- 熵（S）：记忆的混乱和不确定性（争议性）
- 自由能（G）：G = U - TS，记忆有效性（决定是否能"做功"）

物理意义：
- 热量只在温差>0 时传递 → 记忆只在关联度足够大时被提取
- 系统做功需要 G>0 → 记忆可用需要自由能>0

当前实现：热度系统（内能 U 的代理指标）
预留接口：温度系统、熵系统、自由能系统
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional


# 热度评分说明（0-100 数值，代表内能 U 的代理）
# 🔥 高热度区：70-100 (频繁访问/高内能)
# 🌤️ 中热度区：40-69 (中等访问/中内能)
# ❄️ 低热度区：10-39 (较少访问/低内能)
# 🧊 冻结区：0-9 (明确废弃/负自由能)


class HeatManager:
    """
    热度管理器（四系统架构中的内能 U 模块）

    职责：
    1. 追踪记忆被访问的总次数（内能 U）
    2. 计算热度评分（U 的 0-100 标准化）
    3. 支持时间衰减、轮次衰减
    4. 用户主动升温（增加 U）
    5. 死灰复燃检测（U 低但 T 高的情况）

    预留接口：
    - TemperatureManager: 计算关联度 T
    - EntropyManager: 计算争议性 S
    - FreeEnergyManager: 计算 G = U - TS
    """

    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化温度管理器

        Args:
            db_path: SQLite 数据库路径
            config: 配置字典
        """
        self.db_path = db_path
        self.config = config or {}

        # 温度配置
        self.time_decay_rate = self.config.get(
            'TIME_DECAY_RATE', 0.1)  # 每天衰减 0.1 分
        self.round_decay_rate = self.config.get(
            'ROUND_DECAY_RATE', 5)  # 每轮衰减 5 分
        self.user_heat_bonus = self.config.get(
            'USER_HEAT_BONUS', 30)   # 用户主动升温 +30 分

        # 温度参考阈值（仅用于显示建议）
        self.high_threshold = 70    # 高温区参考
        self.low_threshold = 40     # 低温区参考
        self.frozen_threshold = 10  # 冻结区参考

        # 初始化数据库
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self):
        """确保数据库表结构存在"""
        # 检查 heat_score 字段是否存在
        cursor = self.db.execute("PRAGMA table_info(multimodal_slices)")
        columns = [row['name'] for row in cursor.fetchall()]

        # 逐个检查并添加缺失的列（避免重复列错误）
        if 'heat_score' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN heat_score INTEGER DEFAULT 50")
        if 'last_heated_at' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN last_heated_at TIMESTAMP")
        if 'freeze_reason' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN freeze_reason TEXT")
        if 'freeze_by' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN freeze_by TEXT")
        if 'freeze_at' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN freeze_at TIMESTAMP")
        if 'last_mentioned_round' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN last_mentioned_round INTEGER")
        if 'iteration_status' not in columns:
            self.db.execute(
                "ALTER TABLE multimodal_slices ADD COLUMN iteration_status TEXT DEFAULT 'active'")

        self.db.commit()

        # 创建温度日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS heat_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slice_id TEXT NOT NULL,
                old_score INTEGER,
                new_score INTEGER,
                reason TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_temp_log_slice ON heat_log(slice_id)")
        self.db.commit()

    def calculate_heat(self, slice_id: str, current_round: int = None) -> Dict:
        """
        计算记忆温度

        Args:
            slice_id: 切片 ID
            current_round: 当前轮次

        Returns:
            温度计算结果
        """
        # 获取记忆信息
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        # 基础分数
        score = memory.get('heat_score', 50)

        # 1. 时间衰减
        created_at = datetime.fromisoformat(memory['created_at'])
        days_old = (datetime.now() - created_at).days
        time_decay = days_old * self.time_decay_rate
        score -= time_decay

        # 2. 轮次衰减
        if current_round is not None:
            last_round = memory.get('last_mentioned_round') or 0
            rounds_since_mentioned = current_round - last_round
            round_decay = rounds_since_mentioned * self.round_decay_rate
            score -= round_decay

        # 3. 温度分数即为最终结果（0-100 连续数值）
        new_score = max(0, min(100, int(score)))  # 限制在 0-100
        old_score = memory.get('heat_score', 50)

        # 4. 更新数据库
        self._update_heat(slice_id, new_score, current_round)

        # 5. 记录日志
        self._log_change(
            slice_id, old_score, new_score,
            '自动温度计算', 'system'
        )

        return {
            'slice_id': slice_id,
            'old_score': old_score,
            'new_score': new_score,
            'label': self._get_heat_label(new_score),
            'time_decay': time_decay,
            'round_decay': round_decay if current_round else 0
        }

    def heat(self, slice_id: str, reason: str = "用户主动升温",
             changed_by: str = "user") -> Dict:
        """
        加热记忆（升温）

        Args:
            slice_id: 切片 ID
            reason: 升温原因
            changed_by: 操作者

        Returns:
            升温结果
        """
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        old_score = memory.get('heat_score', 50)

        # 升温
        new_score = min(100, old_score + self.user_heat_bonus)  # 不超过 100

        # 更新数据库
        self.db.execute("""
            UPDATE multimodal_slices
            SET heat_score = ?, last_heated_at = ?
            WHERE slice_id = ?
        """, (new_score, datetime.now().isoformat(), slice_id))
        self.db.commit()

        # 记录日志
        self._log_change(slice_id, old_score, new_score, reason, changed_by)

        return {
            'slice_id': slice_id,
            'old_score': old_score,
            'new_score': new_score,
            'label': self._get_heat_label(new_score),
            'bonus': self.user_heat_bonus
        }

    def cool(self, slice_id: str, reason: str = "自然冷却",
             changed_by: str = "system") -> Dict:
        """
        冷却记忆（降温）

        Args:
            slice_id: 切片 ID
            reason: 降温原因
            changed_by: 操作者

        Returns:
            降温结果
        """
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        old_score = memory.get('heat_score', 50)

        # 降温
        new_score = max(0, old_score - 20)  # 不低于 0

        # 更新数据库
        self.db.execute("""
            UPDATE multimodal_slices
            SET heat_score = ?
            WHERE slice_id = ?
        """, (new_score, slice_id))
        self.db.commit()

        # 记录日志
        self._log_change(slice_id, old_score, new_score, reason, changed_by)

        return {
            'slice_id': slice_id,
            'old_score': old_score,
            'new_score': new_score,
            'label': self._get_heat_label(new_score)
        }

    def freeze(self, slice_id: str, reason: str,
               changed_by: str = "user") -> Dict:
        """
        冻结记忆（防止死灰复燃）

        Args:
            slice_id: 切片 ID
            reason: 冻结原因
            changed_by: 操作者

        Returns:
            冻结结果
        """
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        old_score = memory.get('heat_score', 50)

        # 冻结（温度设为 0）
        self.db.execute("""
            UPDATE multimodal_slices
            SET heat_score = ?,
                freeze_reason = ?, freeze_by = ?, freeze_at = ?,
                iteration_status = 'frozen'
            WHERE slice_id = ?
        """, (0, reason, changed_by, datetime.now().isoformat(), slice_id))
        self.db.commit()

        # 记录日志
        self._log_change(slice_id, old_score, 0, reason, changed_by)

        return {
            'slice_id': slice_id,
            'old_score': old_score,
            'new_score': 0,
            'label': '🧊 冻结',
            'reason': reason,
            'frozen_by': changed_by
        }

    def thaw(self, slice_id: str, reason: str = "用户解冻",
             changed_by: str = "user") -> Dict:
        """
        解冻记忆

        Args:
            slice_id: 切片 ID
            reason: 解冻原因
            changed_by: 操作者

        Returns:
            解冻结果
        """
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        if memory.get('heat_score', 50) > 10:
            return {'error': '该记忆未被冻结（分数>10）'}

        old_score = memory.get('heat_score', 0)

        # 解冻到温暖状态（50 分）
        new_score = 50

        self.db.execute("""
            UPDATE multimodal_slices
            SET heat_score = ?,
                freeze_reason = NULL, freeze_by = NULL, freeze_at = NULL
            WHERE slice_id = ?
        """, (new_score, slice_id))
        self.db.commit()

        # 记录日志
        self._log_change(slice_id, old_score, new_score, reason, changed_by)

        return {
            'slice_id': slice_id,
            'old_score': old_score,
            'new_score': new_score,
            'label': self._get_heat_label(new_score)
        }

    def detect_zombie_revival(self, slice_id: str, triggered_by: str) -> Dict:
        """
        检测死灰复燃

        Args:
            slice_id: 切片 ID
            triggered_by: 触发者（user/agent）

        Returns:
            检测结果
        """
        memory = self._get_memory(slice_id)
        if not memory:
            return {'error': '记忆不存在'}

        # 获取 AI 关键词
        ai_keywords = memory.get('ai_keywords', '[]')
        try:
            keywords = json.loads(ai_keywords)
        except (json.JSONDecodeError, TypeError):
            keywords = []

        # 查找相关的冻结记忆
        frozen_related = self._find_frozen_related(keywords)

        if triggered_by == 'user':
            # 用户主动提到 → 升温，不报警
            if frozen_related:
                self.heat(slice_id, "用户主动提及淘汰方案", 'user')
            return {
                'is_zombie': False,
                'triggered_by': 'user',
                'frozen_related_count': len(frozen_related),
                'action': '用户主动升温'
            }

        elif triggered_by == 'agent':
            # Agent 突然发病 → 报警
            if frozen_related:
                # 冻结当前记忆，防止幻觉传播
                self.freeze(
                    slice_id,
                    f"Agent 幻觉：提及淘汰方案 {frozen_related[0]['memory_path']}",
                    'system'
                )
                return {
                    'is_zombie': True,
                    'triggered_by': 'agent',
                    'frozen_memories': frozen_related,
                    'action': '已冻结，防止幻觉传播'
                }

        return {
            'is_zombie': False,
            'triggered_by': triggered_by
        }

    def _find_frozen_related(self, keywords: List[str]) -> List[Dict]:
        """查找相关的冻结记忆"""
        if not keywords:
            return []

        # 构建搜索条件
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("ai_keywords LIKE ?")
            params.append(f'%{kw}%')

        cursor = self.db.execute(f"""
            SELECT slice_id, memory_path, freeze_reason, freeze_at
            FROM multimodal_slices
            WHERE iteration_status = 'frozen'
              AND ({' OR '.join(conditions)})
        """, params)

        return [dict(row) for row in cursor.fetchall()]

    def recalculate_all(self, current_round: int) -> Dict:
        """
        重新计算所有记忆的温度

        Args:
            current_round: 当前轮次

        Returns:
            统计信息
        """
        cursor = self.db.execute("""
            SELECT slice_id FROM multimodal_slices
            WHERE iteration_status != 'frozen'
        """)

        stats = {'hot': 0, 'warm': 0, 'cold': 0, 'frozen': 0}

        for row in cursor.fetchall():
            result = self.calculate_heat(row['slice_id'], current_round)
            if 'new_temp' in result:
                stats[result['new_temp']] += 1

        return stats

    def _get_memory(self, slice_id: str) -> Optional[Dict]:
        """获取记忆信息"""
        cursor = self.db.execute(
            "SELECT * FROM multimodal_slices WHERE slice_id = ?",
            (slice_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def _get_heat_label(self, score: int) -> str:
        """
        分数转温度标签（仅供参考）

        Args:
            score: 0-100 温度分数

        Returns:
            温度标签字符串
        """
        if score >= 70:
            return '🔥 高温'
        elif score >= 40:
            return '🌤️ 中温'
        elif score >= 10:
            return '❄️ 低温'
        else:
            return '🧊 冻结'

    def _update_heat(self, slice_id: str, temp: str, score: int,
                     current_round: int = None):
        """更新温度"""
        if current_round is not None:
            self.db.execute("""
                UPDATE multimodal_slices
                SET heat_score = ?, last_mentioned_round = ?
                WHERE slice_id = ?
            """, (score, current_round, slice_id))
        else:
            self.db.execute("""
                UPDATE multimodal_slices
                SET heat_score = ?
                WHERE slice_id = ?
            """, (score, slice_id))
        self.db.commit()

    def _log_change(self, slice_id: str, old_score: int, new_score: int,
                    reason: str, changed_by: str):
        """记录温度变更日志"""
        self.db.execute("""
            INSERT INTO heat_log
            (slice_id, old_score, new_score, reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        """, (slice_id, old_score, new_score, reason, changed_by))
        self.db.commit()

    def get_heat_history(self, slice_id: str, limit: int = 10) -> List[Dict]:
        """获取温度变更历史"""
        cursor = self.db.execute("""
            SELECT old_score, new_score, reason, changed_by, changed_at
            FROM heat_log
            WHERE slice_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (slice_id, limit))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 使用示例
if __name__ == '__main__':
    import tempfile
    import os

    # 创建测试数据库
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # 创建温度管理器
    temp_mgr = HeatManager(db_path, {
        'TIME_DECAY_RATE': 0.1,
        'ROUND_DECAY_RATE': 5,
        'USER_HEAT_BONUS': 30
    })

    print("✅ 温度管理器初始化成功")

    # 清理
    temp_mgr.close()
    os.close(db_fd)
