"""
熵系统测试（TDD）
"""

import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.entropy_manager import EntropyManager


def create_test_manager():
    """创建测试管理器"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # 创建基础表结构
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE multimodal_slices (
            slice_id TEXT PRIMARY KEY,
            memory_path TEXT,
            content TEXT,
            ai_summary TEXT,
            ai_keywords TEXT,
            iteration_version TEXT,
            iteration_status TEXT DEFAULT 'active',
            temperature TEXT DEFAULT 'warm',
            entropy INTEGER DEFAULT NULL,
            entropy_level TEXT DEFAULT NULL,
            entropy_trend TEXT DEFAULT NULL,
            last_entropy_change TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    
    config = {
        'ENABLE_ENTROPY': True,
        'HIGH_ENTROPY_THRESHOLD': 70,
        'MEDIUM_ENTROPY_THRESHOLD': 40
    }
    
    manager = EntropyManager(db_path, config)
    return manager, db_fd


def test_entropy_calculation():
    """测试 1: 熵值计算"""
    print("\n[测试 1] 熵值计算...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入高熵数据（多个方案）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, content, ai_summary)
            VALUES (?, ?, ?, ?)
        """, (
            'high_entropy_001',
            '/projects/plan_discussion',
            '我们在讨论方案 A、方案 B、方案 C、方案 D、方案 E，各有优劣，待定',
            '多方案讨论中'
        ))
        manager.db.commit()
        
        # 计算熵值
        result = manager.calculate_entropy('high_entropy_001')
        
        assert 'new_entropy' in result
        assert result['new_entropy'] >= 70  # 高熵
        assert result['new_level'] == 'high'
        
        print(f"   ✅ 高熵计算成功：{result['new_entropy']} ({result['new_level']})")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_low_entropy():
    """测试 2: 低熵场景"""
    print("\n[测试 2] 低熵场景...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入低熵数据（已决策执行）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, content, ai_summary, iteration_version)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'low_entropy_001',
            '/projects/execution',
            '已确定用方案 B，开始执行，v3 版本',
            '执行中',
            'v3'
        ))
        manager.db.commit()
        
        # 计算熵值
        result = manager.calculate_entropy('low_entropy_001')
        
        assert result['new_entropy'] < 40  # 低熵
        assert result['new_level'] == 'low'
        
        print(f"   ✅ 低熵计算成功：{result['new_entropy']} ({result['new_level']})")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_project_entropy():
    """测试 3: 项目整体熵值"""
    print("\n[测试 3] 项目整体熵值...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入多个记忆
        for i in range(5):
            manager.db.execute("""
                INSERT INTO multimodal_slices 
                (slice_id, memory_path, content, entropy, entropy_level)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f'proj_{i}',
                '/projects/test',
                f'内容{i}',
                50 + i * 10,
                'medium'
            ))
        manager.db.commit()
        
        # 获取项目熵值
        result = manager.get_project_entropy('/projects')
        
        assert result['memory_count'] == 5
        assert 'avg_entropy' in result
        assert result['avg_entropy'] >= 50
        
        print(f"   ✅ 项目熵值：{result['avg_entropy']:.1f} ({result['level']})")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_high_entropy_alert():
    """测试 4: 高熵预警"""
    print("\n[测试 4] 高熵预警...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入高熵数据
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, entropy, entropy_level, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'alert_001',
            '/projects/stuck',
            85,
            'high',
            '2026-03-15 00:00:00'  # 30 天前
        ))
        manager.db.commit()
        
        # 触发预警
        result = manager.alert_high_entropy('alert_001', threshold=80)
        
        assert result['alert'] == True
        assert 'suggestion' in result
        
        print(f"   ✅ 高熵预警：{result['message']}")
        print(f"      建议：{result['suggestion']}")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_entropy_anomaly():
    """测试 5: 熵值异常检测"""
    print("\n[测试 5] 熵值异常检测...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入异常数据（低熵但熵增）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, content, entropy, entropy_level, entropy_trend)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'anomaly_001',
            '/projects/decision',
            '已确定方案，开始执行',
            30,
            'low',
            'increasing'
        ))
        manager.db.commit()
        
        # 检测异常
        result = manager.detect_entropy_anomaly('anomaly_001')
        
        assert result['has_anomaly'] == True
        assert len(result['anomalies']) > 0
        
        print(f"   ✅ 检测到异常：{len(result['anomalies'])} 个")
        for anomaly in result['anomalies']:
            print(f"      - {anomaly['type']}: {anomaly['message']}")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_entropy_history():
    """测试 6: 熵变历史"""
    print("\n[测试 6] 熵变历史...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入数据并多次计算
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, content)
            VALUES (?, ?, ?)
        """, ('history_001', '/test', '方案 A 方案 B 方案 C'))
        manager.db.commit()
        
        # 多次计算熵值
        manager.calculate_entropy('history_001')
        manager.calculate_entropy('history_001')
        manager.calculate_entropy('history_001')
        
        # 获取历史
        history = manager.get_entropy_history('history_001', limit=10)
        
        assert len(history) >= 1
        
        print(f"   ✅ 熵变历史：{len(history)} 条记录")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_entropy_switch():
    """测试 7: 熵系统开关"""
    print("\n[测试 7] 熵系统开关...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 初始状态
        assert manager.is_enabled() == True
        
        # 禁用
        manager.disable()
        assert manager.is_enabled() == False
        
        # 禁用后计算应返回错误
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path)
            VALUES (?, ?)
        """, ('test_001', '/test'))
        manager.db.commit()
        
        result = manager.calculate_entropy('test_001')
        assert result.get('error') == '熵系统未启用'
        
        # 重新启用
        manager.enable()
        assert manager.is_enabled() == True
        
        print(f"   ✅ 开关功能正常")
        
    finally:
        manager.close()
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("熵系统测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_entropy_calculation,
        test_low_entropy,
        test_project_entropy,
        test_high_entropy_alert,
        test_entropy_anomaly,
        test_entropy_history,
        test_entropy_switch
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ 失败：{e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ 异常：{e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print(f"通过率：{passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
