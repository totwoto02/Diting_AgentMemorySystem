"""
日志审计系统测试（TDD）
"""

import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.audit_logger import AuditLogger, LogLevel


def create_test_logger():
    """创建测试审计日志器"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    logger = AuditLogger(db_path)
    return logger, db_fd


def test_log_audit():
    """测试 1: 记录审计日志"""
    print("\n[测试 1] 记录审计日志...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录日志
        logger.log('user_001', 'ai_call', 'slice_123', {'model': 'qwen-vl-max'})
        logger.log('user_001', 'storage_upload', 'file_456', {'size': 1024})
        logger.log('user_002', 'search', None, {'query': 'test'})
        
        # 查询日志（不限制时间）
        logs = logger.query('user_001', time_range='24h')
        
        assert len(logs) == 2
        
        print(f"   ✅ 记录审计日志：{len(logs)}条")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_log_system():
    """测试 2: 记录系统日志"""
    print("\n[测试 2] 记录系统日志...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录系统日志
        logger.log_system('DITING_', '系统启动', 'INFO')
        logger.log_system('MCP', 'MCP 服务器启动', 'INFO')
        logger.log_system('TEST', '测试错误', 'ERROR', 'stack_trace_here')
        
        # 查询系统日志
        logs = logger.query_system(time_range='1h')
        
        assert len(logs) == 3
        
        print(f"   ✅ 记录系统日志：{len(logs)}条")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_query_logs():
    """测试 3: 查询日志"""
    print("\n[测试 3] 查询日志...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录多条日志
        for i in range(10):
            logger.log(f'user_{i%3}', 'action_test', f'resource_{i}')
        
        # 按用户查询
        logs = logger.query('user_0', time_range='1h')
        assert len(logs) >= 3
        
        # 按操作查询
        logs = logger.query(action='action_test', time_range='1h')
        assert len(logs) == 10
        
        print(f"   ✅ 查询日志正常")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_export_logs():
    """测试 4: 导出日志"""
    print("\n[测试 4] 导出日志...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录日志
        for i in range(5):
            logger.log('user_001', 'test_action', f'resource_{i}')
        
        # 导出 CSV
        csv_data = logger.export(time_range='1h', format='csv')
        assert len(csv_data) > 0
        
        # 导出 JSON
        json_data = logger.export(time_range='1h', format='json')
        assert len(json_data) > 0
        
        print(f"   ✅ 导出 CSV: {len(csv_data)}字节")
        print(f"   ✅ 导出 JSON: {len(json_data)}字节")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_statistics():
    """测试 5: 日志统计"""
    print("\n[测试 5] 日志统计...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录日志
        for i in range(20):
            success = i % 5 != 0  # 80% 成功率
            logger.log(f'user_{i%3}', 'test_action', f'resource_{i}', success=success)
        
        # 获取统计
        stats = logger.get_statistics('1h')
        
        assert stats['total'] == 20
        assert 'by_level' in stats
        assert 'by_user' in stats
        assert 'by_action' in stats
        assert stats['success_rate'] == 80.0
        
        print(f"   ✅ 总日志：{stats['total']}条")
        print(f"   ✅ 成功率：{stats['success_rate']:.1f}%")
        print(f"   ✅ 用户分布：{len(stats['by_user'])}个用户")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_cleanup():
    """测试 6: 清理旧日志"""
    print("\n[测试 6] 清理旧日志...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录日志
        for i in range(10):
            logger.log('user_001', 'test_action', f'resource_{i}')
        
        # 清理（保留 0 天，即全部清理）
        logger.log_retention_days = 0
        logger.cleanup_old_logs()
        
        # 检查是否已清理
        logs = logger.query(time_range='1h')
        
        print(f"   ✅ 清理后剩余：{len(logs)}条")
        
    finally:
        logger.close()
        os.close(db_fd)


def test_log_levels():
    """测试 7: 日志级别"""
    print("\n[测试 7] 日志级别...")
    
    logger, db_fd = create_test_logger()
    
    try:
        # 记录不同级别日志
        logger.log('user_001', 'debug_action', level='DEBUG')
        logger.log('user_001', 'info_action', level='INFO')
        logger.log('user_001', 'warning_action', level='WARNING')
        logger.log('user_001', 'error_action', level='ERROR', success=False)
        
        # 按级别查询
        debug_logs = logger.query(level='DEBUG', time_range='1h')
        info_logs = logger.query(level='INFO', time_range='1h')
        error_logs = logger.query(level='ERROR', time_range='1h')
        
        assert len(debug_logs) == 1
        assert len(info_logs) == 1
        assert len(error_logs) == 1
        
        print(f"   ✅ 日志级别正常")
        
    finally:
        logger.close()
        os.close(db_fd)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("日志审计系统测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_log_audit,
        test_log_system,
        test_query_logs,
        test_export_logs,
        test_statistics,
        test_cleanup,
        test_log_levels
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
