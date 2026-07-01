# PRD — Project-Wide Observability

## Project: EthioBio AI Assistant

## Parent Initiative: Production Hardening

## Status: Draft

## Priority: High

## Type: Observability Infrastructure

---

# Executive Summary

The Content Safety Guardrails project defines the *mechanisms* — rate limiters, sanitizers, safety nodes, tool/action gating. This PRD defines how we **observe, measure, trace, and evaluate** the entire system in production, including but not limited to guardrails.

**Scope change (per research 2026):** Observability is project-wide infrastructure (`src/observability/`), not guardrail-coupled. Guardrails are the first consumers, but the same tracing, metrics, and evaluation layer serves every module: tutor synthesis, retrieval, planning, quiz generation, and LLM calls.

Without observability, operators cannot answer:
- "Are guardrails working right now?" (health)
- "Is the safety check adding unacceptable latency?" (tracing)
- "Are we catching all prompt injection attempts?" (evals)
- "Which prompt version caused a quality regression?" (evaluation)
- "Is our cost per request within budget?" (cost attribution)
- "Did quality scores drop week-over-week?" (drift detection)

This project builds **five pillars** of observability aligned with the 2026 OpenTelemetry GenAI semantic conventions standard:

1. **Tracing** — OTel-compatible spans for LLM calls, guardrails, retrieval, and agent steps
2. **Metrics** — counters, histograms, gauges for latency, tokens, cost, error rates
3. **Structured Logging** — consistent event schema across all modules
4. **Health & Alerting** — module-level health registry + threshold-based alerts
5. **Async Evaluation** — LLM-as-judge on sampled traffic, eval-as-span-attribute pattern

---

# Problem Statement

## No Operational Visibility

- LLM call timings, token counts, and finish reasons are opaque — no standardized tracing
- Guardrail events are raw `structlog` calls with no consistent schema or semantic convention
- No metrics exist — cannot track latency p95, token cost per request, or error rate over time
- No way to answer "is the system healthy?" without grepping logs across multiple services
- Cost attribution is manual — no per-request, per-tenant, or per-model cost tracking

## No Evaluative Rigor

- No test datasets for quality dimensions (faithfulness, relevance, safety)
- No catch rate / false positive rate tracking — cannot measure if quality improves or regresses
- No regression suite — changes to prompts or models are untested against known inputs
- No periodic eval runs — system effectiveness is never measured against known-good/bad examples
- No prompt version correlation — cannot tell which prompt version caused a production incident

## No Guardrail-Specific Visibility

- Guardrail timing is invisible in pipeline traces — cannot attribute latency to specific guardrail checks
- No guardrail verdicts in trace metadata — cannot filter traces by "was injection detected?"
- No guardrail-specific health — cannot tell if rate limiter lost Redis connection

---

# Goal

Build a **project-wide observability platform** that:

- Traces every LLM call, guardrail check, retrieval step, and agent action using OTel GenAI semantic conventions
- Exposes latency, token usage, cost, and error rate metrics for every subsystem
- Provides consistent structured logging across all modules with trace correlation
- Offers real-time health visibility per module
- Evaluates quality on sampled traffic using LLM-as-judge, attaching scores as span attributes
- Enables operators to answer "what happened, why, and was it good?" in under 30 seconds

---

# Non-Goals

This project will NOT:

- Provision or configure Grafana/Prometheus/Loki infrastructure (expects existing observability stack)
- Modify existing module behavior (rate limits, detection logic, safety thresholds)
- Change the pipeline graph topology or AgentState
- Add new database tables for observability storage
- Build a custom dashboard UI (consumes from existing tools)
- Replace the existing `PipelineTrace` system — observability is additive
- Store full prompt/completion content by default (content capture is opt-in per OTel semconv privacy guidance)

---

# Architecture

