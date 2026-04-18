"""
DITING_ 完整测试套件 - 覆盖所有 Task 场景

测试范围:
- P0: 多模态基础
- P1: 智能优化
- P2: 温度系统
- P2.5: 熵系统
- P3: 监控告警
- P3: 日志审计
"""

import os
import sys
import tempfile
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有模块
from diting.mft import MFT
from diting.multimodal_manager import MultimodalMemoryManager
from diting.smart_trigger import SmartTrigger
from diting.ai_queue import AIQueueManager
from diting.heat_manager import HeatManager
from diting.entropy_manager import EntropyManager
from diting.monitor import MonitorDashboard
from diting.audit_logger import AuditLogger


def create_test_environment():
    """创建测试环境"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    storage_dir = tempfile.mkdtemp()
    return db_fd, db_path, storage_dir


def test_p0_multimodal():
    """测试 P0: 多模态基础"""
    print("\n" + "="*70)
    print("[P0] 多模态基础测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 创建多模态管理器
        config = {'ENABLE_AI_SUMMARY': False}
        mm = MultimodalMemoryManager(db_path, storage_dir, config)
        
        # 测试图片存储
        image_data = bytes([0xFF, 0xD8, 0xFF, 0xD9])  # JPEG
        result = mm.store_image(image_data, '/test/image_001', 'test.jpg')
        assert 'slice_id' in result
        print(f"   ✅ 图片存储：{result['slice_id'][:8]}...")
        
        # 测试语音存储
        audio_data = bytes([0x4F, 0x67, 0x67, 0x53])  # OGG
        result = mm.store_audio(audio_data, '/test/audio_001', 'test.ogg')
        assert 'slice_id' in result
        print(f"   ✅ 语音存储：{result['slice_id'][:8]}...")
        
        # 测试去重
        result2 = mm.store_image(image_data, '/test/image_002')
        assert result2['is_duplicate'] == True
        print(f"   ✅ 去重检测正常")
        
        # 测试搜索
        results = mm.search('test')
        print(f"   ✅ 搜索功能：{len(results)}条结果")
        
        mm.close()
        print("\n   🎉 P0 多模态基础测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        os.close(db_fd)


def test_p1_intelligence():
    """测试 P1: 智能优化"""
    print("\n" + "="*70)
    print("[P1] 智能优化测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 测试智能触发
        trigger = SmartTrigger({'ENABLE_SMART_TRIGGER': True})
        
        # 重要会议录音应触发 AI
        file_info = {
            'type': 'audio',
            'size': 5 * 1024 * 1024,
            'filename': '重要会议录音.ogg',
            'memory_path': '/work/meetings/2026-04-15'
        }
        should_call = trigger.should_call_ai(file_info)
        assert should_call == True
        print(f"   ✅ 智能触发：重要会议录音应调用 AI")
        
        # 临时截图不应触发
        file_info = {
            'type': 'image',
            'size': 500 * 1024,
            'filename': '截图 20260415.png',
            'memory_path': '/temp/screenshots'
        }
        should_call = trigger.should_call_ai(file_info)
        assert should_call == False
        print(f"   ✅ 智能触发：临时截图不应调用 AI")
        
        # 测试异步队列
        queue = AIQueueManager(db_path)
        task_id = queue.enqueue('/storage/test.jpg', 'image', '/test', 'user_001')
        assert task_id is not None
        print(f"   ✅ 异步队列：任务入队 {task_id[:8]}...")
        
        # 检查队列状态
        status = queue.get_queue_status()
        assert 'pending' in status
        print(f"   ✅ 队列状态：{status['pending']}个待处理")
        
        queue.close()
        print("\n   🎉 P1 智能优化测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def test_p2_temperature():
    """测试 P2: 温度系统"""
    print("\n" + "="*70)
    print("[P2] 温度系统测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 创建基础表
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE multimodal_slices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slice_id TEXT UNIQUE NOT NULL,
                memory_path TEXT,
                temperature_score INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        # 创建温度管理器
        temp_mgr = HeatManager(db_path)
        
        # 插入测试数据
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO multimodal_slices (slice_id, memory_path) VALUES (?, ?)",
                    ('test_001', '/test/memory'))
        conn.commit()
        conn.close()
        
        # 测试加热
        result = temp_mgr.heat('test_001', '用户标记重要', 'user')
        assert result['new_score'] > result['old_score']
        print(f"   ✅ 加热：{result['old_score']} → {result['new_score']} (+{result['bonus']})")
        
        # 测试冷却
        result = temp_mgr.cool('test_001', '自然冷却', 'system')
        assert result['new_score'] < 80
        print(f"   ✅ 冷却：{result['old_score']} → {result['new_score']}")
        
        # 测试冻结
        result = temp_mgr.freeze('test_001', '淘汰方案', 'admin')
        assert result['new_score'] == 0
        print(f"   ✅ 冻结：{result['old_score']} → {result['new_score']}")
        
        # 测试解冻
        result = temp_mgr.thaw('test_001', '用户解冻', 'user')
        assert result['new_score'] == 50
        print(f"   ✅ 解冻：{result['old_score']} → {result['new_score']}")
        
        temp_mgr.close()
        print("\n   🎉 P2 温度系统测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def test_p25_entropy():
    """测试 P2.5: 熵系统"""
    print("\n" + "="*70)
    print("[P2.5] 熵系统测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 创建基础表
        import sqlite3
        conn = sqlite3.connect(db_path)
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
                entropy INTEGER DEFAULT NULL,
                entropy_level TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        # 创建熵管理器
        entropy_mgr = EntropyManager(db_path, {'ENABLE_ENTROPY': True})
        
        # 插入高熵数据
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO multimodal_slices (slice_id, memory_path, content) VALUES (?, ?, ?)",
                    ('ent_001', '/projects/discussion', '方案 A 方案 B 方案 C 方案 D 方案 E，待定'))
        conn.commit()
        conn.close()
        
        # 测试熵值计算
        result = entropy_mgr.calculate_entropy('ent_001')
        assert result['new_entropy'] >= 70
        print(f"   ✅ 高熵场景：{result['new_entropy']}分 ({result['new_level']})")
        
        # 插入低熵数据
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO multimodal_slices (slice_id, memory_path, content, iteration_version, iteration_status) VALUES (?, ?, ?, ?, ?)",
                    ('ent_002', '/projects/execution', '已确定方案 B，开始执行', 'v3', 'executing'))
        conn.commit()
        conn.close()
        
        # 测试低熵计算
        result = entropy_mgr.calculate_entropy('ent_002')
        assert result['new_entropy'] < 40
        print(f"   ✅ 低熵场景：{result['new_entropy']}分 ({result['new_level']})")
        
        # 测试项目熵值
        project_result = entropy_mgr.get_project_entropy('/projects')
        assert 'avg_entropy' in project_result
        print(f"   ✅ 项目熵值：{project_result['avg_entropy']:.1f}分")
        
        entropy_mgr.close()
        print("\n   🎉 P2.5 熵系统测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def test_p3_monitor():
    """测试 P3: 监控告警"""
    print("\n" + "="*70)
    print("[P3] 监控告警测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 创建监控面板
        monitor = MonitorDashboard(db_path)
        
        # 测试系统状态
        status = monitor.get_system_status()
        assert 'system' in status
        print(f"   ✅ 系统状态：{status['status']}")
        print(f"      CPU: {status['system']['cpu_percent']:.1f}%")
        print(f"      内存：{status['system']['memory_percent']:.1f}%")
        
        # 测试记录指标
        monitor.record_metric('test_metric', 50.0)
        metrics = monitor.get_metrics('test_metric', '24h')
        assert len(metrics) >= 1
        print(f"   ✅ 记录指标：{len(metrics)}条")
        
        # 测试检查告警
        alerts = monitor.check_alerts()
        print(f"   ✅ 检查告警：{len(alerts)}个")
        
        monitor.close()
        print("\n   🎉 P3 监控告警测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def test_p3_audit():
    """测试 P3: 日志审计"""
    print("\n" + "="*70)
    print("[P3] 日志审计测试")
    print("="*70)
    
    db_fd, db_path, storage_dir = create_test_environment()
    
    try:
        # 创建审计日志器
        logger = AuditLogger(db_path)
        
        # 测试记录审计日志
        logger.log('user_001', 'ai_call', 'slice_123', {'model': 'qwen-vl-max'})
        logger.log('user_001', 'storage_upload', 'file_456', {'size': 1024})
        
        logs = logger.query('user_001', time_range='24h')
        assert len(logs) == 2
        print(f"   ✅ 记录审计日志：{len(logs)}条")
        
        # 测试记录系统日志
        logger.log_system('DITING_', '系统启动', 'INFO')
        sys_logs = logger.query_system(time_range='24h')
        assert len(sys_logs) >= 1
        print(f"   ✅ 记录系统日志：{len(sys_logs)}条")
        
        # 测试导出
        csv_data = logger.export(time_range='24h', format='csv')
        assert len(csv_data) > 0
        print(f"   ✅ 导出 CSV: {len(csv_data)}字节")
        
        # 测试统计
        stats = logger.get_statistics('24h')
        assert stats['total'] >= 1
        print(f"   ✅ 日志统计：{stats['total']}条")
        
        logger.close()
        print("\n   🎉 P3 日志审计测试通过")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("\n" + "🧪"*35)
    print("DITING_ 完整测试套件 - 覆盖所有 Task 场景")
    print("🧪"*35)
    print(f"\n开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("P0 多模态基础", test_p0_multimodal),
        ("P1 智能优化", test_p1_intelligence),
        ("P2 温度系统", test_p2_temperature),
        ("P2.5 熵系统", test_p25_entropy),
        ("P3 监控告警", test_p3_monitor),
        ("P3 日志审计", test_p3_audit)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n   ❌ {name} 异常：{e}")
            results[name] = False
    
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
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
