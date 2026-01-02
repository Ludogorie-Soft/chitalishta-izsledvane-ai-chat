# API Usage Guide

This guide explains how to use the Chitalishta RAG System API, with a focus on the chat endpoints.

## API Base URL

The API is accessible at: **https://chat-api.narodnichitalishta.bg**

All endpoints in this guide should be prefixed with this base URL.

## API Documentation

Access the interactive API documentation:
- **Swagger UI**: https://chat-api.narodnichitalishta.bg/docs (requires authentication - see Swagger UI Authentication below)
- **ReDoc**: https://chat-api.narodnichitalishta.bg/redoc (requires authentication - see Swagger UI Authentication below)

## Authentication

### Public API Authentication (API Key)

All Public API endpoints (chat endpoints) require API key authentication. Include your API key in the `X-API-Key` header with every request.

**How to get an API key:**
- Contact your system administrator to obtain an API key
- The API key is configured via the `API_KEY` environment variable on the server

**Using the API key:**
```bash
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "message": "Какво е читалище?",
    "mode": "medium"
  }'
```

**Error responses:**
- **401 Unauthorized**: Missing or invalid API key
  ```json
  {
    "detail": "API key required"
  }
  ```
  or
  ```json
  {
    "detail": "Invalid API key"
  }
  ```

### Swagger UI Authentication

The Swagger UI documentation (`/docs`) is protected with HTTP Basic Authentication. You'll need to enter credentials when accessing the documentation.

**Credentials:**
- Username and password are configured via `SWAGGER_UI_USERNAME` and `SWAGGER_UI_PASSWORD` environment variables
- Contact your system administrator for credentials

**Note:** Swagger UI authentication is separate from API authentication. You still need to provide an API key when making actual API calls through Swagger UI.

## Chat Endpoints

### POST /chat/ - Main Chat Endpoint

Send a message to the RAG system and get a response.

#### First Message (No conversation_id)

For the first message, **omit** `conversation_id` - the system will create one automatically.

**Request:**
```bash
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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
  },
  "structured_output": null
}
```

**Note:** If `output_format` is specified (other than `"text"`), the `structured_output` field will contain formatted data (tables, bullets, statistics).

**Important:** Save the `conversation_id` from the response for follow-up messages.

#### Continue Conversation (With conversation_id)

Use the same `conversation_id` to maintain context across messages.

**Request:**
```bash
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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
| `output_format` | string | No | `"text"` | Output format: `"text"`, `"table"`, `"bullets"`, or `"statistics"` |
| `stream` | boolean | No | `false` | Whether to stream the response (not used in `/chat/`, use `/chat/stream` instead) |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Assistant's answer in Bulgarian (formatted if `output_format` was specified) |
| `conversation_id` | string | Conversation ID (use for follow-up messages) |
| `intent` | string | Detected intent: `"sql"`, `"rag"`, or `"hybrid"` |
| `routing_confidence` | float | Confidence in intent classification (0.0-1.0) |
| `mode` | string | Hallucination mode used |
| `sql_executed` | boolean | Whether SQL was executed |
| `rag_executed` | boolean | Whether RAG was executed |
| `metadata` | object | Additional metadata (SQL queries, routing explanation, etc.) |
| `structured_output` | object | Structured output data (tables, bullets, statistics) if `output_format` was specified, otherwise `null` |

### POST /chat/stream - Streaming Chat Endpoint

Get real-time streaming responses using Server-Sent Events (SSE).

**Request:**
```bash
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/history" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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
curl -X DELETE "https://chat-api.narodnichitalishta.bg/chat/history/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: your_api_key_here"
```

**Response:**
```json
{
  "status": "success",
  "message": "Conversation deleted"
}
```

## Structured Output Formats

The `output_format` parameter allows you to request structured responses:

| Format | Description | Use Case |
|--------|-------------|----------|
| `"text"` | Plain text answer (default) | General queries |
| `"table"` | Formatted table | Statistical data, comparisons |
| `"bullets"` | Bullet points | Lists, features, summaries |
| `"statistics"` | Statistical summary | Numerical data, metrics |

**Example:**
```bash
# Request table format for statistical data
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "message": "Колко читалища има по области?",
    "mode": "low",
    "output_format": "table"
  }'
```

When `output_format` is specified, the response will include:
- `answer`: The formatted answer (table, bullets, etc.)
- `structured_output`: Additional structured data with formatting details

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
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "message": "Колко читалища има в София?",
    "mode": "low"
  }'

# Creative mode for exploratory queries
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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

## Rate Limiting and Abuse Protection

The API implements rate limiting and abuse detection to prevent misuse:

- **Rate Limiting**: Each conversation/session has rate limits to prevent excessive requests
- **Abuse Detection**: The system monitors for suspicious activity patterns

**Rate Limit Exceeded (429):**
- If you exceed the rate limit, you'll receive a `429 Too Many Requests` response
- The response includes a `retry_after` field indicating when you can retry (in seconds)
- Wait for the specified time before making another request

**Abuse Detected (403):**
- If suspicious activity is detected, the request will be blocked with a `403 Forbidden` response
- Contact your system administrator if you believe this is a false positive

**Best Practices:**
- Don't send requests too rapidly
- Use conversation IDs to maintain context instead of creating new conversations for each message
- If you receive a 429 error, implement exponential backoff in your client

## Complete Example: Multi-Turn Conversation

```bash
# 1. First message (no conversation_id)
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{"message": "Здравей", "mode": "medium"}'
# Response includes: "conversation_id": "abc-123"

# 2. Continue conversation (use conversation_id)
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "message": "Колко читалища има?",
    "conversation_id": "abc-123",
    "mode": "medium"
  }'

# 3. Stream response (use same conversation_id)
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "message": "Разкажи повече",
    "conversation_id": "abc-123",
    "mode": "low"
  }'

# 4. Get conversation history
curl -X POST "https://chat-api.narodnichitalishta.bg/chat/history" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
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
   - Select `output_format`: `text`, `table`, `bullets`, or `statistics` (optional)
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

**401 Unauthorized:**
- Missing or invalid API key
- Expired or invalid JWT token (for Admin/Setup APIs)

**403 Forbidden:**
- Insufficient permissions (for Admin/Setup APIs)
- Abuse detected (suspicious activity detected, request blocked)

**404 Not Found:**
- Conversation not found (when accessing history or deleting conversation)

**429 Too Many Requests:**
- Rate limit exceeded for the conversation/session
  ```json
  {
    "error": "rate_limit_exceeded",
    "message": "Превишен е лимитът за заявки за тази сесия. Моля, опитайте отново след 60 секунди.",
    "retry_after": 60,
    "limit_type": "session"
  }
  ```

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

