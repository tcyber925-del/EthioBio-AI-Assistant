# PRD — Content Safety Guardrails

## Project: EthioBio AI Assistant

## Parent Initiative: Production Hardening

## Status: Draft

## Priority: Critical

## Type: Safety & Security Infrastructure

---

# Executive Summary

EthioBio currently has **15 safety-related files** but **8 critical gaps** including no input sanitization, no rate limiting, a SafetyNode that silently fails open to `safe=True`, and hallucination detection that returns 0% when `citation_map` is empty.

This PRD defines a **5-layer content safety guardrail system** aligned with 2025-2026 industry standards (OWASP LLM Top 10, NIST AI RMF, EU AI Act Article 14) that closes all critical and moderate gaps:

1. **Input Guard** — rate limiting, input validation, prompt injection detection, conversation-level context
2. **Pipeline Guard** — fix broken safety wiring, improve hallucination/claim detection
3. **Output Guard** — content filters, topic enforcement, Amharic-language safety, output on EVERY response
4. **Tool/Action Guard** — pre-execution tool validation, post-execution result inspection, least-privilege tool scoping
5. **Config Guard** — CORS hardening, secret validation, startup checks

---

# Problem Statement

## Critical Gaps

1. **No input sanitization on user messages.** `TutorRequest.question` is passed raw to `run_graph()`. No prompt injection detection, no profanity filtering, no length enforcement at the API layer.

2. **No rate limiting anywhere.** No middleware, no Redis-based throttling, no per-IP or per-user limits. Open vector for abuse.

3. **SafetyNode silently fails open.** When JSON parsing fails (`safety.py:131-134`), defaults to `safe=True, score=1.0`. Any LLM output that breaks the response format passes safety checks.

4. **Hallucination detection bypasses on empty citation_map.** If `citation_map` is empty (legacy pipeline path), `HallucinationDetector` returns 0% hallucination rate (`detector.py:27-35`).

5. **`should_revise()` is dead code.** Defined at `safety.py:161-166` but never imported or called. The graph routes `claim_verifier -> safety -> END` unconditionally — SafetyNode cannot trigger revisions.

## Moderate Gaps

6. **Claim verifier is purely heuristic.** No LLM-powered verification. `extract_claims_simple()` splits on periods with keyword matching. Sophisticated hallucinations pass through.

7. **CORS wide-open fallback.** `allow_origins=[settings.dashboard_url, "*"]` — wildcard when `dashboard_url` is set.

8. **Amharic content bypasses English-language safety prompts.** Safety prompts are English-only; SafetyNode may not reliably evaluate Amharic content.

---

# Goal

Implement a **5-layer content safety guardrail system** that:
- Prevents abusive input before it reaches the pipeline (including multi-turn attacks via conversation context)
- Fixes broken safety wiring in the graph
- Filters dangerous output before it reaches users — on EVERY response, unconditionally
- Validates tool/action calls pre- and post-execution to prevent excessive agency
- Hardens configuration against common deployment mistakes

---

# Non-Goals

This project will NOT:

- Rewrite the LangGraph pipeline topology
- Replace the existing vector store or retrieval system
- Add new database tables for guardrail storage
- Implement full audit log persistence (already handled by tracing)
- Build a separate moderation dashboard or admin UI
- Change the authentication system (JWT/OTP)
- Replace the existing tracing/monitoring system — observability additions are additive
- Implement full agent tool-call authorization (Tool/Action Guard scoped to safety-critical tool calls — general agent authorization is a separate initiative)
- Automatically retrain or recalibrate guardrail thresholds (drift detection is added; recalibration process is manual for MVP)

---

# Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────┐
│        LAYER 1: INPUT GUARD         │
│  ┌──────────┐  ┌─────────────────┐  │
│  │Rate      │  │Input Validation │  │
│  │Limiter   │  │& Sanitization   │  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────────────────────────┐   │
│  │Prompt Injection Detection    │   │
│  │+ Conversation Context Window │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│      LAYER 2: PIPELINE GUARD        │
│  ┌──────────┐  ┌─────────────────┐  │
│  │Fix Safety│  │Wire should_revise│  │
│  │Node      │  │into Graph       │  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────────────┐  ┌─────────┐  │
│  │LLM Claim         │  │Fix Hall.│  │
│  │Verification      │  │Detector │  │
│  └──────────────────┘  └─────────┘  │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│       LAYER 3: OUTPUT GUARD         │
│  ┌──────────┐  ┌─────────────────┐  │
│  │Toxicity  │  │Topic Drift      │  │
│  │Filter    │  │Detection        │  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────────────┐  ┌─────────┐  │
│  │PII Leakage       │  │Amharic  │  │
│  │Detection         │  │Safety   │  │
│  └──────────────────┘  └─────────┘  │
│  ┌──────────────────────────────┐   │
│  │ Runs on EVERY response       │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│     LAYER 4: TOOL/ACTION GUARD      │
│  ┌──────────┐  ┌─────────────────┐  │
│  │Pre-Exec  │  │Post-Exec        │  │
│  │Validation│  │Result Inspection│  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────────────────────────┐   │
│  │Least-Privilege Tool Scoping  │   │
│  │+ Max Step Limits             │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│      LAYER 5: CONFIG GUARD          │
│  ┌──────────┐  ┌─────────────────┐  │
│  │CORS      │  │Secret Validation│  │
│  │Hardening │  │at Startup       │  │
│  └──────────┘  └─────────────────┘  │
│  ┌──────────────────┐               │
│  │Webhook Secret    │               │
│  │Validation        │               │
│  └──────────────────┘               │
└─────────────────────────────────────┘
     │
     ▼
   Response
```

---

# Layer 1: Input Guard

## Module

```
src/guardrails/input/
├── __init__.py
├── rate_limiter.py
├── sanitizer.py
├── prompt_injection.py
└── middleware.py
```

## 1.1 Rate Limiter

### Interface

```python
class RateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if request is allowed, False if rate-limited."""

    async def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Return remaining requests in current window."""
```

### Strategy

- **Per-user:** `ratelimit:user:{user_id}:chat` — 60 requests per 60 seconds
- **Per-IP:** `ratelimit:ip:{ip}:chat` — 120 requests per 60 seconds
- **Global:** `ratelimit:global:chat` — 1000 requests per 60 seconds (configurable)
- Sliding window using Redis sorted sets (ZADD + ZREMRANGEBYSCORE + ZCOUNT)

### Middleware Placement

FastAPI middleware that checks rate before any request reaches route handlers. Returns `429 Too Many Requests` with `Retry-After` header.

## 1.2 Input Sanitizer

### Interface

```python
class InputSanitizer:
    MAX_INPUT_LENGTH: int = 2000
    MAX_MESSAGE_HISTORY: int = 20

    def sanitize(self, text: str) -> str:
        """Strip control characters, normalize Unicode, trim whitespace."""

    def validate_length(self, text: str) -> bool:
        """Check text is within acceptable length bounds."""

    def validate_topic(self, topic: str | None) -> str | None:
        """Validate topic against allowed curriculum topics."""
```

### Behavior

- Strip ASCII control characters (0x00-0x1F except \n \r \t)
- Normalize Unicode (NFC normalization)
- Enforce max length at API schema level (Pydantic `Field(max_length=2000)`)
- Reject empty/whitespace-only input
- Validate topic against known curriculum topics if provided

## 1.3 Prompt Injection Detection

### Interface

```python
class PromptInjectionDetector:
    PATTERNS: list[re.Pattern] = [...]

    def check(self, text: str) -> PromptInjectionResult:
        """Check text for prompt injection attempts."""

    @dataclass
    class PromptInjectionResult:
        detected: bool
        confidence: float
        pattern_match: str | None
```

### Detection Patterns

- System prompt override attempts: "ignore previous instructions", "you are now", "system prompt", etc.
- Role-playing escalation: "act as", "pretend to be", "from now on"
- Delimiter manipulation: token smuggling, payload splitting
- JSON/code injection attempts in natural language
- Base64/encoded content bypass attempts

### Conversation Context Window

Per-turn prompt injection detection misses decomposed attacks spread across multiple turns. Maintain a rolling window of recent turns and pass context to the detector:

```python
class ConversationContext:
    max_turns: int = 5
    recent_messages: list[dict]  # role + content per turn

    def check_escalation(self) -> bool:
        """Detect gradual boundary erosion across turns.
        Returns True if conversational trajectory is moving toward a policy violation."""
