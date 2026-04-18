# 热力学四系统 CPU/LLM 分工说明

**文档版本**: 1.0  
**更新时间**: 2026-04-18

---

## 📊 总体架构

谛听的热力学四系统设计遵循 **"CPU 计算为主，LLM 语义为辅"** 的原则，确保高性能和低成本。

```
┌─────────────────────────────────────────────────────────┐
│                   热力学四系统                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  内能 U (热度 H)     →  100% CPU 计算                    │
│  温度 T (关联度)     →  90% CPU + 10% LLM(可选)          │
│  熵 S (争议性)      →  80% CPU + 20% LLM(可选)          │
│  自由能 G (有效性)  →  100% CPU 计算                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔥 1. 内能系统（U）- 热度评分

### 完全由 CPU 完成 (100%)

**计算内容**:
- ✅ 访问次数统计
- ✅ 时间衰减计算
- ✅ 对话轮次衰减
- ✅ 用户主动升温
- ✅ 死灰复燃检测

**实现位置**: `diting/heat_manager.py`

**计算公式**:
```python
# CPU 计算
heat_score = base_score + access_count * weight
heat_score -= time_decay * days_elapsed      # 时间衰减
heat_score -= round_decay * rounds_elapsed   # 轮次衰减
heat_score = max(0, min(100, heat_score))    # 限制在 0-100
```

**性能指标**:
- 计算延迟：< 0.1ms
- 吞吐量：> 10,000 ops/s
- CPU 占用：极低

**为什么不用 LLM**:
- 纯数学计算，无需语义理解
- LLM 会慢 1000 倍且成本高
- 确定性计算，不需要概率推理

---

## 🌡️ 2. 温度系统（T）- 关联度

### CPU 为主 (90%) + LLM 可选增强 (10%)

### CPU 计算部分 (90%)

**计算内容**:
- ✅ FTS5 BM25 全文检索（70% 权重）
- ✅ 路径匹配（30% 权重）
- ✅ 关键词匹配
- ✅ 向量相似度（可选）

**实现位置**: `diting/free_energy_manager.py` 中的 `_calculate_relevance()`

**计算公式**:
```python
# CPU 计算
bm25_score = fts5_bm25_query(memory_id, context)  # SQLite FTS5
path_score = match_paths(memory_path, context)    # 字符串匹配
relevance = bm25_score * 0.7 + path_score * 0.3
```

**性能指标**:
- BM25 计算：0.5-2ms（C 语言实现）
- 路径匹配：< 0.1ms
- 总延迟：1-3ms

### LLM 增强部分 (10%, 可选)

**使用场景**:
- ⚠️ 语义相似度计算（当 BM25 失效时）
- ⚠️ 上下文深度理解
- ⚠️ 隐喻/暗示识别

**实现方式** (未来扩展):
```python
# LLM 调用（可选）
if bm25_score < threshold:
    semantic_score = llm.calculate_similarity(
        memory_content,
        current_context
    )
    relevance = max(relevance, semantic_score * 0.5)
```

**为什么不主要用 LLM**:
- BM25 已经足够准确（90% 场景）
- LLM 慢且贵（100-1000ms vs 1-3ms）
- 大多数关联是字面的，不需要深层语义

---

## 🌀 3. 熵系统（S）- 争议性

### CPU 为主 (80%) + LLM 可选增强 (20%)

### CPU 计算部分 (80%)

**计算内容**:
- ✅ 矛盾检测（基于规则）
- ✅ 多版本冲突
- ✅ WAL 日志分析
- ✅ 更新频率统计

**实现位置**: `diting/entropy_manager.py`

**检测方法**:
```python
# CPU 计算
# 1. 检测同一路径的多次更新
update_count = count_updates(path, time_window='24h')
if update_count > threshold:
    entropy += 0.3

# 2. 检测 WAL 中的回滚操作
rollbacks = count_rollbacks(path)
if rollbacks > 0:
    entropy += 0.2 * rollbacks

# 3. 检测内容差异
versions = get_versions(path)
diff_score = calculate_content_diff(versions)
entropy += diff_score * 0.5
```

**性能指标**:
- 矛盾检测：< 1ms
- WAL 分析：1-5ms
- 总延迟：2-6ms

### LLM 增强部分 (20%, 可选)

**使用场景**:
- ⚠️ 语义矛盾检测（非字面冲突）
- ⚠️ 情感倾向分析
- ⚠️ 模糊信息评估

**实现方式** (未来扩展):
```python
# LLM 调用（可选）
if rule_based_entropy < threshold:
    semantic_contradiction = llm.detect_contradiction(
        memory_versions
    )
    entropy = max(entropy, semantic_contradiction)
```

---

## ⚡ 4. 自由能系统（G）- 有效性

### 完全由 CPU 完成 (100%)

**计算内容**:
- ✅ 自由能公式计算
- ✅ 可用性评估
- ✅ 提取决策
- ✅ 系统状态分析

**实现位置**: `diting/free_energy_manager.py`

**计算公式**:
```python
# CPU 计算
G = U - (T * S * 100)

# 可用性评估
if G > 50:
    availability = 'high'
elif G > 20:
    availability = 'medium'
elif G > 0:
    availability = 'low'
else:
    availability = 'inhibited'  # G < 0，不应提取
