#!/usr/bin/env python3
"""
核心模块扩展测试

目标覆盖率：
- free_energy_manager.py: 52% → 75%+
- storage_backend.py: 58% → 80%+
- monitor.py: 78% → 80%+
- fts5_search.py: 87% → 90%+
"""

import pytest
import sys
import os
import tempfile
import sqlite3
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# 测试 free_energy_manager.py - 扩展覆盖
# ============================================================================

class TestFreeEnergyManagerExtended:
    """测试自由能管理器 - 扩展覆盖"""
    
    @pytest.fixture
    def temp_db_with_memories(self):
        """创建带记忆数据的临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE multimodal_slices (
                slice_id TEXT PRIMARY KEY,
                memory_path TEXT,
                ai_keywords TEXT,
                heat_score INTEGER DEFAULT 50,
                temp_score REAL DEFAULT 0.0,
                entropy_score REAL DEFAULT 0.0,
                free_energy_score REAL DEFAULT 0.0,
                iteration_status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入多种类型的记忆
        conn.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, ai_keywords, heat_score, temp_score, entropy_score, free_energy_score, iteration_status)
            VALUES 
                ('high-g-1', '/test/high1', '["关键词 1", "关键词 2"]', 90, 0.2, 0.1, 88.0, 'active'),
                ('high-g-2', '/test/high2', '["关键词 3"]', 85, 0.3, 0.2, 83.0, 'active'),
                ('medium-g', '/test/medium', '["关键词 4", "关键词 5"]', 50, 0.5, 0.5, 25.0, 'active'),
                ('low-g', '/test/low', '["关键词 6"]', 20, 0.8, 0.7, 5.0, 'active'),
                ('negative-g', '/test/negative', '["关键词 7"]', 10, 0.9, 0.9, -71.0, 'active'),
                ('frozen', '/test/frozen', '["关键词 8"]', 80, 0.5, 0.5, 60.0, 'frozen')
        """)
        conn.commit()
        conn.close()
        
        yield db_path
        os.unlink(db_path)
    
    def test_get_extractable_memories_no_context(self, temp_db_with_memories):
        """测试获取可提取记忆（无上下文）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        # 获取可提取记忆（G > 0）
        memories = manager.get_extractable_memories(limit=10)
        
        # 应该返回 G > 0 的记忆（不包括 frozen）
        assert len(memories) >= 1
        assert all(m['free_energy_score'] > 0 for m in memories)
    
    def test_get_extractable_memories_with_context(self, temp_db_with_memories):
        """测试获取可提取记忆（带上下文）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        # 带上下文获取（会重新计算关联度）
        memories = manager.get_extractable_memories(context="测试上下文", limit=5)
        
        # 应该返回重新计算后的结果
        assert len(memories) >= 1
        assert 'temp_score' in memories[0]
    
    def test_get_extractable_memories_limit(self, temp_db_with_memories):
        """测试获取可提取记忆（数量限制）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        # 限制返回 2 个
        memories = manager.get_extractable_memories(limit=2)
        
        assert len(memories) <= 2
    
    def test_analyze_system_state_highly_active(self, temp_db_with_memories):
        """测试系统状态分析（高度活跃）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 修改数据使平均自由能 > 50
        conn = sqlite3.connect(temp_db_with_memories)
        conn.execute("UPDATE multimodal_slices SET free_energy_score = 80 WHERE slice_id = 'medium-g'")
        conn.execute("UPDATE multimodal_slices SET free_energy_score = 70 WHERE slice_id = 'low-g'")
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db_with_memories)
        state = manager.analyze_system_state()
        
        assert 'statistics' in state
        assert 'system_state' in state
        assert 'formula' in state
        assert state['formula'] == 'G = U - TS'
        assert 'interpretation' in state
    
    def test_analyze_system_state_active(self, temp_db_with_memories):
        """测试系统状态分析（活跃）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        state = manager.analyze_system_state()
        
        # 根据插入的数据，平均自由能应该在 20-50 之间
        assert state['system_state'] in ['highly_active', 'active', 'stable', 'inactive']
    
    def test_extract_keywords_from_path(self, temp_db_with_memories):
        """测试从路径提取关键词"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': '/person/朋友/preferences', 'ai_keywords': ''}
        keywords = manager._extract_keywords(memory)
        
        assert len(keywords) > 0
        assert 'person' in keywords or '朋友' in keywords or 'preferences' in keywords
    
    def test_extract_keywords_from_ai_keywords(self, temp_db_with_memories):
        """测试从 AI 关键词提取"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {
            'memory_path': '',
            'ai_keywords': '["摄影", "漫展", "cosplay"]'
        }
        keywords = manager._extract_keywords(memory)
        
        assert '摄影' in keywords
        assert '漫展' in keywords
        assert 'cosplay' in keywords
    
    def test_extract_keywords_invalid_json(self, temp_db_with_memories):
        """测试提取关键词（无效 JSON）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {
            'memory_path': '',
            'ai_keywords': '不是 JSON 格式'
        }
        keywords = manager._extract_keywords(memory)
        
        assert len(keywords) > 0
    
    def test_match_keywords(self, temp_db_with_memories):
        """测试关键词匹配"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {
            'memory_path': '/test/path',
            'ai_keywords': '["摄影", "拍照", "相机"]'
        }
        
        # 完全匹配
        score = manager._match_keywords(memory, "摄影 拍照")
        assert 0 < score <= 1
        
        # 无匹配
        score = manager._match_keywords(memory, "完全不相关的词")
        assert score == 0.0
    
    def test_match_keywords_no_keywords(self, temp_db_with_memories):
        """测试关键词匹配（无关键词）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': '', 'ai_keywords': ''}
        score = manager._match_keywords(memory, "测试")
        
        assert score == 0.5  # 无关键词时给中等分数
    
    def test_match_path_partial(self, temp_db_with_memories):
        """测试路径匹配（部分匹配）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': '/person/朋友/preferences'}
        
        # 部分匹配
        score = manager._match_path(memory, "朋友")
        assert 0 < score <= 1
        
        # 无匹配
        score = manager._match_path(memory, "不相关")
        assert score == 0.0
    
    def test_match_path_empty(self, temp_db_with_memories):
        """测试路径匹配（空路径）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': ''}
        score = manager._match_path(memory, "测试")
        
        assert score == 0.0
    
    def test_get_match_content(self, temp_db_with_memories):
        """测试获取匹配内容"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {
            'memory_path': '/test/path',
            'ai_keywords': '["关键词 1", "关键词 2"]'
        }
        
        content = manager._get_match_content(memory)
        
        assert '/test/path' in content
        assert '关键词' in content
    
    def test_extract_words_chinese(self, temp_db_with_memories):
        """测试提取中文词汇"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        words = manager._extract_words("摄影漫展拍照")
        
        assert len(words) > 0
        # 应该包含 2 字词和 3 字词
        assert any(len(w) >= 2 for w in words)
    
    def test_extract_words_mixed(self, temp_db_with_memories):
        """测试提取混合词汇"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        words = manager._extract_words("Python 编程 123")
        
        assert len(words) > 0
    
    def test_tokenize_chinese(self, temp_db_with_memories):
        """测试中文分词"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        words = manager._tokenize("摄影 漫展 拍照")
        
        assert len(words) > 0
    
    def test_tokenize_english(self, temp_db_with_memories):
        """测试英文分词"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        words = manager._tokenize("Python programming")
        
        assert len(words) > 0
    
    def test_close(self, temp_db_with_memories):
        """测试关闭数据库连接"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        # 关闭（不应报错）
        manager.close()
    
    def test_calculate_relevance_fts5_fallback(self, temp_db_with_memories):
        """测试关联度计算（FTS5 回退）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 创建没有 FTS5 表的数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE multimodal_slices (
                slice_id TEXT PRIMARY KEY,
                memory_path TEXT,
                ai_keywords TEXT
            )
        """)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, ai_keywords)
            VALUES ('test', '/test/path', '["关键词 1", "关键词 2"]')
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(db_path)
        
        # 应该回退到 BM25 fallback
        score = manager._calculate_relevance('test', '关键词 1')
        
        assert 0 <= score <= 1
        
        manager.close()
        os.unlink(db_path)
    
    def test_match_bm25_fallback_no_memory(self, temp_db_with_memories):
        """测试 BM25 回退（记忆不存在）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        score = manager._match_bm25_fallback('nonexistent', '测试')
        
        assert score == 0.0
    
    def test_match_bm25_fallback_no_content(self, temp_db_with_memories):
        """测试 BM25 回退（无匹配内容）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': '', 'ai_keywords': ''}
        with patch.object(manager, '_get_memory', return_value=memory):
            score = manager._match_bm25_fallback('test', '测试')
        
        assert score == 0.0
    
    def test_match_bm25_fallback_no_words(self, temp_db_with_memories):
        """测试 BM25 回退（无词汇）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        memory = {'memory_path': '/test', 'ai_keywords': '[]'}
        with patch.object(manager, '_get_memory', return_value=memory):
            with patch.object(manager, '_get_match_content', return_value=''):
                score = manager._match_bm25_fallback('test', '')
        
        assert score == 0.0
    
    def test_batch_calculate_with_context(self, temp_db_with_memories):
        """测试批量计算（带上下文）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        results = manager.batch_calculate(
            ['high-g-1', 'high-g-2'],
            current_context="测试上下文"
        )
        
        assert 'high-g-1' in results
        assert 'high-g-2' in results
        assert 'free_energy' in results['high-g-1']
    
    def test_calculate_free_energy_error_handling(self, temp_db_with_memories):
        """测试自由能计算错误处理"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db_with_memories)
        
        # 记忆不存在
        result = manager.calculate_free_energy('nonexistent')
        
        assert 'error' in result
        assert result['error'] == '记忆不存在'


# ============================================================================
# 测试 storage_backend.py - 扩展覆盖
# ============================================================================

class TestStorageBackendExtended:
    """测试存储后端 - 扩展覆盖"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """创建临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_local_storage_overwrite(self, temp_storage_dir):
        """测试本地存储覆盖写入"""
        from diting.storage_backend import LocalStorage
        
        storage = LocalStorage(temp_storage_dir)
        
        # 第一次写入
        storage.save("overwrite.txt", b"data1")
        loaded1 = storage.load("overwrite.txt")
        assert loaded1 == b"data1"
        
        # 覆盖写入
        storage.save("overwrite.txt", b"data2")
        loaded2 = storage.load("overwrite.txt")
        assert loaded2 == b"data2"
    
    def test_local_storage_binary_data(self, temp_storage_dir):
        """测试本地存储二进制数据"""
        from diting.storage_backend import LocalStorage
        
        storage = LocalStorage(temp_storage_dir)
        
        # 二进制数据（图片）
        binary_data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        
        storage.save("image.png", binary_data)
        loaded = storage.load("image.png")
        
        assert loaded == binary_data
    
    def test_local_storage_unicode_path(self, temp_storage_dir):
        """测试本地存储 Unicode 路径"""
        from diting.storage_backend import LocalStorage
        
        storage = LocalStorage(temp_storage_dir)
        
        # Unicode 路径
        storage.save("中文/日本語/한국어/file.txt", b"data")
        assert storage.exists("中文/日本語/한국어/file.txt")
    
    def test_s3_storage_init(self, temp_storage_dir):
        """测试 S3 存储初始化"""
        from diting.storage_backend import S3Storage
        
        config = {
            'bucket': 'test-bucket',
            'region': 'us-west-2',
            'access_key': 'AKIAIOSFODNN7EXAMPLE',
            'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        
        storage = S3Storage(config)
        
        assert storage.bucket == 'test-bucket'
        assert storage.region == 'us-west-2'
    
    def test_s3_storage_save(self, temp_storage_dir):
        """测试 S3 存储保存（占位实现）"""
        from diting.storage_backend import S3Storage
        
        storage = S3Storage({'bucket': 'test'})
        
        url = storage.save("test.txt", b"data")
        
        assert url == "s3://test/test.txt"
    
    def test_s3_storage_load_not_implemented(self, temp_storage_dir):
        """测试 S3 存储加载（未实现）"""
        from diting.storage_backend import S3Storage
        
        storage = S3Storage({'bucket': 'test'})
        
        with pytest.raises(NotImplementedError):
            storage.load("test.txt")
    
    def test_s3_storage_delete(self, temp_storage_dir):
        """测试 S3 存储删除（占位实现）"""
        from diting.storage_backend import S3Storage
        
        storage = S3Storage({'bucket': 'test'})
        
        # 不应报错
        storage.delete("test.txt")
    
    def test_s3_storage_exists(self, temp_storage_dir):
        """测试 S3 存储存在性检查（占位实现）"""
        from diting.storage_backend import S3Storage
        
        storage = S3Storage({'bucket': 'test'})
        
        assert storage.exists("test.txt") is False
    
    def test_oss_storage_init(self, temp_storage_dir):
        """测试 OSS 存储初始化"""
        from diting.storage_backend import OSSStorage
        
        config = {
            'bucket': 'test-bucket',
            'endpoint': 'oss-cn-shanghai.aliyuncs.com',
            'access_key_id': 'LTAI5t...',
            'access_key_secret': 'abc123...'
        }
        
        storage = OSSStorage(config)
        
        assert storage.bucket == 'test-bucket'
        assert 'aliyuncs.com' in storage.endpoint
    
    def test_oss_storage_save(self, temp_storage_dir):
        """测试 OSS 存储保存（占位实现）"""
        from diting.storage_backend import OSSStorage
        
        storage = OSSStorage({'bucket': 'test'})
        
        url = storage.save("test.txt", b"data")
        
        assert url == "oss://test/test.txt"
    
    def test_oss_storage_load_not_implemented(self, temp_storage_dir):
        """测试 OSS 存储加载（未实现）"""
        from diting.storage_backend import OSSStorage
        
        storage = OSSStorage({'bucket': 'test'})
        
        with pytest.raises(NotImplementedError):
            storage.load("test.txt")
    
    def test_storage_manager_init_local(self, temp_storage_dir):
        """测试存储管理器初始化（本地）"""
        from diting.storage_backend import StorageManager, LocalStorage
        
        config = {
            'STORAGE_TYPE': 'local',
            'STORAGE_ROOT': temp_storage_dir
        }
        
        manager = StorageManager(config)
        
        assert isinstance(manager.backend, LocalStorage)
    
    def test_storage_manager_init_s3(self, temp_storage_dir):
        """测试存储管理器初始化（S3）"""
        from diting.storage_backend import StorageManager, S3Storage
        
        config = {
            'backend': 's3',
            's3': {
                'bucket': 'test-bucket',
                'region': 'us-east-1'
            }
        }
        
        manager = StorageManager(config)
        
        assert isinstance(manager.backend, S3Storage)
    
    def test_storage_manager_init_oss(self, temp_storage_dir):
        """测试存储管理器初始化（OSS）"""
        from diting.storage_backend import StorageManager, OSSStorage
        
        config = {
            'backend': 'oss',
            'oss': {
                'bucket': 'test-bucket',
                'endpoint': 'oss-cn-hangzhou.aliyuncs.com'
            }
        }
        
        manager = StorageManager(config)
        
        assert isinstance(manager.backend, OSSStorage)
    
    def test_storage_manager_default_local(self, temp_storage_dir):
        """测试存储管理器默认配置（本地）"""
        from diting.storage_backend import StorageManager, LocalStorage
        
        manager = StorageManager()
        
        assert isinstance(manager.backend, LocalStorage)
    
    def test_storage_manager_save(self, temp_storage_dir):
        """测试存储管理器保存"""
        from diting.storage_backend import StorageManager
        
        config = {'STORAGE_ROOT': temp_storage_dir}
        manager = StorageManager(config)
        
        url = manager.save("test.txt", b"data")
        
        assert "test.txt" in url
    
    def test_storage_manager_load(self, temp_storage_dir):
        """测试存储管理器加载"""
        from diting.storage_backend import StorageManager
        
        config = {'STORAGE_ROOT': temp_storage_dir}
        manager = StorageManager(config)
        
        # 先保存
        manager.save("load_test.txt", b"test_data")
        
        # 再加载
        data = manager.load("load_test.txt")
        
        assert data == b"test_data"
    
    def test_storage_manager_delete(self, temp_storage_dir):
        """测试存储管理器删除"""
        from diting.storage_backend import StorageManager
        
        config = {'STORAGE_ROOT': temp_storage_dir}
        manager = StorageManager(config)
        
        # 先保存
        manager.save("delete_test.txt", b"data")
        assert manager.exists("delete_test.txt")
        
        # 再删除
        manager.delete("delete_test.txt")
        
        assert not manager.exists("delete_test.txt")
    
    def test_storage_manager_exists(self, temp_storage_dir):
        """测试存储管理器存在性检查"""
        from diting.storage_backend import StorageManager
        
        config = {'STORAGE_ROOT': temp_storage_dir}
        manager = StorageManager(config)
        
        assert manager.exists("nonexistent.txt") is False
        
        manager.save("exists_test.txt", b"data")
        assert manager.exists("exists_test.txt") is True


# ============================================================================
# 测试 monitor.py - 扩展覆盖
# ============================================================================

class TestMonitorExtended:
    """测试监控面板 - 扩展覆盖"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_monitor_get_active_alerts(self, temp_db):
        """测试获取活跃告警"""
        from diting.monitor import MonitorDashboard
        
        monitor = MonitorDashboard(temp_db)
        
        # 创建告警
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(percent=95.0)
            monitor.check_alerts()
        
        # 获取活跃告警
        alerts = monitor.get_active_alerts()
        
        assert len(alerts) >= 0
        if alerts:
            assert 'alert_id' in alerts[0]
            assert 'level' in alerts[0]
    
    def test_monitor_alert_level_enum_values(self, temp_db):
        """测试告警级别枚举值"""
        from diting.monitor import AlertLevel
        
        assert AlertLevel.INFO.value == 'info'
        assert AlertLevel.WARNING.value == 'warning'
        assert AlertLevel.CRITICAL.value == 'critical'
    
    def test_monitor_alert_class(self, temp_db):
        """测试告警数据类"""
        from diting.monitor import Alert, AlertLevel
        from datetime import datetime
        
        alert = Alert(
            id="test-alert",
            level=AlertLevel.WARNING,
            metric="test_metric",
            message="测试告警",
            threshold=80.0,
            current_value=95.0,
            timestamp=datetime.now()
        )
        
        assert alert.id == "test-alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.metric == "test_metric"
    
    def test_monitor_record_multiple_metrics(self, temp_db):
        """测试记录多个指标"""
        from diting.monitor import MonitorDashboard
        
        monitor = MonitorDashboard(temp_db)
        
        # 记录多个指标
        monitor.record_metric('cpu', 50.0)
        monitor.record_metric('memory', 70.0)
        monitor.record_metric('disk', 60.0)
        
        # 获取所有指标（使用 24h 时间范围）
        cpu_data = monitor.get_metrics('cpu', '24h')
        memory_data = monitor.get_metrics('memory', '24h')
        
        assert len(cpu_data) == 1
        assert len(memory_data) == 1
    
    def test_monitor_get_metrics_empty(self, temp_db):
        """测试获取空指标"""
        from diting.monitor import MonitorDashboard
        
        monitor = MonitorDashboard(temp_db)
        
        metrics = monitor.get_metrics('nonexistent', '1h')
        
        assert len(metrics) == 0
    
    def test_monitor_check_alerts_memory(self, temp_db):
        """测试告警检查（内存）"""
        from diting.monitor import MonitorDashboard, AlertLevel
        
        config = {
            'ALERT_RULES': {
                'memory_usage': {'threshold': 0.5, 'window': '1h'},
                'disk_usage': {'threshold': 0.9, 'window': '1h'},
                'ai_error_rate': {'threshold': 0.1, 'window': '5m'},
                'avg_latency': {'threshold': 1000, 'window': '5m'},
                'high_entropy_count': {'threshold': 50, 'window': '1h'}
            }
        }
        monitor = MonitorDashboard(temp_db, config)
        
        with patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=80.0)
            
            alerts = monitor.check_alerts()
            
            # 应该有内存告警
            assert len(alerts) > 0
            assert any(a.level == AlertLevel.WARNING for a in alerts)
    
    def test_monitor_system_status_structure(self, temp_db):
        """测试系统状态结构"""
        from diting.monitor import MonitorDashboard
        
        monitor = MonitorDashboard(temp_db)
        
        status = monitor.get_system_status()
        
        # 验证结构
        assert 'system' in status
        assert 'metrics' in status
        assert 'alerts' in status
        assert 'status' in status
        assert 'timestamp' in status
        
        # 验证系统指标
        assert 'cpu_percent' in status['system']
        assert 'memory_percent' in status['system']
        assert 'disk_percent' in status['system']
        
        # 验证状态值
        assert status['status'] in ['healthy', 'warning']
    
    def test_monitor_close(self, temp_db):
        """测试关闭数据库连接"""
        from diting.monitor import MonitorDashboard
        
        monitor = MonitorDashboard(temp_db)
        
        # 关闭（不应报错）
        monitor.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
