# Internal API Usage Guide

This document explains how to use the important ingestion, indexing, and vector store management endpoints. The endpoints are ordered as a developer would use them when starting the project for the first time with an empty Chroma database.

## Authentication

### Setup API Authentication (JWT Token)

All Setup API endpoints (ingestion, indexing, vector store management) require JWT token authentication. You must first obtain a JWT token by logging in, then include it in the `Authorization` header with every request.

**Step 1: Login to get JWT token**

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_swagger_ui_username",
    "password": "your_swagger_ui_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Important:**
- Save the `access_token` - it expires in 30 minutes
- Save the `refresh_token` - use it to get a new access token when it expires
- Use the same credentials as Swagger UI (`SWAGGER_UI_USERNAME` and `SWAGGER_UI_PASSWORD`)

**Step 2: Use JWT token in requests**

Include the access token in the `Authorization` header:

```bash
curl -X POST "http://localhost:8000/index/database" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Step 3: Refresh token when expired**

When your access token expires (after 30 minutes), use the refresh token to get a new one:

```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error responses:**
- **401 Unauthorized**: Invalid or expired token
  ```json
  {
    "detail": "Invalid or expired token"
  }
  ```
- **403 Forbidden**: Insufficient permissions (not an administrator)
  ```json
  {
    "detail": "Administrator access required"
  }
  ```

**Note:** All Setup API endpoints require administrator role. Only users with administrator privileges can access these endpoints.

## Workflow Overview

When setting up the project for the first time, follow this sequence:

1. **Setup database** - Create all necessary tables in PostgreSQL
2. **Preview** what will be indexed (optional but recommended)
3. **Index** the data into Chroma
4. **Verify** what was indexed
5. **Manage** the vector store if needed

---

## Step 1: Setup Database

Before indexing data, ensure your PostgreSQL database has all the necessary tables. If you're starting with an empty database, you need to create the schema.

### Initialize Database Schema

**Purpose:** Create all database tables required by the application (Chitalishte, InformationCard, etc.) based on SQLAlchemy models.

**When to run:**
- When setting up a fresh/empty database
- After creating a new database
- If tables are missing

**When to skip:**
- If you're reusing an existing database that already has tables
- If you've already run this step before

### Local Development

If running the application locally (not in Docker):

```bash
poetry run python scripts/init_db.py
```

**Expected output:**
```
Creating database tables...
Database tables created successfully!
```

### Production/Docker

If running in Docker containers, you have two options:

**Option 1: Using the init script (if scripts directory is available)**

```bash
# Execute the init script inside the app container
docker exec chitalishta_ai_chat_api python scripts/init_db.py
```

**Option 2: Direct Python command (recommended if scripts are not in image)**

If the scripts directory is not available in the Docker image, use this direct Python command:

```bash
docker exec chitalishta_ai_chat_api python -c "
import sys
sys.path.insert(0, '/app')
from app.db.database import Base, engine
print('Creating database tables...')
Base.metadata.create_all(bind=engine)
print('Database tables created successfully!')
"
```

**Expected output:**
```
Creating database tables...
Database tables created successfully!
```

**Note:** If you get "No such file or directory" when trying to use the script, use Option 2 instead. This happens when the pre-built Docker image doesn't include the scripts directory.

### Verify Tables Were Created

You can verify the tables were created by connecting to PostgreSQL:

**Local:**
```bash
psql -U your_user -d your_database -c "\dt"
```

**Docker:**
```bash
docker exec chitalishta_db_ai_chat psql -U chitalishtaPotrebitel -d chitalishta_db_prod -c "\dt"
```

**Expected tables:**
- `chitalishte` - Main table for Chitalishte records
- `information_card` - Table for InformationCard records
- Other application tables as defined in the models

### Troubleshooting

**Error: "relation already exists"**
- This means tables already exist - you can skip this step
- The script is idempotent, so running it multiple times is safe

**Error: "database connection failed"**
- Verify `DATABASE_URL` is correctly set in your `.env` file
- Ensure the PostgreSQL container is running: `docker ps`
- Check database credentials match your `.env` configuration

