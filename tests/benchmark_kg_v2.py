"""
知识图谱 V2 性能基准测试

测试不同数据量级下的性能表现
"""

import sys
import os
import time
import random
import string
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.knowledge_graph_v2 import KnowledgeGraphV2


def generate_random_text(length=100):
    """生成随机中文文本"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    words = []
    for _ in range(length // 5):
        word_len = random.randint(2, 4)
        word = ''.join(random.choices(chars, k=word_len))
        words.append(word)
    return ' '.join(words)


def extract_keywords_simple(text):
    """简单关键词提取（2-4 字）"""
    words = text.replace(",", " ").replace(";", " ").split()
    return [w for w in words if 2 <= len(w) <= 4]


def benchmark_add_concepts(kg, count):
    """基准测试：添加概念"""
    start = time.time()
    
    for i in range(count):
        name = f"概念_{i}"
        kg.add_concept(name, "test", [f"别名_{i}"])
    
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_add_edges(kg, count):
    """基准测试：添加边"""
    start = time.time()
    
    for i in range(count):
        from_concept = f"概念_{random.randint(0, count-1)}"
        to_concept = f"概念_{random.randint(0, count-1)}"
        kg.add_edge(from_concept, to_concept, "related", 1.0)
    
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_query(kg, concept_count, query_count):
    """基准测试：查询性能"""
    start = time.time()
    
    for i in range(query_count):
        concept_name = f"概念_{random.randint(0, concept_count-1)}"
        kg.get_concept_by_name(concept_name)
        kg.get_related_concepts(concept_name, top_k=5)
    
    elapsed = time.time() - start
    return elapsed, query_count / elapsed


def benchmark_search_expansion(kg, concept_count, search_count):
    """基准测试：搜索扩展性能"""
    start = time.time()
    
    for i in range(search_count):
        concept_name = f"概念_{random.randint(0, concept_count-1)}"
        kg.search_with_expansion(concept_name, max_depth=2)
    
    elapsed = time.time() - start
    return elapsed, search_count / elapsed


def run_benchmark(scale, db_path=":memory:"):
    """运行基准测试"""
    print(f"\n{'='*70}")
    print(f"数据规模：{scale:,} 个概念")
    print(f"{'='*70}")
    
    # 创建图谱
    kg = KnowledgeGraphV2(db_path)
    
    # 测试 1: 添加概念
    print(f"\n[测试 1] 添加 {scale:,} 个概念...")
    t1, ops1 = benchmark_add_concepts(kg, scale)
    print(f"   ⏱️  耗时：{t1:.3f} 秒")
    print(f"   📊 速度：{ops1:.0f} 概念/秒")
    
    # 测试 2: 添加边（10 倍于概念数）
    edge_count = scale * 10
    print(f"\n[测试 2] 添加 {edge_count:,} 条边...")
    t2, ops2 = benchmark_add_edges(kg, edge_count)
    print(f"   ⏱️  耗时：{t2:.3f} 秒")
    print(f"   📊 速度：{ops2:.0f} 边/秒")
    
    # 测试 3: 查询性能
    query_count = min(1000, scale)
    print(f"\n[测试 3] 查询 {query_count:,} 次...")
    t3, ops3 = benchmark_query(kg, scale, query_count)
    print(f"   ⏱️  耗时：{t3:.3f} 秒")
    print(f"   📊 速度：{ops3:.0f} 查询/秒")
    print(f"   ⚡ 平均延迟：{t3/query_count*1000:.2f} ms/查询")
    
    # 测试 4: 搜索扩展
    search_count = min(100, scale // 10)
    print(f"\n[测试 4] 搜索扩展 {search_count:,} 次...")
    t4, ops4 = benchmark_search_expansion(kg, scale, search_count)
    print(f"   ⏱️  耗时：{t4:.3f} 秒")
    print(f"   📊 速度：{ops4:.0f} 搜索/秒")
    print(f"   ⚡ 平均延迟：{t4/search_count*1000:.2f} ms/搜索")
    
    # 统计信息
    stats = kg.get_stats()
    print(f"\n[统计] 概念数：{stats['concept_count']:,}, 边数：{stats['edge_count']:,}")
    
    return {
        "scale": scale,
        "add_concept_ops": ops1,
        "add_edge_ops": ops2,
        "query_ops": ops3,
        "search_ops": ops4,
        "query_latency_ms": t3/query_count*1000,
        "search_latency_ms": t4/search_count*1000,
        "stats": stats
    }


def main():
    """运行所有基准测试"""
    print("\n" + "🚀" * 35)
    print("知识图谱 V2 性能基准测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀" * 35 + "\n")
    
    results = []
    
    # 小规模测试 (100 概念)
    results.append(run_benchmark(100))
    
    # 中等规模测试 (1000 概念)
    results.append(run_benchmark(1000))
    
    # 大规模测试 (10000 概念)
    results.append(run_benchmark(10000))
    
    # 超大规模测试 (100000 概念)
    print(f"\n{'='*70}")
    print("⚠️  注意：超大规模测试可能需要较长时间...")
    print(f"{'='*70}")
    results.append(run_benchmark(100000))
    
    # 汇总报告
    print("\n" + "📊" * 35)
    print("性能基准测试汇总报告")
    print("📊" * 35)
    
    print(f"\n{'数据规模':<15} {'添加概念':<12} {'添加边':<12} {'查询':<12} {'搜索':<12} {'查询延迟':<12} {'搜索延迟':<12}")
    print(f"{'':15} {'(ops/s)':<12} {'(ops/s)':<12} {'(ops/s)':<12} {'(ops/s)':<12} {'(ms)':<12} {'(ms)':<12}")
    print("-" * 95)
    
    for r in results:
        scale = r["scale"]
        print(f"{scale:>12,} {r['add_concept_ops']:>12.0f} {r['add_edge_ops']:>12.0f} "
              f"{r['query_ops']:>12.0f} {r['search_ops']:>12.0f} "
              f"{r['query_latency_ms']:>12.2f} {r['search_latency_ms']:>12.2f}")
    
    # 性能分析
    print(f"\n{'='*70}")
    print("性能分析")
    print(f"{'='*70}")
    
    # 对比小规模 vs 大规模
    small = results[0]
    large = results[-1]
    
    print(f"\n📈 规模增长：{small['scale']:,} → {large['scale']:,} ({large['scale']/small['scale']:.0f}x)")
    print(f"\n⚡ 查询延迟变化：{small['query_latency_ms']:.2f}ms → {large['query_latency_ms']:.2f}ms "
          f"({large['query_latency_ms']/small['query_latency_ms']:.2f}x)")
    print(f"⚡ 搜索延迟变化：{small['search_latency_ms']:.2f}ms → {large['search_latency_ms']:.2f}ms "
          f"({large['search_latency_ms']/small['search_latency_ms']:.2f}x)")
    
    # 性能评级
    print(f"\n{'='*70}")
    print("性能评级")
    print(f"{'='*70}")
    
    avg_query_latency = sum(r['query_latency_ms'] for r in results) / len(results)
    avg_search_latency = sum(r['search_latency_ms'] for r in results) / len(results)
    
    if avg_query_latency < 1:
        print(f"\n✅ 查询性能：优秀 (<1ms)")
    elif avg_query_latency < 10:
        print(f"\n✅ 查询性能：良好 (<10ms)")
    else:
        print(f"\n⚠️  查询性能：一般 (>10ms)")
    
    if avg_search_latency < 10:
        print(f"✅ 搜索扩展性能：优秀 (<10ms)")
    elif avg_search_latency < 50:
        print(f"✅ 搜索扩展性能：良好 (<50ms)")
    else:
        print(f"⚠️  搜索扩展性能：一般 (>50ms)")
    
    # 建议
    print(f"\n{'='*70}")
    print("优化建议")
    print(f"{'='*70}")
    
    if large['query_latency_ms'] > 10:
        print("\n💡 建议：")
        print("   - 考虑添加更多索引")
        print("   - 优化查询 SQL")
        print("   - 使用查询缓存")
    else:
        print("\n✅ 当前性能表现优秀，无需优化")
    
    print(f"\n{'='*70}")
    print("🎉 性能基准测试完成！")
    print(f"{'='*70}\n")
    
    return results


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
