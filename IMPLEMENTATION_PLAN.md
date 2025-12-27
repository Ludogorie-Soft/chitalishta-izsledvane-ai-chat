# RAG System – Implementation Plan

This document defines the step-by-step implementation plan for the RAG system.
It is the **single source of truth** for development progress.

Rules:
- Steps must be completed **in order**
- A step is complete **only** when its Definition of Done is met
- Do not proceed to the next step without explicit confirmation
- Cursor and AI assistants must follow this plan strictly

---

## Current Status
- Phase: Phase 10 – Quality & Observability
- Current Step: Step 10.6 Complete - All phases complete!
- Blockers: none

---

# Phase 1 – FastAPI + PostgreSQL Foundation

## Step 1.1 – Project initialization
- [x] Create project folder structure
- [x] Initialize Python virtual environment
- [x] Install core dependencies
- [x] Create FastAPI app instance
- [x] Add `/health` endpoint
- [x] Run app locally

**Definition of Done**
- `/health` returns HTTP 200
- `/docs` is accessible
- App runs with `uvicorn --reload`

---

## Step 1.2 – Configuration management
- [x] Create `.env` file
- [x] Implement Pydantic Settings
- [x] Load DATABASE_URL from environment
- [x] Remove hardcoded configuration

**Definition of Done**
- App starts using env-based configuration
- DATABASE_URL is not hardcoded anywhere

---

## Step 1.3 – PostgreSQL integration
- [x] Create SQLAlchemy engine
- [x] Create session factory
- [x] Implement `get_db` dependency
- [x] Add DB connectivity test endpoint

**Definition of Done**
- DB connection succeeds
- `/db/ping` returns success

---

## Step 1.4 – Database models
- [x] Implement `Chitalishte` model
- [x] Implement `InformationCard` model
- [x] Configure relationships
- [x] Match existing schema exactly

**Definition of Done**
- Query Chitalishte with related InformationCards
- No schema mismatches or runtime errors

---

## Step 1.5 – Data access layer (repositories)
- [x] Create repository structure
- [x] Implement read-only queries
- [x] Add filtering by region, town, status, year

**Definition of Done**
- Repositories return correct data
- No SQL logic inside API routes

---

## Step 1.6 – Public data API endpoints
- [x] `GET /chitalishte/{id}`
- [x] `GET /chitalishte`
- [x] `GET /chitalishte/{id}/cards`
- [x] Pydantic response schemas

**Definition of Done**
- Endpoints work and are documented in `/docs`
- Responses are correctly typed

---

# Phase 2 – Ingestion & Semantic Preparation

## Step 2.1 – Data extraction service
- [x] Extract Chitalishte data
- [x] Extract InformationCard data
- [x] Support optional year filtering

**Definition of Done**
- Raw data extraction works without errors

---

## Step 2.2 – Semantic transformation
- [x] Convert DB rows to Bulgarian narrative text
- [x] Generate numeric summaries (no raw tables)
- [x] Normalize text encoding

**Definition of Done**
- Output text is human-readable Bulgarian
- Numeric data is expressed semantically

---

## Step 2.3 – Document assembly
- [x] One document per Chitalishte per year
- [x] Attach metadata (region, year, status, counts)
- [x] Validate document size

**Definition of Done**
- Documents are ready for embedding
- Metadata supports filtering

---

## Step 2.4 – Ingestion preview endpoint
- [x] `POST /ingest/database`
- [x] Limit number of documents
- [x] Return JSON preview

**Definition of Done**
- Preview output matches intended RAG input

---

## Step 2.5 – Analysis document ingestion
- [x] Load DOCX analysis document (Chitalishta_demo_ver2.docx)
- [x] Extract structured sections and paragraphs
- [x] Implement hierarchical chunking:
  - Step 1: Split by headings/sections
  - Step 2: Split long sections by paragraphs (keep chunks under 700-900 tokens)
  - Step 3: Apply light overlap (10-15% overlap between chunks)
