"""
Batch Processor 批量处理器测试用例

目标：覆盖率 78% → 90%+
"""

import math
import pytest
import tempfile
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from diting.batch_processor import BatchProcessor, BatchTask


class TestBatchTask:
    """批量任务数据类测试"""

    def test_batch_task_creation(self):
        """测试任务创建"""
        from datetime import datetime
        task = BatchTask(
            id="task_001",
            task_type="test",
            priority=5,
            data={"key": "value"},
            created_at=datetime.now()
        )
        
        assert task.id == "task_001"
        assert task.task_type == "test"
        assert task.priority == 5
        assert task.data == {"key": "value"}

    def test_batch_task_comparison(self):
        """测试任务优先级比较"""
        from datetime import datetime
        task1 = BatchTask(
            id="task_1",
            task_type="test",
            priority=10,
            data={},
            created_at=datetime.now()
        )
        task2 = BatchTask(
            id="task_2",
            task_type="test",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        # 优先级高的应该排在前面
        assert task1 < task2


class TestBatchProcessorInit:
    """初始化测试"""

    def test_init_default(self, tmp_path):
        """测试默认初始化"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        assert processor.batch_size == 50
        assert processor.process_interval == 300
        assert processor.running is True
        
        processor.stop()

    def test_init_with_config(self, tmp_path):
        """测试自定义配置初始化"""
        db_path = str(tmp_path / "batch.db")
        config = {
            'BATCH_SIZE': 100,
            'PROCESS_INTERVAL': 600
        }
        processor = BatchProcessor(db_path, config)
        
        assert processor.batch_size == 100
        assert processor.process_interval == 600
        
        processor.stop()


class TestBatchProcessorEnqueue:
    """任务入队测试"""

    def test_enqueue(self, tmp_path):
        """测试入队任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        # enqueue 返回 None，但会在数据库创建任务
        result = processor.enqueue(
            "task_001",
            "test",
            {"key": "value"},
            priority=5
        )
        
        # enqueue 返回 None，但任务已入队
        assert result is None
        
        # 验证任务在队列中
        status = processor.get_queue_status()
        assert status["pending"] >= 1
        
        processor.stop()

    def test_enqueue_high_priority(self, tmp_path):
        """测试入队高优先级任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        result = processor.enqueue(
            "task_urgent",
            "urgent",
            {},
            priority=100
        )
        
        assert result is None
        
        status = processor.get_queue_status()
        assert status["pending"] >= 1
        
        processor.stop()

    def test_enqueue_empty_data(self, tmp_path):
        """测试入队空数据任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        result = processor.enqueue(
            "task_empty",
            "test",
            {}
        )
        
        assert result is None
        
        status = processor.get_queue_status()
        assert status["pending"] >= 1
        
        processor.stop()


class TestBatchProcessorDequeue:
    """任务出队测试"""

    def test_dequeue_batch(self, tmp_path):
        """测试批量出队"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        # 入队一些任务
        for i in range(5):
            processor.enqueue(f"task_{i}", "test", {"index": i})
        
        # 出队
        batch = processor.dequeue_batch(batch_size=3)
        
        assert len(batch) <= 3
        
        processor.stop()

    def test_dequeue_empty_queue(self, tmp_path):
        """测试空队列出队"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        batch = processor.dequeue_batch(batch_size=5)
        
        assert len(batch) == 0
        
        processor.stop()


class TestBatchProcessorProcess:
    """任务处理测试"""

    def test_process_batch(self, tmp_path):
        """测试处理批量任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        # 入队任务
        processor.enqueue("task_1", "test", {"data": "value"})
        
        # 出队
        batch = processor.dequeue_batch(batch_size=1)
        
        if batch:
            # 定义一个简单的处理器
            def simple_processor(task):
                return {"processed": True}
            
            # 处理批次
            result = processor.process_batch(batch, simple_processor)
            
            assert isinstance(result, dict)
        
        processor.stop()

    def test_complete_task(self, tmp_path):
        """测试完成任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        processor.enqueue("task_1", "test", {})
        
        processor.complete_task("task_1", result={"success": True})
        
        processor.stop()

    def test_complete_task_with_error(self, tmp_path):
        """测试完成任务（带错误）"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        processor.enqueue("task_1", "test", {})
        
        processor.complete_task(
            "task_1",
            result=None,
            error="Test error"
        )
        
        processor.stop()


class TestBatchProcessorQueue:
    """队列管理测试"""

    def test_get_queue_status(self, tmp_path):
        """测试获取队列状态"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        # 入队一些任务
        processor.enqueue("task_1", "type1", {}, 0)
        processor.enqueue("task_2", "type1", {}, 0)
        processor.enqueue("task_3", "type2", {}, 0)
        
        status = processor.get_queue_status()
        
        # 状态包含 pending, processing, completed, failed
        assert "pending" in status
        assert status["pending"] >= 3
        
        processor.stop()

    def test_get_batch_history(self, tmp_path):
        """测试获取批量历史"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        history = processor.get_batch_history()
        
        assert isinstance(history, list)
        
        processor.stop()


class TestBatchProcessorEdgeCases:
    """边界条件测试"""

    def test_stop_processor(self, tmp_path):
        """测试停止处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        processor.stop()
        
        assert processor.running is False

    def test_multiple_enqueue_same_type(self, tmp_path):
        """测试多个同类型任务"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        for i in range(10):
            processor.enqueue(f"task_{i}", "same_type", {"index": i}, 0)
        
        status = processor.get_queue_status()
        assert status["pending"] >= 10
        
        processor.stop()

    def test_large_data_enqueue(self, tmp_path):
        """测试大数据入队"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        large_data = {"data": "A" * 10000}
        result = processor.enqueue("task_large", "test", large_data, 0)
        
        assert result is None
        
        status = processor.get_queue_status()
        assert status["pending"] >= 1
        
        processor.stop()

    def test_close(self, tmp_path):
        """测试关闭处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path)
        
        processor.enqueue("task_1", "test", {}, 0)
        
        processor.close()


_FAST_CONFIG = {"PROCESS_INTERVAL": 1}


class TestProcessAiSummary:
    """AI 摘要处理测试"""

    def _make_task(self, content=""):
        return BatchTask(
            id="test_ai",
            task_type="ai_summary",
            priority=0,
            data={"content": content},
            created_at=datetime.now(),
        )

    def test_short_content(self, tmp_path):
        """测试短内容（< 200 字符）直接返回"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            short = "Hello world"
            task = self._make_task(content=short)
            result = processor._process_ai_summary(task)

            assert result["status"] == "processed"
            assert result["summary"] == short
            assert "..." not in result["summary"]
        finally:
            processor.stop()

    def test_long_content(self, tmp_path):
        """测试长内容（> 200 字符）截断并加省略号"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            long_content = "A" * 300
            task = self._make_task(content=long_content)
            result = processor._process_ai_summary(task)

            assert result["status"] == "processed"
            assert result["summary"] == "A" * 200 + "..."
            assert len(result["summary"]) == 203  # 200 + len("...")
        finally:
            processor.stop()

    def test_empty_content(self, tmp_path):
        """测试空内容返回 no_content"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(content="")
            result = processor._process_ai_summary(task)

            assert result["status"] == "no_content"
            assert result["summary"] == ""
        finally:
            processor.stop()

    def test_missing_content_key(self, tmp_path):
        """测试缺少 content 键返回 no_content"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="test_ai",
                task_type="ai_summary",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            result = processor._process_ai_summary(task)

            assert result["status"] == "no_content"
            assert result["summary"] == ""
        finally:
            processor.stop()

    def test_exact_200_chars(self, tmp_path):
        """测试恰好 200 字符不截断"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            content = "B" * 200
            task = self._make_task(content=content)
            result = processor._process_ai_summary(task)

            assert result["status"] == "processed"
            assert result["summary"] == content
            assert "..." not in result["summary"]
        finally:
            processor.stop()


class TestProcessEntropyCalc:
    """熵值计算处理测试"""

    def _make_task(self, content=""):
        return BatchTask(
            id="test_entropy",
            task_type="entropy_calc",
            priority=0,
            data={"content": content},
            created_at=datetime.now(),
        )

    def test_uniform_text_low_entropy(self, tmp_path):
        """测试均匀文本（重复字符）→ 低熵"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # 全是同一个字符 → 熵为 0（只有一种字符）
            task = self._make_task(content="AAAAAAAAAA")
            result = processor._process_entropy_calc(task)

            assert result["status"] == "processed"
            assert result["entropy"] == 0.0
        finally:
            processor.stop()

    def test_varied_text_high_entropy(self, tmp_path):
        """测试多样文本 → 高熵"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # 每个字符都不同 → 高熵
            content = "abcdefghij"
            task = self._make_task(content=content)
            result = processor._process_entropy_calc(task)

            assert result["status"] == "processed"
            # 每个字符出现一次，均匀分布，熵应接近 1.0
            assert result["entropy"] > 0.9
        finally:
            processor.stop()

    def test_empty_content(self, tmp_path):
        """测试空内容返回 no_content"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(content="")
            result = processor._process_entropy_calc(task)

            assert result["status"] == "no_content"
            assert result["entropy"] == 0.0
        finally:
            processor.stop()

    def test_moderate_entropy(self, tmp_path):
        """测试中等熵值"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # A 和 B 各 50% → 熵约 1.0（两种等概率字符）
            content = "ABABABABAB"
            task = self._make_task(content=content)
            result = processor._process_entropy_calc(task)

            assert result["status"] == "processed"
            assert 0.0 <= result["entropy"] <= 1.0
        finally:
            processor.stop()

    def test_entropy_normalized_range(self, tmp_path):
        """测试熵值在 [0, 1] 范围内"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # 各种输入都应返回 [0, 1] 范围的熵值
            for content in ["a", "abc", "aabbc", "xyz123!@#"]:
                task = self._make_task(content=content)
                result = processor._process_entropy_calc(task)

                assert result["status"] == "processed"
                assert 0.0 <= result["entropy"] <= 1.0
        finally:
            processor.stop()


class TestProcessTempCalc:
    """温度计算处理测试"""

    def _make_task(self, access_count=0, last_access_hours=0, round_count=0):
        return BatchTask(
            id="test_temp",
            task_type="temp_calc",
            priority=0,
            data={
                "access_count": access_count,
                "last_access_hours": last_access_hours,
                "round_count": round_count,
            },
            created_at=datetime.now(),
        )

    def test_basic_temperature(self, tmp_path):
        """测试基本温度计算"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(
                access_count=500,
                last_access_hours=24,
                round_count=1,
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            assert 0.0 <= result["temperature"] <= 1.0
        finally:
            processor.stop()

    def test_high_access_recent(self, tmp_path):
        """测试高访问 + 近期访问 → 高温度"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(
                access_count=1000,
                last_access_hours=0,
                round_count=0,
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            # (1000/1000) * exp(0) * 1/(1+0) = 1.0 * 1.0 * 1.0 = 1.0
            assert result["temperature"] == 1.0
        finally:
            processor.stop()

    def test_zero_access(self, tmp_path):
        """测试零访问 → 温度为 0"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(
                access_count=0,
                last_access_hours=100,
                round_count=5,
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            assert result["temperature"] == 0.0
        finally:
            processor.stop()

    def test_old_access_decays(self, tmp_path):
        """测试旧访问时间 → 温度衰减"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # 非常久没访问 → exp(-large/168) ≈ 0
            task = self._make_task(
                access_count=1000,
                last_access_hours=10000,
                round_count=0,
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            assert result["temperature"] < 0.01  # 接近 0
        finally:
            processor.stop()

    def test_high_round_count_reduces(self, tmp_path):
        """测试高轮次 → 温度降低"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task_low_round = self._make_task(
                access_count=500, last_access_hours=0, round_count=0
            )
            task_high_round = self._make_task(
                access_count=500, last_access_hours=0, round_count=100
            )
            result_low = processor._process_temp_calc(task_low_round)
            result_high = processor._process_temp_calc(task_high_round)

            assert result_low["temperature"] > result_high["temperature"]
        finally:
            processor.stop()

    def test_clamped_to_max_1(self, tmp_path):
        """测试温度被 clamp 到最大值 1.0"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            # access_count > 1000 且 round_count=0, recent → 可能 > 1，但应被 clamp
            task = self._make_task(
                access_count=5000,
                last_access_hours=0,
                round_count=0,
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            assert result["temperature"] <= 1.0
        finally:
            processor.stop()

    def test_missing_data_keys(self, tmp_path):
        """测试缺少数据键 → 默认值 0"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="test_temp",
                task_type="temp_calc",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            result = processor._process_temp_calc(task)

            assert result["status"] == "processed"
            # 所有默认值为 0 → temperature = 0
            assert result["temperature"] == 0.0
        finally:
            processor.stop()


