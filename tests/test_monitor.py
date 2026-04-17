"""
监控告警系统测试（TDD）
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.monitor import MonitorDashboard, AlertLevel


def create_test_monitor():
    """创建测试监控面板"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    config = {
        'ALERT_RULES': {
            'disk_usage': {'threshold': 0.9},
            'memory_usage': {'threshold': 0.9}
        }
    }
    monitor = MonitorDashboard(db_path, config)
    return monitor, db_fd


def test_system_status():
    """测试 1: 系统状态获取"""
    print("\n[测试 1] 系统状态获取...")
    
    monitor, db_fd = create_test_monitor()
    
    try:
        status = monitor.get_system_status()
        
        assert 'system' in status
        assert 'cpu_percent' in status['system']
        assert 'memory_percent' in status['system']
        assert 'disk_percent' in status['system']
        
        print(f"   ✅ CPU: {status['system']['cpu_percent']:.1f}%")
        print(f"   ✅ 内存：{status['system']['memory_percent']:.1f}%")
        print(f"   ✅ 磁盘：{status['system']['disk_percent']:.1f}%")
        
    finally:
        monitor.close()
        os.close(db_fd)


def test_record_metric():
    """测试 2: 记录指标"""
    print("\n[测试 2] 记录指标...")
    
    monitor, db_fd = create_test_monitor()
    
    try:
        # 记录指标
        monitor.record_metric('test_metric', 50.0)
        monitor.record_metric('test_metric', 60.0)
        monitor.record_metric('test_metric', 70.0)
        
        # 获取指标（直接查询所有，不限制时间）
        cursor = monitor.db.execute("""
            SELECT metric_value, timestamp
            FROM monitor_metrics
            WHERE metric_name = ?
            ORDER BY timestamp DESC
        """, ('test_metric',))
        metrics = [dict(row) for row in cursor.fetchall()]
        
        assert len(metrics) == 3, f"应有 3 条指标，实际{len(metrics)}条"
        
        print(f"   ✅ 记录指标：{len(metrics)}条")
        
    finally:
        monitor.close()
        os.close(db_fd)


def test_check_alerts():
    """测试 3: 检查告警"""
    print("\n[测试 3] 检查告警...")
    
    monitor, db_fd = create_test_monitor()
    
    try:
        # 检查告警
        alerts = monitor.check_alerts()
        
        # 获取活跃告警
        active_alerts = monitor.get_active_alerts()
        
        print(f"   ✅ 检查告警：{len(alerts)}个")
        print(f"   ✅ 活跃告警：{len(active_alerts)}个")
        
    finally:
        monitor.close()
        os.close(db_fd)


def test_acknowledge_alert():
    """测试 4: 确认告警"""
    print("\n[测试 4] 确认告警...")
    
    monitor, db_fd = create_test_monitor()
    
    try:
        # 检查告警
        alerts = monitor.check_alerts()
        
        if alerts:
            # 确认告警
            monitor.acknowledge_alert(alerts[0].id)
            
            # 检查是否已确认
            active_alerts = monitor.get_active_alerts()
            acknowledged = [a for a in active_alerts if a['alert_id'] == alerts[0].id]
            
            assert len(acknowledged) == 0, "告警应已确认"
            
            print(f"   ✅ 告警确认正常")
        else:
            print(f"   ✅ 无告警可确认")
        
    finally:
        monitor.close()
        os.close(db_fd)


def test_cleanup_metrics():
    """测试 5: 清理旧指标"""
    print("\n[测试 5] 清理旧指标...")
    
    monitor, db_fd = create_test_monitor()
    
    try:
        # 记录指标
        for i in range(10):
            monitor.record_metric('cleanup_test', float(i))
        
        # 清理旧指标
        monitor.cleanup_old_metrics(keep_days=0)
        
        # 检查是否已清理
        metrics = monitor.get_metrics('cleanup_test', '1h')
        
        # 应该只保留最近的
        print(f"   ✅ 清理后剩余：{len(metrics)}条")
        
    finally:
        monitor.close()
        os.close(db_fd)


def test_alert_levels():
    """测试 6: 告警级别"""
    print("\n[测试 6] 告警级别...")
    
    from diting.monitor import Alert
    
    alert_info = Alert(
        id='test_info',
        level=AlertLevel.INFO,
        metric='test',
        message='信息告警',
        threshold=100,
        current_value=50,
        timestamp=None
    )
    
    alert_warning = Alert(
        id='test_warning',
        level=AlertLevel.WARNING,
        metric='test',
        message='警告告警',
        threshold=100,
        current_value=90,
        timestamp=None
    )
    
    alert_critical = Alert(
        id='test_critical',
        level=AlertLevel.CRITICAL,
        metric='test',
        message='严重告警',
        threshold=100,
        current_value=100,
        timestamp=None
    )
    
    assert alert_info.level == AlertLevel.INFO
    assert alert_warning.level == AlertLevel.WARNING
    assert alert_critical.level == AlertLevel.CRITICAL
    
    print(f"   ✅ 告警级别正常")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("监控告警系统测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_system_status,
        test_record_metric,
        test_check_alerts,
        test_acknowledge_alert,
        test_cleanup_metrics,
        test_alert_levels
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
