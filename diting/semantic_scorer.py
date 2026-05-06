"""
LLM 语义评分器

职责：
1. 接收 query + 候选列表
2. 调用 LLM API 获取语义相关度分数
3. 支持缓存（相同 query 不重复请求）
4. 支持降级（API 失败时回退到 BM25 分数）

支持的 LLM 提供商：
- dashscope (阿里云灵积，默认)
- openai (OpenAI API)
- anthropic (Claude API)
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import httpx

from diting.errors import (
    LLMAPIError,
    LLMConnectionError,
    LLMException,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class TTLCache:
    """
    带 TTL 的 LRU 缓存实现

    用于缓存 LLM 语义评分结果，相同 query 在 TTL 内不重复请求
    """

    def __init__(self, capacity: int = 100, ttl_seconds: int = 3600):
        """
        初始化 TTL 缓存

        Args:
            capacity: 缓存容量
            ttl_seconds: 缓存过期时间（秒），默认 1 小时
        """
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据（自动检查 TTL）

        Args:
            key: 缓存键

        Returns:
            缓存的值，不存在或过期返回 None
        """
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                # 检查是否过期
                if time.time() - timestamp < self.ttl_seconds:
                    # 移动到末尾（最近使用）
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    # 过期，删除
                    del self.cache[key]
                    self.evictions += 1
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """
        向缓存添加数据

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            current_time = time.time()
            if key in self.cache:
                # 更新并移动到末尾
                self.cache.move_to_end(key)
                self.cache[key] = (value, current_time)
            else:
                # 添加新条目
                if len(self.cache) >= self.capacity:
                    # 删除最旧的条目
                    self.cache.popitem(last=False)
                    self.evictions += 1
                self.cache[key] = (value, current_time)

    def delete(self, key: str) -> None:
        """
        从缓存删除数据

        Args:
            key: 缓存键
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def cleanup_expired(self) -> int:
        """
        清理过期缓存条目

        Returns:
            清理的条目数量
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                k for k, (_, ts) in self.cache.items()
                if current_time - ts >= self.ttl_seconds
            ]
            for k in expired_keys:
                del self.cache[k]
                self.evictions += 1
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "capacity": self.capacity,
                "size": len(self.cache),
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": f"{hit_rate:.2f}%",
            }


class SemanticScorer:
    """
    LLM 语义评分器

    使用 LLM 对候选记忆进行语义相关度评分
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化评分器

        配置项：
        - llm_provider: "openai" | "dashscope" | "anthropic"
        - llm_api_key: API Key
        - llm_model: 模型名称（如 qwen-turbo）
        - llm_base_url: API 地址（可选）
        - cache_enabled: 是否启用缓存（默认 True）
        - cache_ttl: 缓存过期时间（秒，默认 3600）
        - cache_capacity: 缓存容量（默认 100）
        - max_candidates: 单次最多评分候选数（默认 20）
        - timeout: API 超时时间（秒，默认 10）
        - llm_weight: LLM 分数权重（默认 0.75）
        """
        self.provider = config.get("llm_provider", "dashscope")
        self.api_key = config.get("llm_api_key", "")
        self.model = config.get("llm_model", "qwen-turbo")
        self.base_url = config.get("llm_base_url", "")
        self.max_candidates = config.get("max_candidates", 20)
        self.timeout = config.get("timeout", 10)
        self.llm_weight = config.get("llm_weight", 0.75)

        # 初始化缓存
        cache_enabled = config.get("cache_enabled", True)
        cache_ttl = config.get("cache_ttl", 3600)
        cache_capacity = config.get("cache_capacity", 100)
        self.cache = TTLCache(capacity=cache_capacity, ttl_seconds=cache_ttl) if cache_enabled else None

        # 验证配置
        if not self.api_key:
            logger.warning("LLM API Key 未配置，语义评分将降级为 BM25")
            self.enabled = False
        else:
            self.enabled = True

        # 统计信息
        self.total_requests = 0
        self.total_tokens = 0
        self.total_errors = 0
        self.cache_hits = 0

    async def score(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        对候选列表进行语义评分

        Args:
            query: 搜索查询
            candidates: BM25 粗排结果列表 [{inode, v_path, content, rank, ...}]
            context: 可选的上下文信息

        Returns:
            评分后的候选列表，每个增加 semantic_score 字段 (0-100)
        """
        if not self.enabled or not candidates:
            # 未启用或无候选，返回原始结果（semantic_score = BM25 normalized）
            return self._fallback_to_bm25(candidates)

        # 限制候选数量
        if len(candidates) > self.max_candidates:
            # 取前 max_candidates 评分，其余用 BM25
            scored_candidates = candidates[: self.max_candidates]
            fallback_candidates = candidates[self.max_candidates :]
        else:
            scored_candidates = candidates
            fallback_candidates = []

        # 检查缓存
        cache_key = self._get_cache_key(query, scored_candidates, context)
        if self.cache:
            cached_scores = self.cache.get(cache_key)
            if cached_scores is not None:
                self.cache_hits += 1
                logger.debug(f"缓存命中，query: {query}")
                # 应用缓存的分数
                for i, candidate in enumerate(scored_candidates):
                    candidate["semantic_score"] = cached_scores[i]
                # 合并结果
                return self._merge_results(
                    scored_candidates, fallback_candidates, self.llm_weight
                )

        try:
            # 构建 prompt
            prompt = self._build_prompt(query, scored_candidates, context)

            # 调用 LLM API
            self.total_requests += 1
            llm_scores = await self._call_llm(prompt, len(scored_candidates))

            # 验证分数数量
            if len(llm_scores) != len(scored_candidates):
                logger.warning(
                    f"LLM 返回分数数量不匹配: {len(llm_scores)} vs {len(scored_candidates)}"
                )
                return self._fallback_to_bm25(candidates)

            # 应用分数
            for i, candidate in enumerate(scored_candidates):
                candidate["semantic_score"] = llm_scores[i]

            # 写入缓存
            if self.cache:
                self.cache.put(cache_key, llm_scores)

            # 合并结果
            return self._merge_results(
                scored_candidates, fallback_candidates, self.llm_weight
            )

        except Exception as e:
            self.total_errors += 1
            logger.error(f"LLM API 调用失败: {e}")
            return self._fallback_to_bm25(candidates)

    def _get_cache_key(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        context: Optional[str],
    ) -> str:
        """
        生成缓存 key

        基于 query + candidates 的 inode 列表 + context
        """
        # 提取 inode 列表
        inode_list = [str(c.get("inode", "")) for c in candidates]
        key_data = f"{query}|{','.join(inode_list)}|{context or ''}"
        # 使用 hash 避免过长
        return hashlib.md5(key_data.encode()).hexdigest()

    def _build_prompt(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        context: Optional[str],
    ) -> str:
        """
        构建 LLM 评分 prompt

        设计原则：
        - 简洁高效，控制 token 消耗
        - 明确评分标准
        - 要求结构化输出（JSON）
        """
        # 构建候选列表描述
        candidates_text = []
        for i, c in enumerate(candidates, 1):
            # 截取内容前 200 字
            content_preview = c.get("content", "")[:200]
            v_path = c.get("v_path", "")
            candidates_text.append(f"{i}. [路径] {v_path}\n   {content_preview}")

        candidates_str = "\n\n".join(candidates_text)

        # 构建上下文
        context_str = f"\n当前上下文：{context}\n" if context else ""

        prompt = f"""你是一个记忆检索相关性评分助手。

任务：评估以下记忆片段与用户查询的语义相关度。

查询：{query}
{context_str}
候选记忆：
{candidates_str}

评分标准（0-100）：
- 90-100: 直接回答查询，高度相关
- 70-89: 间接相关，有参考价值
- 40-69: 部分相关，有些许联系
- 0-39: 基本无关

要求：
1. 只输出 JSON 数组，格式：[分数1, 分数2, ...]
2. 分数数量必须等于候选数量（{len(candidates)} 个）
3. 不要输出任何其他内容"""

        return prompt

    async def _call_llm(self, prompt: str, expected_count: int) -> List[float]:
        """
        调用 LLM API

        Args:
            prompt: 评分 prompt
            expected_count: 期望的分数数量

        Returns:
            分数列表 (0-100)
        """
        if self.provider == "dashscope":
            return await self._call_dashscope(prompt, expected_count)
        elif self.provider == "openai":
            return await self._call_openai(prompt, expected_count)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt, expected_count)
        else:
            raise LLMException(f"不支持的 LLM 提供商: {self.provider}")

    async def _call_dashscope(
        self, prompt: str, expected_count: int
    ) -> List[float]:
        """
        调用阿里云灵积 API (dashscope)

        使用 HTTP 请求调用 qwen 系列模型
        """
        url = self.base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"result_format": "text"},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    raise LLMAPIError(f"API 错误 {response.status_code}: {response.text}")

                data = response.json()
                output = data.get("output", {})
                text = output.get("text", "")
                usage = data.get("usage", {})

                self.total_tokens += usage.get("total_tokens", 0)

                return self._parse_response(text, expected_count)

        except httpx.TimeoutException:
            raise LLMTimeoutError(f"API 超时（{self.timeout}s）") from None
        except httpx.ConnectError:
            raise LLMConnectionError("API 连接失败") from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError("API 速率限制") from None
            raise LLMAPIError(f"API HTTP 错误: {e}") from None
        except LLMException:
            raise
        except Exception as e:
            raise LLMException(f"API 调用异常: {e}") from e

    async def _call_openai(self, prompt: str, expected_count: int) -> List[float]:
        """
        调用 OpenAI API

        使用标准的 OpenAI Chat Completion API
        """
        url = self.base_url or "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    raise LLMAPIError(f"API 错误 {response.status_code}: {response.text}")

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMAPIError("API 返回空结果")

                text = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})

                self.total_tokens += usage.get("total_tokens", 0)

                return self._parse_response(text, expected_count)

        except httpx.TimeoutException:
            raise LLMTimeoutError(f"API 超时（{self.timeout}s）") from None
        except httpx.ConnectError:
            raise LLMConnectionError("API 连接失败") from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError("API 速率限制") from None
            raise LLMAPIError(f"API HTTP 错误: {e}") from None
        except LLMException:
            raise
        except Exception as e:
            raise LLMException(f"API 调用异常: {e}") from e

    async def _call_anthropic(
        self, prompt: str, expected_count: int
    ) -> List[float]:
        """
        调用 Anthropic Claude API

        使用 Claude Messages API
        """
        url = self.base_url or "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    raise LLMAPIError(f"API 错误 {response.status_code}: {response.text}")

                data = response.json()
                content = data.get("content", [])
                if not content:
                    raise LLMAPIError("API 返回空结果")

                text = content[0].get("text", "")
                usage = data.get("usage", {})

                self.total_tokens += usage.get("input_tokens", 0) + usage.get(
                    "output_tokens", 0
                )

                return self._parse_response(text, expected_count)

        except httpx.TimeoutException:
            raise LLMTimeoutError(f"API 超时（{self.timeout}s）") from None
        except httpx.ConnectError:
            raise LLMConnectionError("API 连接失败") from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError("API 速率限制") from None
            raise LLMAPIError(f"API HTTP 错误: {e}") from None
        except LLMException:
            raise
        except Exception as e:
            raise LLMException(f"API 调用异常: {e}") from e

    def _parse_response(self, text: str, expected_count: int) -> List[float]:
        """
        解析 LLM 返回的分数

        Args:
            text: LLM 返回的文本
            expected_count: 期望的分数数量

        Returns:
            分数列表 (0-100)
        """
        try:
            text = text.strip()

            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                scores = json.loads(json_str)
            else:
                scores = json.loads(text)

            if not isinstance(scores, list):
                raise LLMAPIError("返回结果不是列表")

            if len(scores) != expected_count:
                raise LLMAPIError(
                    f"分数数量不匹配: {len(scores)} vs {expected_count}"
                )

            result = []
            for s in scores:
                score = float(s)
                score = max(0.0, min(100.0, score))
                result.append(score)

            return result

        except json.JSONDecodeError as e:
            raise LLMAPIError(f"JSON 解析失败: {e}") from e
        except LLMAPIError:
            raise
        except Exception as e:
            raise LLMAPIError(f"响应解析失败: {e}") from e

    def _fallback_to_bm25(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        降级到 BM25 分数

        当 LLM API 失败时，使用归一化的 BM25 分数作为 semantic_score

        Args:
            candidates: 候选列表

        Returns:
            带 semantic_score 的候选列表
        """
        if not candidates:
            return candidates

        # BM25 rank 是负数（越负越相关），需要转换
        # 归一化：最高相关度 = 100，最低 = 0
        ranks = [c.get("rank", 0) for c in candidates]

        # BM25 rank 范围不定，使用相对归一化
        # 假设最相关的是 rank 最小（最负）
        if ranks:
            min_rank = min(ranks)
            max_rank = max(ranks)
            rank_range = max_rank - min_rank if max_rank != min_rank else 1.0

            for c in candidates:
                # rank 越小（越负）越相关 → semantic_score 越高
                normalized_rank = (c.get("rank", min_rank) - min_rank) / rank_range
                # 反转：0 rank → 100 score, max rank → 0 score
                c["semantic_score"] = 100.0 * (1.0 - normalized_rank)

        return candidates

    def _merge_results(
        self,
        scored_candidates: List[Dict[str, Any]],
        fallback_candidates: List[Dict[str, Any]],
        llm_weight: float,
    ) -> List[Dict[str, Any]]:
        """
        合并评分结果

        计算融合分数：final_score = LLM_score × llm_weight + BM25_score × (1 - llm_weight)

        Args:
            scored_candidates: LLM 评分的候选
            fallback_candidates: BM25 降级的候选
            llm_weight: LLM 权重

        Returns:
            合并后的候选列表
        """
        bm25_weight = 1.0 - llm_weight

        # 处理 LLM 评分的候选
        for c in scored_candidates:
            semantic_score = c.get("semantic_score", 50.0)
            bm25_normalized = self._normalize_bm25_score(c.get("rank", 0))
            # 融合分数
            c["temp_score"] = semantic_score * llm_weight + bm25_normalized * bm25_weight

        # 处理 BM25 降级的候选
        for c in fallback_candidates:
            bm25_normalized = self._normalize_bm25_score(c.get("rank", 0))
            c["semantic_score"] = bm25_normalized  # 用 BM25 作为 semantic_score
            c["temp_score"] = bm25_normalized  # 纯 BM25

        # 合并并排序（按 temp_score 降序）
        all_candidates = scored_candidates + fallback_candidates
        all_candidates.sort(key=lambda x: x.get("temp_score", 0), reverse=True)

        return all_candidates

    def _normalize_bm25_score(self, rank: float) -> float:
        """
        归一化 BM25 rank 到 0-100

        BM25 rank 是负数，越小（越负）越相关

        Args:
            rank: BM25 rank 值

        Returns:
            归一化分数 (0-100)
        """
        # 简化处理：rank 范围 -10 到 0
        # rank = -10 → score = 100
        # rank = 0 → score = 50 (作为基准)
        if rank <= -10:
            return 100.0
        elif rank >= 0:
            return 50.0
        else:
            # 线性映射：[-10, 0] → [100, 50]
            return 50.0 + (rank + 10) * 5.0

    def get_stats(self) -> Dict[str, Any]:
        """
        获取评分器统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "llm_weight": self.llm_weight,
            "max_candidates": self.max_candidates,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_errors": self.total_errors,
            "cache_hits": self.cache_hits,
            "error_rate": f"{self.total_errors / self.total_requests * 100:.2f}%"
            if self.total_requests > 0
            else "0%",
        }

        if self.cache:
            stats["cache"] = self.cache.get_stats()

        return stats

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()

    def cleanup_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数量
        """
        if self.cache:
            return self.cache.cleanup_expired()
        return 0