class TestProcessFileFreeze:
    """文件冻结处理测试"""

    def _make_task(self, status="archived", file_id="file_001"):
        return BatchTask(
            id="test_freeze",
            task_type="file_cleanup",
            priority=0,
            data={"status": status, "file_id": file_id},
            created_at=datetime.now(),
        )

    def test_archived_should_freeze(self, tmp_path):
        """测试 archived 状态文件应被冻结"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(status="archived", file_id="file_123")
            result = processor._process_file_freeze(task)

            assert result["status"] == "frozen"
            assert result["file_id"] == "file_123"
        finally:
            processor.stop()

    def test_active_should_skip(self, tmp_path):
        """测试 active 状态文件应跳过"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(status="active", file_id="file_456")
            result = processor._process_file_freeze(task)

            assert result["status"] == "skipped"
            assert result["reason"] == "not_archived"
        finally:
            processor.stop()

    def test_other_status_should_skip(self, tmp_path):
        """测试非 archived 状态均跳过"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            for status in ["active", "draft", "pending", "deleted"]:
                task = self._make_task(status=status)
                result = processor._process_file_freeze(task)

                assert result["status"] == "skipped"
                assert result["reason"] == "not_archived"
        finally:
            processor.stop()

    def test_missing_status_should_skip(self, tmp_path):
        """测试缺少 status 字段应跳过"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="test_freeze",
                task_type="file_cleanup",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            result = processor._process_file_freeze(task)

            assert result["status"] == "skipped"
            assert result["reason"] == "not_archived"
        finally:
            processor.stop()


