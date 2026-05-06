# Diting LLM 语义评分增强方案

> **方案定位**：Diting 内部自己调 LLM（配置 API Key），在 search() 返回时对候选记忆做语义评分增强。
>
> **核心原则**：LLM 做初始语义判断（占大头），CPU 做后续衰减维护（时间/轮次/用户操作）。
> LLM 给起始分数，CPU 管分数变化。各司其职，成本可控。

---

## 1. 为什么选这个方案？

### 对比三种方案

| 方案 | 自主性 | 跨环境 | 实现难度 | 额外请求 |
|------|--------|--------|----------|----------|
| A. OpenClaw 侧做 rerank | ❌ 依赖外部改动 | ❌ 仅 OpenClaw | 中 | 零（复用已有 LLM） |
| **B. Diting 内部 LLM rerank** | **✅ 完全自主** | **✅ 跨所有环境** | **低** | **⚠️ 独立 LLM 请求** |
| C. 纯 CPU 特征融合 | ✅ 完全自主 | ✅ 跨所有环境 | 中 | 零（但效果有限） |

### 方案 B 优势
- ✅ **完全自主**：不依赖任何外部框架改动
- ✅ **跨环境可用**：OpenClaw / Claude Code / 任何 MCP 客户端都能用
- ✅ **实现简单**：新增一个 scorer 模块，改动集中在 Diting 内部
- ✅ **可渐进增强**：可以先用简单 prompt，再逐步优化
- ⚠️ 不是"零额外请求"，但可以用缓存/批量来降低成本

---

## 2. 架构设计

### 2.1 整体流程

```
用户查询
  │
  ▼
┌─────────────────────────────────────────────┐
│  Step 1: FTS5 BM25 粗排 (CPU)               │
│  - 返回 top 20-50 候选                       │
│  - 0 额外成本，毫秒级                         │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  Step 2: LLM 语义精排（占大头）              │
│  - 将 query + 候选列表发给 LLM               │
│  - LLM 返回语义相关度分数 (0-100)，占 70-80% │
│  - BM25 分数占 20-30%，做辅助校准            │
│  - 合并为起始分数 temp_score (温度 T)         │
│  - 可配置开关，默认启用                       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  Step 3: CPU 后续衰减维护                    │
│  - 时间衰减：每天 -0.1 分                     │
│  - 轮次衰减：每轮 -5 分                       │
│  - 用户操作：升温 +30 / 降温 -20              │
│  - 纯 CPU，零额外成本                         │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  Step 4: 自由能排序 (CPU)                    │
│  - G = U - TS 公式计算                       │
│  - 按自由能排序返回 top K                     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              返回最终结果
```

### 2.1.1 权重分配（核心变更）

| 阶段 | LLM 权重 | CPU 权重 | 说明 |
|------|---------|---------|------|
| **起始分数** | **70-80%** | 20-30% | LLM 语义判断为主，BM25 辅助校准 |
| **后续衰减** | 0% | **100%** | 时间/轮次/用户操作，纯 CPU |
| **整体占比** | ~10-15% | ~85-90% | LLM 只给起点，CPU 管全程 |

**设计哲学**：
- LLM 擅长语义理解 → 给起始分数（一次性成本）
- CPU 擅长规则计算 → 管后续变化（零边际成本）
- 类似"LLM 点火，CPU 滑行"

### 2.2 模块划分

```
diting/
├── fts5_search.py          # 现有，不变（BM25 粗排）
├── semantic_scorer.py      # 新增：LLM 语义评分器
├── config.py               # 修改：增加 LLM 配置项
├── mft.py                  # 修改：search() 集成 semantic_scorer
├── cache.py                # 现有，可复用（缓存 LLM 结果）
└── mcp_server.py           # 小改：传递 enable_semantic 参数
```

---

## 3. 详细设计

### 3.1 新增 `semantic_scorer.py`

```python
"""
LLM 语义评分器

职责：
1. 接收 query + 候选列表
2. 调用 LLM API 获取语义相关度分数
3. 支持缓存（相同 query 不重复请求）
4. 支持降级（API 失败时回退到 BM25 分数）
"""

class SemanticScorer:
    def __init__(self, config: Dict):
        """
        初始化评分器
        
        配置项：
        - llm_provider: "openai" | "dashscope" | "anthropic"
        - llm_api_key: API Key
        - llm_model: 模型名称（如 qwen-turbo）
        - llm_base_url: API 地址（可选）
        - cache_enabled: 是否启用缓存（默认 True）
        - cache_ttl: 缓存过期时间（秒，默认 3600）
        - max_candidates: 单次最多评分候选数（默认 20）
        - timeout: API 超时时间（秒，默认 10）
        """
        pass

    async def score(
        self,
        query: str,
        candidates: List[Dict],
        context: Optional[str] = None,
    ) -> List[Dict]:
        """
        对候选列表进行语义评分
        
        Args:
            query: 搜索查询
            candidates: BM25 粗排结果列表 [{inode, v_path, content, rank, ...}]
            context: 可选的上下文信息（如当前对话主题）
        
        Returns:
            评分后的候选列表，每个增加 semantic_score 字段 (0-100)
        """
        # 1. 检查缓存
        # 2. 构建 prompt
        # 3. 调用 LLM API
        # 4. 解析结果
        # 5. 写入缓存
        # 6. 返回结果
        pass

    def _build_prompt(self, query: str, candidates: List[Dict]) -> str:
        """
        构建 LLM 评分 prompt
        
        设计原则：
        - 简洁高效，控制 token 消耗
        - 明确评分标准
        - 要求结构化输出（JSON）
        """
        pass

    def _parse_response(self, response: str) -> List[float]:
        """解析 LLM 返回的分数"""
        pass

    def _get_cache_key(self, query: str) -> str:
        """生成缓存 key"""
        pass
```

