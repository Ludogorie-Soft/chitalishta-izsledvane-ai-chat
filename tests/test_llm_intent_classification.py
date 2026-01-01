"""Tests for LLM-based intent classification (LangChain).

These tests are skipped unless LangChain + LLM provider (OpenAI or Hugging Face) are properly configured.
"""

import os

import pytest

pytest.importorskip("langchain_core")

from app.core.config import settings
from app.rag.intent_classification import QueryIntent
from app.rag.llm_intent_classification import (  # noqa: E402
    LLMIntentClassifier,
    get_default_llm,
    get_llm_intent_classifier,
)

# Check which provider is configured
LLM_PROVIDER = os.getenv("LLM_PROVIDER", getattr(settings, "llm_provider", "openai")).lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY".lower())

# Skip tests if provider is not configured
if LLM_PROVIDER == "openai":
    if not OPENAI_API_KEY:
        pytest.skip(
            "OPENAI_API_KEY is not set - skipping LLM intent classification tests.",
            allow_module_level=True,
        )
    pytest.importorskip("langchain_openai")
elif LLM_PROVIDER == "tgi":
    pytest.skip(
        "TGI provider tests not yet implemented - skipping tests.",
        allow_module_level=True,
    )
else:
    pytest.skip(
        f"Unknown LLM provider: {LLM_PROVIDER}. " "Set LLM_PROVIDER to 'openai' or 'tgi'.",
        allow_module_level=True,
    )


class TestLLMIntentClassification:
    """Integration-like tests for LLMIntentClassifier using configured LLM provider via LangChain."""

    @pytest.fixture(scope="session")
    def llm_classifier(self) -> LLMIntentClassifier:
        """Create an LLMIntentClassifier with default LLM."""
        classifier = get_llm_intent_classifier()
        assert isinstance(classifier, LLMIntentClassifier)
        return classifier

    @pytest.mark.parametrize(
        "query,expected_intent",
        [
            ("Колко читалища има в Пловдив?", QueryIntent.SQL),
            ("Какво е читалище и какво представлява?", QueryIntent.RAG),
            ("Колко читалища има и разкажи за тях?", QueryIntent.HYBRID),
        ],
    )
    def test_basic_intent_detection(
        self, llm_classifier: LLMIntentClassifier, query, expected_intent
    ):
        """LLM should roughly classify typical SQL/RAG/hybrid queries correctly."""
        result = llm_classifier.classify(query)

        assert isinstance(result.intent, QueryIntent)
        assert 0.0 <= result.confidence <= 1.0
        assert result.intent in [QueryIntent.SQL, QueryIntent.RAG, QueryIntent.HYBRID]

        # We don't require perfect match, but expect it to lean towards the expected intent
        # for clear examples. If it doesn't, at least ensure confidence is not very high.
        if result.intent != expected_intent:
            assert result.confidence < 0.8

    def test_empty_query_behavior(self, llm_classifier: LLMIntentClassifier):
        """Empty query should mirror rule-based behavior (RAG, 0.0 confidence)."""
        result = llm_classifier.classify("")

        assert result.intent == QueryIntent.RAG
        assert result.confidence == 0.0
        assert "Празна заявка" in result.explanation

    def test_explanation_is_bulgarian(self, llm_classifier: LLMIntentClassifier):
        """Reason field should be Bulgarian text."""
        result = llm_classifier.classify("Какво е читалище?")

        assert result.explanation
        assert any(char in result.explanation for char in "абвгдежзийклмнопрстуфхцчшщъьюя")
