# EthioBio AI Assistant - Planning

## Objectives
Build an AI-powered biology learning and teaching assistant for Ethiopian middle and high school education. Helps teachers save time, helps students learn more effectively, and supports parents and school administrators with simple, useful updates.

## Scope
### In Scope (v1)
- Telegram bot
- English-first biology Q&A
- Amharic support for explanations and summaries
- Curriculum-aligned retrieval
- Quiz generation
- Lesson planning
- Student progress tracking
- Parent summaries
- Teacher review dashboard
- Ollama-first model routing
- Fallback AI provider support
- Logging, monitoring, and evaluation

### Out of Scope (v1)
- Full mobile app
- Video learning platform
- Custom foundation model training
- Real-time classroom proctoring
- Non-biology subjects
- Full offline classroom package

## Approach
### Product Principles
- **Curriculum first**: answers must match Ethiopian biology content.
- **English first**: curriculum content is mainly English.
- **AI is assistive, not authoritative**: teachers control final output.
- **Low-resource friendly**: text-first, mobile-first, lightweight.
- **Modular by design**: agents and tools must be replaceable.
- **Fallback ready**: local models are primary; external providers are backup.
- **Safe and explainable**: the system should be understandable and auditable.

### AI Architecture
- **Primary**: Ollama-hosted open models for most requests
- **Fallback**: external providers when local model confidence is low, request is too complex, quality is insufficient, or local service is unavailable
- **Model Router**: decides which model to use, whether to use retrieval, call a tool, ask clarification, or fallback

### Agent System
- Orchestrator Agent
- Curriculum Retrieval Agent
- Tutor Agent
- Quiz Agent
- Lesson Planner Agent
- Translation Agent
- Student Progress Agent
- Parent Summary Agent
- Safety Agent
- Evaluation Agent

## Risks & Mitigation
| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Hallucinated answers | High | RAG, safety checks, fallback, teacher review |
| Weak Amharic output | Medium | Use Amharic selectively, keep English primary |
| Local model performance issues | High | Model routing and fallback providers |
| Poor curriculum alignment | High | Curated content store and human review |
| Low internet access | Medium | Text-first design and cached responses |

## Resources Needed
### Backend
- Python, FastAPI

### Data Storage
- PostgreSQL, Redis

### AI Runtime
- Ollama, provider adapters for fallback APIs

### Retrieval Layer
- pgvector, Qdrant, or Chroma

### Channels
- Telegram (v1), WhatsApp (later)

### Infrastructure
- Dockerized services, migration scripts, environment templates, health checks, backups