```

- Store the last N user messages in the session
- Before each new check, evaluate whether the trajectory of the conversation is trending toward policy-violating behavior
- If escalation detected, escalate to LLM judge for secondary review

### Threshold

- Confidence > 0.7: Block request, return 400 with `injection_detected`
- Confidence 0.4–0.7: Flag for review in trace metadata, allow through
- Borderline cases (0.4–0.7) feed into conversation context; repeated borderline from same session escalates

---

# Layer 2: Pipeline Guard

## 2.1 Fix SafetyNode Silent Fail-Open

### Current Behavior (`safety.py:131-134`)

```python
except (json.JSONDecodeError, KeyError):
    state.safe = True          # FAIL-OPEN: assumes safe on parse error
    state.safety_issues = []
    state.safety_score = 1.0
```

### Fixed Behavior

```python
except (json.JSONDecodeError, KeyError) as e:
    state.safe = False         # FAIL-CLOSED: assume unsafe on parse error
    state.safety_issues = [f"Safety check parse failure: {e}"]
    state.safety_score = 0.0
```

Additionally add retry logic: if the LLM fails to produce valid JSON on first attempt, retry once with a stricter prompt that includes an example of the expected JSON format.

## 2.2 Wire `should_revise()` into Graph

### Current Topology

```
claim_verifier → safety → END
```

SafetyNode can only `END`. The `should_revise()` function exists but is never called.

### New Topology

```
claim_verifier → safety → conditional
    ├── "finalize" → END
    ├── "revise" → tutor (max 2 revisions)
    └── "reject" → END (with teacher_review=True)
```

### Implementation

- Move `should_revise()` from `safety.py` to a standalone routing function
- Import it in `orchestrator.py` and add a conditional edge from `"safety"`:
  ```python
  workflow.add_conditional_edges(
      "safety",
      route_after_safety,
      {"finalize": END, "revise": "tutor", "reject": END},
  )
  ```
- Track `safety_revision_count` on AgentState (separate from `revision_count` used by claim_verifier)
- Max 2 safety revisions before forcing to `"finalize"`

## 2.3 LLM-Based Claim Verification

### Current

ClaimVerifierNode uses `extract_claims_simple()` — heuristic sentence splitting + keyword classification. No LLM verification.

### New

Add an LLM-based verification path alongside the existing heuristic path:

```python
class LLMClaimVerifier:
    async def extract_claims(self, response: str) -> list[Claim]:
        """Use LLM to extract factual claims with type classification."""

    async def verify_claims(self, claims: list[Claim], evidence: str) -> list[Claim]:
        """Use LLM to verify each claim against evidence text."""
```

### Behavior

- If LLM verification succeeds, use its results as primary
- If LLM is unavailable or times out, fall back to heuristic verification
- Claims are marked `is_grounded: true/false` with LLM-provided reasoning
- Groundedness threshold for routing stays the same (0.6 finalize, 0.3 revise, <0.3 reject)

## 2.4 Fix Hallucination Detection Bypass

### Current (`detector.py:27-35`)

```python
if not citation_map:
    return HallucinationReport(
        hallucination_rate=0.0,
        grounding_score=1.0,   # INCORRECT: assumes perfect grounding
        ...
    )
```

### Fixed

When `citation_map` is empty but `evidence_items` exist, generate a citation map from evidence items. Only return perfect score when both are empty AND there is no response text to verify.

```python
if not citation_map and not evidence_items:
    return HallucinationReport(...hallucination_rate=0.0...)
elif not citation_map and evidence_items:
    # Build citation_map from evidence items to avoid blind pass
    citation_map = [_build_citation_from_evidence(e) for e in evidence_items]
```

---

# Layer 3: Output Guard

**Critical rule: Output guard runs on EVERY response unconditionally.** Input guards are NOT a gate that makes output filtering optional. A prompt that passes input screening can still elicit a policy-violating output. Every response passes through toxicity, PII, and topic enforcement checks before delivery.

## Module

```
src/guardrails/output/
├── __init__.py
├── toxicity.py
├── topic_enforcer.py
├── pii_detector.py
└── safety_prompts_am.py    # Amharic safety prompt
```

## 3.1 Toxicity Filter

### Interface

```python
class ToxicityFilter:
    BLOCKED_PATTERNS: list[re.Pattern] = [...]

    def check(self, text: str) -> ToxicityResult:
        """Check output for toxic/harmful content."""

    @dataclass
    class ToxicityResult:
        detected: bool
        categories: list[str]  # e.g., ["profanity", "violence", "hate_speech"]
        confidence: float
