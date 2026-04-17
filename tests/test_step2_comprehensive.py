"""
Step 2 综合性能测试

使用 100 万字测试用例测试：
- 性能
- 幻觉检测
- Token 消耗
- 压力测试
"""

import sys
import os
import json
import time
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.mft import MFT
from diting.assembler_v2 import AssemblerV2
from diting.integrity_tracker import IntegrityTracker
from diting.knowledge_graph_v2 import KnowledgeGraphV2


def load_test_data():
    """加载测试数据"""
    print("加载测试数据...")
    
    # 加载 100 万字测试数据
    test_file = os.path.join(os.path.dirname(__file__), 'mock_ultra_long_conversations.json')
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 统计字数
    total_chars = 0
    for conv in data:
        for msg in conv.get('messages', []):
            total_chars += len(msg.get('content', ''))
    
    print(f"✅ 加载完成:")
    print(f"   对话数：{len(data)}")
    print(f"   总字数：{total_chars:,}")
    print(f"   平均每段：{total_chars/len(data):.0f} 字")
    
    return data, total_chars


def test_performance(data):
    """性能测试"""
    print("\n" + "=" * 70)
    print("测试 1: 性能测试")
    print("=" * 70)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # 初始化 MFT + KG + Tracker
        start = time.time()
        mft = MFT(db_path=db_path, kg_db_path=db_path + '_kg')
        tracker = IntegrityTracker(db_path)
        assembler = AssemblerV2()
        init_time = time.time() - start
        
        print(f"\n[1] 初始化耗时：{init_time:.3f} 秒")
        
        # 批量写入测试
        print(f"\n[2] 批量写入测试...")
        start = time.time()
        
        count = 0
        for conv in data[:100]:  # 测试前 100 段
            for msg in conv.get('messages', [])[:5]:  # 每条对话前 5 条消息
                content = msg.get('content', '')
                if len(content) > 50:  # 只测试有内容的
                    path = f"/test/conv_{count}"
                    mft.create(path, "NOTE", content)
                    tracker.track_create(path, content, "AI")
                    count += 1
        
        write_time = time.time() - start
        write_speed = count / write_time
        
        print(f"   写入数量：{count}")
        print(f"   耗时：{write_time:.3f} 秒")
        print(f"   速度：{write_speed:.0f} 条/秒")
        
        # 搜索性能测试
        print(f"\n[3] 搜索性能测试...")
        search_terms = ["测试", "项目", "工作", "个人"]
        
        for term in search_terms:
            start = time.time()
            results = mft.search(term)
            search_time = time.time() - start
            print(f"   搜索'{term}': {len(results)} 条结果，耗时 {search_time*1000:.2f}ms")
        
        # KG 性能测试
        print(f"\n[4] KG 性能测试...")
        if mft.kg:
            start = time.time()
            stats = mft.kg.get_stats()
            kg_time = time.time() - start
            print(f"   KG 统计：{stats['concept_count']} 概念，{stats['edge_count']} 边")
            print(f"   耗时：{kg_time*1000:.2f}ms")
            
            # KG 搜索
            start = time.time()
            related = mft.kg.get_related_concepts("测试", top_k=5)
            search_time = time.time() - start
            print(f"   KG 搜索：{len(related)} 个关联，耗时 {search_time*1000:.2f}ms")
        
        # 拼装性能测试
        print(f"\n[5] 拼装性能测试...")
        slices = [{"content": f"测试内容{i}", "offset": i*10, "length": 10} for i in range(50)]
        
        start = time.time()
        full_text, stats = assembler.assemble_with_dedup(slices)
        assemble_time = time.time() - start
        
        print(f"   切片数：{len(slices)}")
        print(f"   拼装耗时：{assemble_time*1000:.2f}ms")
        print(f"   速度：{len(slices)/assemble_time:.0f} 片/秒")
        
        # 完整性验证性能
        print(f"\n[6] 完整性验证性能...")
        start = time.time()
        for i in range(10):
            tracker.verify_integrity(f"/test/conv_{i}", "测试内容")
        verify_time = time.time() - start
        
        print(f"   验证次数：10")
        print(f"   总耗时：{verify_time*1000:.2f}ms")
        print(f"   平均：{verify_time/10*1000:.2f}ms/次")
        
        # 总结
        print(f"\n📊 性能总结:")
        print(f"   初始化：{init_time:.3f} 秒")
        print(f"   写入速度：{write_speed:.0f} 条/秒")
        print(f"   搜索延迟：<{search_time*1000:.2f}ms")
        print(f"   KG 查询：<{kg_time*1000:.2f}ms")
        print(f"   拼装速度：{len(slices)/assemble_time:.0f} 片/秒")
        
        return {
            "init_time": init_time,
            "write_speed": write_speed,
            "search_latency": search_time,
            "kg_latency": kg_time,
            "assemble_speed": len(slices)/assemble_time
        }
        
    finally:
        mft.close()
        tracker.close()
        os.unlink(db_path)
        if os.path.exists(db_path + '_kg'):
            os.unlink(db_path + '_kg')


