# Chat Logging to Database

This document explains the chat logging system that stores all POST /chat requests and responses in the PostgreSQL database.

## Overview

All chat requests are automatically logged to the `chat_logs` table with comprehensive information including:
- Request and response data
- LLM operations (model, token usage, latency)
- SQL queries (when executed)
- Cost tracking (total tokens)
- Error information (for failed requests)
- Performance metrics

## Database Schema

The `chat_logs` table includes:

### Core Fields
- `id`: Primary key (BIGSERIAL)
- `request_id`: Unique request ID (UUID string, for correlation with structured logs)
- `conversation_id`: Conversation ID linking messages in same conversation
- `created_at`: Timestamp when record was created
- `request_timestamp`: Timestamp when request was received

### Request Data
- `user_message`: User's question/message (TEXT)
- `hallucination_mode`: Mode used ('low', 'medium', 'high')
- `output_format`: Output format requested ('text', 'table', 'bullets', 'statistics')

### Response Data
- `answer`: Assistant's response (TEXT, nullable for errors)
- `intent`: Detected intent ('sql', 'rag', 'hybrid')
- `routing_confidence`: Confidence score (0.00-1.00)
- `sql_executed`: Boolean flag
- `rag_executed`: Boolean flag
- `sql_query`: SQL query if executed (TEXT)

### Performance & Cost
- `response_time_ms`: Total response time in milliseconds
- `total_input_tokens`: Total input tokens across all LLM calls
- `total_output_tokens`: Total output tokens across all LLM calls
- `total_tokens`: Total tokens used
- `cost_usd`: Calculated cost in USD (based on model pricing and token usage)
- `llm_model`: Primary LLM model used (e.g., 'gpt-4o-mini', 'text-embedding-3-small')
- `llm_operations`: JSONB array of LLM operations with model, tokens, latency

### Additional Data
- `response_metadata`: JSONB with routing_explanation, rag_metadata, etc.
- `structured_output`: JSONB with structured output if requested
- `error_occurred`: Boolean flag
- `error_type`: Error type (e.g., 'ValidationError')
- `error_message`: Error message (TEXT)
- `http_status_code`: HTTP status code (200, 400, 500, etc.)
- `client_ip`: Client IP address
- `user_agent`: User agent string

## Setup

### 1. Create the Table

Run the migration script:

```bash
poetry run python scripts/create_chat_logs_table.py
```

Or use the existing init script (which will create all tables including chat_logs):

```bash
poetry run python scripts/init_db.py
```

### 2. Verify Table Creation

```sql
-- Check table exists
SELECT * FROM chat_logs LIMIT 1;

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'chat_logs';
```

## Usage

### Automatic Logging

Logging happens automatically for all POST /chat requests. No additional code is needed.

### Querying Logs

#### Get all logs for a conversation

```python
from app.db.database import SessionLocal
from app.db.models import ChatLog

db = SessionLocal()
logs = db.query(ChatLog).filter(
    ChatLog.conversation_id == "your-conversation-id"
).order_by(ChatLog.created_at).all()
```

#### Get logs with SQL queries

```python
logs = db.query(ChatLog).filter(
    ChatLog.sql_executed == True
).all()
```

#### Get error logs

```python
errors = db.query(ChatLog).filter(
    ChatLog.error_occurred == True
).all()
```

#### Get logs by date range

```python
from datetime import datetime, timedelta

start_date = datetime.now() - timedelta(days=7)
logs = db.query(ChatLog).filter(
    ChatLog.created_at >= start_date
).all()
```

#### Calculate total token usage

```python
from sqlalchemy import func

total_tokens = db.query(func.sum(ChatLog.total_tokens)).filter(
    ChatLog.total_tokens.isnot(None)
).scalar()
```

#### Get average response time

```python
avg_response_time = db.query(func.avg(ChatLog.response_time_ms)).filter(
    ChatLog.response_time_ms.isnot(None)
).scalar()
```

### LLM Operations Analysis

The `llm_operations` field contains a JSONB array of all LLM calls:

```json
[
  {
    "model": "gpt-4o-mini",
    "input_tokens": 150,
    "output_tokens": 75,
    "total_tokens": 225,
    "latency_ms": 523.45,
    "timestamp": "2025-01-15T10:30:45.123456"
  },
  {
    "model": "gpt-4o-mini",
    "input_tokens": 200,
    "output_tokens": 100,
    "total_tokens": 300,
    "latency_ms": 678.90,
    "timestamp": "2025-01-15T10:30:46.234567"
  }
]
```

Query LLM operations using JSONB:

```sql
-- Find logs with specific model
SELECT * FROM chat_logs
WHERE llm_operations @> '[{"model": "gpt-4o-mini"}]';

-- Query response metadata
SELECT * FROM chat_logs
WHERE response_metadata @> '{"routing_explanation": "SQL intent detected"}';

-- Find logs with high token usage
SELECT * FROM chat_logs
WHERE total_tokens > 1000;
```

## Indexes

The following indexes are created for performance:

- `idx_chat_logs_conversation_id`: For querying by conversation
- `idx_chat_logs_created_at`: For date range queries
- `idx_chat_logs_intent`: For filtering by intent
- `idx_chat_logs_sql_executed`: Partial index for SQL queries
- `idx_chat_logs_error_occurred`: Partial index for errors
- `idx_chat_logs_response_metadata_gin`: GIN index for JSONB response_metadata queries
- `idx_chat_logs_llm_operations_gin`: GIN index for JSONB LLM operations queries

## Admin Page Integration

When building the admin page, you can:

1. **List all chat logs** with pagination
2. **Filter by**:
   - Date range
   - Conversation ID
   - Intent (sql, rag, hybrid)
   - Errors only
   - SQL executed
3. **Sort by**:
   - Date (newest first)
   - Response time
   - Token usage
4. **View details**:
   - Full request/response
   - LLM operations breakdown
   - SQL query (if executed)
   - Error details (if failed)
5. **Export**:
   - CSV export
   - JSON export

## Example Admin Query

```python
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

def get_chat_logs(
    db: Session,
    conversation_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    intent: Optional[str] = None,
    errors_only: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    """Get chat logs with filters."""
    query = db.query(ChatLog)

    if conversation_id:
        query = query.filter(ChatLog.conversation_id == conversation_id)

    if start_date:
        query = query.filter(ChatLog.created_at >= start_date)

    if end_date:
        query = query.filter(ChatLog.created_at <= end_date)

    if intent:
        query = query.filter(ChatLog.intent == intent)

    if errors_only:
        query = query.filter(ChatLog.error_occurred == True)

    return query.order_by(ChatLog.created_at.desc()).limit(limit).offset(offset).all()
```

## Notes

- **Data Retention**: Logs are kept forever (as requested)
- **Volume**: Designed for 10-100 requests per day (no partitioning needed)
- **Privacy**: User messages are stored as-is (no masking)
- **Performance**: Indexes are optimized for common admin queries

## Future Enhancements

Potential additions for the admin page:
- Cost calculation based on token usage and model pricing
- Performance dashboards (average response time, token usage trends)
- Error rate monitoring
- Most common queries/intents analysis
- User message search (full-text search on user_message)

