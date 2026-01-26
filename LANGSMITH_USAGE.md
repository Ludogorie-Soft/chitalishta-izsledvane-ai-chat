# LangSmith Observability Guide

This project is integrated with [LangSmith](https://smith.langchain.com/) for tracing and debugging RAG operations.

## Configuration

LangSmith tracing is configured via environment variables in `.env`:

```bash
# Enable/Disable Tracing
LANGCHAIN_TRACING_V2=true

# API Key (Get from LangSmith Settings)
LANGCHAIN_API_KEY=lsv2_pt_...

# Endpoint (REQUIRED for EU accounts)
# Default is US: https://api.smith.langchain.com
# For EU use: https://eu.api.smith.langchain.com
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com

# Project Name
LANGCHAIN_PROJECT=chitalishta-rag

# Environment Tag (dev/prod)
LANGCHAIN_ENVIRONMENT=dev
```

## What is Traced?

We selectively trace operations to balance observability with privacy and cost:

| Component | Traced? | Notes |
|-----------|---------|-------|
| **RAG Chain** | ✅ Yes | Full retrieval, context assembly, and generation |
| **Intent Classification** | ✅ Yes | Router logic and LLM classification |
| **Hybrid Synthesis** | ✅ Yes | Final answer generation combining sources |
| **SQL Agent** | ❌ No | **Excluded** to prevent logging SQL queries externally. Use `chat_logs` database table for SQL debugging. |

## How to Use

1.  **Log in** to [LangSmith](https://smith.langchain.com/).
2.  Select the project `chitalishta-rag` (or your configured project name).
3.  **Filter Traces**:
    *   By `request_id`: You can search metadata for specific request IDs from your application logs.
    *   By `environment`: Filter by `dev` or `prod` tags.
4.  **Analyze Runs**:
    *   Click on a run to see the full trace tree.
    *   Inspect "Retriever" runs to see what documents were fetched.
    *   Inspect "LLM" runs to see the exact prompts and completions.

## Troubleshooting

If traces are not appearing:
1.  Check if `LANGCHAIN_TRACING_V2=true` in `.env`.
2.  Verify `LANGCHAIN_API_KEY` is correct.
3.  Ensure the application was restarted after changing `.env`.
4.  Check application logs for "Failed to initialize LangSmith tracer" warnings.