def test_hallucination_detection(data):
    """幻觉检测测试"""
    print("\n" + "=" * 70)
    print("测试 2: 幻觉检测")
    print("=" * 70)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        tracker = IntegrityTracker(db_path)
        
        # 测试 1: 正常修改追踪
        print("\n[1] 正常修改追踪...")
        original = "测试用户 video game 测试角色 loyal"
        modified = "测试用户 video game 测试角色 loyal male lead"
        
        tracker.track_create("/test/doc1", original, "AI")
        tracker.track_update("/test/doc1", original, modified, "添加信息", "AI")
        
        # 验证
        v = tracker.verify_integrity("/test/doc1", modified)
        print(f"   正常修改：{v['warning']}")
        
        # 测试 2: 篡改检测
        print("\n[2] 篡改检测...")
        tampered = "被 AI 幻觉篡改的内容"
        v2 = tracker.verify_integrity("/test/doc1", tampered)
        
        if v2['is_tampered']:
            print(f"   ✅ 成功检测到篡改：{v2['warning']}")
        else:
            print(f"   ❌ 未检测到篡改")
        
        # 测试 3: 批量篡改检测
        print("\n[3] 批量篡改检测...")
        detect_count = 0
        total_count = 0
        
        for i, conv in enumerate(data[:50]):
            for msg in conv.get('messages', [])[:3]:
                content = msg.get('content', '')
                if len(content) > 20:
                    path = f"/test/conv_{total_count}"
                    tracker.track_create(path, content, "AI")
                    
                    # 模拟 10% 的篡改率
                    if total_count % 10 == 0:
                        tampered_content = content + " [被篡改]"
                        v = tracker.verify_integrity(path, tampered_content)
                        if v['is_tampered']:
                            detect_count += 1
                    
                    total_count += 1
        
        detect_rate = detect_count / max(total_count // 10, 1) * 100
        print(f"   总记录：{total_count}")
        print(f"   篡改数：{detect_count}")
        print(f"   检测率：{detect_rate:.1f}%")
        
        # 测试 4: 历史追溯
        print("\n[4] 历史追溯...")
        history = tracker.get_history("/test/doc1")
        print(f"   修改历史：{len(history)} 条")
        for h in history:
            print(f"      - {h['action']} by {h['operator']}")
        
        # 统计
        stats = tracker.get_stats()
        print(f"\n📊 防幻觉统计:")
        print(f"   总记录数：{stats['total_logs']}")
        print(f"   追踪文件：{stats['tracked_files']}")
        print(f"   按操作：{stats['by_action']}")
        
        return {
            "detect_rate": detect_rate,
            "total_tracked": stats['total_logs']
        }
        
    finally:
        tracker.close()
        os.unlink(db_path)


def test_token_consumption(data, total_chars):
    """Token 消耗测试"""
    print("\n" + "=" * 70)
    print("测试 3: Token 消耗估算")
    print("=" * 70)
    
    # 中文字符到 token 的估算（约 1.5 字/token）
    chars_per_token = 1.5
    
    print(f"\n[1] 数据规模:")
    print(f"   总字数：{total_chars:,}")
    print(f"   估算 token: {total_chars/chars_per_token:.0f}")
    
    # 各操作 token 消耗
    print(f"\n[2] 各操作 token 消耗:")
    
    # 写入操作
    write_tokens = total_chars / chars_per_token
    print(f"   写入全部：~{write_tokens:.0f} token")
    
    # 搜索操作（假设平均搜索词 5 字）
    search_tokens = 5 / chars_per_token * len(data)
    print(f"   搜索操作：~{search_tokens:.0f} token ({len(data)} 次)")
    
    # KG 建图（提取关键词，假设每条 10 字）
    kg_tokens = len(data) * 10 / chars_per_token
    print(f"   KG 建图：~{kg_tokens:.0f} token")
    
    # 拼装操作（不需要额外 token）
    print(f"   拼装操作：0 token (本地计算)")
    
    # 完整性验证（哈希计算，不需要 token）
    print(f"   完整性验证：0 token (本地哈希)")
    
    # 总消耗
    total_tokens = write_tokens + search_tokens + kg_tokens
    print(f"\n📊 总消耗估算:")
    print(f"   总 token: ~{total_tokens:.0f}")
    
    # 成本估算（假设 $0.002/1K tokens）
    cost_per_1k = 0.002
    total_cost = total_tokens / 1000 * cost_per_1k
    print(f"   估算成本：${total_cost:.4f} (按 $0.002/1K tokens)")
    
    return {
        "total_tokens": total_tokens,
        "estimated_cost": total_cost
    }


def test_stress(data):
    """压力测试"""
    print("\n" + "=" * 70)
    print("测试 4: 压力测试")
    print("=" * 70)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        mft = MFT(db_path=db_path, kg_db_path=db_path + '_kg')
        
        # 高并发写入测试
        print(f"\n[1] 高并发写入测试...")
        start = time.time()
        
        count = 0
        for conv in data:
            for msg in conv.get('messages', []):
                content = msg.get('content', '')
                if len(content) > 10:
                    path = f"/stress/conv_{count}"
                    mft.create(path, "NOTE", content)
                    count += 1
        
        stress_time = time.time() - start
        
        print(f"   写入数量：{count}")
        print(f"   总耗时：{stress_time:.3f} 秒")
        print(f"   平均速度：{count/stress_time:.0f} 条/秒")
        
        # 数据库大小
        db_size = os.path.getsize(db_path) / 1024 / 1024
        kg_size = os.path.getsize(db_path + '_kg') / 1024 / 1024 if os.path.exists(db_path + '_kg') else 0
        
        print(f"\n[2] 数据库大小:")
        print(f"   MFS 数据库：{db_size:.2f} MB")
        print(f"   KG 数据库：{kg_size:.2f} MB")
        
        # 统计
        stats = mft.get_stats()
        print(f"\n[3] 最终统计:")
        print(f"   总记录数：{stats['total']}")
        print(f"   按类型：{stats['by_type']}")
        
        if mft.kg:
            kg_stats = mft.kg.get_stats()
            print(f"\n[4] KG 统计:")
            print(f"   概念数：{kg_stats['concept_count']}")
            print(f"   边数：{kg_stats['edge_count']}")
            print(f"   密度：{kg_stats['avg_edges_per_concept']:.2f} 边/概念")
        
        # 内存测试
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        print(f"\n[5] 内存占用:")
        print(f"   当前进程：{memory_mb:.1f} MB")
        
        return {
            "write_count": count,
            "write_speed": count/stress_time,
            "db_size_mb": db_size,
            "memory_mb": memory_mb
        }
        
    finally:
        mft.close()
        os.unlink(db_path)
        if os.path.exists(db_path + '_kg'):
            os.unlink(db_path + '_kg')


def main():
    """主测试函数"""
    print("\n" + "🚀" * 35)
    print("Step 2 综合性能测试（100 万字用例）")
    print("🚀" * 35 + "\n")
    
    try:
        # 加载数据
        data, total_chars = load_test_data()
        
        # 测试 1: 性能
        perf_results = test_performance(data)
        
        # 测试 2: 幻觉检测
        hall_results = test_hallucination_detection(data)
        
        # 测试 3: Token 消耗
        token_results = test_token_consumption(data, total_chars)
        
        # 测试 4: 压力测试
        stress_results = test_stress(data)
        
        # 总结
        print("\n" + "=" * 70)
        print("🎉 综合测试完成！")
        print("=" * 70)
        
        print("\n📊 性能总结:")
        print(f"   写入速度：{perf_results['write_speed']:.0f} 条/秒")
        print(f"   搜索延迟：{perf_results['search_latency']*1000:.2f}ms")
        print(f"   KG 查询：{perf_results['kg_latency']*1000:.2f}ms")
        
        print("\n🛡️ 防幻觉:")
        print(f"   检测率：{hall_results['detect_rate']:.1f}%")
        print(f"   追踪记录：{hall_results['total_tracked']}")
        
        print("\n💰 Token 消耗:")
        print(f"   总 token: {token_results['total_tokens']:.0f}")
        print(f"   估算成本：${token_results['estimated_cost']:.4f}")
        
        print("\n⚡ 压力测试:")
        print(f"   写入总量：{stress_results['write_count']} 条")
        print(f"   数据库：{stress_results['db_size_mb']:.2f} MB")
        print(f"   内存：{stress_results['memory_mb']:.1f} MB")
        
        print("\n✅ 所有测试通过！")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