```

### Categories

- Profanity (English + common Amharic terms)
- Violence/self-harm references
- Hate speech / discriminatory content
- Sexual content inappropriate for educational context
- Dangerous behavior instructions

## 3.2 Topic Drift Detection

### Interface

```python
class TopicEnforcer:
    def check(self, response: str, allowed_topic: str | None) -> TopicCheckResult:
        """Check if response stays within allowed topic."""

    @dataclass
    class TopicCheckResult:
        on_topic: bool
        confidence: float
        drifted_topics: list[str]
```

### Behavior

- If `topic` is set on the request, verify response stays within that topic
- Use keyword presence + LLM verification for high-confidence check
- Flag drifted responses for teacher review instead of blocking

## 3.3 PII Leakage Detection

### Interface

```python
class PIIDetector:
    PATTERNS: dict[str, re.Pattern] = {
        "email": ...,
        "phone": ...,
        "ethiopian_phone": ...,  # +251 format
        "credit_card": ...,
        "address": ...,
    }

    def check(self, text: str) -> PIICheckResult:
        """Check output for leaked PII."""

    @dataclass
    class PIICheckResult:
        detected: bool
        pii_types: list[str]
        redacted_text: str | None
```

### Behavior

- Detect and optionally redact PII in output
- Log PII detection events for security auditing
- Do NOT redact in-place for educational content (flag for manual review)

## 3.4 Amharic Safety Prompt

Add Amharic-language safety prompt to SafetyNode:

```
የኢትዮባዮ ደህንነት ተቆጣጣሪ ነዎት። የሚከተለውን የባዮሎጂ ትምህርት ይገምግሙ፦
1. ትክክለኛነት
2. የክፍል ደረጃ ተመጣጣኝነት
3. ደህንነት (ጎጂ ይዘት የለም)
4. ሥርዓተ ትምህርት አሰላለፍ
```

Select prompt based on `state.language` in SafetyNode.

---

# Layer 4: Tool/Action Guard

**Why separate from Output Guard:** Output filtering catches what the model *says*. Tool/action gating catches what the model *does*. An agent that produces a safe response can still execute dangerous tool calls (OWASP LLM06 — Excessive Agency). These require separate defenses that operate around function execution, not text generation.

## Module

```
src/guardrails/action/
├── __init__.py
├── pre_execution.py     # Validate tool name, params, scope before call
├── post_execution.py    # Inspect result before returning to context
├── allowlist.py         # Tool allow/deny lists per intent
└── step_limiter.py      # Max step / max tool call limits
```

## 4.1 Pre-Execution Validation

### Interface

```python
@dataclass
class ToolCall:
    name: str
    params: dict
    intent: str | None

class PreExecutionGuard:
    def validate(self, call: ToolCall) -> ValidationResult:
        """Check tool call before execution. Return pass/block."""

    @dataclass
    class ValidationResult:
        allowed: bool
        reason: str | None
        redacted_params: dict | None
```

### Checks

- **Tool name allowlist:** Only known tools can be invoked. Unknown tools are blocked.
- **Parameter schema validation:** Each tool call validated against its parameter schema (Pydantic model). Reject malformed or injected parameters.
- **Parameter sanitization:** Strip PII or secrets from tool params before execution.
- **Scope enforcement:** Per-intent tool allowlists — a "search" intent should not call "send_email".

### Behavior

- Blocked calls return a descriptive error to the orchestrator, not to the user
- Blocked events are logged with full call context
- Parameter redaction is additive (original params flagged, not destroyed)

## 4.2 Post-Execution Inspection

### Interface

```python
class PostExecutionGuard:
    def inspect(self, call: ToolCall, result: Any) -> InspectionResult:
        """Check tool result before injecting back into LLM context."""

    @dataclass
    class InspectionResult:
        safe: bool
        redacted_result: Any | None
        truncation_needed: bool
