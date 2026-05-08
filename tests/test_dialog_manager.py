"""
Dialog Manager 对话管理器测试用例

目标：覆盖率 75% → 90%+
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch, call
from diting.dialog_manager import DialogManager


class TestDialogManagerInit:
    """初始化测试"""

    def test_init(self):
        """测试初始化"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        assert manager.mft == mft
        assert manager.path_hot == "/dialog/hot"
        assert manager.path_warm == "/dialog/warm"
        assert manager.path_cold == "/dialog/cold"
        assert manager.hot_days == 7
        assert manager.warm_days == 30


class TestDialogManagerAddDialog:
    """添加对话测试"""

    def test_add_dialog_basic(self):
        """测试基本添加对话"""
        mft = MagicMock()
        mft.create.return_value = True
        manager = DialogManager(mft)
        
        path = manager.add_dialog("session1", "user", "Hello")
        
        assert path.startswith("/dialog/hot/session1/")
        mft.create.assert_called_once()
        
        call_args = mft.create.call_args
        # mft.create 的参数是 (path, type, content, **metadata)
        assert call_args[0][2] == "Hello"  # content

    def test_add_dialog_with_metadata(self):
        """测试带元数据添加对话"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        manager.add_dialog("session1", "assistant", "Hi", metadata={"key": "value"})
        
        mft.create.assert_called_once()

    def test_add_dialog_batch(self):
        """测试批量添加对话"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"}
        ]
        
        paths = manager.add_dialog_batch("session1", messages)
        
        assert len(paths) == 3
        assert mft.create.call_count == 3

    def test_add_dialog_batch_empty(self):
        """测试空批量添加"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        paths = manager.add_dialog_batch("session1", [])
        
        assert len(paths) == 0
        assert mft.create.call_count == 0


class TestDialogManagerMarkImportant:
    """标记重要对话测试"""

    def test_mark_as_important_success(self):
        """测试成功标记重要"""
        mft = MagicMock()
        mft.read.return_value = {"content": "Important content"}
        mft.create.return_value = True
        mft.update.return_value = True
        manager = DialogManager(mft)
        
        result = manager.mark_as_important("/dialog/hot/session1/msg", reason="测试")
        
        assert result is True
        mft.create.assert_called_once()
        mft.update.assert_called_once()

    def test_mark_as_important_not_found(self):
        """测试标记不存在的对话"""
        mft = MagicMock()
        mft.read.return_value = None
        manager = DialogManager(mft)
        
        result = manager.mark_as_important("/nonexistent", reason="测试")
        
        assert result is False
        mft.create.assert_not_called()

    def test_mark_as_important_empty_reason(self):
        """测试标记重要无原因"""
        mft = MagicMock()
        mft.read.return_value = {"content": "Content"}
        manager = DialogManager(mft)
        
        result = manager.mark_as_important("/dialog/hot/session1/msg")
        
        assert result is True


class TestDialogManagerExtractSummary:
    """提取摘要测试"""

    def test_extract_summary_short(self):
        """测试短内容摘要"""
        mft = MagicMock()
        mft.read.return_value = {"content": "Short content"}
        manager = DialogManager(mft)
        
        summary = manager.extract_summary("/path")
        
        assert summary == "Short content"

    def test_extract_summary_long(self):
        """测试长内容摘要"""
        mft = MagicMock()
        long_content = "A" * 300
        mft.read.return_value = {"content": long_content}
        manager = DialogManager(mft)
        
        summary = manager.extract_summary("/path")
        
        assert len(summary) == 203  # 200 + "..."
        assert summary.endswith("...")

    def test_extract_summary_not_found(self):
        """测试提取不存在的对话"""
        mft = MagicMock()
        mft.read.return_value = None
        manager = DialogManager(mft)
        
        summary = manager.extract_summary("/nonexistent")
        
        assert summary is None

    def test_extract_summary_exact_200(self):
        """测试正好 200 字的内容"""
        mft = MagicMock()
        content = "A" * 200
        mft.read.return_value = {"content": content}
        manager = DialogManager(mft)
        
        summary = manager.extract_summary("/path")
        
        assert summary == content
        assert not summary.endswith("...")


class TestDialogManagerMigrateToWarm:
    """迁移到温数据测试"""

    def test_migrate_to_warm_success(self):
        """测试成功迁移"""
        mft = MagicMock()
        mft.read.return_value = {"content": "Content to migrate"}
        mft.create.return_value = True
        mft.update.return_value = True
        manager = DialogManager(mft)
        
        result = manager.migrate_to_warm("/dialog/hot/session1/msg")
        
        assert result is True
        mft.create.assert_called_once()
        mft.update.assert_called_once()

    def test_migrate_to_warm_extract_fails(self):
        """测试摘要提取失败"""
        mft = MagicMock()
        mft.read.return_value = None  # 提取失败
        manager = DialogManager(mft)
        
        result = manager.migrate_to_warm("/dialog/hot/session1/msg")
        
        assert result is False
        mft.create.assert_not_called()


class TestDialogManagerArchive:
    """归档测试"""

    def _make_memory(self, v_path: str, update_ts: str, content: str = "test") -> dict:
        return {"v_path": v_path, "update_ts": update_ts, "content": content}

    @patch("diting.dialog_manager.datetime")
    def test_archive_hot_to_warm(self, mock_dt):
        """热数据超过 7 天 → 移到温数据区"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        old_ts = (now - timedelta(days=10)).isoformat()  # 10天前 → 超过阈值
        hot_mem = self._make_memory("/dialog/hot/s1/20260428_msg", old_ts, "hello")

        mft = MagicMock()
        mft.search.side_effect = [
            [hot_mem],  # hot 查询
            [],         # warm 查询
        ]
        mft.create.return_value = True
        mft.update.return_value = True
        mft.read.return_value = {"content": "hello"}

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats["hot_to_warm"] == 1
        assert stats["warm_archived"] == 0
        # 原热数据被标记为 archived
        mft.update.assert_called_with("/dialog/hot/s1/20260428_msg", status="archived")
        # 新摘要被写入温数据区
        mft.create.assert_called_once()
        create_args = mft.create.call_args[0]
        assert create_args[0].startswith("/dialog/warm/")

    @patch("diting.dialog_manager.datetime")
    def test_archive_hot_not_expired(self, mock_dt):
        """热数据未超过 7 天 → 不迁移"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        recent_ts = (now - timedelta(days=3)).isoformat()  # 3天前 → 未过期
        hot_mem = self._make_memory("/dialog/hot/s1/recent_msg", recent_ts)

        mft = MagicMock()
        mft.search.side_effect = [[hot_mem], []]

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats["hot_to_warm"] == 0
        mft.create.assert_not_called()
        mft.update.assert_not_called()

    @patch("diting.dialog_manager.datetime")
    def test_archive_warm_to_archived(self, mock_dt):
        """温数据超过 30 天 → status='archived'"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        old_ts = (now - timedelta(days=35)).isoformat()  # 35天前 → 超过阈值
        warm_mem = self._make_memory("/dialog/warm/old_msg", old_ts)

        mft = MagicMock()
        mft.search.side_effect = [
            [],          # hot 查询
            [warm_mem],  # warm 查询
        ]
        mft.update.return_value = True

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats["hot_to_warm"] == 0
        assert stats["warm_archived"] == 1
        mft.update.assert_called_with("/dialog/warm/old_msg", status="archived")

    @patch("diting.dialog_manager.datetime")
    def test_archive_warm_not_expired(self, mock_dt):
        """温数据未超过 30 天 → 不归档"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        recent_ts = (now - timedelta(days=15)).isoformat()  # 15天前 → 未过期
        warm_mem = self._make_memory("/dialog/warm/recent_msg", recent_ts)

        mft = MagicMock()
        mft.search.side_effect = [[], [warm_mem]]

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats["warm_archived"] == 0
        mft.update.assert_not_called()

    @patch("diting.dialog_manager.datetime")
    def test_archive_mixed(self, mock_dt):
        """混合场景：热→温 + 温→归档"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        hot_old = self._make_memory(
            "/dialog/hot/s1/old1", (now - timedelta(days=10)).isoformat(), "content1"
        )
        hot_new = self._make_memory(
            "/dialog/hot/s1/new1", (now - timedelta(days=2)).isoformat(), "content2"
        )
        warm_old = self._make_memory(
            "/dialog/warm/old_w1", (now - timedelta(days=40)).isoformat(), "content3"
        )
        warm_new = self._make_memory(
            "/dialog/warm/new_w1", (now - timedelta(days=10)).isoformat(), "content4"
        )

        mft = MagicMock()
        mft.search.side_effect = [
            [hot_old, hot_new],     # hot 查询
            [warm_old, warm_new],   # warm 查询
        ]
        mft.create.return_value = True
        mft.update.return_value = True
        mft.read.return_value = {"content": "dummy"}

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats["hot_to_warm"] == 1
        assert stats["warm_archived"] == 1

    @patch("diting.dialog_manager.datetime")
    def test_archive_empty(self, mock_dt):
        """无数据时返回零统计"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        mft = MagicMock()
        mft.search.side_effect = [[], []]

        manager = DialogManager(mft)
        stats = manager.archive_old_dialogs()

        assert stats == {"hot_to_warm": 0, "warm_archived": 0}

    @patch("diting.dialog_manager.datetime")
    def test_no_memories_deleted(self, mock_dt):
        """核心原则：归档不删除，mft.delete 不应被调用"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        hot_old = self._make_memory(
            "/dialog/hot/s1/old1", (now - timedelta(days=10)).isoformat()
        )
        warm_old = self._make_memory(
            "/dialog/warm/old_w1", (now - timedelta(days=40)).isoformat()
        )

        mft = MagicMock()
        mft.search.side_effect = [[hot_old], [warm_old]]
        mft.create.return_value = True
        mft.update.return_value = True
        mft.read.return_value = {"content": "x"}

        manager = DialogManager(mft)
        manager.archive_old_dialogs()

        mft.delete.assert_not_called()

    @patch("diting.dialog_manager.datetime")
    def test_cleanup_alias_calls_archive(self, mock_dt):
        """cleanup_old_dialogs 兼容别名内部调用 archive_old_dialogs"""
        now = datetime(2026, 5, 8, 12, 0, 0)
        mock_dt.now.return_value = now

        mft = MagicMock()
        mft.search.side_effect = [[], []]

        manager = DialogManager(mft)
        stats = manager.cleanup_old_dialogs()

        assert "hot_to_warm" in stats
        assert "warm_archived" in stats
        assert stats == {"hot_to_warm": 0, "warm_archived": 0}


