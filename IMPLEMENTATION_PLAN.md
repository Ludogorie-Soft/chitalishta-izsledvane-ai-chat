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
- Phase: Phase 3 – Vector Store & Embeddings (Chroma)
- Current Step: Phase 3 Complete - Ready for Phase 4
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

# Phase 4 – Query Understanding & Routing

## Step 4.1 – Rule-based intent classification
- [ ] Define Bulgarian keyword rules
- [ ] Compute rule confidence
- [ ] Return intent + confidence

**Definition of Done**
- Simple queries are correctly classified

---

## Step 4.2 – LLM-based intent classification
- [ ] Implement LLM classifier
- [ ] Structured JSON output
- [ ] Confidence score returned

**Definition of Done**
- Ambiguous queries are handled correctly

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
- [ ] Chroma retriever
- [ ] Metadata filtering (support both DB content and analysis document)
- [ ] Retrieval priority logic:
  - Retrieve analysis document only when relevant
  - Do not let analysis document override DB facts
  - Prefer DB content for factual queries
- [ ] Prompt templates (Bulgarian)
- [ ] Context assembly from multiple sources

**Definition of Done**
- RAG answers are grounded in context
- System distinguishes between DB facts and analysis document content
- Retrieval prioritizes DB content for factual queries

---

## Step 5.2 – SQL agent
- [ ] Read-only SQL agent
- [ ] Aggregation support
- [ ] Safety constraints

**Definition of Done**
- Numeric answers are correct and safe

---

## Step 5.3 – Hybrid pipeline
- [ ] SQL → text context
- [ ] RAG enrichment
- [ ] Unified answer format

**Definition of Done**
- Hybrid queries return correct combined answers

---

# Phase 6 – LLM Management

## Step 6.1 – LLM registry
- [ ] OpenAI models
- [ ] Hugging Face models
- [ ] Task-based selection

**Definition of Done**
- Models are swappable at runtime

---

## Step 6.2 – Hallucination control modes
- [ ] Low tolerance mode
- [ ] High tolerance mode
- [ ] Temperature and prompt control

**Definition of Done**
- User can switch answer strictness

---

# Phase 7 – API & UX

## Step 7.1 – Chat endpoint
- [ ] `/chat` endpoint
- [ ] Streaming responses
- [ ] Mode selection

**Definition of Done**
- Chat works end-to-end

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

## Step 10.1 – Logging & metrics
- [ ] Query logs
- [ ] Routing logs
- [ ] Error tracking

**Definition of Done**
- System behavior is observable

---

## Step 10.2 – Evaluation
- [ ] Bulgarian test queries
- [ ] Groundedness checks
- [ ] Regression safety

**Definition of Done**
- Quality is measurable and stable
