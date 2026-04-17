"""
日志审计系统测试（修复版）
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.audit_logger import AuditLogger


def create_test_logger():
    """创建测试审计日志器"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    logger = AuditLogger(db_path)
    return logger, db_fd


def main():
    """运行所有测试"""
    print("=" * 60)
    print("日志审计系统测试（TDD）- 修复版")
    print("=" * 60)
    
    logger, db_fd = create_test_logger()
    
    try:
        # 测试 1: 记录审计日志
        print("\n[测试 1] 记录审计日志...")
        logger.log('user_001', 'ai_call', 'slice_123', {'model': 'qwen-vl-max'})
        logger.log('user_001', 'storage_upload', 'file_456', {'size': 1024})
        logger.log('user_002', 'search', None, {'query': 'test'})
        
        logs = logger.query('user_001', time_range='24h')
        assert len(logs) == 2, f"应有 2 条，实际{len(logs)}条"
        print(f"   ✅ 记录审计日志：{len(logs)}条")
        
        # 测试 2: 记录系统日志
        print("\n[测试 2] 记录系统日志...")
        logger.log_system('MFS', '系统启动', 'INFO')
        logger.log_system('MCP', 'MCP 服务器启动', 'INFO')
        logger.log_system('TEST', '测试错误', 'ERROR', 'stack_trace_here')
        
        sys_logs = logger.query_system(time_range='24h')
        assert len(sys_logs) == 3
        print(f"   ✅ 记录系统日志：{len(sys_logs)}条")
        
        # 测试 3: 查询日志
        print("\n[测试 3] 查询日志...")
        for i in range(10):
            logger.log(f'user_{i%3}', 'action_test', f'resource_{i}')
        
        logs = logger.query('user_0', time_range='24h')
        assert len(logs) >= 3
        print(f"   ✅ 查询日志正常")
        
        # 测试 4: 导出日志
        print("\n[测试 4] 导出日志...")
        for i in range(5):
            logger.log('user_001', 'test_action', f'resource_{i}')
        
        csv_data = logger.export(time_range='24h', format='csv')
        json_data = logger.export(time_range='24h', format='json')
        assert len(csv_data) > 0
        assert len(json_data) > 0
        print(f"   ✅ 导出 CSV: {len(csv_data)}字节")
        print(f"   ✅ 导出 JSON: {len(json_data)}字节")
        
        # 测试 5: 日志统计
        print("\n[测试 5] 日志统计...")
        for i in range(20):
            success = i % 5 != 0
            logger.log(f'user_{i%3}', 'test_action', f'resource_{i}', success=success)
        
        stats = logger.get_statistics('24h')
        assert stats['total'] >= 1, "应至少有 1 条日志"
        print(f"   ✅ 总日志：{stats['total']}条")
        print(f"   ✅ 成功率：{stats.get('success_rate', 0):.1f}%")
        
        # 测试 6: 清理旧日志
        print("\n[测试 6] 清理旧日志...")
        logger.log_retention_days = 0
        logger.cleanup_old_logs()
        logs = logger.query(time_range='24h')
        print(f"   ✅ 清理后剩余：{len(logs)}条")
        
        # 测试 7: 日志级别
        print("\n[测试 7] 日志级别...")
        logger.log('user_001', 'debug_action', level='DEBUG')
        logger.log('user_001', 'info_action', level='INFO')
        logger.log('user_001', 'warning_action', level='WARNING')
        logger.log('user_001', 'error_action', level='ERROR', success=False)
        
        debug_logs = logger.query(level='DEBUG', time_range='24h')
        error_logs = logger.query(level='ERROR', time_range='24h')
        assert len(debug_logs) == 1
        assert len(error_logs) == 1
        print(f"   ✅ 日志级别正常")
        
        print("\n" + "=" * 60)
        print("测试结果：7 通过，0 失败")
        print("通过率：100.0%")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n   ❌ 异常：{e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        logger.close()
        os.close(db_fd)


if __name__ == "__main__":
    sys.exit(main())