```
Application Layer (FastAPI + LangGraph)
     │
     ├──► OpenTelemetry SDK (Python)
     │         ├── gen_ai.* spans (LLM calls, agent steps)
     │         ├── guardrail.* spans (rate limit, injection, safety, tool gate)
     │         ├── retrieval.* spans (search, rerank)
     │         └── http.* spans (request lifecycle)
     │
     ├──► Metrics (in-process counters + histograms)
     │         └──► OTel metrics pipeline / structlog debug events
     │
     ├──► Structured Logging (log_event with consistent schema)
     │         └──► structlog → centralized logging
     │
     └──► Health Registry (module status, last error, uptime)
              └──► GET /health/modules

Eval Pipeline (async, offline, 10-20% sampled)
     │
     ├──► Sampler (head-based: trace 100% / eval sample 10-20%)
     ├──► LLM-as-Judge (async evaluation of faithfulness, relevance, safety, toxicity)
     ├──► Score Writer (attaches eval results as gen_ai.evaluation.* span attributes)
     └──► Drift Detector (compares scores week-over-week, alerts on >10% drop)

OTel Collector (optional for production deployment)
     ├──► Tail-based sampling (retain 100% errors, low-score evals, high-cost traces)
     ├──► PII redaction processor (strip secrets before export)
     └──► Export to backend (Langfuse, Tempo, or SigNoz)
```

---

# Module Specifications

## 1. Tracing (OTel GenAI Semantic Conventions)

### Module

```
src/observability/tracing.py
src/observability/instrumentation.py
```

### Approach

The 2026 industry standard is **OpenTelemetry GenAI semantic conventions** (`gen_ai.*` namespace). This replaces ad-hoc `PipelineTrace` sub-spans with standard OTel spans that any OTel-compatible backend can ingest.

**Key attributes per span type:**

| Span Kind | Operation Name | Key Attributes |
|-----------|---------------|----------------|
| LLM Call | `chat {model}` | `gen_ai.request.model`, `gen_ai.provider.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`, `gen_ai.request.temperature` |
| Guardrail | `guardrail.{type}` | `gen_ai.guardrail.triggered`, `guardrail.type`, `guardrail.module`, `guardrail.outcome` |
| Retrieval | `retrieval.search` | `db.query.text`, `db.query.result_count`, `db.query.duration` |
| Agent | `invoke_agent` | `gen_ai.agent.id`, `gen_ai.agent.name`, `gen_ai.tool.definitions` |
| Tool | `execute_tool` | `gen_ai.tool.name`, `gen_ai.tool.arguments`, `gen_ai.tool.result.is_error` |

**Content capture is opt-out by default** (per OTel GenAI semconv recommendation). Prompts and completions are NOT stored on spans unless explicitly enabled. Use external storage references instead.

### Integration

- **OpenLLMetry** (Traceloop, Apache 2.0) auto-instruments OpenAI, Anthropic, LangChain, LlamaIndex with one import. Use as the base instrumentation layer.
- Manual instrumentation for custom modules (guardrails, retrieval, custom tool calls) using OpenTelemetry Python SDK.
- All spans carry `service.name` and `service.version` resource attributes for deployment context.

### Sampling Strategy

- **100% tracing in development and staging**
- **Production:** 10-30% head-based sampling for LLM spans; 100% for guardrail spans (low volume, high value)
- **Tail-based sampling** via OTel Collector: retain 100% of error spans, 100% of low-eval-score spans, 100% of high-cost (>95th percentile) spans, 1-10% of clean spans for trend data

---

## 2. Metrics

### Module

```
src/observability/metrics.py
```

### Implementation

Lightweight in-process collection. For MVP, metrics are emitted as structured log events (no `prometheus_client` dependency). A production deployment scrapes via existing logging pipeline.

### Counters

| Name | Labels | Source |
|------|--------|--------|
| `llm_call_total` | `model`, `provider`, `finish_reason` | Tracing |
| `llm_token_total` | `model`, `token_type` (input/output) | Tracing |
| `guardrail_check_total` | `check_type`, `outcome` | Guardrail modules |
| `guardrail_injection_detected_total` | `pattern_type` | Prompt injection |
| `guardrail_safety_node_outcome_total` | `outcome` (finalize/revise/reject) | SafetyNode |
| `guardrail_toxicity_detected_total` | `category` | Toxicity filter |
| `guardrail_pii_detected_total` | `pii_type` | PII detector |
| `guardrail_tool_blocked_total` | `tool_name`, `reason` | Tool/Action guard |
| `http_request_total` | `method`, `path`, `status_code` | FastAPI |
| `eval_run_total` | `dimension` | Async eval |

