"""
测试 LLM 语义评分器

测试 TTLCache 和 SemanticScorer 的核心功能
"""

import time
import unittest.mock as mock

import pytest

from diting.errors import LLMAPIError
from diting.semantic_scorer import SemanticScorer, TTLCache


class TestTTLCache:
    """测试带 TTL 的 LRU 缓存"""

    def test_put_and_get(self):
        """测试放入和获取"""
        cache = TTLCache(capacity=3, ttl_seconds=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None

    def test_ttl_expiration(self):
        """测试 TTL 过期"""
        cache = TTLCache(capacity=3, ttl_seconds=1)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_capacity_limit(self):
        """测试容量限制"""
        cache = TTLCache(capacity=2, ttl_seconds=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = TTLCache(capacity=2, ttl_seconds=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")
        cache.put("key3", "value3")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_cleanup_expired(self):
        """测试清理过期条目"""
        cache = TTLCache(capacity=3, ttl_seconds=1)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        time.sleep(1.5)
        cache.put("key3", "value3")

        expired_count = cache.cleanup_expired()
        assert expired_count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_get_stats(self):
        """测试统计信息"""
        cache = TTLCache(capacity=3, ttl_seconds=10)

        cache.put("key1", "value1")
        cache.get("key1")
        cache.get("key2")

        stats = cache.get_stats()
        assert stats["capacity"] == 3
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestSemanticScorer:
    """测试 LLM 语义评分器"""

    def test_init_with_api_key(self):
        """测试初始化（有 API Key）"""
        config = {
            "llm_provider": "dashscope",
            "llm_api_key": "test-key",
            "llm_model": "qwen-turbo",
            "cache_enabled": True,
            "cache_ttl": 3600,
        }
        scorer = SemanticScorer(config)

        assert scorer.enabled is True
        assert scorer.provider == "dashscope"
        assert scorer.model == "qwen-turbo"
        assert scorer.cache is not None

    def test_init_without_api_key(self):
        """测试初始化（无 API Key）"""
        config = {
            "llm_provider": "dashscope",
            "llm_api_key": "",
            "llm_model": "qwen-turbo",
        }
        scorer = SemanticScorer(config)

        assert scorer.enabled is False

    def test_fallback_to_bm25(self):
        """测试降级到 BM25"""
        config = {
            "llm_api_key": "",
        }
        scorer = SemanticScorer(config)

        candidates = [
            {"inode": 1, "v_path": "/test/1", "content": "test 1", "rank": -5.0},
            {"inode": 2, "v_path": "/test/2", "content": "test 2", "rank": -2.0},
        ]

        result = scorer._fallback_to_bm25(candidates)

        assert len(result) == 2
        assert "semantic_score" in result[0]
        assert result[0]["semantic_score"] > result[1]["semantic_score"]

    def test_build_prompt(self):
        """测试构建 prompt"""
        config = {
            "llm_api_key": "test-key",
        }
        scorer = SemanticScorer(config)

        query = "用户偏好"
        candidates = [
            {"v_path": "/user/prefs", "content": "用户偏好深色模式"},
            {"v_path": "/user/settings", "content": "用户设置简洁回复"},
        ]

        prompt = scorer._build_prompt(query, candidates, None)

        assert "用户偏好" in prompt
        assert "/user/prefs" in prompt
        assert "/user/settings" in prompt
        assert "[分数1, 分数2]" in prompt or "JSON 数组" in prompt

    def test_parse_response_valid(self):
        """测试解析有效响应"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        text = "[85, 72, 30]"
        result = scorer._parse_response(text, 3)

        assert len(result) == 3
        assert result[0] == 85.0
        assert result[1] == 72.0
        assert result[2] == 30.0

    def test_parse_response_with_extra_text(self):
        """测试解析带额外文本的响应"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        text = "好的，以下是评分结果：[85, 72, 30]"
        result = scorer._parse_response(text, 3)

        assert len(result) == 3
        assert result[0] == 85.0

    def test_parse_response_invalid_count(self):
        """测试解析分数数量不匹配"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        text = "[85, 72]"
        with pytest.raises(LLMAPIError, match="分数数量不匹配"):
            scorer._parse_response(text, 3)

    def test_parse_response_invalid_json(self):
        """测试解析无效 JSON"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        text = "不是 JSON 格式"
        with pytest.raises(LLMAPIError, match="解析失败"):
            scorer._parse_response(text, 3)

    def test_normalize_bm25_score(self):
        """测试 BM25 分数归一化"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        # rank = -10 → score = 100
        assert scorer._normalize_bm25_score(-10.0) == 100.0

        # rank = 0 → score = 50
        assert scorer._normalize_bm25_score(0.0) == 50.0

        # rank = -5 → score = 75
        assert scorer._normalize_bm25_score(-5.0) == 75.0

    def test_get_cache_key(self):
        """测试生成缓存 key"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        query = "test query"
        candidates = [
            {"inode": 1, "v_path": "/test/1"},
            {"inode": 2, "v_path": "/test/2"},
        ]
        context = "test context"

        key1 = scorer._get_cache_key(query, candidates, context)
        key2 = scorer._get_cache_key(query, candidates, None)

        assert key1 != key2
        assert len(key1) == 32

    @pytest.mark.asyncio
    async def test_score_disabled(self):
        """测试语义评分禁用"""
        config = {"llm_api_key": ""}
        scorer = SemanticScorer(config)

        candidates = [
            {"inode": 1, "v_path": "/test/1", "content": "test", "rank": -5.0},
        ]

        result = await scorer.score("query", candidates)

        assert len(result) == 1
        assert "semantic_score" in result[0]

    @pytest.mark.asyncio
    async def test_score_empty_candidates(self):
        """测试空候选列表"""
        config = {"llm_api_key": "test-key"}
        scorer = SemanticScorer(config)

        result = await scorer.score("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_score_api_mock(self):
        """测试 mock API 调用"""
        config = {
            "llm_api_key": "test-key",
            "llm_provider": "dashscope",
            "cache_enabled": False,
        }
        scorer = SemanticScorer(config)

        candidates = [
            {"inode": 1, "v_path": "/test/1", "content": "test 1", "rank": -5.0},
            {"inode": 2, "v_path": "/test/2", "content": "test 2", "rank": -2.0},
        ]

        with mock.patch.object(
            scorer, "_call_dashscope", return_value=[85.0, 60.0]
        ) as mock_call:
            result = await scorer.score("test query", candidates)

            assert len(result) == 2
            assert result[0]["semantic_score"] == 85.0
            assert result[1]["semantic_score"] == 60.0
            mock_call.assert_called_once()

    def test_get_stats(self):
        """测试获取统计信息"""
        config = {
            "llm_api_key": "test-key",
            "cache_enabled": True,
        }
        scorer = SemanticScorer(config)

        stats = scorer.get_stats()

        assert "enabled" in stats
        assert "provider" in stats
        assert "model" in stats
        assert "cache" in stats
        assert stats["enabled"] is True


class TestSemanticScorerIntegration:
    """集成测试（需要真实 API 或 mock）"""

    @pytest.mark.asyncio
    async def test_score_with_error_fallback(self):
        """测试 API 错误时的降级"""
        config = {
            "llm_api_key": "test-key",
            "llm_provider": "dashscope",
            "cache_enabled": False,
        }
        scorer = SemanticScorer(config)

        candidates = [
            {"inode": 1, "v_path": "/test/1", "content": "test", "rank": -5.0},
        ]

        with mock.patch.object(
            scorer, "_call_dashscope", side_effect=Exception("API Error")
        ):
            result = await scorer.score("query", candidates)

            assert len(result) == 1
            assert "semantic_score" in result[0]
            assert scorer.total_errors == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """测试缓存命中"""
        config = {
            "llm_api_key": "test-key",
            "cache_enabled": True,
            "cache_ttl": 10,
        }
        scorer = SemanticScorer(config)

        candidates = [
            {"inode": 1, "v_path": "/test/1", "content": "test", "rank": -5.0},
        ]

        with mock.patch.object(
            scorer, "_call_dashscope", return_value=[85.0]
        ) as mock_call:
            # 第一次调用
            result1 = await scorer.score("query", candidates)
            mock_call.assert_called_once()

            # 第二次调用（应命中缓存）
            result2 = await scorer.score("query", candidates)
            mock_call.assert_called_once()

            assert result1[0]["semantic_score"] == 85.0
            assert result2[0]["semantic_score"] == 85.0
            assert scorer.cache_hits == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
