"""
自定义异常模块
"""


class MFSException(Exception):
    """MFS 基础异常"""

    pass


class MFTException(MFSException):
    """MFT 操作异常"""

    pass


class MFTNotFoundError(MFTException):
    """MFT 条目未找到"""

    pass


class MFTAlreadyExistsError(MFTException):
    """MFT 条目已存在"""

    pass


class MFTInvalidPathError(MFTException):
    """MFT 路径无效"""

    pass


class MCPException(MFSException):
    """MCP 操作异常"""

    pass


class DatabaseException(MFSException):
    """数据库操作异常"""

    pass


class LLMException(MFSException):
    """LLM API 操作异常"""

    pass


class LLMTimeoutError(LLMException):
    """LLM API 超时"""

    pass


class LLMAPIError(LLMException):
    """LLM API 错误响应"""

    pass


class LLMConnectionError(LLMException):
    """LLM API 连接失败"""

    pass


class LLMRateLimitError(LLMException):
    """LLM API 速率限制"""

    pass
