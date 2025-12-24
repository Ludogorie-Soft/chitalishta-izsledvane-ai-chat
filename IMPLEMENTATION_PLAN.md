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
- Phase: Phase 5 – RAG & SQL Pipelines
- Current Step: Phase 5.2 Complete - Ready for Phase 5.3 (Hybrid Pipeline)
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
- [x] `POST /ingest/preview`
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
- [ ] Combine rule + LLM signals
- [ ] Final intent decision
- [ ] Safe fallback to hybrid

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
- [ ] Create LangChain chain for hybrid queries (SequentialChain or custom chain)
- [ ] SQL → text context conversion (format SQL results as narrative)
- [ ] RAG enrichment using retrieval chain
- [ ] Combine SQL and RAG results using LangChain's chain composition
- [ ] Unified answer format (Bulgarian)
- [ ] Routing logic to determine when to use SQL vs RAG vs hybrid

**Definition of Done**
- Hybrid queries return correct combined answers
- LangChain orchestrates SQL and RAG pipeline execution
- Results are properly formatted and combined

---

# Phase 6 – LLM Management

## Step 6.1 – LLM registry
- [ ] Use LangChain's LLM abstraction (ChatOpenAI, HuggingFacePipeline, etc.)
- [ ] Create LLM factory/registry using LangChain's model abstractions
- [ ] Support OpenAI models (via langchain-openai)
- [ ] Support Hugging Face models (via langchain-community)
- [ ] Task-based selection (different models for classification vs generation)
- [ ] Configuration via environment variables

**Definition of Done**
- Models are swappable at runtime via LangChain abstraction
- Multiple LLM providers supported
- Task-specific model selection works

---

## Step 6.2 – Hallucination control modes
- [ ] Implement mode-based LLM configuration (via LangChain LLM parameters)
- [ ] Low tolerance mode (low temperature, strict prompts, citation requirements)
- [ ] High tolerance mode (higher temperature, more creative prompts)
- [ ] Temperature and prompt control via LangChain chain configuration
- [ ] Prompt templates that enforce grounding in retrieved context
- [ ] Mode selection in API requests

**Definition of Done**
- User can switch answer strictness
- Different modes use appropriate temperature and prompt strategies
- LangChain chains respect mode configuration

---

# Phase 7 – API & UX

## Step 7.1 – Chat endpoint
- [ ] `/chat` endpoint (FastAPI route)
- [ ] Implement streaming using LangChain's streaming support (streaming=True)
- [ ] Chat history management (optional use of LangChain memory OR custom conversation state)
- [ ] Mode selection (low/high tolerance)
- [ ] Integration with RAG/SQL/Hybrid chains
- [ ] Error handling and timeout management

**Definition of Done**
- Chat works end-to-end
- Streaming responses work correctly
- Chat history is maintained across conversation (via LangChain memory or custom state)
- Mode selection affects response generation
- Memory implementation is flexible and not locked into LangChain abstractions

---

## Step 7.2 – Structured outputs
- [ ] Tables
- [ ] Bullet summaries
- [ ] Statistics

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
- [ ] Dockerfile
- [ ] Environment config
- [ ] Local build

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

# Phase 10 – Quality & Observability

## Step 10.1 – Structured logging foundation
- [ ] Install structured logging library (`structlog` or `loguru`)
- [ ] Configure JSON-formatted logs with timestamps
- [ ] Set up log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Create log rotation strategy (file size/time-based)
- [ ] Add request ID generation (UUID) for trace correlation
- [ ] Implement FastAPI middleware for request/response logging
- [ ] Log all API endpoints (query, routing, errors)

**Definition of Done**
- All application events are logged in structured JSON format
- Request tracing works end-to-end with trace IDs
- Logs are searchable and parseable

---

## Step 10.2 – LangChain observability (callbacks)
- [ ] Create custom LangChain callback handler (`LocalTraceCallbackHandler`)
- [ ] Implement callback methods:
  - `on_llm_start` / `on_llm_end` (log LLM calls, token usage, latency)
  - `on_retriever_start` / `on_retriever_end` (log retrieval queries and results)
  - `on_chain_start` / `on_chain_end` (log chain execution flow)
  - `on_chain_error` (log chain failures with context)
- [ ] Store trace data (inputs, outputs, intermediate steps) in structured logs
- [ ] Include trace IDs in all callback logs for correlation
- [ ] Log metadata (model used, retrieval count, document sources)
- [ ] Integrate callbacks into all LangChain chains (RAG, SQL agent, hybrid)

**Definition of Done**
- All LangChain operations are traceable via callbacks
- Full execution flow is logged (retrieval → LLM → response)
- Token usage and latency are captured for each operation
- Traces can be correlated with API requests via trace IDs

---

## Step 10.3 – Performance monitoring
- [ ] Install metrics library (`prometheus-client`)
- [ ] Define key metrics:
  - Request counters (total queries, by endpoint, by status)
  - Latency histograms (RAG queries, SQL queries, LLM calls, retrieval)
  - Token usage counters (input tokens, output tokens, by model)
  - Error rates (by error type, by endpoint)
- [ ] Create timing decorators for critical operations
- [ ] Expose Prometheus metrics endpoint (`/metrics`)
- [ ] Track system metrics (CPU, memory, database connection pool)
- [ ] Log performance metrics to structured logs

**Definition of Done**
- Performance metrics are collected and exposed
- Latency tracking works for all critical paths
- System health metrics are monitored
- Metrics endpoint is accessible for scraping

---

## Step 10.4 – Cost tracking
- [ ] Create cost tracking service (`CostTracker`)
- [ ] Define pricing models for all LLM providers:
  - OpenAI models (GPT-4, GPT-3.5-turbo, embeddings)
  - Hugging Face models (if using API)
- [ ] Track costs per LLM call:
  - Input tokens × input price
  - Output tokens × output price
  - Embedding tokens × embedding price
- [ ] Store cost data (PostgreSQL table or structured logs)
- [ ] Calculate costs per:
  - Request/query
  - User (if applicable)
  - Endpoint
  - Model
- [ ] Generate cost summaries (daily, monthly totals)
- [ ] Log cost information in structured logs

**Definition of Done**
- All LLM API costs are tracked and calculated
- Cost data is stored and queryable
- Cost summaries can be generated
- Cost information is included in request logs

---

## Step 10.5 – Production monitoring setup
- [ ] Set up log aggregation (optional: ELK stack or simple log viewer)
- [ ] Configure Grafana dashboards (optional: Docker setup):
  - Request rate and latency graphs
  - Error rate trends
  - Token usage over time
  - Cost trends
  - System resource usage
- [ ] Create alerting rules (optional):
  - High error rate alerts
  - High latency alerts
  - Cost threshold alerts
- [ ] Set up log retention policy
- [ ] Document observability setup and usage

**Definition of Done**
- Production monitoring is operational
- Dashboards provide visibility into system health
- Alerts notify on critical issues (if configured)
- Observability tools are documented

---

## Step 10.6 – Evaluation
- [ ] Bulgarian test queries
- [ ] Groundedness checks
- [ ] Regression safety

**Definition of Done**
- Quality is measurable and stable
