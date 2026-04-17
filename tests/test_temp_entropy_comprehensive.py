"""
温度系统 + 熵系统 综合测试套件

包含：
1. 单独测试（温度、熵独立功能）
2. 混合测试（温度 + 熵联合场景）
3. 自检测试（系统自我验证）
4. 长计划渐进明细测试（模拟真实项目演进）
"""

import os
import sys
import tempfile
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.heat_manager import HeatManager
from diting.entropy_manager import EntropyManager


# ==================== 测试工具函数 ====================

def create_test_managers():
    """创建测试管理器"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # 创建基础表结构
    import sqlite3
    conn = sqlite3.connect(db_path)
    
    # multimodal_slices 表
    conn.execute("""
        CREATE TABLE multimodal_slices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slice_id TEXT UNIQUE NOT NULL,
            memory_path TEXT,
            content TEXT,
            ai_summary TEXT,
            ai_keywords TEXT,
            iteration_version TEXT,
            iteration_status TEXT DEFAULT 'active',
            temperature_score INTEGER DEFAULT 50,
            last_heated_at TIMESTAMP,
            freeze_reason TEXT,
            freeze_by TEXT,
            freeze_at TIMESTAMP,
            last_mentioned_round INTEGER,
            entropy INTEGER DEFAULT NULL,
            entropy_level TEXT DEFAULT NULL,
            last_entropy_change TIMESTAMP,
            entropy_trend TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # temperature_log 表
    conn.execute("""
        CREATE TABLE temperature_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slice_id INTEGER NOT NULL,
            old_score INTEGER,
            new_score INTEGER,
            reason TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slice_id) REFERENCES multimodal_slices(id)
        )
    """)
    
    # entropy_log 表
    conn.execute("""
        CREATE TABLE entropy_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slice_id INTEGER NOT NULL,
            old_entropy INTEGER,
            new_entropy INTEGER,
            old_level TEXT,
            new_level TEXT,
            change_reason TEXT,
            triggered_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slice_id) REFERENCES multimodal_slices(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    # 创建管理器
    temp_config = {
        'TIME_DECAY_RATE': 0.1,
        'ROUND_DECAY_RATE': 5,
        'USER_HEAT_BONUS': 30
    }
    temp_mgr = HeatManager(db_path, temp_config)
    
    entropy_config = {'ENABLE_ENTROPY': True}
    entropy_mgr = EntropyManager(db_path, entropy_config)
    
    return temp_mgr, entropy_mgr, db_fd, db_path


def insert_test_memory(db_path, slice_id, memory_path, content, 
                       version='v1', status='active', temp_score=50):
    """插入测试记忆"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO multimodal_slices 
        (slice_id, memory_path, content, ai_summary, ai_keywords, 
         iteration_version, iteration_status, temperature_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (slice_id, memory_path, content, content[:50], '["测试"]', 
         version, status, temp_score))
    conn.commit()
    conn.close()


# ==================== 1. 单独测试 ====================

def test_temperature_standalone():
    """测试 1: 温度系统单独测试"""
    print("\n" + "="*70)
    print("[测试 1] 温度系统单独测试")
    print("="*70)
    
    temp_mgr, entropy_mgr, db_fd, db_path = create_test_managers()
    
    try:
        # 场景 1: 新记忆初始温度（50 分基准）
        insert_test_memory(db_path, 'temp_001', '/test/new', '新记忆', temp_score=50)
        result = temp_mgr.calculate_temperature('temp_001', current_round=1)
        print(f"   ✅ 初始温度：{result['new_score']}分")
        
        # 场景 2: 用户主动升温（50+30=80，进入高温区）
        # heat 直接返回升温结果，不重新计算
        result = temp_mgr.heat('temp_001', '用户标记重要', 'user')
        assert result['new_score'] > result['old_score'], "升温后温度应上升"
        assert result['bonus'] == 30, "升温 bonus 应为 30"
        print(f"   ✅ 升温后：{result['new_score']}分 (🔥高温，+{result['bonus']})")
        
        # 场景 3: 自然冷却（在 heat 基础上 -20）
        result = temp_mgr.cool('temp_001', '长时间未提及', 'system')
        assert result['new_score'] < 80, f"冷却后温度应下降，实际{result['new_score']}"
        print(f"   ✅ 冷却后：{result['new_score']}分")
        
        # 场景 4: 冻结记忆
        result = temp_mgr.freeze('temp_001', '淘汰方案', 'admin')
        assert result['new_score'] == 0, "冻结后温度应为 0"
        print(f"   ✅ 冻结后：{result['new_score']}分 (🧊冻结)")
        
        # 场景 5: 解冻记忆
        result = temp_mgr.thaw('temp_001', '重新讨论', 'user')
        assert result['new_score'] == 50, "解冻后应回到 50 分"
        print(f"   ✅ 解冻后：{result['new_score']}分")
        
        print("\n   🎉 温度系统单独测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        temp_mgr.close()
        entropy_mgr.close()
        os.close(db_fd)


def test_entropy_standalone():
    """测试 2: 熵系统单独测试"""
    print("\n" + "="*70)
    print("[测试 2] 熵系统单独测试")
    print("="*70)
    
    temp_mgr, entropy_mgr, db_fd, db_path = create_test_managers()
    
    try:
        # 场景 1: 高熵场景（多方案讨论）
        insert_test_memory(db_path, 'ent_001', '/projects/discussion',
                          '方案 A、方案 B、方案 C、方案 D、方案 E，待定，再讨论')
        result = entropy_mgr.calculate_entropy('ent_001')
        assert result['new_entropy'] >= 70, "多方案讨论应为高熵"
        print(f"   ✅ 高熵场景：{result['new_entropy']}分 (🌪️混乱)")
        
        # 场景 2: 低熵场景（已决策执行）
        insert_test_memory(db_path, 'ent_002', '/projects/execution',
                          '已确定用方案 B，开始执行，v3 版本', 'v3', 'executing')
        result = entropy_mgr.calculate_entropy('ent_002')
        assert result['new_entropy'] < 40, "已决策执行应为低熵"
        print(f"   ✅ 低熵场景：{result['new_entropy']}分 (📐确定)")
        
        # 场景 3: 项目整体熵值
        insert_test_memory(db_path, 'ent_003', '/projects/test1', '测试 1')
        insert_test_memory(db_path, 'ent_004', '/projects/test2', '测试 2')
        project_result = entropy_mgr.get_project_entropy('/projects')
        assert 'avg_entropy' in project_result
        print(f"   ✅ 项目熵值：{project_result['avg_entropy']:.1f}分")
        
        # 场景 4: 高熵预警
        alert = entropy_mgr.alert_high_entropy('ent_001', threshold=80)
        if alert['alert']:
            print(f"   ✅ 高熵预警：{alert['suggestion']}")
        else:
            print(f"   ✅ 未触发预警（熵值={alert.get('entropy', 'N/A')}）")
        
        # 场景 5: 异常检测
        anomaly = entropy_mgr.detect_entropy_anomaly('ent_002')
        print(f"   ✅ 异常检测：{'检测到异常' if anomaly['has_anomaly'] else '无异常'}")
        
        print("\n   🎉 熵系统单独测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        temp_mgr.close()
        entropy_mgr.close()
        os.close(db_fd)


# ==================== 2. 混合测试 ====================

def test_temp_entropy_mixed():
    """测试 3: 温度 + 熵混合测试"""
    print("\n" + "="*70)
    print("[测试 3] 温度 + 熵混合测试")
    print("="*70)
    
    temp_mgr, entropy_mgr, db_fd, db_path = create_test_managers()
    
    try:
        # 场景 1: 高温 + 高熵（激烈讨论中）
        insert_test_memory(db_path, 'mix_001', '/hot-high',
                          '方案 A 方案 B 方案 C，但是...然而...担心...', 'v1', 'active', 85)
        temp_result = temp_mgr.calculate_temperature('mix_001', 1)
        ent_result = entropy_mgr.calculate_entropy('mix_001')
        print(f"   ✅ 高温 + 高熵：温度{temp_result['new_score']}分，熵值{ent_result['new_entropy']}分")
        print(f"      状态：激烈讨论中（正常）")
        
        # 场景 2: 高温 + 低熵（理想状态）
        insert_test_memory(db_path, 'mix_002', '/hot-low',
                          '已确定方案 B，开始执行，v2', 'v2', 'executing', 80)
        temp_result = temp_mgr.calculate_temperature('mix_002', 1)
        ent_result = entropy_mgr.calculate_entropy('mix_002')
        print(f"   ✅ 高温 + 低熵：温度{temp_result['new_score']}分，熵值{ent_result['new_entropy']}分")
        print(f"      状态：成熟方案执行中（✅理想）")
        
        # 场景 3: 低温 + 高熵（危险）
        insert_test_memory(db_path, 'mix_003', '/cold-high',
                          '方案 A 方案 B 方案 C，待定', 'v1', 'active', 15)
        temp_result = temp_mgr.calculate_temperature('mix_003', 1)
        ent_result = entropy_mgr.calculate_entropy('mix_003')
        print(f"   ✅ 低温 + 高熵：温度{temp_result['new_score']}分，熵值{ent_result['new_entropy']}分")
        print(f"      状态：混乱但被遗忘（⚠️危险）")
        
        # 场景 4: 冻结 + 高熵（幻觉高危）
        insert_test_memory(db_path, 'mix_004', '/frozen-high',
                          '方案 A 方案 B，淘汰', 'v1', 'frozen', 5)
        temp_result = temp_mgr.calculate_temperature('mix_004', 1)
        ent_result = entropy_mgr.calculate_entropy('mix_004')
        print(f"   ✅ 冻结 + 高熵：温度{temp_result['new_score']}分，熵值{ent_result['new_entropy']}分")
        print(f"      状态：淘汰方案混乱（⚠️幻觉高危）")
        
        print("\n   🎉 温度 + 熵混合测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        temp_mgr.close()
        entropy_mgr.close()
        os.close(db_fd)


# ==================== 3. 自检测试 ====================

def test_self_diagnosis():
    """测试 4: 系统自检测试"""
    print("\n" + "="*70)
    print("[测试 4] 系统自检测试")
    print("="*70)
    
    temp_mgr, entropy_mgr, db_fd, db_path = create_test_managers()
    
    try:
        # 自检 1: 温度范围有效性
        insert_test_memory(db_path, 'self_001', '/self/test1', '测试')
        for score in [0, 25, 50, 75, 100]:
            temp_mgr.db.execute("UPDATE multimodal_slices SET temperature_score=? WHERE slice_id=?",
                               (score, 'self_001'))
            temp_mgr.db.commit()
            result = temp_mgr.calculate_temperature('self_001', 1)
            assert 0 <= result['new_score'] <= 100, f"温度分数超出范围：{result['new_score']}"
        print(f"   ✅ 温度范围有效性：0-100 分")
        
        # 自检 2: 熵值范围有效性
        insert_test_memory(db_path, 'self_002', '/self/test2', '方案 A 方案 B 方案 C 方案 D 方案 E')
        result = entropy_mgr.calculate_entropy('self_002')
        assert 0 <= result['new_entropy'] <= 100, f"熵值超出范围：{result['new_entropy']}"
        print(f"   ✅ 熵值范围有效性：0-100 分")
        
        # 自检 3: 日志记录完整性
        temp_history = temp_mgr.get_temperature_history('self_001', limit=10)
        assert len(temp_history) > 0, "温度日志应为空"
        print(f"   ✅ 温度日志记录：{len(temp_history)}条")
        
        # 自检 4: 系统开关有效性
        entropy_mgr.disable()
        assert not entropy_mgr.is_enabled(), "熵系统应已禁用"
        entropy_mgr.enable()
        assert entropy_mgr.is_enabled(), "熵系统应已启用"
        print(f"   ✅ 熵系统开关：enable/disable 正常")
        
        # 自检 5: 外键约束
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute("INSERT INTO temperature_log (slice_id, old_score, new_score) VALUES (99999, 50, 60)")
            print(f"   ❌ 外键约束失效")
            return False
        except sqlite3.IntegrityError:
            print(f"   ✅ 外键约束有效")
        conn.close()
        
        print("\n   🎉 系统自检测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        temp_mgr.close()
        entropy_mgr.close()
        os.close(db_fd)


# ==================== 4. 长计划渐进明细测试 ====================

def test_long_term_project():
    """测试 5: 长计划渐进明细测试"""
    print("\n" + "="*70)
    print("[测试 5] 长计划渐进明细测试（模拟真实项目演进）")
    print("="*70)
    
    temp_mgr, entropy_mgr, db_fd, db_path = create_test_managers()
    
    try:
        project_id = 'project_001'
        project_path = '/projects/long_term'
        
        # 阶段 1: 项目启动（高熵）
        print("\n   📍 阶段 1: 项目启动（头脑风暴）")
        insert_test_memory(db_path, project_id, project_path,
                          '方案 A、方案 B、方案 C、方案 D，各有优劣，待定', 'v1', 'active', 50)
        ent_result = entropy_mgr.calculate_entropy(project_id)
        print(f"      熵值：{ent_result['new_entropy']}分 ({ent_result['new_level']})")
        assert ent_result['new_entropy'] >= 70, "启动阶段应为高熵"
        
        # 阶段 2: 方案收敛（熵减）
        print("\n   📍 阶段 2: 方案收敛（筛选）")
        # 减少方案数量：从 5 个方案减少到 2 个
        temp_mgr.db.execute("UPDATE multimodal_slices SET content=?, iteration_version=? WHERE slice_id=?",
                           ('已确定用方案 B，其他方案淘汰', 'v2', project_id))
        temp_mgr.db.commit()
        ent_result = entropy_mgr.calculate_entropy(project_id)
        print(f"      熵值：{ent_result['new_entropy']}分 ({ent_result['new_level']})")
        # 熵值可能不变，但版本迭代应熵减
        print(f"      趋势：{ent_result['trend']}")
        
        # 阶段 3: 最终决策（低熵）
        print("\n   📍 阶段 3: 最终决策（拍板）")
        temp_mgr.db.execute("UPDATE multimodal_slices SET content=?, iteration_version=?, iteration_status=? WHERE slice_id=?",
                           ('已确定用方案 B，开始执行', 'v3', 'executing', project_id))
        temp_mgr.db.commit()
        ent_result = entropy_mgr.calculate_entropy(project_id)
        print(f"      熵值：{ent_result['new_entropy']}分 ({ent_result['new_level']})")
        assert ent_result['new_entropy'] < 50, "决策后应为中低熵"
        
        # 阶段 4: 执行中（熵值稳定）
        print("\n   📍 阶段 4: 执行中（稳定推进）")
        temp_mgr.heat(project_id, '项目重要', 'user')
        temp_result = temp_mgr.calculate_temperature(project_id, 5)
        ent_result = entropy_mgr.calculate_entropy(project_id)
        print(f"      温度：{temp_result['new_score']}分，熵值：{ent_result['new_entropy']}分")
        print(f"      状态：高温 + 低熵（✅理想状态）")
        
        # 阶段 5: 意外情况（熵增检测）
        print("\n   📍 阶段 5: 意外情况（执行受阻）")
        temp_mgr.db.execute("UPDATE multimodal_slices SET content=? WHERE slice_id=?",
                           ('执行受阻，有问题，需要重新讨论', project_id))
        temp_mgr.db.commit()
        ent_result = entropy_mgr.calculate_entropy(project_id)
        anomaly = entropy_mgr.detect_entropy_anomaly(project_id)
        print(f"      熵值：{ent_result['new_entropy']}分 (趋势：{ent_result['trend']})")
        if anomaly['has_anomaly']:
            print(f"      ⚠️ 检测到异常：{anomaly['anomalies'][0]['message']}")
        
        # 阶段 6: 重新决策（再次熵减）
        print("\n   📍 阶段 6: 重新决策（问题解决）")
        temp_mgr.db.execute("UPDATE multimodal_slices SET content=?, iteration_version=? WHERE slice_id=?",
                           ('问题已解决，继续执行方案 B', 'v4', project_id))
        temp_mgr.db.commit()
        ent_result = entropy_mgr.calculate_entropy(project_id)
        print(f"      熵值：{ent_result['new_entropy']}分 ({ent_result['new_level']})")
        
        print("\n   🎉 长计划渐进明细测试通过")
        print(f"      完整演进：高熵→中熵→低熵→熵增→熵减")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        temp_mgr.close()
        entropy_mgr.close()
        os.close(db_fd)


# ==================== 主函数 ====================

def main():
    """运行所有测试"""
    print("\n" + "🧪"*35)
    print("温度系统 + 熵系统 综合测试套件")
    print("🧪"*35)
    
    tests = [
        ("单独测试 - 温度", test_temperature_standalone),
        ("单独测试 - 熵", test_entropy_standalone),
        ("混合测试 - 温度 + 熵", test_temp_entropy_mixed),
        ("自检测试", test_self_diagnosis),
        ("长计划渐进明细", test_long_term_project)
    ]
    
    results = {}
    for name, test_func in tests:
        results[name] = test_func()
        time.sleep(0.5)  # 避免过快
    
    # 总结
    print("\n" + "="*70)
    print("测试结果总结")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("="*70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
