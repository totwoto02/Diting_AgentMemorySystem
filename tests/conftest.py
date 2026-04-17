"""
pytest 配置和共享 fixtures
"""

import pytest
import tempfile
import os
from pathlib import Path

from diting.mft import MFT
from diting.database import Database
from diting.config import Config


@pytest.fixture
def temp_db():
    """
    创建临时数据库用于测试
    
    Usage:
        def test_something(temp_db):
            mft = MFT(temp_db)
            # ...
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # 清理临时文件
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def memory_mft():
    """
    创建内存 MFT 实例用于测试
    每个测试使用独立的内存数据库
    
    Usage:
        def test_something(memory_mft):
            inode = memory_mft.create(...)
            # ...
    """
    # 使用唯一标识创建独立的内存数据库
    import uuid
    db_uri = f"file:memdb_{uuid.uuid4().hex}?mode=memory&cache=private"
    mft = MFT(db_uri)
    yield mft
    mft.close()


@pytest.fixture
def temp_mft(temp_db):
    """
    创建临时文件 MFT 实例用于测试
    
    Usage:
        def test_something(temp_mft):
            inode = temp_mft.create(...)
            # ...
    """
    mft = MFT(temp_db)
    yield mft
    mft.close()


@pytest.fixture
def sample_memory_data():
    """示例记忆数据"""
    return {
        "path": "/test/sample",
        "type": "NOTE",
        "content": "这是一条测试记忆"
    }
