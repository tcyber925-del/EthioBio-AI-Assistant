# Observability & Guardrails — Usage Guide

## Quick Start

```bash
# Start the full observability stack
docker compose up -d postgres redis jaeger prometheus grafana

# Check everything is up
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl http://localhost:8000/health/modules

# Open in browser
open http://localhost:16686    # Jaeger traces
open http://localhost:9090     # Prometheus targets (should see app scraping)
open http://localhost:3001     # Grafana (admin / ethiobio)
```

---

## 1. Tracing

Spans use GenAI semantic conventions and are exported via OTLP gRPC to Jaeger when `OTEL_ENDPOINT` is set.

### Creating a custom span

```python
from src.observability.tracing import tracer

with tracer.start_as_current_span("my.custom.span") as span:
    span.set_attribute("my.key", "my.value")
    result = do_work()
```

### Logging a guardrail event (manual)

```python
from src.observability.tracing import (
    tracer, GUARDRAIL_TYPE, GUARDRAIL_MODULE, GUARDRAIL_OUTCOME,
)

with tracer.start_as_current_span("guardrail.my_check") as span:
    span.set_attribute(GUARDRAIL_MODULE, "my_check")
    span.set_attribute(GUARDRAIL_TYPE, "input")
    span.set_attribute(GUARDRAIL_OUTCOME, "passed")
    result = my_check(text)
```

### Attaching eval scores to an existing span

```python
from src.observability.tracing import set_eval_on_span

with tracer.start_as_current_span("something") as span:
    set_eval_on_span(span, "faithfulness", 0.92, "No contradictions found")
```

### Tracing an LLM route call

This happens automatically in `ModelRouter.route()` — no action needed. All GenAI attributes (model, provider, temperature, token usage, finish reason) are set on the span.

---

## 2. Metrics

Metrics are Prometheus-format and exported at `GET /metrics`. The registry is a singleton guarded by `observability_metrics_enabled`.

### Recording metrics

```python
from src.observability.metrics import inc_counter, set_gauge, observe_histogram, Timer

# Counter — monotonically increasing
inc_counter("my_event_count", labels={"category": "science"})

# Gauge — current value
set_gauge("my_value", 42.0, labels={"type": "temperature"})

# Histogram (duration)
with Timer("my_operation_duration", labels={"module": "search"}) as _:
    result = await search(query)
```

### Using the registry directly

```python
from src.observability.metrics import registry

if registry:
    counter = registry.counter("api.requests")
    counter.inc(labels={"endpoint": "/chat"})
```

### Prometheus text format

The `GET /metrics` endpoint outputs:

```
# HELP guardrail_invocations Counter metric
# TYPE guardrail_invocations counter
guardrail_invocations{module="toxicity"} 42

# HELP guardrail_toxicity_duration_ms Gauge metric
# TYPE guardrail_toxicity_duration_ms gauge
guardrail_toxicity_duration_ms 3.2
```

---

## 3. Structured Logging

All observability components use `structlog` with a consistent event schema.

```python
from src.observability.structured_logging import log_event

log_event(
    event="user_signup",
    domain="auth",
    user_id="abc-123",
    outcome="success",
    details={"method": "telegram"},
)
```

The default logger is `structlog.get_logger()` — use it for ad-hoc logs anywhere.

---

## 4. Health Registry

Per-module health tracking with degraded/unhealthy detection. Wired into `GET /health/modules`.

### Manual health tracking

```python
from src.observability.health import health_registry

if health_registry:
    # Register a module (auto-creates)
    health_registry.register("my_module")

    # Record a request outcome
    health_registry.record_request("my_module", error=False)
    health_registry.record_request("my_module", error=True)

    # Set explicit status
    health_registry.set_status("my_module", "degraded", details="Rate limit exceeded")
    health_registry.set_status("my_module", "unhealthy", error="Connection refused")

    # Read status
    status = health_registry.overall_status()  # "healthy" | "degraded" | "unhealthy"
    snapshot = health_registry.to_dict(include_details=True)
```

### Guardrail modules auto-register

During startup, `main.py` registers these guardrail modules automatically: `rate_limiter`, `input_sanitizer`, `prompt_injection`, `conversation_context`, `toxicity`, `topic_enforcer`, `pii_scanner`, `tool_guard`, `safety_node`, `claim_verifier`, `hallucination_detector`.

---

## 5. The `@observe_guardrail` Decorator

This is the primary way to instrument guardrail functions. It does three things automatically:

1. Creates an OTel span (`guardrail.{module}`) with type/outcome/triggered attributes
2. Records a counter metric (`guardrail.invocations`) and duration gauge
3. Updates the health registry
4. Emits a structured log event

### Usage

```python
from src.observability.guardrail_instrumentation import observe_guardrail

@observe_guardrail(module="toxicity", guardrail_type="output")
def check_toxicity(text: str) -> ToxicityResult:
    # ... your logic
    return ToxicityResult(flagged=False, score=0.01, categories=[])
```

Works for both `async def` and regular `def` functions. The decorator auto-detects and wraps correctly.

### Trigger detection

The decorator calls `_is_triggered(result)` which checks common guardrail result shapes:
- `result.blocked` (ToolGuardResult)
- `result.flagged` (ToxicityResult, PIIScanResult)
- `result.detected` (PromptInjectionResult)
- `result.passed == False`
- `result.on_topic == False`
- `result.allowed == False`
- `dict` keys: `triggered`, `flagged`, `blocked`, `detected`

If your result class doesn't match, add a property to match one of these conventions.

---

## 6. Guardrails Reference

### Input Guardrails

| Guardrail | Class | Decorated Method | What It Checks |
|-----------|-------|------------------|----------------|
| Rate Limiter | `RateLimiter` | N/A (middleware) | Redis-backed token bucket per user/IP on `/chat` |
| Input Sanitizer | `InputSanitizer` | `sanitize()` | Strips dangerous input, validates length |
| Prompt Injection | `PromptInjectionDetector` | `check()` | 10 regex patterns for prompt injection attempts |
| Conversation Context | `ConversationContext` | `check_multiturn_attack()` | 11 keyword-set patterns for multi-turn jailbreaks |

**Rate limiter middleware** is registered at module level in `main.py` with lazy Redis client. It intercepts all `/chat` requests.

### Output Guardrails

| Guardrail | Class | Decorated Method | What It Checks |
|-----------|-------|------------------|----------------|
| Toxicity | `ToxicityDetector` | `check()` | 8 regex pattern groups (violence, hate, self-harm, etc.) |
| Topic Enforcer | `TopicEnforcer` | `check()` | 44 biology keywords + 5 off-topic regexes |
| PII Scanner | `PIIScanner` | `scan()` | 6 regex patterns (phone, email, SSN, Ethiopian ID, credit card, Ethiopian phone) |

**OutputGuardrailRunner** composes all three and checks them in sequence. It's the main entry point:

```python
from src.guardrails.output import OutputGuardrailRunner

runner = OutputGuardrailRunner()
result = runner.check(response_text, topic="Cell Biology")
if result.blocked:
    # response was flagged — handle rejection
    print(result.reasons)
```

Run all output guardrails manually:

```python
from src.guardrails.output.toxicity import ToxicityDetector
from src.guardrails.output.topic_enforcer import TopicEnforcer
from src.guardrails.output.pii_scanner import PIIScanner

tox = ToxicityDetector()
t = tox.check(text)
if t.flagged:
    ...

enforcer = TopicEnforcer()
e = enforcer.check(text, topic=topic)
if not e.on_topic:
    ...

scanner = PIIScanner()
p = scanner.scan(text)
if p.flagged:
    ...
```

### Action Guardrails (Tool Calls)

```python
from src.guardrails.action import ToolGuard, ToolGuardResult

guard = ToolGuard()

# Validate a tool call
validation = guard.validate_tool_call("get_weather", {"city": "Addis Ababa"})
if not validation.allowed:
    print(validation.reason)

# Check step/tool call limits
errors = guard.check_step_limits(tool_call_count=5, step_count=10)

# Validate tool response
result = guard.check_response("get_weather", {"city": "Addis Ababa"}, response_data)
if result.blocked:
    print(result.reasons)
```

Allowed tools: `search_curriculum`, `generate_quiz`, `create_lesson_plan`, `get_progress`, `get_weak_topics`, `recommend_quiz`, `search_vector_store`, `generate_diagram`.

### Drift Monitoring

```python
from src.guardrails.drift import DriftMonitor

monitor = DriftMonitor()

# Record a check outcome
monitor.record_check("toxicity", triggered=True)
monitor.record_check("toxicity", triggered=False)

# Check for drift
alert = monitor.check_drift("toxicity")
if alert:
    print(f"Drift detected: {alert.message}")

# Rebaseline when drift is addressed
monitor.rebaseline("toxicity")

# Get all pending alerts
alerts = monitor.get_alerts(clear=True)
```

---

## 7. Evaluation Pipeline

