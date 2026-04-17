"""
智能触发策略

根据文件类型、大小、用户标记等条件，智能决定是否调用 AI 生成概括
"""

from typing import Dict, Optional


class SmartTrigger:
    """智能触发器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化智能触发器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 智能触发开关
        self.enabled = self.config.get('ENABLE_SMART_TRIGGER', True)
        
        # 文件类型优先级
        self.file_type_priority = {
            'audio': 0.9,    # 语音优先调用（转文字价值高）
            'image': 0.5,    # 图片中等优先级
            'video': 0.3,    # 视频低优先级（文件大，成本高）
        }
        
        # 文件大小阈值（字节）
        self.size_thresholds = {
            'image': {
                'min_call': 100 * 1024,      # >100KB 考虑调用
                'max_call': 10 * 1024 * 1024, # <10MB 才调用
            },
            'audio': {
                'min_call': 10 * 1024,       # >10KB 考虑调用
                'max_call': 50 * 1024 * 1024, # <50MB 才调用
            }
        }
        
        # 月度 AI 调用配额
        self.monthly_quota = self.config.get('AI_MONTHLY_QUOTA', 100)
        self.quota_used = 0
        
        # 用户标记权重
        self.user_mark_weights = {
            'important': 1.0,      # 用户标记重要 → 必调用
            'skip_ai': -1.0,       # 用户标记跳过 → 不调用
            'archive': -0.5,       # 归档文件 → 低优先级
        }
    
    def should_call_ai(self, file_info: Dict, user_preference: Optional[str] = None) -> bool:
        """
        智能判断是否调用 AI
        
        Args:
            file_info: 文件信息字典
                - type: 文件类型（image/audio）
                - size: 文件大小（字节）
                - filename: 文件名
                - memory_path: 记忆路径
                - user_marked: 用户标记（important/skip_ai/archive/None）
            user_preference: 用户强制偏好（True/False/None）
        
        Returns:
            是否调用 AI
        """
        # 1. 智能触发未启用 → 不调用
        if not self.enabled:
            return False
        
        # 2. 用户强制指定 → 优先
        if user_preference is True:
            return True
        if user_preference is False:
            return False
        
        # 3. 检查配额
        if self.quota_used >= self.monthly_quota:
            return False  # 配额用尽
        
        # 4. 用户标记优先
        user_mark = file_info.get('user_marked')
        if user_mark:
            weight = self.user_mark_weights.get(user_mark, 0)
            if weight > 0:
                return True  # 重要文件
            elif weight < 0:
                return False  # 跳过/归档
        
        # 5. 文件类型优先级
        file_type = file_info.get('type', 'unknown')
        type_priority = self.file_type_priority.get(file_type, 0.5)
        
        # 6. 文件大小检查
        file_size = file_info.get('size', 0)
        size_ok = self._check_size_threshold(file_type, file_size)
        
        if not size_ok:
            return False  # 文件太大或太小
        
        # 7. 文件名分析（包含关键词的文件可能重要）
        filename = file_info.get('filename', '')
        filename_score = self._analyze_filename(filename)
        
        # 8. 记忆路径分析（特定路径的文件可能重要）
        memory_path = file_info.get('memory_path', '')
        path_score = self._analyze_memory_path(memory_path)
        
        # 9. 综合评分
        total_score = (
            type_priority * 0.4 +      # 类型权重 40%
            (1.0 if size_ok else 0.0) * 0.3 +  # 大小权重 30%
            filename_score * 0.2 +     # 文件名权重 20%
            path_score * 0.1           # 路径权重 10%
        )
        
        # 阈值判断（>0.6 调用）
        return total_score > 0.6
    
    def _check_size_threshold(self, file_type: str, file_size: int) -> bool:
        """检查文件大小是否在合理范围"""
        thresholds = self.size_thresholds.get(file_type)
        
        if not thresholds:
            return True  # 未知类型，默认通过
        
        return (
            thresholds['min_call'] <= file_size <= thresholds['max_call']
        )
    
    def _analyze_filename(self, filename: str) -> float:
        """
        分析文件名，判断重要性
        
        高分关键词：重要、会议、备忘、合同、计划
        低分关键词：临时、截图、复制、新建
        """
        if not filename:
            return 0.5  # 默认
        
        filename_lower = filename.lower()
        
        # 高分关键词
        high_score_keywords = [
            '重要', '会议', '备忘', '合同', '计划', '总结', '报告',
            'project', 'meeting', 'note', 'contract', 'plan'
        ]
        
        # 低分关键词
        low_score_keywords = [
            '临时', '截图', '复制', '新建', '未命名', 'test',
            'temp', 'screenshot', 'copy', 'untitled'
        ]
        
        # 计算分数
        high_count = sum(1 for kw in high_score_keywords if kw in filename_lower)
        low_count = sum(1 for kw in low_score_keywords if kw in filename_lower)
        
        if high_count > low_count:
            return 0.9
        elif low_count > high_count:
            return 0.2
        else:
            return 0.5
    
    def _analyze_memory_path(self, memory_path: str) -> float:
        """
        分析记忆路径，判断重要性
        
        高分路径：/important/, /projects/, /meetings/
        低分路径：/temp/, /cache/, /test/
        """
        if not memory_path:
            return 0.5
        
        path_lower = memory_path.lower()
        
        # 高分路径
        high_score_paths = [
            '/important', '/projects', '/meetings', '/work',
            '/关键', '/项目', '/会议', '/工作'
        ]
        
        # 低分路径
        low_score_paths = [
            '/temp', '/cache', '/test', '/trash',
            '/临时', '/缓存', '/测试', '/垃圾'
        ]
        
        for path in high_score_paths:
            if path in path_lower:
                return 0.9
        
        for path in low_score_paths:
            if path in path_lower:
                return 0.2
        
        return 0.5
    
    def use_quota(self):
        """使用一次配额"""
        self.quota_used += 1
    
    def get_quota_status(self) -> Dict:
        """获取配额状态"""
        return {
            'used': self.quota_used,
            'total': self.monthly_quota,
            'remaining': self.monthly_quota - self.quota_used,
            'percentage': self.quota_used / self.monthly_quota * 100
        }
    
    def reset_quota(self):
        """重置配额（每月初调用）"""
        self.quota_used = 0


# 使用示例
if __name__ == '__main__':
    # 创建触发器
    trigger = SmartTrigger({
        'ENABLE_SMART_TRIGGER': True,
        'AI_MONTHLY_QUOTA': 100
    })
    
    # 测试场景 1: 重要会议录音
    file_info_1 = {
        'type': 'audio',
        'size': 5 * 1024 * 1024,  # 5MB
        'filename': '重要会议录音.ogg',
        'memory_path': '/work/meetings/2026-04-15',
        'user_marked': None
    }
    
    result_1 = trigger.should_call_ai(file_info_1)
    print(f"场景 1（重要会议录音）: {'调用 AI' if result_1 else '不调用'}")
    # 预期：调用 AI（语音 + 重要关键词）
    
    # 测试场景 2: 临时截图
    file_info_2 = {
        'type': 'image',
        'size': 500 * 1024,  # 500KB
        'filename': '截图 20260415.png',
        'memory_path': '/temp/screenshots',
        'user_marked': None
    }
    
    result_2 = trigger.should_call_ai(file_info_2)
    print(f"场景 2（临时截图）: {'调用 AI' if result_2 else '不调用'}")
    # 预期：不调用（截图 + 临时路径）
    
    # 测试场景 3: 用户标记重要
    file_info_3 = {
        'type': 'image',
        'size': 2 * 1024 * 1024,  # 2MB
        'filename': 'photo.jpg',
        'memory_path': '/photos/2026-04',
        'user_marked': 'important'
    }
    
    result_3 = trigger.should_call_ai(file_info_3)
    print(f"场景 3（用户标记重要）: {'调用 AI' if result_3 else '不调用'}")
    # 预期：调用 AI（用户强制）
    
    # 配额状态
    status = trigger.get_quota_status()
    print(f"\n配额状态：{status['used']}/{status['total']} ({status['percentage']:.1f}%)")