**Error: "permission denied"**
- Ensure the database user has CREATE TABLE permissions
- Verify the user specified in `POSTGRES_USER` has sufficient privileges

**Error: "can't open file '/app/scripts/init_db.py': [Errno 2] No such file or directory"**
- The scripts directory is not included in the Docker image
- Use Option 2 (Direct Python command) from the Production/Docker section above
- This is common with pre-built Docker images that don't include development scripts

### Next Steps

After creating the tables:
1. If you have existing data, you can import it using SQL scripts or direct database operations
2. If starting fresh, proceed to Step 2 (Preview Data) or Step 3 (Index Data)

**Note:** The database tables only need to be created once. After the schema is initialized, you can proceed with indexing operations.

---

## Step 2: Preview Data (Optional)

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
  -H "Authorization: Bearer your_jwt_token_here" \
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
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{"document_name": "Chitalishta_demo_ver2.docx"}'
```

---

## Step 3: Index Data

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
curl -X POST "http://localhost:8000/index/database" \
  -H "Authorization: Bearer your_jwt_token_here"

# Index with filters
curl -X POST "http://localhost:8000/index/database?region=Пловдив&year=2023&limit=100" \
  -H "Authorization: Bearer your_jwt_token_here"
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
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{"document_name": "Chitalishta_demo_ver2.docx"}'
```

**Note:** This endpoint:
- Loads DOCX file from `documents/` directory
- Chunks using hierarchical strategy (by headings, then paragraphs)
- Generates embeddings for each chunk
- Stores in Chroma with `source: "analysis_document"` metadata

---

## Step 4: Verify Indexed Data

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
curl -X GET "http://localhost:8000/index/stats" \
  -H "Authorization: Bearer your_jwt_token_here"
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
curl -X GET "http://localhost:8000/vector-store/status" \
  -H "Authorization: Bearer your_jwt_token_here"
```

**Use Case:** Health check to verify Chroma is operational and see where data is stored.

---

## Step 5: Manage Vector Store (If Needed)

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
curl -X POST "http://localhost:8000/vector-store/clear" \
  -H "Authorization: Bearer your_jwt_token_here"
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
curl -X POST "http://localhost:8000/vector-store/reset" \
  -H "Authorization: Bearer your_jwt_token_here"
```

**Use Case:**
- Complete reset when collection structure needs to be recreated
- More aggressive than `clear` - deletes and recreates the collection
- Use when you want a completely fresh start

**Note:** `reset` is more aggressive than `clear` - it deletes and recreates the collection entirely.

---

## Typical First-Time Setup Sequence

When starting with an empty database and Chroma:

1. **Setup database:**
   ```bash
   # Local: poetry run python scripts/init_db.py
   # Docker (Option 1): docker exec chitalishta_ai_chat_api python scripts/init_db.py
   # Docker (Option 2 - if scripts not available):
   docker exec chitalishta_ai_chat_api python -c "import sys; sys.path.insert(0, '/app'); from app.db.database import Base, engine; Base.metadata.create_all(bind=engine); print('Database tables created successfully!')"
   ```

2. **Login to get JWT token:**
   ```bash
   POST /auth/login                        # Get access and refresh tokens
   ```

3. **Preview (optional):**
   ```bash
   POST /ingest/database?limit=5          # Preview database records (requires JWT)
   POST /ingest/analysis-document         # Preview analysis document chunks (requires JWT)
   ```

4. **Index:**
   ```bash
   POST /index/database                    # Index all database records (requires JWT)
   POST /index/analysis-document           # Index analysis document (requires JWT)
   ```

5. **Verify:**
   ```bash
   GET /index/stats                        # Check what was indexed (requires JWT)
   GET /vector-store/status                # Verify Chroma is working (requires JWT)
   ```

6. **If needed, reset and re-index:**
   ```bash
   POST /vector-store/clear                # Clear all documents (requires JWT)
   # Then re-run indexing endpoints
   ```

**Note:** All Setup API endpoints require JWT authentication. Include `Authorization: Bearer <token>` header in all requests.

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

