# Document Copilot — Implementation Checklist

This checklist tracks the step-by-step implementation of **Document Copilot** for Driftwood Capital, based on [client-brief.md](client-brief.md), [architecture.md](architecture.md), and [AGENTS.md](../AGENTS.md).

---

## Strategy: Where to Start & Why

### The Logical Sequence: **Data & Backend Foundation First**

1. **Why Backend & Database First:**
   - Document Copilot's entire value proposition is **trust, grounding, and accurate SEC citation**. The core risk is hallucination and citation failure ("a wrong but confident answer is worse than no answer").
   - The data model (`source_documents`, `document_chunks`, `embeddings`, `tsvectors`, `chat_threads`, `citations`) defines the contracts for both ingestion and the frontend.
   - Without ingested data and a working retrieval engine, the frontend would only be an empty shell with nothing to query.

2. **Parallel Frontend Development:**
   - Once the database schema, auth contracts, and streaming API endpoints (`POST /chat/stream`) are specified, the frontend can be scaffolded and wired to Supabase Auth in parallel.

---

## Phase 0: External Services & Data Preparation

- [x] **0.1 Supabase Project Setup**
  - [x] Create hosted Supabase project (see [docs/guides/supabase-setup.md](guides/supabase-setup.md))
  - [x] Record credentials in `.env`: Project URL, `anon` key, `service_role` key, direct Postgres connection string
  - [x] Configure Auth: Enable Email provider (disable "Confirm email" for local dev)
- [x] **0.2 SEC Sample Corpus Ingestion Download**
  - [x] Run `python data/download.py` from repository root
  - [x] Verify 10-K filings are downloaded for Apple, Amazon, Alphabet, Microsoft, and NVIDIA (FY 2021–2025)

---

## Phase 1: Backend Foundation & Database Schema

