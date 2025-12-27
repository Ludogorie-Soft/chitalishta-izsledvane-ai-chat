# Internal API Usage Guide

This document explains how to use the important ingestion, indexing, and vector store management endpoints. The endpoints are ordered as a developer would use them when starting the project for the first time with an empty Chroma database.

## Workflow Overview

When setting up the project for the first time, follow this sequence:

1. **Preview** what will be indexed (optional but recommended)
2. **Index** the data into Chroma
3. **Verify** what was indexed
4. **Manage** the vector store if needed

---

## Step 1: Preview Data (Optional)

Before indexing, you can preview what will be created. This helps verify the data and chunking strategy.

### POST /ingest/database

Preview database records that would be converted into documents for indexing.

**Purpose:** See what documents will be assembled from PostgreSQL database records (Chitalishte + InformationCard data) before indexing.

**Request:**
```bash
POST /ingest/database
Content-Type: application/json

{
  "region": "Пловдив",      # Optional: Filter by region
  "town": null,              # Optional: Filter by town
  "status": "Действащо",    # Optional: Filter by status
  "year": 2023,             # Optional: Filter by year (null = all years)
  "limit": 10               # Optional: Max documents to preview (default: 10, max: 100)
}
```

**Response:**
- Returns preview of documents with content, metadata, and size information
- Does NOT store anything in Chroma
- Use this to verify document assembly before indexing

**Example:**
```bash
curl -X POST "http://localhost:8000/ingest/database" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

### POST /ingest/analysis-document

Preview chunks that would be created from a DOCX analysis document.

**Purpose:** See how the analysis document will be chunked before indexing.

**Request:**
```bash
POST /ingest/analysis-document
Content-Type: application/json

{
  "document_name": "Chitalishta_demo_ver2.docx"
}
```

**Response:**
- Returns preview of chunks with content, metadata, and size information
- Does NOT store anything in Chroma
- Shows how the document will be split into semantic chunks

**Example:**
```bash
curl -X POST "http://localhost:8000/ingest/analysis-document" \
  -H "Content-Type: application/json" \
  -d '{"document_name": "Chitalishta_demo_ver2.docx"}'
```

---

## Step 2: Index Data

After previewing (or skipping preview), index the data into Chroma vector store.

### POST /index/database

Index database records from PostgreSQL into the vector store.

**Purpose:** Extract database records (Chitalishte + InformationCard data), convert them to semantic documents, embed them, and store in Chroma for RAG retrieval.

**Request:**
```bash
POST /index/database?region=Пловдив&year=2023&limit=100
```

**Query Parameters:**
- `region`: Optional filter by region (case-sensitive)
- `town`: Optional filter by town (case-sensitive)
- `status`: Optional filter by status (case-sensitive)
- `year`: Optional filter by year
- `limit`: Optional limit on number of documents to index
- `offset`: Number of documents to skip (default: 0)

**Response:**
```json
{
  "status": "success",
  "message": "Indexed 50 documents successfully.",
  "indexed": 50,
  "skipped": 0,
  "errors": 0,
  "total": 50
}
```

**Example:**
```bash
# Index all documents
curl -X POST "http://localhost:8000/index/database"

# Index with filters
curl -X POST "http://localhost:8000/index/database?region=Пловдив&year=2023&limit=100"
```

**Note:** This endpoint:
- Extracts structured data from PostgreSQL (Chitalishte + InformationCard records)
- Converts database records into semantic documents (one per Chitalishte per year)
- Generates embeddings for each document
- Stores in Chroma with `source: "database"` metadata

### POST /index/analysis-document

Index an analysis document (DOCX file) into the vector store.

**Purpose:** Process a DOCX file, chunk it into semantic chunks, embed the chunks, and store in Chroma.

**Request:**
```bash
POST /index/analysis-document
Content-Type: application/json

