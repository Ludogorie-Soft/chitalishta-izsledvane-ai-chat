# Reply Certainty Feature

## Overview

The **Reply Certainty** feature provides a confidence score (0.0-1.0) indicating how certain the system is that the answer provided is correct. This is separate from **Routing Certainty**, which indicates confidence in choosing the right pipeline (SQL vs RAG vs Hybrid).

## Key Concepts

### Two Types of Certainty

1. **Routing Certainty** (`routing_confidence`)
   - How confident we are that SQL/RAG/Hybrid was the right choice
   - Calculated by intent classification (rule-based + LLM)
   - Range: 0.0 - 1.0

2. **Reply Certainty** (`reply_certainty`) - **NEW**
   - How confident we are that the answer itself is correct
   - Calculated based on execution success, data quality, groundedness
   - Range: 0.0 - 1.0

### Example

```
Query: "Колко читалища има в България?"
Answer: "В България има 3597 читалища..."

Routing Confidence: 50% (low keyword matches, but intent was correct)
Reply Certainty: 95% (SQL executed successfully, simple COUNT query, reasonable result)
```

## Implementation Details

### 1. SQL Reply Certainty

Factors considered:
- **Execution success** (40 points): Did the SQL query execute successfully?
- **Query complexity** (40 points): Simple COUNT vs complex JOINs
- **Result validation** (15 points): Are results reasonable? (not empty, not too large)
- **Clean execution** (5 points): No warnings or sanitization issues

**Score Breakdown:**
- Simple aggregations (COUNT, SUM): Up to 95%
- Single table queries: Up to 90%
- JOINs without subqueries: Up to 85%
- Complex queries (CTEs, subqueries): Up to 75%
- Failed execution: 5%

### 2. RAG Reply Certainty

Factors considered:
- **Groundedness score** (50 points): How much of the answer is supported by retrieved documents?
- **Document count** (20 points): More documents = more context
- **Hallucination detection** (20 points): No phrases like "нямам информация"
- **Document relevance** (10 points): Average relevance score of retrieved documents

**Score Breakdown:**
- High groundedness (>0.8) + 5+ docs + no hallucinations: 85-90%
- Medium groundedness (0.5-0.8): 60-75%
- Low groundedness (<0.5): 30-50%
- Hallucination phrases detected: 20%

### 3. Hybrid Reply Certainty

For hybrid queries (SQL + RAG), we:
1. Calculate SQL certainty and RAG certainty separately
2. Estimate contribution ratio (how much each contributed to final answer)
3. Detect numerical conflicts between SQL and RAG results
4. Apply weighted average with conflict penalty if needed

**Conflict Handling:**
- **Trust SQL over RAG** for numerical data
- If SQL contribution > 50%: 10% penalty for conflicts
- If RAG contribution > 50%: 20% penalty for conflicts
- No conflict detected: +3% bonus for agreement

**Example Calculation:**
```python
SQL certainty: 95%
RAG certainty: 75%
SQL contribution: 30% (one number in longer answer)
RAG contribution: 70%
No conflict detected

Hybrid certainty = 0.95 * 0.3 + 0.75 * 0.7 + 0.03 = 0.88 (88%)
```

## API Response

### ChatResponse Schema

```json
{
  "answer": "В България има 3597 читалища...",
  "conversation_id": "uuid",
  "intent": "sql",
  "routing_confidence": 0.50,
  "reply_certainty": 0.95,
  "mode": "medium",
  "sql_executed": true,
  "rag_executed": false,
  "metadata": {
    "routing_explanation": "...",
    "sql_query": "SELECT COUNT(*) FROM chitalishta",
    "rag_metadata": {}
  },
  "certainty_breakdown": {
    "method": "sql",
    "sql_certainty": 0.95
  },
  "structured_output": null
}
```

### Certainty Breakdown for SQL

```json
{
  "method": "sql",
  "sql_certainty": 0.95
}
```

### Certainty Breakdown for RAG

```json
{
  "method": "rag",
  "rag_certainty": 0.82,
  "rag_details": {
    "groundedness_score": 0.85,
    "is_grounded": true,
    "missing_info_count": 2,
    "document_count": 5,
    "hallucination_detected": false,
    "avg_relevance_score": 0.78
  }
}
```

### Certainty Breakdown for Hybrid

```json
{
  "method": "hybrid",
  "sql_certainty": 0.95,
  "rag_certainty": 0.75,
  "sql_contribution": 0.3,
  "rag_contribution": 0.7,
  "conflict_detected": false,
  "rag_details": {
    "groundedness_score": 0.80,
    "is_grounded": true,
    "document_count": 4,
    "hallucination_detected": false
  }
}
```