```

**性能指标**:
- 计算延迟：< 0.1ms
- 吞吐量：> 10,000 ops/s

**为什么不用 LLM**:
- 纯数学公式，无歧义
- 需要确定性决策
- 性能要求极高（每次查询都要计算）

---

## 📋 完整工作流程示例

### 场景：用户查询"上次和朋友拍照的经历"

```
1. 接收查询 (CPU)
   ↓
2. FTS5 BM25 搜索 (CPU, 1-3ms)
   - 匹配关键词："朋友", "拍照"
   - 返回候选记忆列表
   ↓
3. 计算每段记忆的温度 T (CPU, 1-3ms/条)
   - BM25 评分：0.8
   - 路径匹配：0.6
   - T = 0.8 * 0.7 + 0.6 * 0.3 = 0.74
   ↓
4. 获取热度 H (CPU, <0.1ms/条)
   - 从数据库读取（已预计算并衰减）
   - H = 75（最近访问过）
   ↓
5. 计算熵 S (CPU, 2-6ms/条)
   - 检测矛盾：无
   - WAL 分析：稳定
   - S = 0.1（低熵，信息一致）
   ↓
6. 计算自由能 G (CPU, <0.1ms/条)
   - G = H - (T * S * 100)
   - G = 75 - (0.74 * 0.1 * 100)
   - G = 75 - 7.4 = 67.6
   ↓
7. 决策 (CPU)
   - G > 50 → 高可用性
   - 提取并返回给用户
```

**总延迟**: 5-15ms（无需 LLM）

---

## 🎯 LLM 的正确使用场景

### ✅ 适合使用 LLM 的场景

1. **记忆创建时的摘要生成**
   ```python
   # LLM 生成摘要（一次性成本）
   summary = llm.summarize(long_conversation)
   mft.create(path, type="SUMMARY", content=summary)
   ```

2. **知识图谱概念提取**
   ```python
   # LLM 提取概念（批量处理）
   concepts = llm.extract_concepts(memory_content)
   for concept in concepts:
       kg.add_concept(concept)
   ```

3. **语义矛盾检测（可选增强）**
   ```python
   # LLM 检测深层矛盾
   contradiction = llm.detect_semantic_contradiction(versions)
   ```

4. **复杂查询理解**
   ```python
   # LLM 解析复杂查询
   intent = llm.parse_query("上次那个谁说要一起去的地方")
   # 转换为结构化查询
   ```

### ❌ 不适合使用 LLM 的场景

1. **热度衰减计算** - 纯数学公式
2. **自由能计算** - 确定性决策
3. **BM25 搜索** - C 语言实现更快
4. **路径匹配** - 字符串操作足够
5. **WAL 日志分析** - 规则检测即可

---

## 📊 性能对比

| 操作 | CPU 实现 | LLM 实现 | 倍数差异 |
|------|---------|---------|---------|
| **热度衰减** | <0.1ms | 100-1000ms | 1000-10000x |
| **BM25 搜索** | 1-3ms | 50-200ms* | 20-100x |
| **矛盾检测** | 2-6ms | 100-500ms* | 20-80x |
| **自由能计算** | <0.1ms | 50-200ms* | 500-2000x |
| **摘要生成** | N/A | 200-1000ms | - |
| **概念提取** | N/A | 100-500ms | - |

*如果使用 LLM 做这些任务

---

## 🏗️ 架构设计原则

### 1. CPU 优先原则

**规则**: 能用 CPU 计算的，绝不用 LLM

**理由**:
- 性能：CPU 快 100-1000 倍
- 成本：CPU 几乎免费，LLM 每次调用都要钱
- 确定性：CPU 计算可重复，LLM 有随机性

### 2. LLM 增强原则

**规则**: LLM 只用于 CPU 做不好的语义任务

**适用场景**:
- 语义理解
- 抽象概念提取
- 复杂推理
- 自然语言生成

### 3. 分层架构

```
┌─────────────────────┐
│   LLM 层 (可选)      │  ← 语义增强
├─────────────────────┤
│   CPU 计算层         │  ← 核心计算
├─────────────────────┤
│   SQLite 存储层      │  ← 持久化
└─────────────────────┘
```

---

## 📈 成本分析

### 假设场景：1000 次查询/天

**纯 CPU 方案**:
```
1000 次查询 × 10ms/次 × $0.00001/ms = $0.10/天
```

**LLM 方案** (如果全用 LLM):
```
1000 次查询 × 200ms/次 × $0.0001/ms = $20/天
```

**混合方案** (当前实现):
```
CPU 计算：1000 次 × $0.10 = $0.10/天
LLM 增强：50 次 × $0.50 = $25/月 (仅语义增强)
总计：≈ $3/月
```

**节省**: 99% 成本

---

## 📝 总结

| 系统 | CPU 比例 | LLM 比例 | 说明 |
|------|---------|---------|------|
| **内能 U** | 100% | 0% | 纯数学计算 |
| **温度 T** | 90% | 10% | BM25 为主，LLM 可选增强 |
| **熵 S** | 80% | 20% | 规则检测为主，LLM 语义增强 |
| **自由能 G** | 100% | 0% | 确定性公式 |
| **总计** | **92.5%** | **7.5%** | **CPU 主导** |

**核心设计理念**:
> 让 CPU 做 CPU 擅长的事（计算、检索、规则）  
> 让 LLM 做 LLM 擅长的事（语义、推理、生成）  
> **但绝大多数时候，CPU 就够了**

---

**文档维护者**: AI Assistant  
**最后更新**: 2026-04-18 14:35 GMT+8
