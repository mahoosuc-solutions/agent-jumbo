# Cost Optimization for AI Agent Systems

## Overview

AI agent costs are dominated by LLM inference (token consumption). Unlike traditional compute where costs are relatively predictable, AI agent costs vary dramatically based on task complexity, model choice, prompt design, and caching strategy. A poorly optimized agent system can cost 10-50x more than a well-optimized one for the same output quality. This document covers practical strategies for controlling and reducing costs.

## Cost Anatomy

Understanding where money goes is the first step.

```
Typical AI Agent Cost Breakdown:
------------------------------------
LLM inference (input tokens):   35-45%
LLM inference (output tokens):  30-40%
Embedding generation:            5-10%
Vector store queries:             2-5%
Tool execution (external APIs):   5-10%
Compute (agent runtime):          3-5%
```

LLM inference dominates. Optimizing token usage provides the highest ROI.

## 1. Model Selection Strategy

### Tiered Model Architecture

Do not use a single model for everything. Match model capability to task difficulty.

```python
class ModelRouter:
    MODELS = {
        "fast": {
            "name": "claude-haiku",
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "use_for": ["classification", "simple_qa", "summarization", "routing"],
        },
        "balanced": {
            "name": "claude-sonnet",
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "use_for": ["multi_step_reasoning", "code_generation", "analysis"],
        },
        "capable": {
            "name": "claude-opus",
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "use_for": ["complex_reasoning", "creative_writing", "edge_cases"],
        },
    }

    def select_model(self, task_type: str, complexity: str = "normal") -> str:
        if complexity == "simple" or task_type in self.MODELS["fast"]["use_for"]:
            return self.MODELS["fast"]["name"]
        elif complexity == "complex" or task_type in self.MODELS["capable"]["use_for"]:
            return self.MODELS["capable"]["name"]
        else:
            return self.MODELS["balanced"]["name"]
```

### Cost Impact of Model Choice

| Task | Haiku | Sonnet | Opus |
|------|-------|--------|------|
| Classify a support ticket | $0.0003 | $0.004 | $0.02 |
| Generate a 500-word report | $0.002 | $0.025 | $0.12 |
| 10-step agent workflow | $0.02 | $0.25 | $1.20 |
| 1000 documents/day pipeline | $3 | $40 | $200 |

Using Haiku for classification instead of Opus saves 98% on that step.

### Cascade Pattern

Start with a cheap model. If it fails or confidence is low, fall back to a more capable (expensive) model.

```python
class ModelCascade:
    TIERS = ["claude-haiku", "claude-sonnet", "claude-opus"]

    async def complete(self, messages: list, min_confidence: float = 0.8) -> Response:
        for model in self.TIERS:
            response = await self.llm.complete(messages=messages, model=model)

            if response.confidence >= min_confidence:
                self.metrics.record("cascade.resolved_at", model)
                return response

            # Log why we're escalating
            self.metrics.record("cascade.escalation", model, reason="low_confidence")

        # Return the opus response even if confidence is low
        return response
```

In practice, 60-70% of requests resolve at the cheapest tier. This saves 40-50% compared to always using the expensive model.

## 2. Caching Strategies

### Response Caching

Cache LLM responses for identical or semantically similar queries.

```python
class ResponseCache:
    def __init__(self, ttl: int = 3600):
        self.cache = RedisCache(ttl=ttl)

    async def get_or_compute(
        self,
        messages: list,
        model: str,
        temperature: float = 0,
    ) -> Response:
        # Only cache deterministic requests
        if temperature > 0:
            return await self.llm.complete(messages, model=model, temperature=temperature)

        cache_key = self.compute_key(messages, model)
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.increment("cache.hit")
            return cached

        self.metrics.increment("cache.miss")
        response = await self.llm.complete(messages, model=model, temperature=0)
        await self.cache.set(cache_key, response)
        return response

    def compute_key(self, messages: list, model: str) -> str:
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
```