### 3.2 LLM Prompt 设计

```
你是一个记忆检索相关性评分助手。

任务：评估以下记忆片段与用户查询的语义相关度。

查询：{query}
{上下文信息}

候选记忆：
1. [路径] {v_path}
   {content 前 200 字}

2. [路径] ...
   ...

评分标准（0-100）：
- 90-100: 直接回答查询，高度相关
- 70-89:  间接相关，有参考价值
- 40-69:  部分相关，有些许联系
- 0-39:   基本无关

要求：
1. 只输出 JSON 数组，格式：[分数1, 分数2, ...]
2. 分数数量必须等于候选数量
3. 不要输出任何其他内容
```

### 3.3 配置扩展（config.py）

```python
class Config:
    def __init__(self, db_path=None):
        # ... 现有配置 ...
        
        # LLM 语义评分配置
        self.llm_provider = os.getenv("DITING_LLM_PROVIDER", "dashscope")
        self.llm_api_key = os.getenv("DITING_LLM_API_KEY", "")
        self.llm_model = os.getenv("DITING_LLM_MODEL", "qwen-turbo")
        self.llm_base_url = os.getenv("DITING_LLM_BASE_URL", "")
        self.semantic_scoring_enabled = os.getenv("DITING_SEMANTIC_SCORING", "true").lower() == "true"
        self.semantic_cache_ttl = int(os.getenv("DITING_SEMANTIC_CACHE_TTL", "3600"))
        self.semantic_max_candidates = int(os.getenv("DITING_SEMANTIC_MAX_CANDIDATES", "20"))
        self.semantic_timeout = int(os.getenv("DITING_SEMANTIC_TIMEOUT", "10"))
```

### 3.4 MFT 集成（mft.py）

```python
# 在 MFT.__init__ 中
if config.semantic_scoring_enabled and config.llm_api_key:
    self.semantic_scorer = SemanticScorer(config)
else:
    self.semantic_scorer = None

def search(self, query, scope=None, top_k=10, context=None, enable_semantic=True):
    """
    搜索记忆
    
    新增参数：
    - context: 上下文信息（用于语义评分）
    - enable_semantic: 是否启用语义评分（默认 True）
    """
    # Step 1: BM25 粗排（取更多候选）
    fetch_k = top_k * 3 if enable_semantic and self.semantic_scorer else top_k
    results = self.fts5.search(query, scope, top_k=fetch_k)
    
    if not results:
        return []
    
    # Step 2: LLM 语义精排（可选）
    if enable_semantic and self.semantic_scorer:
        results = await self.semantic_scorer.score(query, results, context)
    
    # Step 3: 热力学后处理
    results = self._apply_thermodynamics(results)
    
    # Step 4: 返回 top K
    return results[:top_k]
```

### 3.5 分数融合公式

```
起始分数 (temp_score) = LLM_score × 0.75 + BM25_score × 0.25

其中：
- LLM_score: 0-100（LLM 语义相关度评分）
- BM25_score: 0-100（BM25 归一化分数）
- 权重 0.75/0.25 可配置（DITING_LLM_WEIGHT 环境变量）

后续衰减（CPU 全权负责）：
最终分数 = 起始分数 - 时间衰减 - 轮次衰减 + 用户操作
```

### 3.6 降级策略

```
正常流程：BM25 → LLM 评分(75%) + BM25(25%) → CPU 衰减 → 自由能排序 → 返回
降级路径：
  1. LLM API 超时/失败 → 回退到纯 BM25（100%）+ CPU 衰减
  2. LLM 返回格式错误 → 回退到纯 BM25（100%）+ CPU 衰减
  3. LLM API Key 未配置 → 跳过语义评分，纯 BM25 + CPU 衰减
  4. 候选数 > max_candidates → 取前 max_candidates 评分，其余用 BM25 分数
```

---

## 4. 成本控制

### 4.1 Token 消耗估算

| 项目 | 单次消耗 | 说明 |
|------|----------|------|
| Prompt | ~300-500 tokens | query + 20 个候选（每个 ~150 字） |
| Response | ~100 tokens | 20 个分数的 JSON 数组 |
| **合计** | **~400-600 tokens/次** | |