## Database Schema

### chat_logs Table

New column added:
```sql
reply_certainty NUMERIC(3, 2) NULL  -- 0.00 to 1.00
```

Certainty breakdown is stored in `response_metadata` JSONB column under `certainty_breakdown` key.

Example:
```json
{
  "routing_explanation": "...",
  "certainty_breakdown": {
    "method": "sql",
    "sql_certainty": 0.95
  }
}
```

## Usage Examples

### Frontend Display

```javascript
// Display certainty to users with appropriate styling
if (response.reply_certainty >= 0.8) {
  showHighCertaintyBadge();  // Green badge "Висока увереност"
} else if (response.reply_certainty >= 0.5) {
  showModerateCertaintyBadge();  // Yellow badge "Умерена увереност"
} else {
  showLowCertaintyBadge();  // Red badge "Ниска увереност"
}
```

### Monitoring & Alerts

```python
# Alert on low certainty answers
if reply_certainty < 0.3:
    send_alert("Low certainty answer detected", {
        "query": user_message,
        "certainty": reply_certainty,
        "breakdown": certainty_breakdown
    })
```

### Analytics Queries

```sql
-- Find queries with high routing confidence but low reply certainty
SELECT
    user_message,
    intent,
    routing_confidence,
    reply_certainty,
    answer
FROM chat_logs
WHERE routing_confidence > 0.8
  AND reply_certainty < 0.5
ORDER BY created_at DESC
LIMIT 100;

-- Average certainty by intent type
SELECT
    intent,
    AVG(reply_certainty) as avg_reply_certainty,
    AVG(routing_confidence) as avg_routing_confidence,
    COUNT(*) as query_count
FROM chat_logs
WHERE reply_certainty IS NOT NULL
GROUP BY intent
ORDER BY avg_reply_certainty DESC;
```

## Migration

To add the new column to your existing database:

```bash
python scripts/add_reply_certainty_to_chat_logs.py
```

This will:
1. Add `reply_certainty` column (NUMERIC(3, 2))
2. Create index for performance
3. Add column comment

## Configuration

No configuration needed - reply certainty is calculated automatically for all queries.

## Testing

Example test cases:

```python
# Test SQL certainty - simple query
result = pipeline.query("Колко читалища има?")
assert result["reply_certainty"] >= 0.90  # High certainty for simple COUNT

# Test SQL certainty - complex query
result = pipeline.query("Средният брой по региони с JOIN...")
assert result["reply_certainty"] >= 0.70  # Lower certainty for complex queries

# Test RAG certainty - well-grounded answer
result = pipeline.query("Какво е читалище?")
assert result["reply_certainty"] >= 0.75  # Good certainty with high groundedness

# Test hybrid certainty
result = pipeline.query("Колко читалища има и каква е тяхната история?")
assert "sql_contribution" in result["certainty_breakdown"]
assert "rag_contribution" in result["certainty_breakdown"]
```

## Troubleshooting

### Low Reply Certainty for Simple Queries

**Problem:** Simple SQL query has low reply certainty despite correct results.

**Solutions:**
1. Check if SQL execution was successful (`sql_success: true`)
2. Verify result is not empty or unreasonably large
3. Check for SQL validation warnings in logs

### High Reply Certainty for Wrong Answers

**Problem:** System is confident but answer is incorrect.

**Solutions:**
1. For SQL: Review query complexity scoring - may need adjustment
2. For RAG: Check groundedness thresholds - may be too lenient
3. Add more validation rules in `reply_certainty.py`

### Certainty Breakdown Missing

**Problem:** `certainty_breakdown` is null or empty.

**Solutions:**
1. Check logs for `reply_certainty_calculation_failed` errors
2. Verify intent is recognized (SQL, RAG, or HYBRID)
3. Ensure required data is available (sql_result, rag_result)

## Future Enhancements

Potential improvements:
1. **LLM-based self-evaluation** for ambiguous cases
2. **Historical accuracy tracking** to adjust certainty over time
3. **User feedback integration** to calibrate certainty scores
4. **Domain-specific rules** for chitalishta-specific queries
5. **Confidence intervals** instead of single point estimates

## References

- Source code: `app/services/reply_certainty.py`
- Integration: `app/rag/hybrid_pipeline.py`
- Database migration: `scripts/add_reply_certainty_to_chat_logs.py`
- API schema: `app/api/chat_schemas.py`