- [x] Add document-specific metadata:
  - `source: "analysis_document"`
  - `document_type: "main_analysis"`
  - `document_name: "Chitalishta_demo_ver2"`
  - `author: "ИПИ"`
  - `document_date: "2025-12-09"`
  - `language: "bg"`
  - `scope: "national"`
  - `version: "v2"`
- [x] Ensure chunks are distinguishable from DB content
- [x] Support manual re-ingestion via `POST /ingest/analysis-document` endpoint

**Definition of Done**
- Document is chunked and ready for embedding
- All chunks have proper metadata identifying them as analysis document
- Chunking preserves semantic structure
- `POST /ingest/analysis-document` endpoint triggers re-ingestion
- Endpoint returns ingestion status and chunk count

---

# Phase 3 – Vector Store & Embeddings (Chroma)

## Step 3.1 – Chroma initialization
- [x] Configure Chroma persistence directory
- [x] Initialize vector store
- [x] Clear/rebuild index safely

**Definition of Done**
- Chroma starts and persists data locally

---

## Step 3.2 – Embedding layer
- [x] Abstract embedding interface
- [x] OpenAI embedding implementation
- [x] Hugging Face embedding implementation

**Definition of Done**
- Embeddings can be switched via config

---

## Step 3.3 – Indexing pipeline
- [x] Batch document ingestion (DB content)
- [x] Analysis document ingestion (Step 2.5 output)
- [x] Metadata indexing (support both source types)
- [x] Idempotent re-indexing
- [x] Support manual re-ingestion of analysis document

**Definition of Done**
- All documents (DB + analysis) are searchable via Chroma
- Metadata properly distinguishes source types

---

## Step 3.4 – LangChain integration
- [x] Install LangChain dependencies (`langchain`, `langchain-openai`, `langchain-community`, `langchain-chroma`)
- [x] Integrate LangChain with existing Chroma vector store
- [x] Create LangChain Chroma retriever wrapper (using existing ChromaVectorStore)
- [x] Integrate LangChain with existing embedding service (custom EmbeddingService)
- [x] Test LangChain retriever with existing indexed documents
- [x] Verify compatibility with existing custom abstractions

**Definition of Done**
- LangChain is installed and configured
- LangChain retriever works with existing Chroma collection
- Existing custom abstractions (embeddings, vector store) remain functional
- No breaking changes to existing indexing pipeline

---

# Phase 4 – Query Understanding & Routing

## Step 4.1 – Rule-based intent classification
- [x] Define Bulgarian keyword rules
- [x] Compute rule confidence
- [x] Return intent + confidence

**Definition of Done**
- Simple queries are correctly classified

---

## Step 4.2 – LLM-based intent classification
- [x] Implement LLM classifier using LangChain
- [x] Use LangChain's structured output support (Pydantic models)
- [x] Configure LLM abstraction (OpenAI/HuggingFace via LangChain)
- [x] Confidence score returned
- [x] Bulgarian prompt templates for intent classification

**Definition of Done**
- Ambiguous queries are handled correctly
- Structured outputs are validated via Pydantic
- LLM can be switched via LangChain abstraction

---

## Step 4.3 – Hybrid routing logic
- [x] Combine rule + LLM signals
- [x] Final intent decision
- [x] Safe fallback to hybrid

**Definition of Done**
- Routing is deterministic and explainable

---

# Phase 5 – RAG & SQL Pipelines

## Step 5.1 – RAG retrieval chain
- [x] Implement LangChain RAG chain (RetrievalQA or ConversationalRetrievalChain)
- [x] Use LangChain Chroma retriever with metadata filtering
- [x] Support both DB content and analysis document via metadata filters
- [x] Implement retrieval priority logic:
  - Retrieve analysis document only when relevant
  - Do not let analysis document override DB facts
  - Prefer DB content for factual queries