### Histograms

| Name | Labels | Source |
|------|--------|--------|
| `llm_call_duration_seconds` | `model`, `provider` | Tracing |
| `guardrail_check_duration_seconds` | `check_type` | Guardrail modules |
| `http_request_duration_seconds` | `method`, `path` | FastAPI |
| `eval_score` | `dimension` (faithfulness, relevance, safety) | Async eval |

### Gauges

| Name | Labels | Source |
|------|--------|--------|
| `guardrail_hallucination_rate` | — | Hallucination detector |
| `guardrail_groundedness_score` | — | Claim verifier |
| `llm_cost_total_usd` | `model` | Cost calculation |
| `health_overall_status` | — | Health registry |

### Collection

Metrics are emitted via `logger.debug("observability.metric", ...)`. In production, route to:
- OTel metrics pipeline → Prometheus
- `mtail` / `promtail` → Loki

---

## 3. Structured Logging

### Module

```
src/observability/structured_logging.py
```

### Schema

Every observability event follows this schema:

```python
{
    "event": "observability.{domain}.{action}",
    "domain": "llm|guardrail|retrieval|eval|http|system",
    "module": str | None,
    "outcome": "pass|block|flag|error|success|failure",
    "duration_ms": float | None,
    "trace_id": str | None,
    "span_id": str | None,
    "user_id": str | None,
    "details": dict,
}
```

### Event Catalog

| Event | Level | Domain | When |
|-------|-------|--------|------|
| `observability.llm.call_started` | DEBUG | LLM | LLM call begins |
| `observability.llm.call_completed` | INFO | LLM | LLM call ends with token counts |
| `observability.llm.call_failed` | ERROR | LLM | LLM call error/timeout |
| `observability.guardrail.check` | DEBUG | Guardrail | Guardrail check executed |
| `observability.guardrail.blocked` | WARNING | Guardrail | Request blocked |
| `observability.guardrail.flagged` | INFO | Guardrail | Borderline case flagged |
| `observability.guardrail.error` | ERROR | Guardrail | Guardrail exception |
| `observability.eval.run_started` | INFO | Eval | Eval run begins |
| `observability.eval.score_recorded` | DEBUG | Eval | Single score recorded |
| `observability.eval.drift_detected` | WARNING | Eval | Week-over-week score drop |
| `observability.eval.run_completed` | INFO | Eval | All evals done |
| `observability.health.check` | DEBUG | System | Health check response |
| `observability.health.degraded` | WARNING | System | Module degraded |
| `observability.alert.fired` | WARNING | System | Alert threshold crossed |

---

## 4. Health Endpoint

### Module

```
src/observability/health.py
```

### Endpoint

```
GET /health/modules
```

### Response

```json
{
  "status": "healthy|degraded|unhealthy",
  "modules": {
    "rate_limiter": {
      "status": "healthy",
      "redis_connected": true,
      "enabled": true
    },
    "toxicity_filter": {
      "status": "healthy",
      "enabled": true
    },
    "llm_provider": {
      "status": "healthy",
      "provider": "ollama",
      "model": "llama3",
      "last_call_ms": 1234
    },
    "eval_pipeline": {
      "status": "healthy",
      "last_run": "2026-07-01T15:30:00Z",
      "samples_evaluated": 150
    }
  },
  "uptime_seconds": 84321,
  "requests_since_startup": 1542,
  "errors_since_startup": 17
}
```

### Health Registry

Tracks per-module:
- `status`: healthy | degraded | unhealthy
- `details`: arbitrary module-specific metadata
- `last_error`: string or null
- `last_checked`: ISO timestamp

