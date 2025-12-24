# API Usage Guide

This guide explains how to use the Chitalishta RAG System API, with a focus on the chat endpoints.

## API Documentation

Access the interactive API documentation:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

## Chat Endpoints

### POST /chat/ - Main Chat Endpoint

Send a message to the RAG system and get a response.

#### First Message (No conversation_id)

For the first message, **omit** `conversation_id` - the system will create one automatically.

**Request:**
```bash
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Какво е читалище?",
    "mode": "medium"
  }'
```

**Response:**
```json
{
  "answer": "Читалището е културна институция...",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "rag",
  "routing_confidence": 0.9,
  "mode": "medium",
  "sql_executed": false,
  "rag_executed": true,
  "metadata": {
    "routing_explanation": "RAG intent detected",
    "sql_query": null,
    "rag_metadata": {}
  }
}
```

**Important:** Save the `conversation_id` from the response for follow-up messages.

#### Continue Conversation (With conversation_id)

Use the same `conversation_id` to maintain context across messages.

**Request:**
```bash
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Колко читалища има в Пловдив?",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "medium"
  }'
```

The system will include previous messages as context when generating the response.

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `message` | string | Yes | - | User's message/question in Bulgarian |
| `conversation_id` | string | No | Auto-created | Conversation ID for maintaining chat history |
| `mode` | string | No | `"medium"` | Hallucination control mode: `"low"`, `"medium"`, or `"high"` |
| `stream` | boolean | No | `false` | Whether to stream the response (not used in `/chat/`, use `/chat/stream` instead) |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Assistant's answer in Bulgarian |
| `conversation_id` | string | Conversation ID (use for follow-up messages) |
| `intent` | string | Detected intent: `"sql"`, `"rag"`, or `"hybrid"` |
| `routing_confidence` | float | Confidence in intent classification (0.0-1.0) |
| `mode` | string | Hallucination mode used |
| `sql_executed` | boolean | Whether SQL was executed |
| `rag_executed` | boolean | Whether RAG was executed |
| `metadata` | object | Additional metadata (SQL queries, routing explanation, etc.) |

### POST /chat/stream - Streaming Chat Endpoint

Get real-time streaming responses using Server-Sent Events (SSE).

**Request:**
```bash
curl -X POST "https://your-api-domain.com/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Разкажи за читалищата в България",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "medium"
  }'
```

**Response (SSE stream):**
```
data: Текст
data: отговора
data: се
data: изпраща
data: на части
data: {"conversation_id": "...", "intent": "rag", ...}
data: [DONE]
```

**Note:** Use the same `conversation_id` to maintain context, just like with `/chat/`.

### POST /chat/history - Get Chat History

Retrieve all messages from a conversation.

**Request:**
```bash
curl -X POST "https://your-api-domain.com/chat/history" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "Какво е читалище?"
    },
    {
      "role": "assistant",
      "content": "Читалището е културна институция..."
    },
    {
      "role": "user",
      "content": "Колко читалища има?"
    },
    {
      "role": "assistant",
      "content": "Има много читалища..."
    }
  ]
}
```

### DELETE /chat/history/{conversation_id} - Delete Conversation

Delete a conversation and all its messages.

**Request:**
```bash
curl -X DELETE "https://your-api-domain.com/chat/history/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "status": "success",
  "message": "Conversation deleted"
}
```

## Hallucination Control Modes

The `mode` parameter controls how strict the AI is with facts:

| Mode | Temperature | Use Case |
|------|------------|----------|
| `"low"` | 0.0 | Strict, factual answers. Only uses provided context. |
| `"medium"` | 0.3 | Balanced (default). Uses context with some flexibility. |
| `"high"` | 0.7 | Creative answers. More flexible with context. |

**Example:**
```bash
# Strict mode for factual queries
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Колко читалища има в София?",
    "mode": "low"
  }'

# Creative mode for exploratory queries
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Разкажи интересна история за читалищата",
    "mode": "high"
  }'
```

## Conversation ID Rules

- **First message**: Omit `conversation_id` → System creates one automatically
- **Follow-up messages**: Use the `conversation_id` from previous response
- **New conversation**: Omit `conversation_id` again → Creates a new conversation
- **Invalid ID**: If you provide a non-existent ID, system creates a new conversation

## Complete Example: Multi-Turn Conversation

```bash
# 1. First message (no conversation_id)
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Здравей", "mode": "medium"}'
# Response includes: "conversation_id": "abc-123"

# 2. Continue conversation (use conversation_id)
curl -X POST "https://your-api-domain.com/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Колко читалища има?",
    "conversation_id": "abc-123",
    "mode": "medium"
  }'

# 3. Stream response (use same conversation_id)
curl -X POST "https://your-api-domain.com/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Разкажи повече",
    "conversation_id": "abc-123",
    "mode": "low"
  }'

# 4. Get conversation history
curl -X POST "https://your-api-domain.com/chat/history" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc-123"}'
```

## Using FastAPI Interactive Docs

The easiest way to test the API is using the built-in Swagger UI:

1. **Open in browser:**
   Navigate to `/docs` on your API server

2. **Find the `/chat/` endpoint** and click "Try it out"

3. **Enter your message:**
   - Leave `conversation_id` empty for first message
   - Select `mode`: `low`, `medium`, or `high`
   - Click "Execute"

4. **Copy the `conversation_id`** from the response for follow-up messages

## Query Types

The system automatically routes queries to the appropriate pipeline:

### SQL Queries (Numeric/Statistical)
- "Колко читалища има?"
- "Средният брой членове"
- "Топ 5 области по брой читалища"

### RAG Queries (Descriptive/Explanatory)
- "Какво е читалище?"
- "Разкажи за историята на читалищата"
- "Какво правят читалищата?"

### Hybrid Queries (Both)
- "Колко читалища има и разкажи за тях?"
- "Статистика за читалищата в Пловдив и обясни какво правят"

## Error Handling

### Common Errors

**400 Bad Request:**
- Invalid request format
- Missing required fields

**500 Internal Server Error:**
- LLM service unavailable
- Database connection issues
- Model loading errors

**Example Error Response:**
```json
{
  "detail": "Error processing request: TGI service is not available..."
}
```

## Other Endpoints

### Health Check
```bash
GET /health
```

### Database Ping
```bash
GET /db/ping
```

### Vector Store Status
```bash
GET /vector-store/status
```

For more information about other endpoints, see the Swagger UI documentation at `/docs`