```

### Checks

- **Result size cap:** Truncate oversized results to prevent context flooding
- **Sensitive data filter:** Redact PII or secrets from API responses
- **Anomalous result detection:** Flag results whose shape/type differs from expected schema (may indicate compromised external service)
- **Result toxicity check:** For tools that generate text output, run text through output guard

## 4.3 Least-Privilege Tool Scoping

- Each supported intent (search, quiz, explain, summarize, etc.) has a declared tool allowlist
- Tools outside the allowlist for the current intent are rejected at pre-execution
- Allowlists are defined in config, not in code, to enable per-tenant or per-deployment variation

## 4.4 Max Step Limits

- Hard limit on consecutive tool calls per user request (default: 10)
- Hard limit on total agent steps (LLM calls + tool calls) per request (default: 15)
- When exceeded, the orchestrator returns a fallback response: "I need to simplify my approach. Let me give you a direct answer instead."
- Counters reset per-request, not per-session

---

# Layer 5: Config Guard

## 5.1 CORS Hardening

### Current (`main.py:106-112`)

```python
allow_origins=[settings.dashboard_url, "*"]
```

### Fix

- Remove `"*"` from origins
- In production, validate `dashboard_url` is set and use it exclusively
- In development (`debug=True`), allow `localhost` origins
- Log a warning at startup if CORS is configured with wildcard

## 5.2 Startup Validation

Add a `startup_checks()` function that runs on app startup:

| Check | Failure Behavior |
|-------|-----------------|
| `jwt_secret != "change-me-jwt-secret"` | Log warning |
| `secret_key != "change-me"` | Log warning |
| `telegram_webhook_secret` is set if webhook URL is set | Log warning |
| `dashboard_url != "*"` | Log warning |
| `rate_limiter` is configured | Log warning if missing |
| Redis is reachable | Log warning |

---

# Files Modified / Created

## New Files

```
src/guardrails/
├── __init__.py
├── input/
│   ├── __init__.py
│   ├── rate_limiter.py
│   ├── sanitizer.py
│   ├── prompt_injection.py
│   ├── conversation_context.py   # Multi-turn attack detection
│   └── middleware.py
├── output/
│   ├── __init__.py
│   ├── toxicity.py
│   ├── topic_enforcer.py
│   ├── pii_detector.py
│   └── safety_prompts_am.py
├── action/
│   ├── __init__.py
│   ├── pre_execution.py
│   ├── post_execution.py
│   ├── allowlist.py
│   └── step_limiter.py
└── startup.py                # Layer 5 startup checks
```

## Modified Files

| File | Change |
|------|--------|
| `src/graph/nodes/safety.py` | Fix fail-open, add Amharic prompt, wire retry |
| `src/graph/orchestrator.py` | Add conditional edge from safety node, tool gating integration |
| `src/graph/state.py` | Add `safety_revision_count`, `tool_call_history` fields |
| `src/graph/nodes/claim_verifier.py` | Add LLM-based verification path |
| `src/evaluation/hallucination/detector.py` | Fix empty citation_map bypass |
| `src/main.py` | Add rate limiter middleware, CORS fix, startup checks |
| `src/config.py` | Add rate limit + guardrail + tool gating settings |
| `src/schemas/chat.py` | Add `max_length` validation on `question` |
| `src/api/chat.py` | Add input sanitizer + prompt injection + conversation context before `run_graph()` |

---

# Error Handling

## Rate Limit Exceeded

```http
429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
```

## Prompt Injection Detected

```http
400 Bad Request
{
  "detail": "Message rejected: potential prompt injection detected",
  "code": "INJECTION_DETECTED"
}
```

## Pipeline Guardrail Failure

SafetyNode parse failure → `safe=False, score=0.0` (NOT silent pass)

## Internal Guardrail Error

If any guardrail component raises an unexpected exception:
- Log the error with full context
- Allow the request to proceed (fail-open for internal errors, not safety failures)
- Flag in trace metadata

---

# Observability (MVP)

For MVP, guardrails log key events via `structlog` with minimal metadata:

| Event | Level | When |
|-------|-------|------|
| `rate_limit_exceeded` | WARNING | Request blocked by rate limit |
| `prompt_injection_detected` | WARNING | Prompt injection caught |
| `safety_node_parse_failure` | ERROR | Safety JSON parse failed |
| `safety_node_revision` | INFO | Safety triggered a revision |
| `output_toxicity_detected` | WARNING | Toxic content in output |
| `output_pii_detected` | WARNING | PII leaked in output |
| `topic_drift_detected` | INFO | Response drifted off-topic |
| `startup_check_failed` | WARNING | Configuration issue found |

Full observability (metrics, health endpoint, tracing integration, alerting, evals) is a separate project: see `01-Planning/PRD's/Project-Wide Observability/`.

---

# Guardrail Drift Monitoring

Guardrails are not a set-and-forget deployment. Model updates, new attack patterns, and evolving application scope require ongoing calibration.

