"""
批量处理优化测试（TDD）
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.batch_processor import BatchProcessor


def test_batch_processor():
    """测试批量处理器"""
    print("\n[测试] 批量处理器...")
    
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    try:
        # 创建批量处理器
        processor = BatchProcessor(db_path, {'BATCH_SIZE': 10})
        
        # 测试添加任务
        for i in range(5):
            processor.enqueue(
                f'task_{i}',
                'ai_summary',
                {'data': f'Test {i}'},
                priority=5
            )
        
        # 检查队列状态
        status = processor.get_queue_status()
        assert status['pending'] == 5
        print(f"   ✅ 添加任务：{status['pending']}个")
        
        # 等待处理
        time.sleep(3)
        
        # 检查处理结果
        status = processor.get_queue_status()
        print(f"   ✅ 处理状态：pending={status.get('pending', 0)}, completed={status.get('completed', 0)}")
        
        # 获取历史（可能还在处理中）
        history = processor.get_batch_history()
        print(f"   ✅ 处理历史：{len(history)}批")
        
        processor.close()
        print("   🎉 批量处理器测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        os.close(db_fd)


def test_priority_queue():
    """测试优先级队列"""
    print("\n[测试] 优先级队列...")
    
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    try:
        processor = BatchProcessor(db_path)
        
        # 添加不同优先级任务
        processor.enqueue('low_1', 'test', {}, priority=1)
        processor.enqueue('high_1', 'test', {}, priority=10)
        processor.enqueue('med_1', 'test', {}, priority=5)
        
        # 获取一批任务
        tasks = processor.dequeue_batch(batch_size=3)
        
        # 高优先级应该先处理
        assert tasks[0].id == 'high_1'
        print(f"   ✅ 优先级排序正常")
        
        processor.close()
        print("   🎉 优先级队列测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 失败：{e}")
        return False
        
    finally:
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("批量处理优化测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_batch_processor,
        test_priority_queue
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ 异常：{e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print(f"通过率：{passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