### Semantic Caching

For queries that are not identical but semantically equivalent, use embedding similarity.

```python
class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.95):
        self.threshold = similarity_threshold
        self.vector_store = VectorStore("response_cache")

    async def get_similar(self, query: str) -> Response | None:
        embedding = await self.embedder.embed(query)
        results = await self.vector_store.search(embedding, top_k=1)

        if results and results[0].score >= self.threshold:
            self.metrics.increment("semantic_cache.hit")
            return results[0].metadata["response"]

        self.metrics.increment("semantic_cache.miss")
        return None
```

### Cache Hit Rate Targets

| Cache Type | Target Hit Rate | Typical Savings |
|-----------|----------------|-----------------|
| Exact match | 15-25% | 15-25% of LLM costs |
| Semantic cache | 10-20% additional | 10-15% of remaining |
| Combined | 25-40% | 25-35% total |

## 3. Token Budget Management

### Prompt Optimization

Reduce input tokens without losing quality.

```python
class PromptOptimizer:
    def optimize_system_prompt(self, prompt: str) -> str:
        """Remove redundancy and verbosity from system prompts."""
        # Measure baseline
        baseline_tokens = self.count_tokens(prompt)

        # Remove redundant instructions
        optimized = self.deduplicate_instructions(prompt)

        # Compress examples (keep one, remove redundant ones)
        optimized = self.compress_examples(optimized)

        # Remove filler words and unnecessary formatting
        optimized = self.remove_filler(optimized)

        savings = baseline_tokens - self.count_tokens(optimized)
        self.metrics.record("prompt_optimization.tokens_saved", savings)
        return optimized

    def truncate_context(self, context: str, max_tokens: int) -> str:
        """Intelligently truncate context to fit budget."""
        current = self.count_tokens(context)
        if current <= max_tokens:
            return context

        # Strategy: Keep first and last sections, truncate middle
        sections = context.split("\n\n")
        if len(sections) <= 2:
            return context[:max_tokens * 4]  # Rough char estimate

        keep_first = len(sections) // 3
        keep_last = len(sections) // 3
        return "\n\n".join(
            sections[:keep_first]
            + ["[... truncated ...]"]
            + sections[-keep_last:]
        )
```

### Conversation History Management

Long conversations accumulate tokens. Manage history to prevent runaway costs.

```python
class ConversationManager:
    MAX_HISTORY_TOKENS = 8000

    def trim_history(self, messages: list[dict]) -> list[dict]:
        """Keep system prompt + recent messages within budget."""
        system = [m for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]

        total_tokens = sum(self.count_tokens(m["content"]) for m in system)

        # Add messages from most recent, drop oldest when over budget
        kept = []
        for msg in reversed(non_system):
            msg_tokens = self.count_tokens(msg["content"])
            if total_tokens + msg_tokens > self.MAX_HISTORY_TOKENS:
                break
            kept.insert(0, msg)
            total_tokens += msg_tokens

        # If we dropped messages, add a summary of dropped content
        if len(kept) < len(non_system):
            dropped = non_system[:len(non_system) - len(kept)]
            summary = self.summarize_dropped(dropped)
            kept.insert(0, {"role": "system", "content": f"Earlier conversation summary: {summary}"})

        return system + kept
```

## 4. Batch Processing

### Request Batching

For non-interactive workloads, batch multiple requests to reduce overhead.

```python
class BatchProcessor:
    def __init__(self, batch_size: int = 10, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: list[BatchItem] = []

    async def submit(self, request: LLMRequest) -> asyncio.Future:
        future = asyncio.get_event_loop().create_future()
        self.queue.append(BatchItem(request=request, future=future))

        if len(self.queue) >= self.batch_size:
            await self.flush()

        return future

    async def flush(self):
        if not self.queue:
            return

        batch = self.queue[:self.batch_size]
        self.queue = self.queue[self.batch_size:]

        # Process batch (use batch API if available, otherwise concurrent calls)
        results = await asyncio.gather(*[
            self.llm.complete(item.request) for item in batch
        ])

        for item, result in zip(batch, results):
            item.future.set_result(result)
```

