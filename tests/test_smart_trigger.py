"""
智能触发策略测试（TDD）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.smart_trigger import SmartTrigger


def test_trigger_important_audio():
    """测试 1: 重要会议录音应调用 AI"""
    print("\n[测试 1] 重要会议录音...")
    
    trigger = SmartTrigger()
    
    file_info = {
        'type': 'audio',
        'size': 5 * 1024 * 1024,
        'filename': '重要会议录音.ogg',
        'memory_path': '/work/meetings/2026-04-15',
        'user_marked': None
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == True, "重要会议录音应调用 AI"
    print("   ✅ 通过：调用 AI")


def test_trigger_temp_screenshot():
    """测试 2: 临时截图不应调用 AI"""
    print("\n[测试 2] 临时截图...")
    
    trigger = SmartTrigger()
    
    file_info = {
        'type': 'image',
        'size': 500 * 1024,
        'filename': '截图 20260415.png',
        'memory_path': '/temp/screenshots',
        'user_marked': None
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == False, "临时截图不应调用 AI"
    print("   ✅ 通过：不调用 AI")


def test_user_mark_important():
    """测试 3: 用户标记重要应调用 AI"""
    print("\n[测试 3] 用户标记重要...")
    
    trigger = SmartTrigger()
    
    file_info = {
        'type': 'image',
        'size': 2 * 1024 * 1024,
        'filename': 'photo.jpg',
        'memory_path': '/photos/2026-04',
        'user_marked': 'important'
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == True, "用户标记重要应调用 AI"
    print("   ✅ 通过：调用 AI")


def test_user_mark_skip():
    """测试 4: 用户标记跳过不应调用 AI"""
    print("\n[测试 4] 用户标记跳过...")
    
    trigger = SmartTrigger()
    
    file_info = {
        'type': 'audio',
        'size': 3 * 1024 * 1024,
        'filename': 'voice.ogg',
        'memory_path': '/notes/2026-04',
        'user_marked': 'skip_ai'
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == False, "用户标记跳过不应调用 AI"
    print("   ✅ 通过：不调用 AI")


def test_quota_limit():
    """测试 5: 配额用尽不应调用 AI"""
    print("\n[测试 5] 配额限制...")
    
    trigger = SmartTrigger({'AI_MONTHLY_QUOTA': 2})
    
    file_info = {
        'type': 'audio',
        'size': 1 * 1024 * 1024,
        'filename': 'voice.ogg',
        'memory_path': '/notes/test',
        'user_marked': None
    }
    
    # 使用 2 次配额
    trigger.use_quota()
    trigger.use_quota()
    
    # 第 3 次应失败
    result = trigger.should_call_ai(file_info)
    
    assert result == False, "配额用尽不应调用 AI"
    
    # 检查配额状态
    status = trigger.get_quota_status()
    assert status['remaining'] == 0, "剩余配额应为 0"
    
    print("   ✅ 通过：配额限制正常")


def test_file_size_too_large():
    """测试 6: 文件过大不应调用 AI"""
    print("\n[测试 6] 文件过大...")
    
    trigger = SmartTrigger()
    
    file_info = {
        'type': 'image',
        'size': 20 * 1024 * 1024,  # 20MB，超过阈值
        'filename': 'large_photo.jpg',
        'memory_path': '/photos/2026-04',
        'user_marked': None
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == False, "文件过大不应调用 AI"
    print("   ✅ 通过：文件大小限制正常")


def test_smart_disabled():
    """测试 7: 智能触发关闭时不应调用 AI"""
    print("\n[测试 7] 智能触发关闭...")
    
    trigger = SmartTrigger({'ENABLE_SMART_TRIGGER': False})
    
    file_info = {
        'type': 'audio',
        'size': 1 * 1024 * 1024,
        'filename': '重要会议.ogg',
        'memory_path': '/work/meetings',
        'user_marked': None
    }
    
    result = trigger.should_call_ai(file_info)
    
    assert result == False, "智能触发关闭时不应调用 AI"
    print("   ✅ 通过：智能触发开关正常")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("智能触发策略测试（TDD）")
    print("=" * 60)
    
    tests = [
        test_trigger_important_audio,
        test_trigger_temp_screenshot,
        test_user_mark_important,
        test_user_mark_skip,
        test_quota_limit,
        test_file_size_too_large,
        test_smart_disabled
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