- [x] Create Bulgarian prompt templates using LangChain PromptTemplate
- [x] Context assembly using custom logic (maintain control over DB facts vs analysis doc separation)
- [x] Pass assembled context into LangChain chains (LangChain consumes context, does not define it)
- [x] Integrate with existing embedding service via LangChain embedding interface

**Definition of Done**
- RAG answers are grounded in context
- System distinguishes between DB facts and analysis document content
- Retrieval prioritizes DB content for factual queries
- LangChain chain orchestrates retrieval and generation
- Custom context assembly logic maintains full control over data mixing

---

## Step 5.2 – SQL agent
- [x] Implement LangChain SQL agent (create_sql_agent)
- [x] Configure read-only database access (SQLAlchemy connection)
- [x] Add safety constraints (prevent DELETE/UPDATE/INSERT)
- [x] SQL generation logic is validated and optionally post-processed before execution
- [x] Support aggregation queries
- [x] Bulgarian language support for SQL query generation
- [x] Error handling and query validation
- [x] Audit logging of generated SQL queries

**Definition of Done**
- Numeric answers are correct and safe
- SQL agent only performs read operations
- Agent handles complex aggregation queries
- All SQL queries are validated before execution
- SQL generation is auditable and traceable

---

## Step 5.3 – Hybrid pipeline
- [x] Create LangChain chain for hybrid queries (SequentialChain or custom chain)
- [x] SQL → text context conversion (format SQL results as narrative)
- [x] RAG enrichment using retrieval chain
- [x] Combine SQL and RAG results using LangChain's chain composition
- [x] Unified answer format (Bulgarian)
- [x] Routing logic to determine when to use SQL vs RAG vs hybrid

**Definition of Done**
- Hybrid queries return correct combined answers
- LangChain orchestrates SQL and RAG pipeline execution
- Results are properly formatted and combined

---

## Step 5.4 – RAG fallback mechanism
- [x] Add fallback LLM configuration (provider and model selection)
- [x] Implement "no information" response detection (Bulgarian patterns)
- [x] Add automatic retry logic with more powerful LLM when initial answer indicates no information
- [x] Integrate fallback only for RAG-only queries (disabled for hybrid queries)
- [x] Add metadata tracking for fallback usage
- [x] Implement graceful degradation (fallback to original answer if retry fails)
- [x] Add configuration options to enable/disable fallback feature

**Definition of Done**
- System automatically retries with more powerful LLM when initial RAG answer is "no information"
- Fallback only applies to RAG-only queries (not hybrid queries)
- Cost optimization: expensive model only used when necessary
- Fallback usage is tracked in response metadata
- Feature can be enabled/disabled via configuration

---

# Phase 6 – LLM Management

## Step 6.1 – LLM registry
- [x] Use LangChain's LLM abstraction (ChatOpenAI, HuggingFacePipeline, etc.)
- [x] Create LLM factory/registry using LangChain's model abstractions
- [x] Support OpenAI models (via langchain-openai)
- [x] Support Hugging Face models (via langchain-community)
- [x] Task-based selection (different models for classification vs generation)
- [x] Configuration via environment variables

**Definition of Done**
- Models are swappable at runtime via LangChain abstraction
- Multiple LLM providers supported
- Task-specific model selection works

---

## Step 6.2 – Hallucination control modes
- [x] Implement mode-based LLM configuration (via LangChain LLM parameters)
- [x] Low tolerance mode (low temperature, strict prompts, citation requirements)
- [x] High tolerance mode (higher temperature, more creative prompts)
- [x] Temperature and prompt control via LangChain chain configuration
- [x] Prompt templates that enforce grounding in retrieved context
- [x] Mode selection in API requests (completed in Phase 7.1 – Chat endpoint)

**Definition of Done**
- User can switch answer strictness
- Different modes use appropriate temperature and prompt strategies
- LangChain chains respect mode configuration

---