以 qwen-turbo（0.005 元/千 tokens）计算：
- 单次成本：~0.003 元
- 1000 次搜索：~3 元
- 10000 次搜索：~30 元

### 4.2 降本措施

1. **缓存**：相同 query 1 小时内不重复请求
2. **批量**：单次请求评分多个候选（而非逐个）
3. **采样**：候选数超过 20 时，取 BM25 前 20 评分
4. **可选**：用户可关闭语义评分，纯 CPU 模式
5. **模型选择**：默认用 qwen-turbo（便宜快速），可选 qwen-plus（更准更贵）

---

## 5. 实施计划

### Phase 1: 基础框架（1-2 天）

- [ ] 创建 `semantic_scorer.py` 基础类
- [ ] 扩展 `config.py` 增加 LLM 配置
- [ ] 实现 prompt 构建和响应解析
- [ ] 实现缓存机制（复用现有 cache.py）
- [ ] 实现降级策略
- [ ] 单元测试

### Phase 2: 集成和测试（1 天）

- [ ] 修改 `mft.py` 集成 semantic_scorer
- [ ] 修改 `mcp_server.py` 传递参数
- [ ] 集成测试（端到端）
- [ ] 性能测试（延迟对比）

### Phase 3: 优化和文档（1 天）

- [ ] Prompt 调优（评分准确性）
- [ ] 成本监控（token 用量统计）
- [ ] 文档更新（README + API 文档）
- [ ] 环境变量配置示例

---

## 6. 测试策略

### 6.1 单元测试

```python
# tests/test_semantic_scorer.py

class TestSemanticScorer:
    def test_score_basic(self):
        """基础评分功能"""
        
    def test_score_with_context(self):
        """带上下文的评分"""
        
    def test_cache_hit(self):
        """缓存命中，不调用 LLM"""
        
    def test_cache_miss(self):
        """缓存未命中，调用 LLM"""
        
    def test_api_failure_fallback(self):
        """API 失败，回退到 BM25"""
        
    def test_invalid_response_fallback(self):
        """LLM 返回格式错误，回退"""
        
    def test_max_candidates_limit(self):
        """候选数超过限制时的处理"""
        
    def test_no_api_key_skip(self):
        """未配置 API Key，跳过语义评分"""
```

### 6.2 集成测试

```python
# tests/test_search_semantic.py

class TestSemanticSearch:
    def test_end_to_end_search(self):
        """端到端搜索：BM25 → LLM → 热力学"""
        
    def test_search_without_semantic(self):
        """关闭语义评分的搜索"""
        
    def test_search_with_context(self):
        """带上下文的搜索"""
```

### 6.3 性能测试

```python
# tests/test_semantic_performance.py

class TestSemanticPerformance:
    def test_latency_comparison(self):
        """对比：纯 BM25 vs BM25+LLM"""
        
    def test_cache_effectiveness(self):
        """缓存命中率"""
        
    def test_token_cost(self):
        """Token 消耗统计"""
```

---

## 7. 后续演进

### v1.2 增强方向

1. **自适应评分**：根据用户反馈（点击/忽略）调整评分权重
2. **多轮对话上下文**：利用对话历史提升评分准确性
3. **个性化评分**：不同用户有不同的相关性标准
4. **A/B 测试框架**：对比不同 prompt/模型的效果

### 长期方向

1. **本地小模型**：部署轻量级 rerank 模型（如 bge-reranker），零 API 成本
2. **向量索引**：结合 embedding 做双重检索（BM25 + 向量）
3. **增量学习**：根据使用数据持续优化评分模型

---

## 8. 风险和问题

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM API 不稳定 | 搜索延迟增加 | 降级策略 + 超时控制 |
| Token 成本超预期 | 运行成本增加 | 缓存 + 可选开关 + 用量监控 |
| LLM 评分不准 | 排序质量下降 | Prompt 调优 + A/B 测试 |
| 中文语义理解偏差 | 中文搜索结果差 | 选用中文强的模型（qwen） |

---

## 9. 环境变量配置示例

```bash
# .env 或 shell 环境变量

# LLM 配置（必填）
export DITING_LLM_PROVIDER="dashscope"
export DITING_LLM_API_KEY="sk-xxxxx"
export DITING_LLM_MODEL="qwen-turbo"

# 可选配置
export DITING_LLM_BASE_URL=""                    # 自定义 API 地址
export DITING_SEMANTIC_SCORING="true"            # 是否启用语义评分
export DITING_SEMANTIC_CACHE_TTL="3600"         # 缓存过期时间（秒）
export DITING_SEMANTIC_MAX_CANDIDATES="20"      # 单次最多评分候选数
export DITING_SEMANTIC_TIMEOUT="10"             # API 超时时间（秒）
```

---

*文档版本：v1.0*
*创建日期：2026-05-01*
*状态：待实施*