- [x] **1.1 Backend Environment & Dependencies**
  - [x] Initialize backend dependencies with `uv sync` (see [docs/guides/backend-setup.md](guides/backend-setup.md))
  - [x] Add required libraries: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`, `structlog`, `openai`, `supabase`, `pydantic-ai`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `pgvector`
  - [x] Add dev dependencies: `pytest`, `ruff`
  - [x] Implement `app/config.py` using `pydantic-settings` (single source of truth for env vars; fail fast on missing keys)
- [ ] **1.3 Structured Logging**
  - [ ] Configure `structlog` with JSON output in `app/logging.py`
  - [ ] Wire into FastAPI startup so all request/ingestion logs are structured
- [x] **1.2 Database Schema & Alembic Migrations**
  - [x] Initialize Alembic in `backend/alembic` configured with `app.config.settings` and direct session connection
  - [x] Define SQLAlchemy models in `app/database/models/`:
    - [x] `users`: `id` (FK to `auth.users`), `email`, `created_at`
    - [x] `source_documents`: `id`, `ticker`, `company_name`, `filing_type`, `fiscal_year`, `filing_date`, `accession_number`, `source_url`, `content_markdown`, `metadata`
    - [x] `document_chunks`: `id`, `document_id`, `chunk_index`, `section`, `page`, `chunk_text`, `embedding` (vector), `search_vector` (`tsvector`), `token_count`, `metadata`
    - [x] `chat_threads`: `id`, `user_id`, `title`, `created_at`, `updated_at`
    - [x] `chat_messages`: `id`, `thread_id`, `role`, `content`, `message_metadata`, `created_at`
    - [x] `message_citations`: `id`, `message_id`, `chunk_id`, `document_id`, `citation_index`, `excerpt`, `page`, `section`
  - [x] Write initial Alembic migration (`uv run alembic revision --autogenerate` + explicit SQL):
    - [x] `CREATE EXTENSION IF NOT EXISTS vector;`
    - [x] Generated `tsvector` trigger/column for lexical full-text search
    - [x] HNSW index on `document_chunks.embedding`
    - [x] GIN index on `document_chunks.search_vector`
    - [x] Row Level Security (RLS) policies for user data isolation
  - [x] Run migration: `uv run alembic upgrade head`

---

## Phase 2: Ingestion & Document Processing Pipeline

- [x] **2.1 Document Parser & Markdown Normalizer (`data/convert.py`)**
  - [x] Parse downloaded SEC 10-K HTML files into clean, structured Markdown using Docling
  - [x] Preserve section headings (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A, Financial Statements)
  - [x] Extract filing metadata (ticker, fiscal year, filing date, accession number) into `data/markdown/manifest.json`

- [x] **2.2 Chunking & Context Enrichment**
  - [x] Implement hierarchical / section-aware chunking with token target (~500–1000 tokens per chunk with overlap)
  - [x] Enrich each chunk with filing metadata header (ticker, year, section, page)
- [x] **2.3 Embedding Generation & Database Storage**
  - [x] Generate Gemini embeddings (`gemini-embedding-001` / 768 dimensions) in batches via Gemini API
  - [x] Implement `app/database/documents.py` — upsert and query helpers for `source_documents`
  - [x] Bulk upsert 25 source documents (Markdown + SEC metadata) into Supabase Postgres
  - [x] Chunk filings, generate vector embeddings, and populate `document_chunks` table (`app.ingest.pipeline`)
  - [x] Verify ingested chunk count, vector dimensions (768), and FTS indexing across all 5 companies (2021–2025)

- [x] **2.4 Ingestion CLI & Idempotency**
  - [x] Create CLI entry point (`python -m app.ingest.pipeline`) to run the full pipeline
  - [x] Implement idempotency: skip already-ingested filings (match on `document_id`)
  - [x] Add progress logging (filing count, chunk count, elapsed time)
---

## Phase 3: Hybrid Retrieval & Grounding Engine

- [x] **3.1 Semantic Search (`pgvector`)**
  - [x] Implement query vector embedding with Gemini (`gemini-embedding-001` / `text-embedding-004`)
  - [x] Implement cosine distance search against `document_chunks.embedding` in `app/retrieval/queries.py`
- [x] **3.2 Lexical Search (Postgres FTS)**
  - [x] Implement `websearch_to_tsquery` against `document_chunks.search_vector` with phrase quoting support
  - [x] Implement `extract_search_keywords` in `app/retrieval/keywords.py` to extract 2–3 salient terms (tickers, years, financial phrases) and prevent AND conjunction drops on conversational queries
- [x] **3.3 Reciprocal Rank Fusion (RRF)**
  - [x] Implement RRF algorithm in `app/retrieval/fusion.py` to merge semantic and keyword rankings
  - [x] Support filtering by ticker, fiscal year, and filing type
  - [x] Implement surrounding context / neighboring chunks retrieval for grounding
- [x] **3.4 Grounding Validator (`app/grounding/validator.py`)**
  - [x] Validate that all generated citations map directly to retrieved chunks
  - [x] Enforce "no citation, no claim" policy: fail or decline answer if passages do not support claims
- [x] **3.5 Unit & Integration Tests**
  - [x] Test hybrid search fusion logic (`tests/retrieval/test_fusion.py`)
  - [x] Test grounding validator with positive and negative assertion cases
  - [x] Test hybrid retriever candidate pipeline with mocked queries (`tests/retrieval/test_retriever.py`)


---

## Phase 4: Assistant Orchestration & Backend API

- [x] **4.1 CORS, Lifespan & App Wiring**
  - [x] Configure CORS middleware in `app/main.py` using `settings.cors_origins`
  - [x] Implement FastAPI lifespan handler for startup/shutdown hooks
- [x] **4.2 Supabase Auth & Client Helpers**
  - [x] Implement `app/database/supabase.py` (admin and user-scoped Supabase client factories using `settings`)
  - [x] Implement `app/auth/dependencies.py` to validate `Authorization: Bearer <token>` against Supabase
  - [x] Create `get_current_user` FastAPI dependency
  - [x] Write unit tests for token validation and thread authorization checks
- [x] **4.3 Chat Persistence (`app/database/chats.py`)**
  - [x] Implement thread CRUD: create, list by user, get by ID with ownership check
  - [x] Implement message persistence: append user/assistant messages to thread
  - [x] Implement citation persistence: bulk insert `message_citations` linked to assistant message
- [x] **4.4 PydanticAI Assistant Agent (`app/assistant/`)**
  - [x] Define agent dependencies in `deps.py` (`DocumentAgentDeps`: user, thread, retriever, grounding validator)
  - [x] Define structured output models in `outputs.py` (`GroundedAnswer`, `Citation`, `SourcePassage`)
  - [x] Provide system prompt in `instructions.md` enforcing Driftwood Capital rules:
    - Ground strictly in retrieved passages
    - Mandatory filing + section citations
    - Explicit refusal when evidence is insufficient
    - Zero speculative investment advice or stock recommendations
- [x] **4.5 Chat Orchestrator (`app/chat/orchestrator.py`)**
  - [x] Coordinate one chat turn end-to-end: auth → retrieval → agent → citation validation → persistence → streaming
  - [x] Implement `app/chat/streaming.py` — emit AI SDK-compatible SSE events (text deltas, citations, finish)
- [x] **4.6 Chat Endpoints (`app/api/chat.py`)**
  - [x] Thread management endpoints: `GET /chat/threads`, `POST /chat/threads`, `GET /chat/threads/{id}/messages`
  - [x] Streaming endpoint: `POST /chat/stream` delegating to `orchestrator`

---

## Phase 5: Frontend Foundation & Authentication

> **Parallelization note:** 5.3 (Auth Flows) depends only on Supabase, not on any backend endpoint. It can be built in parallel with Phase 3 or 4.

- [x] **5.1 Frontend Scaffolding & Tooling**
  - [x] Initialize Vite + React SPA with TypeScript in `frontend/`
  - [x] Configure `pnpm` with `.npmrc` (7-day release age check)
  - [x] Configure Tailwind CSS v4 (`@tailwindcss/vite` plugin)
  - [x] Configure path alias `@/*` in `tsconfig.json` and `vite.config.ts`
  - [x] Install remaining dependencies: `react-router-dom`, `@supabase/supabase-js`, `@ai-sdk/react`, `ai`, `lucide-react`, `react-markdown`, `remark-gfm`
  - [x] Setup shadcn/ui CLI (`pnpm dlx shadcn@latest init`)
- [x] **5.2 Configuration & HTTP Client**
  - [x] Implement `src/lib/env.ts` (validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`)
  - [x] Implement `src/lib/supabase.ts` (browser Supabase client)
  - [x] Implement `src/lib/http.ts` & `src/lib/api.ts` (fetch wrapper with Supabase JWT bearer injection and typed `ApiError`)
- [x] **5.3 Authentication Flows**
  - [x] Build clean Driftwood login / signup page (`src/pages/auth/Login.tsx`) using Supabase email auth
  - [x] Setup Auth context / route guard to redirect unauthenticated analysts

---

## Phase 6: Frontend Chat & Citation Inspector UI

- [x] **6.1 App Layout & Thread Navigation**
  - [x] Build main layout with sidebar for past conversation threads (`src/components/layout/Sidebar.tsx`)
  - [x] Implement "New Chat" action and thread switching with React Router
- [x] **6.2 Streaming Chat Interface**
  - [x] Implement streaming chat container connected to live `POST /chat/stream`
  - [x] Render assistant responses with real-time markdown streaming (`MessageBubble.tsx`)
  - [x] Display suggested analyst prompts (from client brief) in empty states (`EmptyState.tsx`)
- [x] **6.3 Interactive Citation & Source Passage Inspector**
  - [x] Render inline citation badges (e.g., `[AAPL 2024 10-K, Item 7]`) (`CitationBadge.tsx`)
  - [x] Build slide-over drawer to inspect exact source passage excerpts, fiscal year, and metadata in one click (`SourceDrawer.tsx`)
  - [x] Add copy passage / copy quote action for analysts to paste into equity reports
- [x] **6.4 Trust UI & Resilience (Citations, States & Error Handling)**
  - [x] Citation chips/links on assistant messages (`company`, `filing type`, `date`, `page/section`) (`CitationBadge.tsx`)
  - [x] Source passage panel: slide-over drawer showing underlying excerpt for selected citation (`SourceDrawer.tsx`)
  - [x] Empty states:
    - [x] Suggested prompt grid for new chats (`EmptyState.tsx`)
    - [x] Empty thread history state ("No conversation threads yet" in `Sidebar.tsx`)
    - [x] No corpus match / refusal state ("Corpus Boundary — Strict Grounded Refusal" in `MessageBubble.tsx`)
  - [x] Error states:
    - [x] Auth expired (401 redirect to login with actionable sign-in button)
    - [x] Retrieval / server failure (graceful fallback alert banner)
    - [x] Network / CORS connection error banner with host troubleshooting advice
  - [x] Loading & streaming status indicators during assistant run (live `status_event` pipeline updates: searching $\to$ analyzing $\to$ validating)
  - [x] Verification: click a citation badge to inspect the exact passage in one click


---

## Phase 7: End-to-End Verification & Client Brief Benchmarks

> **Note:** Unit tests for retrieval, grounding, and auth are now inline with their respective phases (3.5, 4.2). This phase focuses on full-system integration and the client brief benchmark.

- [ ] **7.1 Client Brief Benchmark Evaluation**
  - Test the 10 representative analyst questions from [client-brief.md](client-brief.md):
    - [ ] Apple revenue mix shift across iPhone, Services, Mac, iPad, Wearables (2021–2025)
    - [ ] Amazon AWS operating income/margins vs. North America & International (2021–2025)
    - [ ] NVIDIA Data Center demand drivers, customer concentration, and supply constraints
    - [ ] Microsoft Azure & AI infrastructure capacity commentary
    - [ ] Alphabet segment revenue trends (Search, YouTube, Cloud, Network)
    - [ ] Risk-factor changes on AI, export controls, and supply chain across all 5 companies
    - [ ] Apple vs. NVIDIA supplier concentration / third-party foundry language comparison
    - [ ] CapEx & purchase commitment trends for hyperscalers (MSFT, GOOGL, AMZN, NVDA)
    - [ ] Geographic revenue exposures in latest 10-Ks
    - [ ] Negative test: GenAI margin proof question (verifying the bot refuses to infer beyond filings)
- [ ] **7.2 Security & Boundaries Check**
  - [ ] Confirm no service-role key leaks to frontend
  - [ ] Confirm user thread isolation (analyst A cannot read analyst B's threads)
  - [ ] Confirm frontend builds cleanly: `pnpm tsc --noEmit` and `pnpm build`

---

## Phase 8: Deployment & Operational Readiness

See [Railway Deployment Runbook](guides/railway-deployment.md) for full instructions and variables mapping.

- [x] **8.1 Backend Containerization & Deployment Setup**
  - [x] Create multi-stage `backend/Dockerfile` with `uv` and Python 3.12
  - [x] Integrate startup Alembic migrations hook (`uv run alembic upgrade head`)
  - [x] Configure dynamic port binding (`--port ${PORT:-8000}`) and healthcheck (`/health`)
  - [x] Add `backend/.dockerignore`
- [x] **8.2 Frontend Containerization & SPA Routing Setup**
  - [x] Create multi-stage `frontend/Dockerfile` (`node:22` builder + `nginx:alpine` runtime)
  - [x] Configure build-time `VITE_*` environment variable arguments
  - [x] Create `frontend/nginx.conf.template` with dynamic `${PORT}` substitution and SPA fallback (`try_files $uri $uri/ /index.html;`)
  - [x] Add `frontend/.dockerignore`
- [x] **8.3 Railway Cloud Execution**
  - [x] Connect repository to Railway project (`document-pilot` / `8617a728-86fd-4ad3-b712-ce489bc8b643`)
  - [x] Deploy backend service (`/backend`) & verify `/health` (`https://document-copilot-backend-production-0fca.up.railway.app`)
  - [x] Deploy frontend service (`/frontend`) & wire `VITE_API_BASE_URL` (`https://document-copilot-frontend-production-3f38.up.railway.app`)
  - [x] Update backend `ALLOWED_ORIGINS` with frontend production domain
- [ ] **8.4 Pilot Handover & Verification**
  - [ ] Smoke test authentication, streaming, and citation drawer on production domains
  - [ ] Onboard pilot group (5 senior analysts) with Driftwood credentials
  - [ ] Validate 3-hour weekly intake time savings goal

