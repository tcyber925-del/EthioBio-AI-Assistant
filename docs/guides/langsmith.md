# LangSmith: Tracing & Evaluation Guide

LangSmith (hosted) is the agent tracing + evaluation plane for the EthioBio
pipeline. It **complements** the existing stack — OTel/PipelineMonitor/Postgres
remain the source of truth for metrics and dashboards; LangSmith adds
LLM-trace visualization, prompt/run inspection, and offline experiments.

## Architecture

```
orchestrator.invoke  ──@langsmith.traceable("ethiobio.pipeline", run_type="chain")──┐
   graph.ainvoke        (nested runs: retrieval, planner, tutor, claim_verifier)     │
   ModelRouter.route  ──@langsmith.traceable("chat_llm", run_type="llm")             │
                                                                                     ▼
                                                                          captured run id
main.py _evaluate_trace ── post_feedback(run_id, results) ◄─── pipeline run metadata
                                                                          (user_id, grade_level,
                                                                           language, intent,
                                                                           langsmith_run_id)
```

- Sampling: `should_trace()` — `random() < settings.langsmith_sampling_rate`
  (no `sampling_ratio` exists in `langsmith.tracing_context`).
- Run id capture: `get_current_run_tree()` only works **inside** the
  `@traceable`-decorated function — this is why `_invoke_graph_traced`
  wraps `graph.ainvoke` and returns `(result, run_id)`.
- Online feedback: `_evaluate_trace` in `src/main.py` posts the async
  evaluation results (faithfulness, relevance, safety, helpfulness) back to
  the run via `post_feedback()` when `trace.metadata["langsmith_run_id"]` exists.
- The `session` SQLAlchemy argument is stripped from LLM inputs via
  `_llm_inputs` in `src/llm/router.py` (not JSON-serializable).
- `ModelRouter.route_stream` is intentionally **not** traced.

## Setup

```bash
# .env
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING_ENABLED=true
LANGSMITH_SAMPLING_RATE=0.1
# LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com  # EU data residency
```

Tracing is opt-in; the pipeline runs normally with it disabled (graceful
`ModuleNotFoundError` fallback if `langsmith` is not installed).

## Offline Evaluation

Datasets (created from existing benchmark scenarios + gold set):

| Dataset | Source | Outputs |
|---------|--------|---------|
| `ethiobio-curriculum` | `src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml` | `expected_topics` |
| `ethiobio-adversarial` | `src/evaluation/benchmark/scenarios/adversarial.yaml` | `expected_topics` |
| `ethiobio-gold` | `data/evaluation/gold_set.json` | `expected_answer`, `topic`, `type` |

```bash
# sync datasets (upserts; stable uuid5 example ids)
python -m src.evaluation.langsmith.sync_datasets

# run an experiment
ethiobio-langsmith --dataset ethiobio-curriculum --evaluators all
ethiobio-langsmith --dataset ethiobio-gold --evaluators faithfulness,relevance --limit 3
ethiobio-langsmith --dataset ethiobio-adversarial --threshold 0.6   # exit 1 on regression
```

- Evaluators: `topic_coverage` (deterministic, uses `expected_topics`) +
  `faithfulness`, `relevance`, `safety`, `helpfulness` (LLM judge — reuses
  `LLMJudge` from `src/observability/evaluation/judge.py`).
- `--limit` samples the first N examples (no native limit in `aevaluate`).
- The CLI forces `sampling_rate=1.0` so every eval run is traced.
- **Requires Ollama + Postgres** (runs the full `run_graph` pipeline) — run
  on a self-hosted runner or the Render cron job (`ethiobio-langsmith-eval` in
  `render.yaml`, Mondays 02:30 UTC), not GitHub-hosted CI.
  `.github/workflows/evaluate.yml` syncs datasets on schedule and runs a
  smoke subset on GitHub-hosted runners.

## Querying Traces

Use the `langsmith` CLI (from the `langsmith-trace` skill):
[install](https://cli.langsmith.com/install.sh) via
`curl -fsSL https://cli.langsmith.com/install.sh | sh`.

```bash
export LANGSMITH_API_KEY=lsv2_...

# Quick health check (projects, recent hierarchy, errors, LLM runs)
scripts/langsmith/verify_tracing.sh

# Manual queries
langsmith trace list --limit 10 --project ethiobio --show-hierarchy --api-key "$LANGSMITH_API_KEY"
langsmith trace list --error --last-n-minutes 60 --api-key "$LANGSMITH_API_KEY"
langsmith trace get <trace-id> --api-key "$LANGSMITH_API_KEY"
langsmith run list --run-type llm --limit 20 --api-key "$LANGSMITH_API_KEY"
langsmith trace export ./traces --limit 20 --full --api-key "$LANGSMITH_API_KEY"
```

- A **trace** is the full execution tree (root `ethiobio.pipeline` + nested
  LangGraph node runs + `chat_llm` runs); a **run** is one node in that tree.
  Query traces first — they preserve hierarchy.
- Filters (`--error`, `--min-latency`, `--tags`, `--filter ...`) apply to the
  root run for `trace *` and any run for `run *`.

## Files

| File | Purpose |
|------|---------|
| `src/observability/langsmith.py` | setup, lazy client, sampling, `traced_run`, run-id capture, feedback posting |
| `src/graph/orchestrator.py` | `_invoke_graph_traced` wrapper + run metadata |
| `src/llm/router.py` | `chat_llm` run tracing, input/output sanitizers |
| `src/main.py` | lifespan setup, online feedback from `_evaluate_trace` |
| `src/evaluation/langsmith/sync_datasets.py` | dataset upsert |
| `src/evaluation/langsmith/eval_target.py` | `run_graph` target wrapper |
| `src/evaluation/langsmith/evaluators.py` | topic coverage + judge evaluators |
| `src/evaluation/langsmith/run.py` | `ethiobio-langsmith` CLI |

## Known Gaps

- `_evaluate_trace` reads `trace.metadata.get("context", "")` but the
  orchestrator never populates `context` — judge dimensions currently run
  without retrieved context. Populate it in `finalize_trace` when the
  retrieval branch provides sources.