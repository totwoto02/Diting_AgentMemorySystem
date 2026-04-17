"""
测试 MFT 与 KG V2 的集成
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diting.mft import MFT


class TestMFTKGIntegration:
    """测试 MFT 与 KG 集成"""

    def test_mft_with_kg_auto_build(self):
        """测试 MFT create 时自动建图"""
        # 创建带 KG 的 MFT
        mft = MFT(db_path=":memory:", kg_db_path=":memory:")
        
        # 验证 KG 已初始化
        assert mft.kg is not None, "KG 应该已初始化"
        
        # 创建记忆
        try:
            mft.create("/test/doc1", "NOTE", "测试用户 video game 测试角色 loyal")
        except Exception:
            # 如果路径已存在，忽略（可能是重复测试）
            pass
        
        # 验证 KG 中有概念
        stats = mft.kg.get_stats()
        assert stats["concept_count"] > 0, "应该有概念被提取"
        assert stats["edge_count"] > 0, "应该有边被创建"
        
        print(f"✅ 自动建图成功：{stats['concept_count']} 个概念，{stats['edge_count']} 条边")

    def test_mft_search_with_kg_expansion(self):
        """测试 MFT search 时 KG 扩展"""
        mft = MFT(db_path=":memory:", kg_db_path=":memory:")
        
        # 创建记忆
        mft.create("/test/doc1", "NOTE", "测试用户 video game 测试角色")
        mft.create("/test/doc2", "NOTE", "测试角色 loyal male lead")
        
        # 测试带 KG 扩展的搜索
        result = mft.search_with_kg("测试用户")
        
        # 验证搜索结果
        assert "search_results" in result
        assert "kg_expansion" in result
        
        # 验证 KG 扩展
        if result["kg_expansion"]:
            assert "expanded_concepts" in result["kg_expansion"]
            print(f"✅ KG 扩展成功：{result['kg_expansion']['expanded_concepts']}")

    def test_keyword_extraction(self):
        """测试关键词提取"""
        mft = MFT(db_path=":memory:")
        
        text = "测试用户 video game 测试角色 loyal male lead"
        keywords = mft._extract_keywords(text, top_k=5)
        
        assert len(keywords) > 0
        assert "测试用户" in keywords or "video game" in keywords
        
        print(f"✅ 关键词提取成功：{keywords}")

    def test_mft_without_kg(self):
        """测试不带 KG 的 MFT 正常工作"""
        mft = MFT(db_path=":memory:")
        
        # 验证 KG 未初始化
        assert mft.kg is None, "KG 应该为 None"
        
        # 创建记忆应该正常工作
        inode = mft.create("/test/doc1", "NOTE", "测试内容")
        assert inode > 0
        
        # search_with_kg 应该返回空扩展
        result = mft.search_with_kg("测试")
        assert result["kg_expansion"] is None
        
        print("✅ 不带 KG 的 MFT 正常工作")


def main():
    """运行测试"""
    print("\n" + "="*60)
    print("MFT 与 KG V2 集成测试")
    print("="*60 + "\n")
    
    test = TestMFTKGIntegration()
    
    try:
        print("[测试 1] MFT create 自动建图...")
        test.test_mft_with_kg_auto_build()
        
        print("\n[测试 2] MFT search KG 扩展...")
        test.test_mft_search_with_kg_expansion()
        
        print("\n[测试 3] 关键词提取...")
        test.test_keyword_extraction()
        
        print("\n[测试 4] 不带 KG 的 MFT...")
        test.test_mft_without_kg()
        
        print("\n" + "="*60)
        print("🎉 所有集成测试通过！")
        print("="*60 + "\n")
        
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