Aggregate counters: total requests, total errors, uptime.

---

## 5. Alerting

### Module

```
src/observability/alerting.py
```

### Thresholds

| Threshold | Severity | Evaluation | Cool-down |
|-----------|----------|------------|-----------|
| Latency p95 > 5s (chat) | P2 | On histogram percentile | 5 min |
| Token cost per request > 2x average | P3 | On span cost attribute | 15 min |
| Error rate > 1% of requests | P1 | On error counter | 1 min |
| Guardrail injection rate > 10/min | P2 | On counter rate | 5 min |
| Safety parse failure > 5/min | P1 | On counter | 1 min |
| PII detected (any) | P1 | Synchronous on detection | 1 min |
| Quality score drop > 10% week-over-week | P2 | Eval comparison | 1 hour |
| Health status == "unhealthy" | P2 | Health endpoint poll | 5 min |

### Behavior

- Thresholds emit `logger.warning("observability.alert", ...)`
- Each threshold has a cooldown to prevent alert storms
- Alert events carry `metric_name`, `current_value`, `threshold`, `severity`

---

## 6. Async Evaluation Pipeline

### Module

```
src/observability/evaluation/
├── __init__.py
├── sampler.py          # Head-based sampling policy
├── judge.py            # LLM-as-judge scoring
├── dimensions.py       # Scoring rubrics
├── writer.py           # Eval-as-span-attribute writer
├── drift.py            # Week-over-week drift detection
├── datasets/
│   ├── faithfulness_cases.txt
│   ├── relevance_cases.txt
│   ├── safety_cases.txt
│   └── clean_cases.txt
└── runner.py           # CLI entry point
```

### Approach

**Eval-as-span-attribute** pattern: attach judge scores directly to the generation span as `gen_ai.evaluation.*` attributes. This ties quality signal to the full trace context.

### Sampling

- **Head-based sampling:** Evaluate 10-20% of production traffic
- **100%** of error traces and high-cost traces get evaluated
- **Stratified sample:** mix of successful and failed requests

### LLM-as-Judge Dimensions

| Dimension | Rubric | Judge Model |
|-----------|--------|-------------|
| Faithfulness | Does the response contradict retrieved context? | GPT-4o-mini / Llama 3.1 8B |
| Relevance | Is the response on-topic and useful for the query? | GPT-4o-mini / Llama 3.1 8B |
| Safety | Does the response contain toxic, harmful, or PII content? | Llama Guard 3 |
| Helpfulness | Does the response answer the user's question? | GPT-4o-mini |

### Score Writing

```python
# Eval-as-span-attribute — attach to the generation span
span.set_attribute("gen_ai.evaluation.faithfulness.score", 0.92)
span.set_attribute("gen_ai.evaluation.relevance.score", 0.85)
span.set_attribute("gen_ai.evaluation.safety.score", 1.0)
span.set_attribute("gen_ai.evaluation.explanation", "Response is grounded in retrieved documents")
```

### Drift Detection

- Compare weekly evaluation scores against a 4-week rolling baseline
- Alert on >10% drop in any dimension week-over-week
- Store per-prompt-version score history for A/B comparison

### Offline Eval Suite

```bash
python -m src.observability.evaluation.runner
```

Output:

```
System Evals — 2026-07-01 15:30 UTC
═══════════════════════════════════════
Faithfulness:   avg 0.92  (n=150)
Relevance:      avg 0.85  (n=150)
Safety:         avg 0.98  (n=150)
Helpfulness:    avg 0.88  (n=150)
───────────────────────────────────────
Overall:        avg 0.91  (n=150)
Drift:          none detected
```

---

# Files Modified / Created

## New Files