### When to Batch

| Scenario | Batch? | Why |
|----------|--------|-----|
| Document processing pipeline | Yes | Non-interactive, high volume |
| Customer support chat | No | Latency-sensitive |
| Report generation | Yes | Can tolerate delay |
| Code review | Maybe | Batch per PR, not per line |

## 5. Embedding Cost Patterns

Embeddings are cheap per-call but expensive at scale due to volume.

### Embedding Cost Comparison

| Provider | Cost per 1M tokens | Notes |
|----------|-------------------|-------|
| OpenAI text-embedding-3-small | $0.02 | Good quality, very cheap |
| OpenAI text-embedding-3-large | $0.13 | Higher quality |
| Cohere embed-v3 | $0.10 | Multi-language |
| Local (e5-base) | $0 (compute only) | Self-hosted, no API costs |

### Optimization Strategies

```python
class EmbeddingOptimizer:
    def __init__(self):
        self.cache = EmbeddingCache()

    async def embed(self, text: str) -> list[float]:
        # Cache embeddings (they are deterministic)
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Chunk and embed
        embedding = await self.embedder.embed(text)
        await self.cache.set(cache_key, embedding, ttl=86400 * 30)  # 30 day cache
        return embedding

    def reduce_embedding_calls(self, documents: list[str]) -> list[str]:
        """Deduplicate and batch documents before embedding."""
        unique = list(set(documents))
        return unique  # Embed unique documents only, then map back
```

## 6. Cost Monitoring and Forecasting

```python
class CostForecaster:
    async def daily_report(self, tenant_id: str) -> CostReport:
        usage = await self.usage_store.get_daily(tenant_id)

        return CostReport(
            date=date.today(),
            total_cost=usage.total_cost,
            breakdown={
                "llm_input": usage.input_token_cost,
                "llm_output": usage.output_token_cost,
                "embeddings": usage.embedding_cost,
                "tools": usage.tool_cost,
            },
            sessions=usage.session_count,
            avg_cost_per_session=usage.total_cost / max(usage.session_count, 1),
            month_to_date=await self.get_mtd(tenant_id),
            projected_monthly=await self.project_monthly(tenant_id),
            vs_last_month=await self.compare_last_month(tenant_id),
        )
```

### Cost Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| Session cost spike | > 5x average session cost | Investigate, possible loop |
| Daily cost surge | > 200% of daily average | Notify admin |
| Monthly projection | > 120% of budget | Alert finance |
| Cache hit rate drop | < 20% (was > 30%) | Check cache health |
| Model tier distribution shift | > 40% opus (was < 20%) | Review routing logic |

## Quick Wins Checklist

- [ ] Use the cheapest model that meets quality requirements for each task type
- [ ] Cache LLM responses for deterministic (temperature=0) requests
- [ ] Cache embeddings (they are deterministic and reusable)
- [ ] Trim conversation history to stay within a token budget
- [ ] Batch non-interactive workloads
- [ ] Implement the cascade pattern (cheap model first, expensive on fallback)
- [ ] Monitor cost per session and set alerts for anomalies
- [ ] Optimize system prompts to reduce input token waste
- [ ] Use structured output to reduce output token waste
- [ ] Set hard token budgets per session to prevent runaway costs

## Cost Optimization Maturity

| Level | Practice | Expected Savings |
|-------|----------|-----------------|
| **L0** | Single model, no caching | Baseline |
| **L1** | Model tiering + response caching | 30-50% reduction |
| **L2** | Cascade + semantic caching + prompt optimization | 50-70% reduction |
| **L3** | Batch processing + embedding optimization + forecasting | 60-80% reduction |

Most teams can reach L1 in a week and L2 in a month. The effort-to-savings ratio is excellent.