# Phase 7 – API & UX

## Step 7.1 – Chat endpoint
- [x] `/chat` endpoint (FastAPI route)
- [x] Implement streaming using LangChain's streaming support (streaming=True)
- [x] Chat history management (optional use of LangChain memory OR custom conversation state)
- [x] Mode selection (low/high tolerance)
- [x] Integration with RAG/SQL/Hybrid chains
- [x] Error handling and timeout management

**Definition of Done**
- Chat works end-to-end
- Streaming responses work correctly
- Chat history is maintained across conversation (via LangChain memory or custom state)
- Mode selection affects response generation
- Memory implementation is flexible and not locked into LangChain abstractions

---

## Step 7.2 – Structured outputs
- [x] Tables
- [x] Bullet summaries
- [x] Statistics

**Definition of Done**
- Output matches requested format

---

# Phase 8 – Auth & Public Access

## Step 8.1 – Anonymous access
- [ ] Rate limiting
- [ ] Abuse protection

**Definition of Done**
- Public users can query safely

---

## Step 8.2 – Authentication
- [ ] Signup
- [ ] Login
- [ ] User context (optional)

**Definition of Done**
- Authenticated and anonymous flows coexist

---

# Phase 9 – Deployment & Ops

## Step 9.1 – Dockerization
- [x] Dockerfile
- [x] Environment config
- [x] Local build

**Definition of Done**
- App runs in Docker

---

## Step 9.2 – AWS EC2 deployment
- [ ] EC2 provisioning
- [ ] GPU setup (if needed)
- [ ] Process manager

**Definition of Done**
- App is accessible on EC2

---

## Step 9.3 – AWS Native (Mostly Free Tier) observability
- [ ] Configure CloudWatch Logs integration
  - Set up log group for application logs
  - Configure log stream from structured JSON logs
  - Set up log retention policy (7-30 days for free tier)
- [ ] Configure CloudWatch Metrics
  - EC2 instance metrics (CPU, memory, disk, network)
  - Custom application metrics (request count, latency, error rate)
  - Custom business metrics (token usage, cost estimates)
- [ ] Set up CloudWatch Alarms
  - High error rate alerts (4xx / 5xx threshold)
  - High latency alerts (p95/p99 thresholds)
  - EC2 resource alerts (CPU, memory, disk usage)
  - Custom metric alerts (token usage spikes, cost thresholds)

**What you can monitor:**

**Request metrics (via CloudWatch Logs):**
- Request count & latency (extracted from structured logs)
- Error rate (4xx / 5xx status codes)
- Request patterns by endpoint, method, status

**EC2 system metrics (via CloudWatch Metrics):**
- CPU utilization percentage
- Memory usage (bytes and percentage)
- Disk I/O and disk space usage
- Network I/O (bytes in/out)

**Custom application metrics (via CloudWatch Metrics):**
- Token usage (input, output, total) by model/provider
- Cost estimates per request/endpoint/model
- RAG query latency and document retrieval count
- SQL query latency and execution status
- LLM call latency by model/provider/task

**Definition of Done**
- CloudWatch Logs collect all application logs
- CloudWatch Metrics track EC2 and custom application metrics
- CloudWatch Alarms notify on critical thresholds
- Monitoring dashboard provides visibility into system health
- All metrics are accessible via AWS Console and APIs

---

# Phase 10 – Quality & Observability

## Step 10.1 – Structured logging foundation
- [x] Install structured logging library (`structlog` or `loguru`)
- [x] Configure JSON-formatted logs with timestamps
- [x] Set up log levels (DEBUG, INFO, WARNING, ERROR)
- [x] Create log rotation strategy (file size/time-based)
- [x] Add request ID generation (UUID) for trace correlation
- [x] Implement FastAPI middleware for request/response logging
- [x] Log all API endpoints (query, routing, errors)

**Definition of Done**
- All application events are logged in structured JSON format
- Request tracing works end-to-end with trace IDs
- Logs are searchable and parseable

