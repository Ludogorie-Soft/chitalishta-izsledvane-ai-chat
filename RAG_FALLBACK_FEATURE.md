# RAG Fallback Feature

## Overview

The RAG system now includes an intelligent fallback mechanism that automatically retries with a more powerful LLM when the initial response indicates "no information" was found. This keeps costs low for basic questions while providing better answers for complex queries.

## How It Works

1. **Initial Query**: The system first tries with the default/cheaper LLM (e.g., `gpt-4o-mini`)
2. **Detection**: If the answer contains "Нямам информация за тази заявка" or similar "no information" patterns, the system detects this
3. **Fallback Retry**: Automatically retries with a more powerful LLM (e.g., `gpt-4o`)
4. **Cost Optimization**: Only uses the expensive model when necessary

## Configuration

Add these settings to your `.env` file:

```bash
# Enable/disable fallback feature (default: true)
RAG_ENABLE_FALLBACK=true

# Fallback LLM provider (empty = use same as LLM_PROVIDER)
LLM_PROVIDER_FALLBACK=openai

# Fallback model for OpenAI (more powerful than default)
OPENAI_CHAT_MODEL_FALLBACK=gpt-4o
```

### Example Configuration

**Cost-Optimized Setup:**
```bash
# Default: cheap model for most queries
LLM_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-4o-mini

# Fallback: powerful model only when needed
LLM_PROVIDER_FALLBACK=openai
OPENAI_CHAT_MODEL_FALLBACK=gpt-4o
RAG_ENABLE_FALLBACK=true
```

**High-Quality Setup:**
```bash
# Default: already using powerful model
LLM_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-4o

# Fallback: even more powerful (optional)
LLM_PROVIDER_FALLBACK=openai
OPENAI_CHAT_MODEL_FALLBACK=gpt-4-turbo
RAG_ENABLE_FALLBACK=true
```

## When Fallback is Used

- ✅ **RAG-only queries**: Fallback is enabled by default
- ❌ **Hybrid queries**: Fallback is disabled (SQL might provide answers)
- ❌ **SQL queries**: Not applicable (no RAG involved)

## Detection Patterns

The system detects "no information" responses by checking for these Bulgarian phrases:
- "нямам информация"
- "няма информация"
- "не мога да намеря"
- "не мога да отговоря"
- "не знам"
- "няма данни"
- "липсва информация"

## Behavior

1. If initial answer is "no information" → retry with fallback LLM
2. If fallback answer is also "no information" → return original answer
3. If fallback answer is different → use fallback answer
4. If fallback LLM fails → return original answer (graceful degradation)

## Logging

The system logs when fallback is triggered:
```
INFO: Initial answer indicates no information. Retrying with fallback LLM for question: ...
INFO: Fallback LLM provided a better answer
```

Or if fallback also fails:
```
INFO: Fallback LLM also returned no information
```

## Metadata

The response includes metadata about fallback usage:
```json
{
  "answer": "...",
  "metadata": {
    "used_fallback_llm": true,
    ...
  }
}
```

## Cost Implications

- **Most queries**: Use cheap model (e.g., `gpt-4o-mini`) - low cost
- **Complex queries**: Use powerful model (e.g., `gpt-4o`) - higher cost, but only when needed
- **Overall**: Lower average cost than always using the powerful model

## Disabling Fallback

To disable the feature entirely:
```bash
RAG_ENABLE_FALLBACK=false
```

## Troubleshooting

If fallback doesn't work:

1. **Check configuration**: Verify `RAG_ENABLE_FALLBACK=true` in `.env`
2. **Check fallback LLM**: Ensure `LLM_PROVIDER_FALLBACK` and model are correctly configured
3. **Check logs**: Look for warnings about fallback LLM initialization
4. **Verify answer pattern**: The system must detect "no information" in the answer

## Example Flow

**Query**: "Може ли читалищата да имат собствени приходи?"

1. Initial attempt with `gpt-4o-mini`:
   - Answer: "Нямам информация за тази заявка."
   - System detects "no information"

2. Fallback retry with `gpt-4o`:
   - Answer: "Да, читалищата могат да имат собствени приходи. Според предоставения контекст..."
   - System uses this better answer

3. Response includes:
   ```json
   {
     "answer": "Да, читалищата могат да имат собствени приходи...",
     "metadata": {
       "used_fallback_llm": true
     }
   }
   ```

