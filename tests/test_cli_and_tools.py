#!/usr/bin/env python3
"""
测试 CLI 工具和辅助模块

覆盖范围：
- cli/version.py
- cli/install_check.py
- migrations/001_add_lcn_pointers.py
- mcp_server_kg_tools.py
- free_energy_manager.py (核心功能)
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from io import StringIO
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# 测试 cli/version.py
# ============================================================================

class TestVersionCLI:
    """测试版本信息 CLI 工具"""
    
    def test_version_main(self, capsys):
        """测试 version main 函数输出"""
        from diting.cli.version import main
        import diting
        
        main()
        captured = capsys.readouterr()
        
        assert "Diting (谛听) 版本信息" in captured.out
        assert diting.__version__ in captured.out
        assert diting.__release_date__ in captured.out
        assert diting.__author__ in captured.out
        assert "核心优化:" in captured.out
        assert "FTS5 BM25" in captured.out
        assert "热力学四系统" in captured.out
        assert "性能提升：30-50%" in captured.out
    
    def test_version_module_import(self):
        """测试 version 模块可导入"""
        from diting.cli import version
        assert hasattr(version, 'main')
        assert callable(version.main)


# ============================================================================
# 测试 cli/install_check.py
# ============================================================================

class TestInstallCheck:
    """测试安装验证工具"""
    
    def test_check_python_version_success(self, capsys):
        """测试 Python 版本检查（成功情况）"""
        from diting.cli.install_check import check_python_version
        
        with patch('sys.version_info', (3, 11, 0)):
            result = check_python_version()
            assert result is True
        
        captured = capsys.readouterr()
        assert "Python 版本" in captured.out
        assert "✅" in captured.out
    
    def test_check_python_version_failure(self, capsys):
        """测试 Python 版本检查（失败情况）"""
        from diting.cli.install_check import check_python_version
        
        with patch('sys.version_info', (3, 9, 0)):
            result = check_python_version()
            assert result is False
        
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "版本过低" in captured.out
    
    def test_check_mfs_import_success(self, capsys):
        """测试 MFS 导入检查（成功情况）"""
        from diting.cli.install_check import check_mfs_import
        
        with patch.dict('sys.modules', {'mfs': MagicMock(__version__='1.0.0')}):
            result = check_mfs_import()
            assert result is True
        
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "MFS 可正常导入" in captured.out
    
    def test_check_mfs_import_failure(self, capsys):
        """测试 MFS 导入检查（失败情况）"""
        from diting.cli.install_check import check_mfs_import
        
        with patch.dict('sys.modules', {'mfs': None}, clear=False):
            if 'mfs' in sys.modules:
                del sys.modules['mfs']
            
            with patch('builtins.__import__', side_effect=ImportError("No module named 'mfs'")):
                result = check_mfs_import()
                assert result is False
        
        captured = capsys.readouterr()
        assert "❌" in captured.out
    
    def test_check_mcp_registration_found(self, capsys, tmp_path):
        """测试 MCP 注册检查（配置文件存在）"""
        from diting.cli.install_check import check_mcp_registration
        import json
        
        # 创建临时配置文件
        config_file = tmp_path / "mcp_config.json"
        config_data = {
            "mcpServers": {
                "mfs-memory": {
                    "command": "mfs-mcp",
                    "args": []
                }
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        with patch('os.path.expanduser', return_value=str(config_file)):
            result = check_mcp_registration()
            assert result is True
        
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "已注册" in captured.out
    
    def test_check_mcp_registration_not_found(self, capsys, tmp_path):
        """测试 MCP 注册检查（配置文件中无 mfs-memory）"""
        from diting.cli.install_check import check_mcp_registration
        import json
        
        # 创建临时配置文件（不含 mfs-memory）
        config_file = tmp_path / "mcp_config.json"
        config_data = {"mcpServers": {}}
        config_file.write_text(json.dumps(config_data))
        
        with patch('os.path.expanduser', return_value=str(config_file)):
            result = check_mcp_registration()
            assert result is False
        
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "未注册" in captured.out
    
    def test_check_mcp_registration_no_config(self, capsys):
        """测试 MCP 注册检查（无配置文件）"""
        from diting.cli.install_check import check_mcp_registration
        
        with patch('os.path.exists', return_value=False):
            result = check_mcp_registration()
            assert result is False
        
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "未找到" in captured.out
    
    def test_check_dependencies_success(self, capsys):
        """测试依赖检查（成功情况）"""
        from diting.cli.install_check import check_dependencies
        
        # sqlite3 是内置模块，应该总是存在
        result = check_dependencies()
        
        captured = capsys.readouterr()
        assert "sqlite3" in captured.out
    
    def test_main_all_checks_pass(self, capsys):
        """测试主函数（所有检查通过）"""
        from diting.cli.install_check import main
        
        with patch('diting.cli.install_check.check_python_version', return_value=True), \
             patch('diting.cli.install_check.check_dependencies', return_value=True), \
             patch('diting.cli.install_check.check_mfs_import', return_value=True), \
             patch('diting.cli.install_check.check_mcp_registration', return_value=True):
            
            result = main()
            assert result == 0
        
        captured = capsys.readouterr()
        assert "所有检查通过" in captured.out
        assert "🎉" in captured.out
    
    def test_main_some_checks_fail(self, capsys):
        """测试主函数（部分检查失败）"""
        from diting.cli.install_check import main
        
        with patch('diting.cli.install_check.check_python_version', return_value=False), \
             patch('diting.cli.install_check.check_dependencies', return_value=True), \
             patch('diting.cli.install_check.check_mfs_import', return_value=True), \
             patch('diting.cli.install_check.check_mcp_registration', return_value=True):
            
            result = main()
            assert result == 1
        
        captured = capsys.readouterr()
        assert "部分检查未通过" in captured.out
        assert "⚠️" in captured.out


# ============================================================================
# 测试 migrations/001_add_lcn_pointers.py
# ============================================================================

class TestMigrationLCNPointers:
    """测试 LCN 指针迁移脚本"""
    
    def test_migrate_add_lcn_pointers_new_table(self):
        """测试迁移（新表，字段不存在）"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_001", 
            os.path.join(os.path.dirname(__file__), '../diting/migrations/001_add_lcn_pointers.py'))
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # 创建基础表（不含 lcn_pointers）
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE mft (
                    id INTEGER PRIMARY KEY,
                    memory_path TEXT
                )
            """)
            conn.commit()
            conn.close()
            
            # 执行迁移
            result = migration.migrate_add_lcn_pointers(db_path)
            assert result is True
            
            # 验证迁移
            verify_result = migration.verify_migration(db_path)
            assert verify_result is True
            
            # 验证字段确实存在
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA table_info(mft)")
            columns = [row[1] for row in cursor.fetchall()]
            assert 'lcn_pointers' in columns
            conn.close()
            
        finally:
            os.unlink(db_path)
    
    def test_migrate_add_lcn_pointers_already_exists(self, capsys):
        """测试迁移（字段已存在）"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_001", 
            os.path.join(os.path.dirname(__file__), '../diting/migrations/001_add_lcn_pointers.py'))
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # 创建包含 lcn_pointers 的表
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE mft (
                    id INTEGER PRIMARY KEY,
                    memory_path TEXT,
                    lcn_pointers TEXT
                )
            """)
            conn.commit()
            conn.close()
            
            # 执行迁移（应该跳过）
            result = migration.migrate_add_lcn_pointers(db_path)
            assert result is True
            
            captured = capsys.readouterr()
            assert "已存在" in captured.out
            assert "跳过" in captured.out
            
        finally:
            os.unlink(db_path)
    
    def test_verify_migration_failure(self, capsys):
        """测试验证失败（字段不存在）"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_001", 
            os.path.join(os.path.dirname(__file__), '../diting/migrations/001_add_lcn_pointers.py'))
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # 创建不含 lcn_pointers 的表
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE mft (
                    id INTEGER PRIMARY KEY,
                    memory_path TEXT
                )
            """)
            conn.commit()
            conn.close()
            
            # 验证应该失败
            result = migration.verify_migration(db_path)
            assert result is False
            
            captured = capsys.readouterr()
            assert "验证失败" in captured.out
            assert "不存在" in captured.out
            
        finally:
            os.unlink(db_path)
    
    def test_migration_main_script_success(self, capsys):
        """测试迁移脚本主函数（成功）"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_001", 
            os.path.join(os.path.dirname(__file__), '../diting/migrations/001_add_lcn_pointers.py'))
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # 创建基础表
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE mft (id INTEGER PRIMARY KEY, memory_path TEXT)")
            conn.commit()
            conn.close()
            
            # 直接调用迁移函数
            result = migration.migrate_add_lcn_pointers(db_path)
            assert result is True
            
            # 验证
            verify_result = migration.verify_migration(db_path)
            assert verify_result is True
            
            captured = capsys.readouterr()
            # 迁移脚本输出的是"成功添加"而不是"迁移完成"
            assert "成功添加" in captured.out or "验证通过" in captured.out
                
        finally:
            os.unlink(db_path)
    
    def test_migration_error_handling(self):
        """测试迁移错误处理（SQLite 错误）"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_001", 
            os.path.join(os.path.dirname(__file__), '../diting/migrations/001_add_lcn_pointers.py'))
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # 使用无效的数据库路径触发错误
        # sqlite3 会抛出 OperationalError，但函数会返回 False
        import sqlite3
        try:
            result = migration.migrate_add_lcn_pointers('/nonexistent/path/to/db.db')
            # 如果没抛异常，应该返回 False
            assert result is False
        except sqlite3.OperationalError:
            # 抛异常也算测试通过（错误处理）
            pass


# ============================================================================
# 测试 mcp_server_kg_tools.py
# ============================================================================

class TestMCPServerKGTools:
    """测试 MCP Server KG 工具"""
    
    @pytest.mark.asyncio
    async def test_kg_search_success(self):
        """测试 kg_search（成功找到）"""
        from diting.mcp_server_kg_tools import _kg_search
        from mcp.types import TextContent
        
        # 创建 mock 对象
        mock_mft = MagicMock()
        mock_mft.kg.search_with_expansion.return_value = {
            "found": True,
            "concept": "测试概念",
            "expanded_concepts": ["关联 1", "关联 2"],
            "suggestion": "建议内容"
        }
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        # 调用工具
        result = await _kg_search(mock_self, {"query": "测试概念", "max_depth": 2})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅ 找到概念" in result[0].text
        assert "测试概念" in result[0].text
        assert "关联概念" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_search_missing_query(self):
        """测试 kg_search（缺少 query 参数）"""
        from diting.mcp_server_kg_tools import _kg_search
        from mcp.types import TextContent
        
        mock_self = MagicMock()
        
        result = await _kg_search(mock_self, {})
        
        assert len(result) == 1
        assert "错误：缺少 query 参数" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_search_kg_not_enabled(self):
        """测试 kg_search（知识图谱未启用）"""
        from diting.mcp_server_kg_tools import _kg_search
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg = None
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_search(mock_self, {"query": "测试"})
        
        assert "知识图谱未启用" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_search_not_found(self):
        """测试 kg_search（未找到概念）"""
        from diting.mcp_server_kg_tools import _kg_search
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg.search_with_expansion.return_value = {"found": False}
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_search(mock_self, {"query": "不存在的概念"})
        
        assert "未找到概念" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_get_related_success(self):
        """测试 kg_get_related（成功）"""
        from diting.mcp_server_kg_tools import _kg_get_related
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg.get_related_concepts.return_value = [
            {"concept": "关联 1", "weight": 0.9},
            {"concept": "关联 2", "weight": 0.7}
        ]
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_get_related(mock_self, {"concept": "测试", "top_k": 5})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "关联概念" in result[0].text
        assert "关联 1" in result[0].text
        assert "权重" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_get_related_missing_concept(self):
        """测试 kg_get_related（缺少 concept 参数）"""
        from diting.mcp_server_kg_tools import _kg_get_related
        from mcp.types import TextContent
        
        mock_self = MagicMock()
        
        result = await _kg_get_related(mock_self, {})
        
        assert "错误：缺少 concept 参数" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_get_related_no_results(self):
        """测试 kg_get_related（无关联概念）"""
        from diting.mcp_server_kg_tools import _kg_get_related
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg.get_related_concepts.return_value = []
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_get_related(mock_self, {"concept": "孤立概念"})
        
        assert "没有关联概念" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_stats_success(self):
        """测试 kg_stats（成功）"""
        from diting.mcp_server_kg_tools import _kg_stats
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg.get_stats.return_value = {
            "concept_count": 1000,
            "edge_count": 5000,
            "avg_edges_per_concept": 5.0
        }
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_stats(mock_self, {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "知识图谱统计" in result[0].text
        assert "概念数" in result[0].text
        assert "1,000" in result[0].text
    
    @pytest.mark.asyncio
    async def test_kg_stats_kg_not_enabled(self):
        """测试 kg_stats（知识图谱未启用）"""
        from diting.mcp_server_kg_tools import _kg_stats
        from mcp.types import TextContent
        
        mock_mft = MagicMock()
        mock_mft.kg = None
        
        mock_self = MagicMock()
        mock_self.mft = mock_mft
        
        result = await _kg_stats(mock_self, {})
        
        assert "知识图谱未启用" in result[0].text


# ============================================================================
# 测试 free_energy_manager.py (核心功能)
# ============================================================================

class TestFreeEnergyManager:
    """测试自由能管理器"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # 创建基础表结构
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
                context_vector TEXT,
                freeze_reason TEXT,
                freeze_by TEXT,
                freeze_at TIMESTAMP,
                last_mentioned_round INTEGER,
                iteration_status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        yield db_path
        os.unlink(db_path)
    
    def test_init_default_config(self, temp_db):
        """测试初始化（默认配置）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        assert manager.db_path == temp_db
        assert manager.extract_threshold == 0.0
        assert manager.high_threshold == 50.0
        assert manager.low_threshold == 10.0
    
    def test_init_custom_config(self, temp_db):
        """测试初始化（自定义配置）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        config = {
            'EXTRACT_THRESHOLD': 10.0,
            'HIGH_THRESHOLD': 80.0,
            'LOW_THRESHOLD': 20.0
        }
        manager = FreeEnergyManager(temp_db, config)
        
        assert manager.extract_threshold == 10.0
        assert manager.high_threshold == 80.0
        assert manager.low_threshold == 20.0
    
    def test_ensure_schema_new_table(self, temp_db):
        """测试确保表结构（新表）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 删除表后重新创建
        conn = sqlite3.connect(temp_db)
        conn.execute("DROP TABLE multimodal_slices")
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        
        # 验证表已创建
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='multimodal_slices'
        """)
        assert cursor.fetchone() is not None
        conn.close()
    
    def test_calculate_free_energy(self, temp_db):
        """测试自由能计算"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 插入测试数据
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score, temp_score, entropy_score)
            VALUES ('test-calc', '/test/calc', 80, 0.5, 0.3)
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        
        # G = U - TS * 100
        # 示例：U=80, T=0.5, S=0.3 → G = 80 - 0.5*0.3*100 = 80 - 15 = 65
        result = manager.calculate_free_energy('test-calc')
        
        assert 'free_energy' in result
        assert result['free_energy'] == 65.0
        assert result['can_extract'] is True
        assert 'G = U - TS' in result['formula']
    
    def test_calculate_free_energy_negative(self, temp_db):
        """测试自由能计算（负值）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 插入测试数据（低热量高熵）
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score, temp_score, entropy_score)
            VALUES ('test-neg', '/test/neg', 10, 0.9, 0.8)
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        
        # G = U - TS * 100 = 10 - 0.9*0.8*100 = 10 - 72 = -62
        result = manager.calculate_free_energy('test-neg')
        
        assert abs(result['free_energy'] - (-62.0)) < 0.001  # 浮点数精度
        assert result['can_extract'] is False  # G < 0 不可提取
    
    def test_evaluate_availability_high(self, temp_db):
        """测试可用性评估（高）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        # G > 50 为 high
        availability = manager._evaluate_availability(75.0)
        assert availability == 'high'
    
    def test_evaluate_availability_medium(self, temp_db):
        """测试可用性评估（中）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        # 10 < G <= 50 为 medium
        availability = manager._evaluate_availability(30.0)
        assert availability == 'medium'
    
    def test_evaluate_availability_low(self, temp_db):
        """测试可用性评估（低）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        # 0 < G <= 10 为 low
        availability = manager._evaluate_availability(5.0)
        assert availability == 'low'
    
    def test_evaluate_availability_frozen(self, temp_db):
        """测试可用性评估（冻结）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        # G <= 0 为 frozen
        availability = manager._evaluate_availability(-5.0)
        assert availability == 'frozen'
    
    def test_batch_calculate(self, temp_db):
        """测试批量计算自由能"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 插入测试数据
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score, temp_score, entropy_score)
            VALUES 
                ('batch-1', '/test/batch1', 80, 0.5, 0.3),
                ('batch-2', '/test/batch2', 60, 0.7, 0.4)
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        results = manager.batch_calculate(['batch-1', 'batch-2'], current_context="测试上下文")
        
        assert 'batch-1' in results
        assert 'batch-2' in results
        assert 'free_energy' in results['batch-1']
        assert 'free_energy' in results['batch-2']
    
    def test_get_memory(self, temp_db):
        """测试获取记忆信息"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 插入测试数据
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score)
            VALUES ('test-get', '/test/get', 85)
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        memory = manager._get_memory('test-get')
        
        assert memory is not None
        assert memory['slice_id'] == 'test-get'
        assert memory['heat_score'] == 85
    
    def test_get_memory_not_found(self, temp_db):
        """测试获取不存在的记忆"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        memory = manager._get_memory('nonexistent')
        
        assert memory is None
    
    def test_match_bm25(self, temp_db):
        """测试 BM25 匹配（简化）"""
        from diting.free_energy_manager import FreeEnergyManager
        
        # 插入测试数据
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, ai_keywords)
            VALUES ('test-bm25', '/test/bm25', '关键词 1，关键词 2')
        """)
        conn.commit()
        conn.close()
        
        manager = FreeEnergyManager(temp_db)
        # _match_bm25 应该返回 0-1 之间的值
        score = manager._match_bm25('test-bm25', '测试上下文')
        assert 0 <= score <= 1
    
    def test_match_path(self, temp_db):
        """测试路径匹配"""
        from diting.free_energy_manager import FreeEnergyManager
        
        manager = FreeEnergyManager(temp_db)
        
        # 创建 mock memory
        memory = {'memory_path': '/test/path/to/memory'}
        context = 'test path'
        
        score = manager._match_path(memory, context)
        assert 0 <= score <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
