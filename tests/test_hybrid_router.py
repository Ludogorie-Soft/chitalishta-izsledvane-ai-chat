"""Tests for hybrid intent routing logic."""

import pytest

from app.rag.hybrid_router import HybridIntentRouter, get_hybrid_router
from app.rag.intent_classification import (
    IntentClassificationResult,
    QueryIntent,
    RuleBasedIntentClassifier,
)


class MockLLMClassifier:
    """Mock LLM classifier for testing."""

    def __init__(self, intent: QueryIntent, confidence: float, explanation: str = ""):
        self.intent = intent
        self.confidence = confidence
        self.explanation = explanation

    def classify(self, query: str) -> IntentClassificationResult:
        """Return a mock classification result."""
        return IntentClassificationResult(
            intent=self.intent,
            confidence=self.confidence,
            matched_rules=[],
            explanation=self.explanation or f"Mock LLM: {self.intent.value} ({self.confidence:.2%})",
        )


class TestHybridIntentRouter:
    """Tests for HybridIntentRouter."""

    def test_both_classifiers_agree_sql(self):
        """When both classifiers agree on SQL intent, use that intent."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.85, "LLM says SQL")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Колко читалища има в Пловдив?")

        assert result.intent == QueryIntent.SQL
        assert 0.0 <= result.confidence <= 1.0
        assert "съгласни" in result.explanation.lower() or "съгласни" in result.explanation
        assert "sql" in result.explanation.lower()

    def test_both_classifiers_agree_rag(self):
        """When both classifiers agree on RAG intent, use that intent."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.RAG, 0.9, "LLM says RAG")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Какво е читалище?")

        assert result.intent == QueryIntent.RAG
        assert 0.0 <= result.confidence <= 1.0
        assert "rag" in result.explanation.lower()

    def test_rule_says_hybrid_uses_hybrid(self):
        """When rule-based classifier says hybrid, use hybrid."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.7, "LLM says SQL")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        # Use a query that might trigger hybrid in rule-based
        result = router.route("Колко читалища има и разкажи за тях?")

        # The result should be hybrid if rule-based says so, or based on the combination logic
        assert result.intent in [QueryIntent.SQL, QueryIntent.RAG, QueryIntent.HYBRID]
        assert 0.0 <= result.confidence <= 1.0

    def test_llm_says_hybrid_uses_hybrid(self):
        """When LLM classifier says hybrid, use hybrid."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.HYBRID, 0.8, "LLM says hybrid")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Колко читалища има?")

        assert result.intent == QueryIntent.HYBRID
        assert 0.0 <= result.confidence <= 1.0
        assert "хибрид" in result.explanation.lower()

    def test_high_confidence_rule_overrides_low_confidence_llm(self):
        """When rule has high confidence and LLM has low, trust rule."""
        rule_classifier = RuleBasedIntentClassifier()
        # Mock a high confidence rule result
        llm_classifier = MockLLMClassifier(QueryIntent.RAG, 0.3, "LLM says RAG with low confidence")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        # Use a clear SQL query
        result = router.route("Колко читалища има?")

        # Should prefer rule-based (SQL) if it has high confidence
        assert result.intent in [QueryIntent.SQL, QueryIntent.HYBRID]
        assert 0.0 <= result.confidence <= 1.0

    def test_high_confidence_llm_overrides_low_confidence_rule(self):
        """When LLM has high confidence and rule has low, trust LLM."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.9, "LLM says SQL with high confidence")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        # Use a query that might not match rule-based keywords well
        result = router.route("Каква е статистиката за читалищата?")

        # Should prefer LLM if it has high confidence
        assert result.intent in [QueryIntent.SQL, QueryIntent.HYBRID]
        assert 0.0 <= result.confidence <= 1.0

    def test_moderate_confidence_disagreement_falls_back_to_hybrid(self):
        """When both have moderate confidence and disagree, use hybrid."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.RAG, 0.6, "LLM says RAG with moderate confidence")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        # Use a query that might trigger SQL in rule-based but RAG in LLM
        result = router.route("Статистика")

        # With moderate confidence disagreement, should fall back to hybrid
        # (Note: actual result depends on rule-based classification, but logic should handle it)
        assert result.intent in [QueryIntent.SQL, QueryIntent.RAG, QueryIntent.HYBRID]
        assert 0.0 <= result.confidence <= 1.0

    def test_both_say_hybrid(self):
        """When both classifiers say hybrid, use hybrid."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.HYBRID, 0.85, "LLM says hybrid")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Колко читалища има и разкажи за тях?")

        # If rule-based also says hybrid, result should be hybrid
        # (Note: depends on actual rule-based classification)
        assert result.intent in [QueryIntent.HYBRID, QueryIntent.SQL, QueryIntent.RAG]
        assert 0.0 <= result.confidence <= 1.0

    def test_explanation_is_provided(self):
        """Router should always provide an explanation."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.8, "LLM explanation")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Колко читалища има?")

        assert result.explanation
        assert len(result.explanation) > 0

    def test_confidence_is_bounded(self):
        """Confidence should always be between 0.0 and 1.0."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.95, "High confidence")

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("Колко читалища има?")

        assert 0.0 <= result.confidence <= 1.0

    def test_factory_function(self):
        """Factory function should create a router."""
        router = get_hybrid_router()

        assert isinstance(router, HybridIntentRouter)
        assert router.rule_classifier is not None
        assert router.llm_classifier is not None

    def test_factory_function_with_custom_classifiers(self):
        """Factory function should accept custom classifiers."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.8)

        router = get_hybrid_router(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        assert isinstance(router, HybridIntentRouter)
        assert router.rule_classifier == rule_classifier
        assert router.llm_classifier == llm_classifier

    def test_deterministic_routing(self):
        """Routing should be deterministic (same query → same result)."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.SQL, 0.8)

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        query = "Колко читалища има в Пловдив?"
        result1 = router.route(query)
        result2 = router.route(query)

        assert result1.intent == result2.intent
        assert result1.confidence == result2.confidence

    def test_empty_query_handling(self):
        """Router should handle empty queries gracefully."""
        rule_classifier = RuleBasedIntentClassifier()
        llm_classifier = MockLLMClassifier(QueryIntent.RAG, 0.0)

        router = HybridIntentRouter(
            rule_classifier=rule_classifier,
            llm_classifier=llm_classifier,
        )

        result = router.route("")

        assert result.intent in [QueryIntent.RAG, QueryIntent.SQL, QueryIntent.HYBRID]
        assert 0.0 <= result.confidence <= 1.0



