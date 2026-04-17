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