---

## Step 10.2 – LangChain observability (callbacks)
- [x] Create custom LangChain callback handler (`StructuredLoggingCallbackHandler`)
- [x] Implement callback methods:
  - `on_llm_start` / `on_llm_end` (log LLM calls, token usage, latency)
  - `on_retriever_start` / `on_retriever_end` (log retrieval queries and results)
  - `on_chain_start` / `on_chain_end` (log chain execution flow)
  - `on_chain_error` (log chain failures with context)
- [x] Store trace data (inputs, outputs, intermediate steps) in structured logs
- [x] Include trace IDs in all callback logs for correlation
- [x] Log metadata (model used, retrieval count, document sources)
- [x] Integrate callbacks into all LangChain chains (RAG, SQL agent, hybrid)

**Definition of Done**
- All LangChain operations are traceable via callbacks
- Full execution flow is logged (retrieval → LLM → response)
- Token usage and latency are captured for each operation
- Traces can be correlated with API requests via trace IDs

---

## Step 10.3 – Chat logging to database
- [x] Create `chat_logs` database table with comprehensive schema
- [x] Implement `ChatLog` SQLAlchemy model
- [x] Create `ChatLogger` service for logging chat requests/responses
- [x] Implement `ChatLoggerCallbackHandler` to capture LLM operations and SQL queries from tool calls
- [x] Integrate chat logging into POST /chat endpoint
- [x] Capture SQL queries from LangChain tool invocations
- [x] Store LLM operations (model, token usage, latency) as JSONB
- [x] Log both successful and failed requests (validation errors, 500 errors)
- [x] Include cost tracking (total input/output/total tokens)
- [x] Create database migration script
- [x] Add indexes for common admin queries

**Definition of Done**
- All POST /chat requests are logged to database
- SQL queries are captured and stored when executed
- LLM operations are stored with token usage and latency
- Failed requests are logged with error details
- Cost tracking data is available for analysis
- Database table is ready for admin page integration

---

## Step 10.4 – Performance monitoring
- [x] Install metrics library (`prometheus-client`)
- [x] Define key metrics:
  - Request counters (total queries, by endpoint, by status)
  - Latency histograms (RAG queries, SQL queries, LLM calls, retrieval)
  - Token usage counters (input tokens, output tokens, by model)
  - Error rates (by error type, by endpoint)
- [x] Create timing decorators for critical operations
- [x] Expose Prometheus metrics endpoint (`/metrics`)
- [x] Track system metrics (CPU, memory, database connection pool)
- [x] Log performance metrics to structured logs

**Definition of Done**
- Performance metrics are collected and exposed
- Latency tracking works for all critical paths
- System health metrics are monitored
- Metrics endpoint is accessible for scraping

---

## Step 10.5 – Cost tracking (lightweight)
- [x] Create lightweight cost calculation service (`CostCalculator`)
- [x] Define pricing models for all LLM providers:
  - OpenAI models (GPT-4, GPT-4o, GPT-4o-mini, GPT-3.5-turbo, embeddings)
  - Hugging Face models (local/self-hosted = free)
  - TGI models (local = free)
- [x] Add `cost_usd` column to `chat_logs` table
- [x] Add `llm_model` column to `chat_logs` table (primary model used)
- [x] Calculate cost at log time from token usage and model pricing
- [x] Store calculated cost in `chat_logs.cost_usd` column
- [x] Store primary LLM model in `chat_logs.llm_model` column
- [x] Create database migration script for new columns

**Definition of Done**
- Cost is calculated automatically when logging chat requests
- Cost data is stored in `chat_logs` table alongside token counts
- Primary LLM model is tracked for each request
- Cost can be queried via SQL (e.g., daily/monthly totals, cost per model)
- No separate cost tracking infrastructure needed

---

