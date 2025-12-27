# Evaluation & Quality Assurance

This document describes the evaluation and quality assurance infrastructure for the RAG system.

## Overview

The evaluation system provides:
- **Bulgarian test queries**: Integration/e2e tests with real Bulgarian queries
- **Groundedness checks**: Validation that RAG answers are supported by retrieved context
- **Regression safety**: Baseline query-answer pairs to prevent quality regressions

## Cost-Conscious Testing Strategy

Tests are organized into tiers to minimize LLM costs:

### Default Tests (Free)
- Run with: `poetry run pytest`
- Uses mocked LLMs (no cost)
- Fast execution
- Excludes integration and e2e tests by default

### Integration Tests (Lower Cost)
- Run with: `poetry run pytest -m integration`
- Uses cheaper LLMs (`gpt-4o-mini` or local TGI)
- Tests end-to-end flows with real data
- Marked with `@pytest.mark.integration`

### E2E Tests (Higher Cost)
- Run with: `poetry run pytest -m e2e`
- Uses production LLMs (`gpt-4o`)
- Full quality validation
- Marked with `@pytest.mark.e2e`

### Running All Tests
```bash
# Run all tests (including integration and e2e)
poetry run pytest -m ""
```

## Baseline Queries

Baseline queries are stored in the `baseline_queries` database table and can be managed via UI.

### Table Schema

```sql
CREATE TABLE baseline_queries (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,  -- Bulgarian query text
    expected_intent VARCHAR(20) NOT NULL,  -- sql/rag/hybrid
    expected_answer TEXT,  -- Expected answer text or pattern
    expected_sql_query TEXT,  -- Optional, if SQL is expected
    expected_rag_executed BOOLEAN NOT NULL DEFAULT FALSE,
    expected_sql_executed BOOLEAN NOT NULL DEFAULT FALSE,
    baseline_metadata JSONB,  -- Flexible additional expectations (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),  -- Optional, for tracking
    is_active BOOLEAN NOT NULL DEFAULT TRUE  -- Enable/disable baselines
);
```

### Creating Baselines

Baselines can be added via SQL or through the admin UI:

```sql
INSERT INTO baseline_queries (
    query,
    expected_intent,
    expected_answer,
    expected_sql_executed,
    expected_rag_executed,
    created_by
) VALUES (
    'Колко читалища има в Пловдив?',
    'sql',
    'В Пловдив има',
    TRUE,
    FALSE,
    'admin'
);
```

### Comparison Modes

The `baseline_metadata` JSONB field can specify comparison modes:

```json
{
  "comparison_mode": "contains",  // or "exact", "pattern"
  "semantic_similarity_threshold": 0.8
}
```

- **exact**: Exact text match
- **contains**: Expected text must be contained in answer
- **pattern**: Regex pattern matching

## Groundedness Checks

The `GroundednessChecker` validates that RAG answers are supported by retrieved context:

### Features

1. **Keyword Overlap**: Checks if significant words from the answer appear in context
2. **Missing Information Detection**: Identifies information in answer not present in context
3. **Hallucination Phrase Detection**: Detects common "no information" phrases

### Usage

```python
from app.services.evaluation import GroundednessChecker

checker = GroundednessChecker()
is_grounded, confidence, missing_info = checker.check_groundedness(
    answer="Читалището е културна институция.",
    retrieved_documents=[{"page_content": "..."}],
    threshold=0.7
)
```

## Evaluation Service

The `EvaluationService` provides comprehensive evaluation against baselines:

### Features

- Intent comparison
- Execution flag validation
- SQL query pattern matching
- Answer comparison (exact/contains/pattern)
- Groundedness checks for RAG answers

### Usage

```python
from app.services.evaluation import EvaluationService
from sqlalchemy.orm import Session

evaluation_service = EvaluationService(db_session)
result = evaluation_service.evaluate_against_baseline(
    baseline=baseline_query,
    actual_result={
        "answer": "...",
        "intent": "sql",
        "sql_executed": True,
        "rag_executed": False,
        "sql_query": "SELECT ..."
    }
)
```

## Running Evaluation Tests

### Setup

1. Create baseline_queries table:
```bash
poetry run python scripts/create_baseline_queries_table.py
```

2. Add baseline queries (via SQL or UI)

3. Configure environment for integration/e2e tests:
```bash
export USE_REAL_LLM=true
export TEST_LLM_MODEL=gpt-4o-mini  # or gpt-4o for e2e
```

### Running Tests

```bash
# Free tests only (default)
poetry run pytest

# Integration tests (cheaper LLMs)
poetry run pytest -m integration

# E2E tests (production LLMs)
poetry run pytest -m e2e

# All tests
poetry run pytest -m ""
```

## Test Files

- `tests/test_evaluation.py`: Integration/e2e tests with Bulgarian queries
  - `TestBulgarianQueriesIntegration`: Integration tests with real queries
  - `TestGroundednessChecks`: Groundedness validation tests
  - `TestBaselineRegression`: Regression tests against baselines
  - `TestE2EQuality`: End-to-end quality tests

## Best Practices

1. **Start with mocked tests**: Always run default tests first (no cost)
2. **Use integration tests for PRs**: Run integration tests before merging
3. **Use e2e tests sparingly**: Only for critical quality checks or before releases
4. **Maintain baselines**: Update baselines when behavior intentionally changes
5. **Monitor costs**: Track LLM usage in integration/e2e test runs

## Future Enhancements

- Admin UI for managing baseline queries
- Automated baseline generation from successful queries
- Semantic similarity scoring for answer comparison
- Cost tracking per test run
- CI/CD integration with conditional test execution

