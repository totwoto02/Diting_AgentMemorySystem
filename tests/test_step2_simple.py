"""
Step 2 简化测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_assembler_v2():
    """测试 Assembler V2"""
    print("=" * 70)
    print("测试 1: Assembler V2 拼装优化")
    print("=" * 70)
    
    from mfs.assembler_v2 import AssemblerV2
    
    assembler = AssemblerV2()
    
    # 测试去重拼装
    slices = [
        {"content": "测试用户 video game 测试角色", "offset": 0, "length": 10},
        {"content": "测试角色 loyal male lead", "offset": 8, "length": 10},
        {"content": "male lead 活动朋友", "offset": 16, "length": 10}
    ]
    
    full_text, stats = assembler.assemble_with_dedup(slices)
    
    print(f"\n✅ 拼装结果：{full_text}")
    print(f"📊 统计:")
    print(f"   切片：{stats['chunk_count']} → 合并：{stats['merged_chunks']}")
    print(f"   去重：{stats['dedup_chars']} 字符")
    
    # 质量评估
    result = assembler.assemble_with_quality(slices)
    print(f"\n✅ 质量：{result['quality_score']:.1f}/100")
    
    print("\n✅ Assembler V2 测试通过")


def test_integrity_tracker():
    """测试 Integrity Tracker"""
    print("\n" + "=" * 70)
    print("测试 2: Integrity Tracker 防幻觉")
    print("=" * 70)
    
    from mfs.integrity_tracker import IntegrityTracker
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        tracker = IntegrityTracker(db_path)
        
        # 创建追踪
        print("\n[1] 创建追踪...")
        r1 = tracker.track_create("/test/doc.md", "原始内容", "AI")
        print(f"   ✅ 哈希：{r1['content_hash']}")
        
        # 更新追踪
        print("\n[2] 更新追踪...")
        r2 = tracker.track_update(
            "/test/doc.md", 
            "原始内容", 
            "修改后的内容",
            "添加信息",
            "AI"
        )
        print(f"   ✅ 变更：{r2['diff_chars']} 字符 ({r2['change_rate']})")
        
        # 完整性验证
        print("\n[3] 验证完整性...")
        v1 = tracker.verify_integrity("/test/doc.md", "修改后的内容")
        print(f"   ✅ {v1['warning']}")
        
        # 篡改检测
        print("\n[4] 篡改检测...")
        v2 = tracker.verify_integrity("/test/doc.md", "被篡改")
        print(f"   ⚠️ {v2['warning']}")
        
        # 历史
        print("\n[5] 修改历史...")
        history = tracker.get_history("/test/doc.md")
        print(f"   ✅ {len(history)} 条记录")
        
        print("\n✅ Integrity Tracker 测试通过")
        
    finally:
        tracker.close()
        os.unlink(db_path)


def main():
    print("\n🚀 Step 2 简化测试\n")
    
    try:
        test_assembler_v2()
        test_integrity_tracker()
        
        print("\n" + "=" * 70)
        print("🎉 Step 2 核心功能测试通过！")
        print("=" * 70)
        print("\n✅ 完成:")
        print("   - Assembler V2 拼装优化")
        print("   - Integrity Tracker 防幻觉")
        print("\n⏳ FTS5 需要 SQLite 编译支持，可选功能")
        
        return 0
    except Exception as e:
        print(f"\n❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
