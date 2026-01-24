# Testing TGI Integration

To test the TGI LLM integration:

1. Start TGI service:
   ```bash
   docker-compose up -d tgi
   ```

2. Wait for model to load (check logs):
   ```bash
   docker-compose logs -f tgi
   ```

3. Verify TGI is healthy:
   ```bash
   curl http://localhost:8080/health
   ```

4. Set environment variable:
   ```bash
   LLM_PROVIDER=tgi
   ```

5. Run LLM intent classification tests:
   ```bash
   poetry run pytest tests/test_llm_intent_classification.py -v
   ```

**Note**: If TGI is unavailable, the system automatically falls back to the rule-based intent classifier.