Config: `eval_sampling_rate: float` in settings (default 0.1 = 10%). Errors always evaluated.

### Sampling

```python
from src.observability.evaluation.sampler import EvalSampler

sampler = EvalSampler()
if sampler.should_evaluate(is_error=True):       # always evaluate errors
    ...                                           # 10% sample for successes
```

### Judging

```python
from src.observability.evaluation.judge import LLMJudge

judge = LLMJudge()
result = await judge.score(
    DIMENSIONS[0],        # EvalDimension with name, system_prompt, scale
    "What is a cell?",
    "A cell is the basic unit of life.",
    context="Grade 9 biology unit 1",
)
# result = {"score": 0.95, "explanation": "..."}
```

### Full eval pipeline

```python
from src.observability.evaluation.writer import evaluate_and_write
from src.observability.evaluation.judge import LLMJudge

judge = LLMJudge()
scores = await evaluate_and_write(
    judge,
    question="What is a cell?",
    response="A cell is the basic unit of life.",
    context="Grade 9 biology",
)
```

This evaluates all 4 dimensions (faithfulness, relevance, safety, helpfulness), attaches scores to the current span, and returns score dicts.

### CLI: Run eval against dataset

```bash
python -m src.observability.evaluation.runner \
    --dataset src/observability/evaluation/datasets/<dataset>.json
```

Exits 0 if overall score >= 0.7, else 1.

### Drift detection

```python
from src.observability.evaluation.drift import drift_detector

# Record weekly average
drift_detector.record_week("faithfulness", avg_score=0.88, n=50)

# Check current score against baseline
baseline = drift_detector.get_baseline("faithfulness")
drift = drift_detector.check_drift("faithfulness", current_score=0.72)
if drift is not None:
    print(f"Drift: {drift:.2f} below baseline")
```

Defaults: warning at 10% drop, alert at 20% drop (configurable via `drift_warning_threshold`, `drift_alert_threshold`).

---

## 8. Dashboard Views

### Jaeger (`http://localhost:16686`)
- **Search**: Find traces by service (`ethiobio-ai-assistant`), operation (`guardrail.*`), tags
- **Trace Detail**: Flame graph of guardrail checks, LLM calls, eval scores as span attributes
- **Filter guardrails**: Search `guardrail.module=toxicity` to see all toxicity checks

### Prometheus (`http://localhost:9090`)
- **Graph**: Query `guardrail_invocations{module="toxicity"}` to see invocation rate
- **Targets**: Verify `http://app:8000/metrics` is being scraped
- **Alerts**: Configure alerting rules in `prometheus/prometheus.yml`

### Grafana (`http://localhost:3001`, admin/ethiobio)
- **EthioBio Overview**: Pre-built dashboard with guardrail invocations, eval scores, durations
- **Explore**: Raw PromQL queries against the Prometheus datasource (auto-provisioned)

---

## 9. Env Guards

| Setting | Default | Notes |
|---------|---------|-------|
| `OTEL_ENDPOINT` | `None` | In-memory only when unset. Set to `http://jaeger:4317` in docker-compose |
| `OTEL_SERVICE_NAME` | `ethiobio-ai-assistant` | OTel resource attribute |
| `TRACELOOP_API_KEY` | `None` | Must be set for OpenLLMetry auto-instrumentation. Falls back gracefully |
| `observability_metrics_enabled` | `true` | Disables Prometheus registry if `false` |
| `observability_health_enabled` | `true` | Disables health registry if `false` |
| `eval_sampling_rate` | `0.1` | Fraction of non-error traces to evaluate (10%) |
| `observability_log_level` | `INFO` | Minimum level for structured log events |
| `otel_log_level` | `WARNING` | OTel SDK internal log level |

---

## 10. Adding a New Guardrail

1. Create your guardrail class in `src/guardrails/<layer>/` (input, output, or action)
2. Decorate the main check method with `@observe_guardrail(module="my_check", guardrail_type="input")`
3. Register the module in `main.py`'s `lifespan` guardrail modules list
4. Wire it into the pipeline (add check call in the relevant orchestrator node)
5. Write tests in `tests/` following existing patterns

```python
from src.observability.guardrail_instrumentation import observe_guardrail

class MyCheckResult:
    def __init__(self, flagged: bool, reason: str = ""):
        self.flagged = flagged
        self.reason = reason

class MyChecker:
    @observe_guardrail(module="my_check", guardrail_type="input")
    def check(self, text: str) -> MyCheckResult:
        if "bad" in text:
            return MyCheckResult(True, "Contains bad word")
        return MyCheckResult(False)
```