class TestDialogManagerSearch:
    """搜索测试"""

    def test_search_dialogs_all_scope(self):
        """测试全范围搜索"""
        mft = MagicMock()
        mft.search.return_value = [{"path": "/test", "content": "match"}]
        manager = DialogManager(mft)
        
        results = manager.search_dialogs("query", scope="all")
        
        assert len(results) >= 0
        assert mft.search.call_count == 3  # hot, warm, cold

    def test_search_dialogs_hot_scope(self):
        """测试热数据范围搜索"""
        mft = MagicMock()
        mft.search.return_value = []
        manager = DialogManager(mft)
        
        results = manager.search_dialogs("query", scope="hot")
        
        assert mft.search.call_count == 1

    def test_search_dialogs_warm_scope(self):
        """测试温数据范围搜索"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        manager.search_dialogs("query", scope="warm")
        
        assert mft.search.call_count == 1

    def test_search_dialogs_cold_scope(self):
        """测试冷数据范围搜索"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        manager.search_dialogs("query", scope="cold")
        
        assert mft.search.call_count == 1

    def test_search_dialogs_no_results(self):
        """测试搜索无结果"""
        mft = MagicMock()
        mft.search.return_value = []
        manager = DialogManager(mft)
        
        results = manager.search_dialogs("nonexistent")
        
        assert results == []


class TestDialogManagerHistory:
    """历史记录测试"""

    def test_get_dialog_history(self):
        """测试获取对话历史"""
        mft = MagicMock()
        mft.search.return_value = [
            {"create_ts": "20260420_100000", "content": "msg1"},
            {"create_ts": "20260420_110000", "content": "msg2"}
        ]
        manager = DialogManager(mft)
        
        history = manager.get_dialog_history("session1", days=7)
        
        assert len(history) == 2
        # 应该按时间排序
        assert history[0]["create_ts"] < history[1]["create_ts"]

    def test_get_dialog_history_empty(self):
        """测试空历史"""
        mft = MagicMock()
        mft.search.return_value = []
        manager = DialogManager(mft)
        
        history = manager.get_dialog_history("nonexistent")
        
        assert history == []


class TestDialogManagerStats:
    """统计测试"""

    def test_get_stats(self):
        """测试获取统计信息"""
        mft = MagicMock()
        manager = DialogManager(mft)
        
        stats = manager.get_stats()
        
        assert stats["hot_path"] == "/dialog/hot"
        assert stats["warm_path"] == "/dialog/warm"
        assert stats["cold_path"] == "/dialog/cold"
        assert stats["hot_days"] == 7
        assert stats["warm_days"] == 30
