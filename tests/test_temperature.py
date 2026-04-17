"""
温度系统测试（TDD）
"""

import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.heat_manager import HeatManager


def create_test_manager():
    """创建测试管理器（预留四系统空间）"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # 创建基础表结构（预留热度、温度、熵、自由能四系统空间）
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE multimodal_slices (
            slice_id TEXT PRIMARY KEY,
            memory_path TEXT,
            ai_keywords TEXT,
            
            -- 热度系统（H）：记忆访问频率
            heat_score INTEGER DEFAULT 50,
            last_heated_at TIMESTAMP,
            
            -- 温度系统（T）：记忆影响力（预留）
            temp_score INTEGER DEFAULT 50,
            
            -- 熵系统（S）：记忆的混乱和不确定性（预留）
            entropy_score REAL DEFAULT 0.0,
            
            -- 自由能系统（G）：G = H - TS（预留）
            free_energy_score REAL DEFAULT 0.0,
            
            -- 冻结状态
            freeze_reason TEXT,
            freeze_by TEXT,
            freeze_at TIMESTAMP,
            
            -- 其他状态
            last_mentioned_round INTEGER,
            iteration_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    
    config = {
        'TIME_DECAY_RATE': 0.1,
        'ROUND_DECAY_RATE': 5,
        'USER_HEAT_BONUS': 30
    }
    
    manager = HeatManager(db_path, config)
    return manager, db_fd


def test_temperature_calculation():
    """测试 1: 温度计算"""
    print("\n[测试 1] 温度计算...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, created_at)
            VALUES (?, ?, ?)
        """, ('test_001', '/test/memory', '2026-04-15 00:00:00'))
        manager.db.commit()
        
        # 计算温度
        result = manager.calculate_heat('test_001', current_round=100)
        
        assert 'new_score' in result
        
        print(f"   ✅ 温度计算成功：{result['new_score']}分")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_heat_memory():
    """测试 2: 加热记忆"""
    print("\n[测试 2] 加热记忆...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score)
            VALUES (?, ?, ?)
        """, ('test_002', '/test/memory', 50))
        manager.db.commit()
        
        # 加热
        result = manager.heat('test_002', '用户标记重要', 'user')
        
        assert result['new_score'] == 80  # 50 + 30
        assert result['bonus'] == 30
        
        print(f"   ✅ 加热成功：50 → {result['new_score']} (+{result['bonus']})")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_cool_memory():
    """测试 3: 冷却记忆"""
    print("\n[测试 3] 冷却记忆...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score)
            VALUES (?, ?, ?)
        """, ('test_003', '/test/memory', 50))
        manager.db.commit()
        
        # 冷却
        result = manager.cool('test_003', '自然冷却', 'system')
        
        assert result['new_score'] == 30  # 50 - 20
        
        print(f"   ✅ 冷却成功：50 → {result['new_score']} (-20)")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_freeze_memory():
    """测试 4: 冻结记忆"""
    print("\n[测试 4] 冻结记忆...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path, heat_score)
            VALUES (?, ?, ?)
        """, ('test_004', '/test/memory', 50))
        manager.db.commit()
        
        # 冻结
        result = manager.freeze('test_004', '淘汰方案，防止死灰复燃', 'admin')
        
        assert result['new_score'] == 0  # 冻结为 0 分
        
        print(f"   ✅ 冻结成功：50 → {result['new_score']}")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_thaw_memory():
    """测试 5: 解冻记忆"""
    print("\n[测试 5] 解冻记忆...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入冻结数据（温度分数<=10 视为冻结）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, heat_score, freeze_reason, freeze_by)
            VALUES (?, ?, ?, ?, ?)
        """, ('test_005', '/test/memory', 5, '测试冻结', 'admin'))
        manager.db.commit()
        
        # 解冻
        result = manager.thaw('test_005', '用户解冻', 'user')
        
        assert result['new_score'] == 50
        
        print(f"   ✅ 解冻成功：5 → {result['new_score']}分")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_zombie_revival_user():
    """测试 6: 死灰复燃检测（用户触发）"""
    print("\n[测试 6] 死灰复燃检测（用户触发）...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, ai_keywords, heat_score)
            VALUES (?, ?, ?, ?)
        """, ('test_006', '/test/memory', '["方案 A", "淘汰"]', 50))
        manager.db.commit()
        
        # 用户触发
        result = manager.detect_zombie_revival('test_006', 'user')
        
        assert result['triggered_by'] == 'user'
        assert result['is_zombie'] == False
        
        print(f"   ✅ 用户触发正常：{result['action']}")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_zombie_revival_agent():
    """测试 7: 死灰复燃检测（Agent 触发）"""
    print("\n[测试 7] 死灰复燃检测（Agent 触发）...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入淘汰方案（冻结）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, ai_keywords, heat_score, iteration_status)
            VALUES (?, ?, ?, ?, ?)
        """, ('frozen_001', '/old/plan_a', '["方案 A", "淘汰"]', 0, 'frozen'))
        manager.db.commit()
        
        # 插入新讨论（Agent 触发）
        manager.db.execute("""
            INSERT INTO multimodal_slices 
            (slice_id, memory_path, ai_keywords, heat_score)
            VALUES (?, ?, ?, ?)
        """, ('test_007', '/new/discussion', '["方案 A", "讨论"]', 50))
        manager.db.commit()
        
        # Agent 触发
        result = manager.detect_zombie_revival('test_007', 'agent')
        
        # 应该检测到死灰复燃
        assert result['triggered_by'] == 'agent'
        
        print(f"   ✅ Agent 触发检测：{result.get('action', '正常')}")
        
    finally:
        manager.close()
        os.close(db_fd)


def test_temperature_history():
    """测试 8: 温度变更历史"""
    print("\n[测试 8] 温度变更历史...")
    
    manager, db_fd = create_test_manager()
    
    try:
        # 插入测试数据
        manager.db.execute("""
            INSERT INTO multimodal_slices (slice_id, memory_path)
            VALUES (?, ?)
        """, ('test_008', '/test/memory'))
        manager.db.commit()
        
        # 多次变更
        manager.heat('test_008', '加热 1', 'user')
        manager.cool('test_008', '冷却 1', 'system')
        manager.heat('test_008', '加热 2', 'user')
        
        # 获取历史
        history = manager.get_heat_history('test_008', limit=10)
        
        assert len(history) >= 3
        
        print(f"   ✅ 历史记录：{len(history)} 条")
        
    finally:
        manager.close()
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("温度系统测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_temperature_calculation,
        test_heat_memory,
        test_cool_memory,
        test_freeze_memory,
        test_thaw_memory,
        test_zombie_revival_user,
        test_zombie_revival_agent,
        test_temperature_history
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
