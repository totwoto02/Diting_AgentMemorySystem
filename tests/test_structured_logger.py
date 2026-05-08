"""
Structured Logger 结构化日志器测试用例
"""

import json
import logging
import pytest

from diting.structured_logger import (
    StructuredFormatter,
    StructuredLogger,
    _STANDARD_RECORD_FIELDS,
)


class TestStructuredFormatter:
    """StructuredFormatter 格式化器测试"""

    def test_format_returns_valid_json(self):
        """format() 输出可解析的 JSON"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "hello world"
        assert "timestamp" in data

    def test_format_includes_extra_fields(self):
        """format() 保留通过 extra 传入的自定义字段"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="op",
            args=(),
            exc_info=None,
        )
        record.operation = "memory_access"
        record.memory_id = "mem_001"
        record.custom_field = 42

        result = formatter.format(record)
        data = json.loads(result)

        assert data["operation"] == "memory_access"
        assert data["memory_id"] == "mem_001"
        assert data["custom_field"] == 42

    def test_format_excludes_standard_record_fields(self):
        """format() 不输出标准 LogRecord 内部字段"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="t",
            level=logging.WARNING,
            pathname="t.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)

        # 标准字段不应出现在输出中
        for field in ("pathname", "lineno", "filename", "module", "funcName",
                      "thread", "threadName", "process", "processName"):
            assert field not in data

    def test_format_with_exception(self):
        """format() 附带异常信息时输出 exception 字段"""
        formatter = StructuredFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="t",
            level=logging.ERROR,
            pathname="t.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert "ValueError: boom" in data["exception"]

    def test_format_handles_string_values(self):
        """format() 正确处理 __dict__ 中以 _ 开头的字段（不输出）"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname="t.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record._private = "should_not_appear"

        result = formatter.format(record)
        data = json.loads(result)

        assert "_private" not in data


class TestStructuredLoggerInit:
    """StructuredLogger 初始化测试"""

    def test_init_default(self):
        """默认初始化不报错"""
        logger = StructuredLogger("test.default")
        assert logger.name == "test.default"
        assert logger.logger is not None

    def test_init_with_config_level(self):
        """配置 level 生效"""
        logger = StructuredLogger("test.level", config={"level": "DEBUG"})
        assert logger.logger.level == logging.DEBUG

    def test_init_with_file_handler(self, tmp_path):
        """配置 file 时添加 FileHandler"""
        log_file = str(tmp_path / "test.log")
        logger = StructuredLogger("test.file", config={"file": log_file})
        file_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_init_no_duplicate_handlers(self):
        """多次初始化同名 logger 不重复添加 handler"""
        logger1 = StructuredLogger("test.dup")
        handler_count = len(logger1.logger.handlers)
        logger2 = StructuredLogger("test.dup")
        assert len(logger2.logger.handlers) == handler_count

    def test_init_propagate_false(self):
        """logger.propagate 设为 False，避免向上冒泡"""
        logger = StructuredLogger("test.prop")
        assert logger.logger.propagate is False


class TestStructuredLoggerLogOperation:
    """log_operation() 测试"""

    def test_log_operation_basic(self, capsys):
        """log_operation() 输出包含 operation 字段的 JSON"""
        logger = StructuredLogger("test.op")
        logger.log_operation("create_memory", path="/user/pref")

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert data["operation"] == "create_memory"
        assert data["path"] == "/user/pref"
        assert data["level"] == "INFO"

    def test_log_operation_with_extra_kwargs(self, capsys):
        """log_operation() 传递多个额外字段"""
        logger = StructuredLogger("test.op2")
        logger.log_operation("search", query="hello", count=5)

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert data["query"] == "hello"
        assert data["count"] == 5


class TestStructuredLoggerLogMemoryAccess:
    """log_memory_access() 测试"""

    def test_log_memory_access_basic(self, capsys):
        """log_memory_access() 输出 memory_access 操作日志"""
        logger = StructuredLogger("test.ma")
        logger.log_memory_access("mem_001", "read")

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert data["operation"] == "memory_access"
        assert data["memory_id"] == "mem_001"
        assert data["action"] == "read"

    def test_log_memory_access_with_user(self, capsys):
        """log_memory_access() 带 user 参数"""
        logger = StructuredLogger("test.ma2")
        logger.log_memory_access("mem_002", "write", user="user_001")

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert data["user"] == "user_001"

    def test_log_memory_access_without_user(self, capsys):
        """log_memory_access() 不传 user 时不出现在输出中"""
        logger = StructuredLogger("test.ma3")
        logger.log_memory_access("mem_003", "delete")

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert "user" not in data


class TestStructuredLoggerLogSearch:
    """log_search() 测试"""

    def test_log_search_basic(self, capsys):
        """log_search() 输出搜索操作日志"""
        logger = StructuredLogger("test.search")
        logger.log_search("hello", result_count=10, duration_ms=12.34)

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert data["operation"] == "search"
        assert data["query"] == "hello"
        assert data["result_count"] == 10
        assert data["duration_ms"] == pytest.approx(12.34)

    def test_log_search_message_format(self, capsys):
        """log_search() 消息包含查询、结果数和耗时"""
        logger = StructuredLogger("test.search2")
        logger.log_search("test", result_count=3, duration_ms=5.0)

        captured = capsys.readouterr()
        data = json.loads(captured.err.strip())

        assert "test" in data["message"]
        assert "3" in data["message"]
        assert "5.00ms" in data["message"]


class TestStructuredLoggerFileOutput:
    """文件输出测试"""

    def test_log_writes_to_file(self, tmp_path):
        """日志正确写入文件，每行是合法 JSON"""
        log_file = str(tmp_path / "output.log")
        logger = StructuredLogger("test.file_out", config={"file": log_file})
        logger.log_operation("file_test", key="value")

        # 刷新 handler
        for handler in logger.logger.handlers:
            handler.flush()

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) >= 1
        data = json.loads(lines[-1])
        assert data["operation"] == "file_test"
        assert data["key"] == "value"


class TestStandardRecordFields:
    """_STANDARD_RECORD_FIELDS 辅助集合测试"""

    def test_contains_expected_fields(self):
        """标准字段集合包含常见 LogRecord 属性"""
        expected = {"message", "msg", "args", "levelname", "levelno",
                    "pathname", "filename", "module", "funcName", "lineno"}
        assert expected.issubset(_STANDARD_RECORD_FIELDS)

    def test_is_frozen_set(self):
        """_STANDARD_RECORD_FIELDS 是 frozenset"""
        assert isinstance(_STANDARD_RECORD_FIELDS, frozenset)
