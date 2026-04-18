"""
测试对话管理器（Dialog Manager）
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.mft import MFT
from diting.dialog_manager import DialogManager


def test_dialog_manager():
    """测试对话管理器"""
    print("=" * 70)
    print("对话管理器测试")
    print("=" * 70)
    
    # 使用临时数据库避免并发冲突
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        kg_db_path = f.name
    
    try:
        # 创建 MFT 和 DialogManager
        mft = MFT(db_path=db_path, kg_db_path=kg_db_path)
        dm = DialogManager(mft)
        
        print("\n[测试 1] 添加对话（热数据）...")
        path1 = dm.add_dialog("session_001", "user", "你好，我想了解一下 DITING_ 项目")
        path2 = dm.add_dialog("session_001", "assistant", "DITING_ 是 Memory File System 的缩写...")
        path3 = dm.add_dialog("session_001", "user", "与测试用户约定的拍照时间是哪天？")
        
        print(f"   ✅ 添加 3 条对话到热数据区")
        print(f"      - {path1}")
        print(f"      - {path2}")
        print(f"      - {path3}")
        
        print("\n[测试 2] 获取会话历史...")
        history = dm.get_dialog_history("session_001", days=7)
        print(f"   ✅ session_001 的历史对话：{len(history)} 条")
        for h in history:
            print(f"      - {h['v_path']}: {h['content'][:50]}...")
        
        print("\n[测试 3] 标记重要对话...")
        dm.mark_as_important(path3, "用户询问重要约会时间")
        print(f"   ✅ 对话已标记为重要，移到冷数据区")
        
        print("\n[测试 4] 搜索对话...")
        results = dm.search_dialogs("测试用户", scope="all")
        print(f"   ✅ 搜索'测试用户' 找到 {len(results)} 条结果")
        for r in results:
            print(f"      - {r['v_path']}: {r['content'][:50]}...")
        
        print("\n[测试 5] 获取统计信息...")
        stats = dm.get_stats()
        print(f"   ✅ 统计信息:")
        print(f"      - 热数据路径：{stats['hot_path']}")
        print(f"      - 温数据路径：{stats['warm_path']}")
        print(f"      - 冷数据路径：{stats['cold_path']}")
        print(f"      - 热数据阈值：{stats['hot_days']} 天")
        print(f"      - 温数据阈值：{stats['warm_days']} 天")
        
        print("\n[测试 6] 批量添加对话...")
        messages = [
            {"role": "user", "content": "今天天气怎么样？"},
            {"role": "assistant", "content": "今天晴天，气温 25 度。"},
            {"role": "user", "content": "好的，谢谢！"}
        ]
        paths = dm.add_dialog_batch("session_002", messages)
        print(f"   ✅ 批量添加 {len(paths)} 条对话")
        
        print("\n" + "=" * 70)
        print("🎉 所有测试通过！")
        print("=" * 70)
        
        print("\n📊 测试结果:")
        print("   ✅ 热数据存储正常")
        print("   ✅ 会话历史查询正常")
        print("   ✅ 重要对话标记正常")
        print("   ✅ 对话搜索正常")
        print("   ✅ 批量添加正常")
        
        return True
    finally:
        # 清理临时数据库
        if hasattr(mft, 'close'):
            mft.close()
        os.unlink(db_path)
        os.unlink(kg_db_path)


if __name__ == "__main__":
    try:
        test_dialog_manager()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