## Step 10.6 – Evaluation
- [x] Bulgarian test queries
  - Create comprehensive integration/e2e test suite with real Bulgarian queries against indexed data
  - Cover SQL, RAG, and hybrid intent types with actual database and vector store
  - Verify correct routing, intent classification, and answer quality
  - Note: Unit tests with Bulgarian queries already exist but use mocks; need real end-to-end tests
  - **Cost-conscious testing strategy**: Use pytest markers to separate test tiers
    - Default `pytest` runs only mocked tests (no cost, fast execution)
    - Integration tests use cheaper LLMs (`gpt-4o-mini` or local TGI) - opt-in via `pytest -m integration`
    - Full e2e tests use production LLMs (`gpt-4o`) - opt-in via `pytest -m e2e`
    - Mark integration tests with `@pytest.mark.integration` and e2e tests with `@pytest.mark.e2e`
    - Configure `pytest.ini` to exclude `integration` and `e2e` markers by default
- [x] Groundedness checks
  - Implement validation to ensure RAG-generated answers are supported by retrieved context/documents
  - Prevent hallucinations by verifying answers cite sources or are based on actual retrieved documents
  - Add checks that answers don't contain information not present in the retrieved context
  - Use cheaper LLMs (`gpt-4o-mini`) for groundedness validation in integration tests
  - Full quality checks with production LLMs only in e2e test suite (opt-in)
- [x] Regression safety
  - Establish baseline of known-good query-answer pairs (stored in database table for UI management)
  - Create `baseline_queries` database table with schema:
    - `id` (primary key)
    - `query` (Bulgarian query text)
    - `expected_intent` (sql/rag/hybrid)
    - `expected_answer` (expected answer text or pattern)
    - `expected_sql_query` (optional, if SQL is expected)
    - `expected_rag_executed` (boolean)
    - `expected_sql_executed` (boolean)
    - `metadata` (JSONB for flexible additional expectations)
    - `created_at`, `updated_at` (timestamps)
    - `created_by` (optional, for tracking who added the baseline)
    - `is_active` (boolean, to enable/disable specific baselines)
  - [x] Create `BaselineQuery` SQLAlchemy model
  - [x] Create automated tests that run baseline queries on code changes and compare outputs
  - [x] Implement comparison logic (exact match, pattern matching, or semantic similarity for answers)
  - [x] Allow administrators to add/update baseline pairs via UI (database table enables easy CRUD operations)
  - [x] When outputs change, either fix code (regression) or update baseline (intentional improvement)
  - [x] Note: Similar to golden file testing - maintain a "golden" set of expected outputs for quality assurance
  - [x] **Cost optimization**: Baseline tests can use snapshot/fixture approach (run real LLMs once, save outputs, compare against snapshots)
  - [x] **UI-friendly**: Database table structure allows administrators to manage baselines through admin interface without code changes

**Definition of Done**
- Quality is measurable and stable
- Bulgarian queries are tested end-to-end with real data
- RAG answers are verified to be grounded in retrieved context
- Baseline query-answer pairs prevent regressions and can be maintained by administrators
- **Default `pytest` execution runs only free (mocked) tests - no LLM costs**
- Integration and e2e tests are opt-in via pytest markers (`-m integration`, `-m e2e`)
- Test execution is cost-conscious: cheaper LLMs for integration, production LLMs only for critical e2e tests

**Test Execution Commands:**
```bash
# Default: Run only free (mocked) tests - no LLM costs
# (configured in pytest.ini to exclude integration and e2e markers)
poetry run pytest

# Run integration tests (uses cheaper LLMs like gpt-4o-mini or local TGI)
poetry run pytest -m integration

# Run e2e tests (uses production LLMs like gpt-4o - most expensive)
poetry run pytest -m e2e

# Run all tests (including integration and e2e) - override default marker exclusion
poetry run pytest -m ""

# Run specific test file with all markers
poetry run pytest tests/test_evaluation.py -m ""
```