class TestRetryWithBackoff:
    """重试机制测试"""

    def test_success_on_first_try(self, tmp_path):
        """测试首次成功 → 无重试"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="retry_test",
                task_type="test",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            handler = MagicMock(return_value={"status": "ok"})

            with patch("diting.batch_processor.time.sleep") as mock_sleep:
                result = processor._retry_with_backoff(handler, task)

            assert result == {"status": "ok"}
            handler.assert_called_once_with(task)
            mock_sleep.assert_not_called()
        finally:
            processor.stop()

    def test_success_after_retry(self, tmp_path):
        """测试重试后成功"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="retry_test",
                task_type="test",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            # 前两次失败，第三次成功
            handler = MagicMock(
                side_effect=[ValueError("fail 1"), ValueError("fail 2"), {"status": "ok"}]
            )

            with patch("diting.batch_processor.time.sleep") as mock_sleep:
                result = processor._retry_with_backoff(handler, task)

            assert result == {"status": "ok"}
            assert handler.call_count == 3
            # 验证 sleep 被调用两次（第 1、2 次失败后）
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)  # 第一次退避
            mock_sleep.assert_any_call(2)  # 第二次退避
        finally:
            processor.stop()

    def test_failure_after_max_retries(self, tmp_path):
        """测试超过最大重试次数 → 抛出异常"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="retry_test",
                task_type="test",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            handler = MagicMock(side_effect=RuntimeError("persistent failure"))

            with patch("diting.batch_processor.time.sleep") as mock_sleep:
                with pytest.raises(RuntimeError, match="persistent failure"):
                    processor._retry_with_backoff(handler, task)

            assert handler.call_count == 3  # max_retries=3
            # sleep 被调用 2 次（最后一次失败不 sleep）
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)
        finally:
            processor.stop()

    def test_custom_max_retries(self, tmp_path):
        """测试自定义最大重试次数"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="retry_test",
                task_type="test",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            handler = MagicMock(side_effect=ValueError("fail"))

            with patch("diting.batch_processor.time.sleep"):
                with pytest.raises(ValueError):
                    processor._retry_with_backoff(handler, task, max_retries=1)

            handler.assert_called_once()
        finally:
            processor.stop()

    def test_backoff_sequence(self, tmp_path):
        """测试退避序列 [1, 2, 4]"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = BatchTask(
                id="retry_test",
                task_type="test",
                priority=0,
                data={},
                created_at=datetime.now(),
            )
            handler = MagicMock(side_effect=ValueError("fail"))

            with patch("diting.batch_processor.time.sleep") as mock_sleep:
                with pytest.raises(ValueError):
                    processor._retry_with_backoff(handler, task, max_retries=3)

            # 验证退避序列
            sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
            assert sleep_calls == [1, 2]
        finally:
            processor.stop()


class TestDefaultProcessor:
    """默认处理器分发测试"""

    def _make_task(self, task_type, data):
        return BatchTask(
            id="dispatch_test",
            task_type=task_type,
            priority=0,
            data=data,
            created_at=datetime.now(),
        )

    def test_dispatch_ai_summary(self, tmp_path):
        """测试分发到 ai_summary 处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task("ai_summary", {"content": "test content"})
            result = processor._default_processor(task)

            assert result["status"] == "processed"
            assert result["summary"] == "test content"
        finally:
            processor.stop()

    def test_dispatch_entropy_calc(self, tmp_path):
        """测试分发到 entropy_calc 处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task("entropy_calc", {"content": "hello"})
            result = processor._default_processor(task)

            assert result["status"] == "processed"
            assert "entropy" in result
        finally:
            processor.stop()

    def test_dispatch_temp_calc(self, tmp_path):
        """测试分发到 temp_calc 处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(
                "temp_calc",
                {"access_count": 100, "last_access_hours": 10, "round_count": 1},
            )
            result = processor._default_processor(task)

            assert result["status"] == "processed"
            assert "temperature" in result
        finally:
            processor.stop()

    def test_dispatch_file_cleanup(self, tmp_path):
        """测试分发到 file_cleanup 处理器"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task(
                "file_cleanup",
                {"status": "archived", "file_id": "f1"},
            )
            result = processor._default_processor(task)

            assert result["status"] == "frozen"
        finally:
            processor.stop()

    def test_unknown_task_type(self, tmp_path):
        """测试未知任务类型返回 unknown_task_type"""
        db_path = str(tmp_path / "batch.db")
        processor = BatchProcessor(db_path, _FAST_CONFIG)
        try:
            task = self._make_task("nonexistent_type", {"data": "value"})
            result = processor._default_processor(task)

            assert result == {"status": "unknown_task_type"}
        finally:
            processor.stop()