```
src/observability/
├── __init__.py
├── tracing.py              # OTel GenAI span creation + helpers
├── instrumentation.py      # OpenLLMetry + manual instrumentation
├── metrics.py              # Counter, Gauge, Histogram, MetricsRegistry
├── structured_logging.py   # log_event() schema
├── health.py               # ModuleHealthRegistry
├── alerting.py             # AlertThreshold, AlertManager
└── evaluation/
    ├── __init__.py
    ├── sampler.py
    ├── judge.py
    ├── dimensions.py
    ├── writer.py
    ├── drift.py
    ├── datasets/
    │   ├── faithfulness_cases.txt
    │   ├── relevance_cases.txt
    │   ├── safety_cases.txt
    │   └── clean_cases.txt
    └── runner.py

tests/test_observability/
├── __init__.py
├── test_tracing.py
├── test_instrumentation.py
├── test_metrics.py
├── test_health.py
├── test_structured_logging.py
├── test_alerting.py
└── test_evaluation/
    ├── __init__.py
    ├── test_sampler.py
    ├── test_judge.py
    ├── test_writer.py
    └── test_drift.py
```

## Modified Files

| File | Change |
|------|--------|
| `src/config.py` | Add observability + evaluation settings |
| `src/main.py` | Add OTel instrumentation init, health endpoint, lifespan hooks |
| `src/core/monitoring.py` | Extend `PipelineTrace` to emit OTel spans (dual-mode during migration) |
| `src/llm/router.py` | Add OTel tracing span for every LLM call |
| `src/graph/nodes/safety.py` | Add guardrail sub-spans to traces |
| `src/graph/orchestrator.py` | Add trace context propagation |
| `src/api/chat.py` | Add HTTP span context |
| `pyproject.toml` | Add `opentelemetry-api`, `opentelemetry-sdk`, `openllmetry` dependencies |
| `evaluation/production/safety_hardening.py` | Add observability certification checks |

---

# Acceptance Criteria

## Tracing

- [ ] Every LLM call produces an OTel span with `gen_ai.*` attributes (model, provider, tokens, finish reason)
- [ ] Guardrail checks produce sub-spans with `guardrail.*` attributes
- [ ] Retrieval steps produce spans with query and result metadata
- [ ] Traces are 100% captured in dev, 10-30% sampled in production
- [ ] Tail-based sampling configured in OTel Collector (errors + low eval scores at 100%)

## Metrics

- [ ] LLM call counters, histograms, and token counters emit per-request
- [ ] Guardrail counters emit per check with `check_type` and `outcome` labels
- [ ] Duration histograms track every guardrail check
- [ ] Cost gauge tracks per-model spend

## Structured Logging

- [ ] All events follow `observability.{domain}.{action}` naming
- [ ] All events include `domain`, `module`, `outcome`
- [ ] `trace_id` and `span_id` are included when available

## Health Endpoint

- [ ] `GET /health/modules` returns JSON with per-module status
- [ ] All registered modules are listed at startup
- [ ] Aggregate counters track requests and errors since startup

## Alerting

- [ ] `AlertThreshold` fires on condition with cooldown
- [ ] P1 thresholds (PII, safety parse failure, error rate) have shortest cooldown
- [ ] Alert events use consistent `observability.alert` namespace

## Async Evaluation

- [ ] 10-20% of production traffic is sampled for evaluation
- [ ] LLM-as-judge scores faithfulness, relevance, safety, helpfulness
- [ ] Scores are written as `gen_ai.evaluation.*` span attributes
- [ ] Drift detection compares week-over-week scores
- [ ] Offline eval runner produces per-dimension averages

---

# Success Definition

Operators can answer these questions in under 10 seconds:

1. **"Is the system healthy?"** → `GET /health/modules` → per-module status
2. **"How fast are LLM calls?"** → `llm_call_duration_seconds` histogram
3. **"What's our error rate?"** → `error_rate` counter → alert if >1%
4. **"Are guardrails catching injections?"** → eval → 90%+ catch rate, <5% FP rate
5. **"Did quality drop this week?"** → eval drift → >10% drop triggers alert
6. **"How much does each request cost?"** → `llm_cost_total_usd` per-model
7. **"Which prompt version regressed?"** → eval scores per prompt version

The observability layer is additive — zero impact on module behavior. Every span, metric, and log is independently disableable via config.
