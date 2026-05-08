"""
结构化日志系统

输出 JSON 格式的结构化日志，支持自定义字段、操作追踪和审计分析。
Structured logging system that outputs JSON-formatted logs with custom fields,
operation tracing, and audit analysis support.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional


# logging.LogRecord 的标准内部字段，不作为 extra 输出
# Standard internal fields of logging.LogRecord, excluded from extra output
_STANDARD_RECORD_FIELDS: frozenset = frozenset({
    "message",
    "msg",
    "args",
    "created",
    "relativeCreated",
    "exc_info",
    "exc_text",
    "stack_info",
    "stack_info_offset",
    "lineno",
    "funcName",
    "pathname",
    "filename",
    "module",
    "levelno",
    "levelname",
    "msecs",
    "thread",
    "threadName",
    "processName",
    "process",
    "name",
    "taskName",
})


class StructuredFormatter(logging.Formatter):
    """
    结构化 JSON 日志格式化器

    将日志记录转换为 JSON 字符串，包含时间戳、级别、日志名、消息，
    以及所有通过 extra 传入的自定义字段。

    Structured JSON log formatter that converts log records to JSON strings,
    including timestamp, level, logger name, message, and all custom fields
    passed via extra.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为 JSON 字符串

        Format a log record as a JSON string.

        Args:
            record: 日志记录对象 / The log record to format

        Returns:
            JSON 格式的日志字符串 / JSON-formatted log string
        """
        log_entry: Dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 收集所有非标准字段作为 extra / Collect all non-standard fields as extra
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_"):
                log_entry[key] = value

        # 附加异常信息 / Attach exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredLogger:
    """
    结构化日志器

    封装 Python 标准 logging 模块，提供 JSON 格式输出和业务级日志方法。
    支持控制台和文件输出，适用于操作审计、记忆访问追踪和搜索分析。

    Structured logger wrapping Python's standard logging module to provide
    JSON-formatted output and business-level logging methods. Supports console
    and file output, suitable for operation auditing, memory access tracing,
    and search analysis.
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        初始化结构化日志器

        Initialize the structured logger.

        Args:
            name: 日志器名称 / Logger name
            config: 配置字典，支持以下可选键 / Configuration dict with optional keys:
                - level (str): 日志级别，默认 "INFO" / Log level, default "INFO"
                - file (str): 日志文件路径 / Log file path
        """
        self.name = name
        self.config = config or {}

        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.config.get("level", "INFO").upper()))
        self.logger.propagate = False

        # 避免重复添加 handler / Avoid duplicate handlers
        if not self.logger.handlers:
            formatter = StructuredFormatter()

            # 控制台输出 / Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # 文件输出（可选）/ File handler (optional)
            log_file = self.config.get("file")
            if log_file:
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

    def log_operation(self, operation: str, **kwargs) -> None:
        """
        记录操作日志

        Log an operation with custom fields.

        Args:
            operation: 操作名称 / Operation name
            **kwargs: 附加字段 / Additional fields
        """
        self.logger.info(operation, extra={"operation": operation, **kwargs})

    def log_memory_access(
        self, memory_id: str, action: str, user: Optional[str] = None
    ) -> None:
        """
        记忆访问日志

        Log a memory access event.

        Args:
            memory_id: 记忆标识 / Memory identifier
            action: 访问动作（read/write/delete/search）/ Access action
            user: 操作用户 / User performing the action
        """
        extra: Dict = {
            "operation": "memory_access",
            "memory_id": memory_id,
            "action": action,
        }
        if user is not None:
            extra["user"] = user

        self.logger.info(
            f"memory_access: {action} {memory_id}",
            extra=extra,
        )

    def log_search(
        self, query: str, result_count: int, duration_ms: float
    ) -> None:
        """
        搜索日志

        Log a search operation with performance metrics.

        Args:
            query: 搜索查询 / Search query
            result_count: 结果数量 / Number of results
            duration_ms: 耗时（毫秒）/ Duration in milliseconds
        """
        self.logger.info(
            f"search: '{query}' -> {result_count} results in {duration_ms:.2f}ms",
            extra={
                "operation": "search",
                "query": query,
                "result_count": result_count,
                "duration_ms": duration_ms,
            },
        )


# 使用示例 / Usage example
if __name__ == "__main__":
    # 创建结构化日志器 / Create structured logger
    logger = StructuredLogger("diting.test")

    # 记录操作日志 / Log an operation
    logger.log_operation("create_memory", path="/user/preferences", type="NOTE")

    # 记录记忆访问 / Log memory access
    logger.log_memory_access("mem_001", "read", user="user_001")

    # 记录搜索 / Log search
    logger.log_search("preferences", result_count=5, duration_ms=12.34)

    # 带文件输出的结构化日志器 / Logger with file output
    # file_logger = StructuredLogger("diting.file", config={"level": "DEBUG", "file": "diting.log"})
    # file_logger.log_operation("test_op", detail="with file output")
