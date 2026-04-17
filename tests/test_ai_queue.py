"""
异步 AI 调用队列测试（TDD）
"""

import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.ai_queue import AIQueueManager, TaskStatus


def create_test_queue():
    """创建测试队列"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    queue = AIQueueManager(db_path, {
        'AI_MAX_CONCURRENT': 2,
        'AI_TASK_TIMEOUT': 60
    })
    return queue, db_fd


def test_enqueue_task():
    """测试 1: 添加任务到队列"""
    print("\n[测试 1] 添加任务...")
    
    queue, db_fd = create_test_queue()
    
    try:
        task_id = queue.enqueue(
            file_path='/storage/test.jpg',
            file_type='image',
            memory_path='/test/image',
            user_id='user_001',
            priority=5
        )
        
        assert task_id is not None
        assert len(task_id) > 0
        
        # 检查队列状态
        status = queue.get_queue_status()
        assert status['pending'] == 1
        
        print(f"   ✅ 任务添加成功：{task_id[:8]}...")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_dequeue_task():
    """测试 2: 从队列获取任务"""
    print("\n[测试 2] 获取任务...")
    
    queue, db_fd = create_test_queue()
    
    try:
        # 添加两个任务
        task1_id = queue.enqueue(
            '/storage/test1.jpg', 'image', '/test/1', 'user_001', priority=3
        )
        task2_id = queue.enqueue(
            '/storage/test2.jpg', 'image', '/test/2', 'user_001', priority=8
        )
        
        # 获取任务（应该先获取高优先级的 task2）
        task = queue.dequeue()
        
        print(f"   调试：task={task.task_id if task else None}, task2_id={task2_id}")
        
        if task is None:
            raise AssertionError("队列为空")
        if task.task_id != task2_id:
            raise AssertionError(f"优先级错误：期望 {task2_id[:8]}..., 实际 {task.task_id[:8]}...")
        if task.status != TaskStatus.PROCESSING:
            raise AssertionError(f"状态错误：{task.status}")
        
        print(f"   ✅ 优先级队列正常：{task.task_id[:8]}...")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_complete_task():
    """测试 3: 标记任务完成"""
    print("\n[测试 3] 完成任务...")
    
    queue, db_fd = create_test_queue()
    
    try:
        task_id = queue.enqueue(
            '/storage/test.jpg', 'image', '/test/image', 'user_001'
        )
        
        # 标记完成
        result = {'summary': '测试完成', 'keywords': ['测试']}
        queue.complete_task(task_id, result)
        
        # 检查状态
        task = queue.get_task(task_id)
        assert task.status == TaskStatus.DONE
        assert task.result == result
        
        print(f"   ✅ 任务完成正常")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_fail_task_with_retry():
    """测试 4: 任务失败重试"""
    print("\n[测试 4] 失败重试...")
    
    queue, db_fd = create_test_queue()
    
    try:
        task_id = queue.enqueue(
            '/storage/test.jpg', 'image', '/test/image', 'user_001'
        )
        
        # 第一次失败
        queue.fail_task(task_id, 'AI 调用失败')
        
        task = queue.get_task(task_id)
        assert task.retry_count == 1
        assert task.status == TaskStatus.PENDING  # 应该回到待处理
        
        # 第二次失败
        queue.fail_task(task_id, 'AI 调用失败')
        
        task = queue.get_task(task_id)
        assert task.retry_count == 2
        
        print(f"   ✅ 重试机制正常")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_fail_task_max_retries():
    """测试 5: 超过最大重试次数"""
    print("\n[测试 5] 超过最大重试...")
    
    queue, db_fd = create_test_queue()
    
    try:
        task_id = queue.enqueue(
            '/storage/test.jpg', 'image', '/test/image', 'user_001'
        )
        
        # 失败 3 次（超过 max_retries=3）
        for i in range(4):
            queue.fail_task(task_id, f'失败 {i+1}')
        
        task = queue.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.retry_count == 3  # 最多重试 3 次
        
        print(f"   ✅ 最大重试限制正常")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_get_user_tasks():
    """测试 6: 获取用户任务列表"""
    print("\n[测试 6] 用户任务列表...")
    
    queue, db_fd = create_test_queue()
    
    try:
        # 添加多个任务
        for i in range(5):
            queue.enqueue(
                f'/storage/test{i}.jpg', 'image', f'/test/{i}', 'user_001'
            )
        
        # 获取用户任务
        tasks = queue.get_user_tasks('user_001')
        
        assert len(tasks) == 5
        
        print(f"   ✅ 用户任务列表正常：{len(tasks)} 个任务")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_queue_status():
    """测试 7: 队列状态统计"""
    print("\n[测试 7] 队列状态...")
    
    queue, db_fd = create_test_queue()
    
    try:
        # 添加不同状态的任务
        queue.enqueue('/storage/1.jpg', 'image', '/test/1', 'user_001')
        queue.enqueue('/storage/2.jpg', 'image', '/test/2', 'user_001')
        
        task3_id = queue.enqueue('/storage/3.jpg', 'image', '/test/3', 'user_001')
        queue.complete_task(task3_id, {'result': 'done'})
        
        # 检查状态
        status = queue.get_queue_status()
        
        assert status['pending'] == 2
        assert status['done'] == 1
        
        print(f"   ✅ 队列状态正常：{status}")
        
    finally:
        queue.close()
        os.close(db_fd)


def test_priority_order():
    """测试 8: 优先级顺序"""
    print("\n[测试 8] 优先级顺序...")
    
    queue, db_fd = create_test_queue()
    
    try:
        # 添加不同优先级的任务
        task_ids = []
        for priority in [1, 5, 3, 9, 2]:
            task_id = queue.enqueue(
                '/storage/test.jpg', 'image', '/test', 'user_001', priority=priority
            )
            task_ids.append(task_id)
        
        # 按优先级出队
        expected_order = [3, 1, 2, 4, 0]  # 优先级 9,5,3,2,1 对应的索引
        
        for expected_idx in expected_order:
            task = queue.dequeue()
            assert task.task_id == task_ids[expected_idx]
        
        print(f"   ✅ 优先级顺序正常")
        
    finally:
        queue.close()
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("异步 AI 调用队列测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_enqueue_task,
        test_dequeue_task,
        test_complete_task,
        test_fail_task_with_retry,
        test_fail_task_max_retries,
        test_get_user_tasks,
        test_queue_status,
        test_priority_order
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
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print(f"通过率：{passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
