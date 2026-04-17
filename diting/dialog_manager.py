"""
对话管理器（Dialog Manager）

实现混合模式对话存储（方案 C）
- 热数据：0-7 天，完整存储
- 温数据：7-30 天，摘要存储
- 冷数据：重要对话，永久保存
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from .mft import MFT


class DialogManager:
    """对话管理器"""

    def __init__(self, mft: MFT):
        """
        初始化对话管理器

        Args:
            mft: MFT 实例
        """
        self.mft = mft
        
        # 存储路径
        self.path_hot = "/dialog/hot"     # 热数据
        self.path_warm = "/dialog/warm"   # 温数据
        self.path_cold = "/dialog/cold"   # 冷数据
        
        # 时间阈值（天）
        self.hot_days = 7
        self.warm_days = 30

    def add_dialog(self, session_id: str, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> str:
        """
        添加对话（存入热数据区）

        Args:
            session_id: 会话 ID
            role: 角色（user/assistant）
            content: 对话内容
            metadata: 可选元数据

        Returns:
            存储路径
        """
        import time
        timestamp = datetime.now()
        # 使用毫秒级时间戳避免冲突
        path = f"{self.path_hot}/{session_id}/{timestamp.strftime('%Y%m%d_%H%M%S')}_{role}_{int(time.time()*1000)}"
        
        self.mft.create(
            path, 
            "NOTE", 
            content,
            status="active"
        )
        
        return path

    def add_dialog_batch(self, session_id: str, messages: List[Dict]) -> List[str]:
        """
        批量添加对话

        Args:
            session_id: 会话 ID
            messages: 消息列表 [{"role": "user", "content": "..."}, ...]

        Returns:
            存储路径列表
        """
        import time
        paths = []
        for i, msg in enumerate(messages):
            # 每条消息间隔 1ms 避免冲突
            time.sleep(0.001)
            path = self.add_dialog(
                session_id, 
                msg.get("role", "user"), 
                msg.get("content", "")
            )
            paths.append(path)
        return paths

    def mark_as_important(self, path: str, reason: str = "") -> bool:
        """
        标记对话为重要（移到冷数据区）

        Args:
            path: 原路径
            reason: 重要原因

        Returns:
            True 如果成功
        """
        # 读取原内容
        record = self.mft.read(path)
        if not record:
            return False
        
        # 移到冷数据区
        new_path = f"{self.path_cold}/{path.split('/')[-1]}"
        self.mft.create(
            new_path,
            "NOTE",
            f"[重要] {reason}\n\n{record['content']}"
        )
        
        # 标记原记录为 archived
        self.mft.update(path, status="archived")
        
        return True

    def extract_summary(self, path: str) -> Optional[str]:
        """
        提取对话摘要

        Args:
            path: 对话路径

        Returns:
            摘要内容
        """
        record = self.mft.read(path)
        if not record:
            return None
        
        # TODO: 调用 AI 模型生成摘要
        # 简化版：提取前 200 字
        content = record['content']
        if len(content) <= 200:
            return content
        
        return content[:200] + "..."

    def migrate_to_warm(self, path: str) -> bool:
        """
        迁移对话到温数据区（转为摘要）

        Args:
            path: 热数据区路径

        Returns:
            True 如果成功
        """
        # 提取摘要
        summary = self.extract_summary(path)
        if not summary:
            return False
        
        # 存入温数据区
        new_path = f"{self.path_warm}/{path.split('/')[-1]}"
        self.mft.create(
            new_path,
            "NOTE",
            f"[摘要] {summary}"
        )
        
        # 标记原记录为 archived
        self.mft.update(path, status="archived")
        
        return True

    def cleanup_old_dialogs(self) -> Dict[str, int]:
        """
        清理过期对话

        Returns:
            清理统计 {"hot_to_warm": X, "warm_deleted": Y}
        """
        stats = {
            "hot_to_warm": 0,
            "warm_deleted": 0
        }
        
        # TODO: 扫描热数据区，超过 7 天的移到温数据区
        # TODO: 扫描温数据区，超过 30 天的删除
        
        return stats

    def search_dialogs(self, query: str, scope: str = "all") -> List[Dict]:
        """
        搜索对话

        Args:
            query: 搜索词
            scope: 搜索范围（hot/warm/cold/all）

        Returns:
            搜索结果列表
        """
        results = []
        
        if scope in ["hot", "all"]:
            hot_results = self.mft.search(query, scope=self.path_hot)
            results.extend(hot_results)
        
        if scope in ["warm", "all"]:
            warm_results = self.mft.search(query, scope=self.path_warm)
            results.extend(warm_results)
        
        if scope in ["cold", "all"]:
            cold_results = self.mft.search(query, scope=self.path_cold)
            results.extend(cold_results)
        
        return results

    def get_dialog_history(self, session_id: str, days: int = 7) -> List[Dict]:
        """
        获取会话历史

        Args:
            session_id: 会话 ID
            days: 回溯天数

        Returns:
            对话列表
        """
        # 搜索该 session 的对话
        results = self.mft.search(session_id, scope=self.path_hot)
        return sorted(results, key=lambda x: x.get('create_ts', ''))

    def get_stats(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        return {
            "hot_path": self.path_hot,
            "warm_path": self.path_warm,
            "cold_path": self.path_cold,
            "hot_days": self.hot_days,
            "warm_days": self.warm_days
        }