## Sources of Drift

| Source | Effect | Detection |
|--------|--------|-----------|
| Model version change | Different output distribution shifts guardrail behavior | Re-baseline eval suite on every model update |
| New injection patterns | 2024-trained classifiers miss 2026 attacks | Periodic red-teaming + dataset refresh |
| Config override accumulation | Emergency patches and feature flags weaken protections | Automated CI/CD guardrail enforcement tests |
| Threshold creep | Operators relax thresholds to reduce false positives | Track trigger rates per guardrail type over time |

## Re-Baseline Process

1. After every model version change, run the full guardrail eval suite
2. Compare catch rate and false positive rate against previous baseline
3. Update thresholds if catch rate dropped >5% or FP rate rose >5%
4. Commit new thresholds to config with changelog entry
5. If a known attack pattern bypasses all layers, add it to the test dataset and the detection patterns

---

# Testing Requirements

## Unit Tests

| Component | Tests |
|-----------|-------|
| Rate Limiter | Check within limit, exceeded limit, window reset, concurrent access |
| Input Sanitizer | Control chars, Unicode, length bounds, empty input |
| Prompt Injection Detector | All pattern categories, edge cases, false positive rate |
| Toxicity Filter | Each category, Amharic terms, edge cases |
| Topic Enforcer | On-topic, drifted, borderline |
| PII Detector | Email, phone, Ethiopian phone, edge cases |

## Integration Tests

| Scenario | Tests |
|----------|-------|
| Full pipeline with rate limiting | Blocked request returns 429 |
| SafetyNode parse failure | Returns unsafe, triggers revision |
| Empty citation_map | Does not return perfect score |
| Pipeline re-revision | Max 2 revisions enforced |

## Existing Tests to Update

| Test File | Change |
|-----------|--------|
| `tests/test_agentic_nodes.py` | Update HallucinationNode + ClaimVerifierNode tests |
| `tests/test_agents.py` | Update SafetyAgent test expectations |
| `tests/evaluation/test_production.py` | Update hardening expectations |

---

# Acceptance Criteria

## Functional (All Layers)

- [ ] Input messages are rate-limited per-user and per-IP
- [ ] Input messages are sanitized (control chars stripped, length enforced)
- [ ] Prompt injection attempts are detected and blocked (confidence > 0.7)
- [ ] SafetyNode does not silently pass on parse failure (fail-closed)
- [ ] `should_revise()` is wired into the graph — safety can trigger revision
- [ ] Claim verification has LLM-powered path (with heuristic fallback)
- [ ] Hallucination detection does not return perfect score on empty citation_map
- [ ] Output is checked for toxicity before delivery
- [ ] Output is checked for PII leakage
- [ ] Output topic drift is detected when topic is specified
- [ ] Amharic content gets Amharic-language safety evaluation
- [ ] CORS does not use wildcard origin
- [ ] Startup validates critical configuration

## Performance

- [ ] Rate limiter check < 5ms (Redis round-trip)
- [ ] Input sanitizer < 1ms
- [ ] Prompt injection detection < 2ms
- [ ] Toxicity filter on output < 2ms
- [ ] PII detection on output < 1ms
- [ ] Zero additional latency on cached/fast-path queries (no unnecessary checks)

## Architectural

- [ ] All guardrails are non-blocking (async)
- [ ] All guardrails can be disabled via config for development
- [ ] No new database tables
- [ ] No changes to existing API response schema (aside from new error codes)
- [ ] Guardrails are independently testable

---

# Success Definition

EthioBio has a **defense-in-depth content safety architecture** aligned with OWASP LLM Top 10 2025 and NIST AI RMF:

1. **Abuse is prevented** before it reaches the pipeline (rate limiting, sanitization)
2. **Prompt injection is caught** at the API layer, including multi-turn decomposition attacks
3. **Pipeline safety is hardened** — no more silent failures, dead code, or bypasses
4. **Output is filtered unconditionally** on EVERY response for toxicity, PII, and topic drift
5. **Amharic content is evaluated** with its own safety prompt
6. **Tool/action calls are validated** pre-execution and post-execution — excessive agency is prevented
7. **Misconfiguration is detected** at startup
8. **All guardrails are testable** and independently disableable
9. **Guardrail drift is monitored** — re-baselined on every model version change
10. **EU AI Act Article 14 compliance** — logged guardrail decisions provide audit evidence for human-oversight requirements