{
  "document_name": "Chitalishta_demo_ver2.docx"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Indexed 25 chunks from analysis document successfully.",
  "indexed": 25,
  "skipped": 0,
  "errors": 0,
  "total": 25
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/index/analysis-document" \
  -H "Content-Type: application/json" \
  -d '{"document_name": "Chitalishta_demo_ver2.docx"}'
```

**Note:** This endpoint:
- Loads DOCX file from `documents/` directory
- Chunks using hierarchical strategy (by headings, then paragraphs)
- Generates embeddings for each chunk
- Stores in Chroma with `source: "analysis_document"` metadata

---

## Step 3: Verify Indexed Data

After indexing, verify what was stored in Chroma.

### GET /index/stats

Get detailed statistics about indexed documents.

**Purpose:** See total count and breakdown by source (database vs analysis document).

**Request:**
```bash
GET /index/stats
```

**Response:**
```json
{
  "status": "success",
  "total_documents": 75,
  "source_distribution": {
    "database": 50,
    "analysis_document": 25
  }
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/index/stats"
```

**Use Case:** Verify indexing was successful and see the distribution of documents by source.

### GET /vector-store/status

Get vector store infrastructure status and health information.

**Purpose:** Check if Chroma is working, see collection name, document count, and storage path.

**Request:**
```bash
GET /vector-store/status
```

**Response:**
```json
{
  "status": "ok",
  "collection_name": "chitalishta_documents",
  "document_count": 75,
  "persist_directory": "/path/to/chroma_db",
  "collection_exists": true
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/vector-store/status"
```

**Use Case:** Health check to verify Chroma is operational and see where data is stored.

---

## Step 4: Manage Vector Store (If Needed)

If you need to clear or reset the vector store, use these endpoints.

### POST /vector-store/clear

Clear all documents from the vector store collection.

**Purpose:** Delete all indexed documents but keep the collection structure.

**Request:**
```bash
POST /vector-store/clear
```

**Response:**
```json
{
  "status": "success",
  "message": "Collection cleared successfully",
  "document_count": 0
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/vector-store/clear"
```

**Use Case:**
- Clear all documents before re-indexing
- Remove all data while keeping the collection structure
- Start fresh without recreating the collection

**Note:** After clearing, you can re-index documents. The collection structure remains intact.

### POST /vector-store/reset

Reset the entire vector store collection.

**Purpose:** Aggressively reset by deleting and recreating the collection (clean state).

**Request:**
```bash
POST /vector-store/reset
```

**Response:**
```json
{
  "status": "success",
  "message": "Collection reset successfully",
  "document_count": 0
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/vector-store/reset"
```

**Use Case:**
- Complete reset when collection structure needs to be recreated
- More aggressive than `clear` - deletes and recreates the collection
- Use when you want a completely fresh start

**Note:** `reset` is more aggressive than `clear` - it deletes and recreates the collection entirely.

---

## Typical First-Time Setup Sequence

When starting with an empty Chroma database:

1. **Preview (optional):**
   ```bash
   POST /ingest/database?limit=5          # Preview database records
   POST /ingest/analysis-document         # Preview analysis document chunks
   ```

2. **Index:**
   ```bash
   POST /index/database                    # Index all database records
   POST /index/analysis-document           # Index analysis document
   ```

3. **Verify:**
   ```bash
   GET /index/stats                        # Check what was indexed
   GET /vector-store/status                # Verify Chroma is working
   ```

4. **If needed, reset and re-index:**
   ```bash
   POST /vector-store/clear                # Clear all documents
   # Then re-run indexing endpoints
   ```

---

## Key Differences

### Preview vs Index
- **Preview endpoints** (`/ingest/*`): Show what will be created, no storage
- **Index endpoints** (`/index/*`): Actually embed and store in Chroma

### Database Records vs Analysis Document
- **Database** (`/index/database`): Converts PostgreSQL records (structured data) into semantic documents
- **Analysis Document** (`/index/analysis-document`): Chunks a DOCX file (unstructured document) into semantic chunks

**Note:** Both sources become "documents" in the vector store terminology, but they originate from different sources:
- Database records → transformed into documents (one per Chitalishte per year)
- DOCX file → chunked into documents (multiple chunks per file)

### Stats vs Status
- **Stats** (`/index/stats`): Content analytics (what's indexed, source breakdown)
- **Status** (`/vector-store/status`): Infrastructure health (is Chroma working, storage path)

### Clear vs Reset
- **Clear** (`/vector-store/clear`): Deletes documents, keeps collection structure
- **Reset** (`/vector-store/reset`): Deletes and recreates collection (more aggressive)

---

## Notes

- All endpoints return JSON responses
- Preview endpoints are optional but recommended for verification
- Indexing can be done incrementally (use filters and limits)
- After indexing, documents are immediately available for RAG queries
- Use `/index/stats` to verify indexing was successful
- Use `/vector-store/status` for health checks and troubleshooting

