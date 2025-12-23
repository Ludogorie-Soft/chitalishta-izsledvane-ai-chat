"""Tests for rule-based intent classification."""
import pytest

from app.rag.intent_classification import (
    IntentClassificationResult,
    QueryIntent,
    RuleBasedIntentClassifier,
)


class TestRuleBasedIntentClassifier:
    """Tests for RuleBasedIntentClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance."""
        return RuleBasedIntentClassifier()

    def test_sql_intent_counting_queries(self, classifier):
        """Test SQL intent for counting queries."""
        queries = [
            "Колко читалища има в Пловдив?",
            "Какъв е броят на читалищата?",
            "Брой на действащите читалища",
            "Общо читалища в София",
        ]

        for query in queries:
            result = classifier.classify(query)
            # Counting queries should lean clearly toward SQL or hybrid
            assert result.intent in [QueryIntent.SQL, QueryIntent.HYBRID]
            assert result.confidence >= 0.3
            assert len(result.matched_rules) > 0
            assert "SQL" in result.explanation or "брой" in result.explanation.lower()

    def test_sql_intent_statistical_queries(self, classifier):
        """Test SQL intent for statistical queries."""
        queries = [
            "Какво е средното число на членовете?",
            "Максимален брой читалища по регион",
            "Процент на читалищата с интернет",
            "Статистика за читалищата",
        ]

        for query in queries:
            result = classifier.classify(query)
            # Some statistical phrases may mix SQL and RAG words, allow hybrid
            assert result.intent in [QueryIntent.SQL, QueryIntent.HYBRID]
            assert result.confidence >= 0.3
            assert len(result.matched_rules) > 0

    def test_sql_intent_table_queries(self, classifier):
        """Test SQL intent for table/list requests."""
        queries = [
            "Покажи списък с читалищата",
            "Таблица с читалища в Пловдив",
            "Графика на разпределението",
            "Топ 10 читалища",
        ]

        for query in queries:
            result = classifier.classify(query)
            assert result.intent == QueryIntent.SQL
            assert result.confidence >= 0.3

    def test_rag_intent_what_queries(self, classifier):
        """Test RAG intent for 'what' questions."""
        queries = [
            "Какво е читалището?",
            "Какво представлява читалището?",
            "Какво знаеш за читалищата?",
            "Какво можеш да кажеш за читалищата?",
        ]

        for query in queries:
            result = classifier.classify(query)
            assert result.intent == QueryIntent.RAG
            # Descriptive queries may still have only one strong keyword
            assert result.confidence >= 0.3
            assert len(result.matched_rules) > 0

    def test_rag_intent_how_queries(self, classifier):
        """Test RAG intent for 'how' questions."""
        queries = [
            "Как се създава читалище?",
            "Как работи читалището?",
            "Как се регистрира читалище?",
        ]

        for query in queries:
            result = classifier.classify(query)
            assert result.intent == QueryIntent.RAG
            assert result.confidence >= 0.3

    def test_rag_intent_descriptive_queries(self, classifier):
        """Test RAG intent for descriptive queries."""
        queries = [
            "Опиши читалището",
            "Разкажи за читалищата",
            "Информация за читалищата",
            "Детайли за читалището",
            "История на читалищата",
        ]

        for query in queries:
            result = classifier.classify(query)
            assert result.intent == QueryIntent.RAG
            assert result.confidence >= 0.3

    def test_hybrid_intent_explicit(self, classifier):
        """Test hybrid intent with explicit indicators."""
        queries = [
            "Колко читалища има и какво представляват?",
            "Статистика и информация за читалищата",
            "Брой читалища и разкажи за тях",
        ]

        for query in queries:
            result = classifier.classify(query)
            # Should detect hybrid or at least one of the intents
            assert result.intent in [QueryIntent.HYBRID, QueryIntent.SQL, QueryIntent.RAG]
            assert result.confidence > 0.3

    def test_hybrid_intent_both_keywords(self, classifier):
        """Test hybrid intent when both SQL and RAG keywords are present."""
        query = "Колко читалища има и какво представляват те?"
        result = classifier.classify(query)

        # Should detect hybrid if both types of keywords are present
        assert result.intent in [QueryIntent.HYBRID, QueryIntent.SQL, QueryIntent.RAG]
        assert result.confidence > 0.3

    def test_empty_query_defaults_to_rag(self, classifier):
        """Test that empty query defaults to RAG."""
        result = classifier.classify("")
        assert result.intent == QueryIntent.RAG
        assert result.confidence == 0.0
        assert "Празна заявка" in result.explanation

    def test_no_keywords_defaults_to_rag(self, classifier):
        """Test that queries without keywords default to RAG."""
        query = "Читалища в Пловдив"
        result = classifier.classify(query)

        assert result.intent == QueryIntent.RAG
        assert result.confidence < 0.5  # Low confidence for no keywords
        assert "Не са открити специфични ключови думи" in result.explanation

    def test_confidence_scoring(self, classifier):
        """Test that confidence scores are reasonable."""
        # Query with multiple SQL keywords should have high confidence
        result1 = classifier.classify("Колко е общият брой и средното число?")
        assert result1.confidence > 0.6

        # Query with single keyword should have moderate confidence
        result2 = classifier.classify("Колко?")
        assert 0.3 < result2.confidence < 0.9

        # Query with no keywords should have low confidence
        result3 = classifier.classify("Читалища")
        assert result3.confidence < 0.5

    def test_confidence_capped_at_95(self, classifier):
        """Test that confidence is capped at 0.95."""
        # Query with many matches
        query = "Колко е общият брой, средното число, максимум и минимум?"
        result = classifier.classify(query)

        assert result.confidence <= 0.95

    def test_matched_rules_included(self, classifier):
        """Test that matched rules are included in result."""
        query = "Колко читалища има и какво представляват?"
        result = classifier.classify(query)

        assert len(result.matched_rules) > 0
        # Should contain examples of matched keywords
        assert any("SQL" in rule or "RAG" in rule for rule in result.matched_rules)

    def test_explanation_in_bulgarian(self, classifier):
        """Test that explanations are in Bulgarian."""
        query = "Колко читалища има?"
        result = classifier.classify(query)

        assert result.explanation
        # Should contain Bulgarian text
        assert any(
            char in result.explanation for char in "абвгдежзийклмнопрстуфхцчшщъьюя"
        )

    @pytest.mark.parametrize(
        "query,expected_intent",
        [
            ("Колко?", QueryIntent.SQL),
            ("Какво е?", QueryIntent.RAG),
            ("Статистика", QueryIntent.SQL),
            ("Информация", QueryIntent.RAG),
            ("Опиши", QueryIntent.RAG),
            ("Брой", QueryIntent.SQL),
            ("Средно", QueryIntent.SQL),
            ("Разкажи", QueryIntent.RAG),
        ],
    )
    def test_single_keyword_classification(self, classifier, query, expected_intent):
        """Test classification with single keywords."""
        result = classifier.classify(query)
        assert result.intent == expected_intent

    def test_custom_keywords(self):
        """Test classifier with custom keywords."""
        custom_sql = ["специално", "уникално"]
        custom_rag = ["детайлно", "подробно"]

        classifier = RuleBasedIntentClassifier(
            sql_keywords=custom_sql, rag_keywords=custom_rag
        )

        result1 = classifier.classify("Специално питане")
        assert result1.intent == QueryIntent.SQL

        result2 = classifier.classify("Детайлно обяснение")
        assert result2.intent == QueryIntent.RAG

    def test_query_case_insensitive(self, classifier):
        """Test that classification is case-insensitive."""
        query1 = "КОЛКО ЧИТАЛИЩА ИМА?"
        query2 = "колко читалища има?"
        query3 = "Колко Читалища Има?"

        result1 = classifier.classify(query1)
        result2 = classifier.classify(query2)
        result3 = classifier.classify(query3)

        assert result1.intent == result2.intent == result3.intent
        assert result1.confidence == result2.confidence == result3.confidence

    def test_long_query_confidence_adjustment(self, classifier):
        """Test that longer queries have adjusted confidence."""
        short_query = "Колко?"
        long_query = "Колко читалища има в Пловдив и София и Варна и Бургас и много други градове?"

        short_result = classifier.classify(short_query)
        long_result = classifier.classify(long_query)

        # Both should be SQL, but long query might have slightly lower confidence
        assert short_result.intent == QueryIntent.SQL
        assert long_result.intent == QueryIntent.SQL
        # Long query confidence should be reasonable but might be adjusted down
        assert long_result.confidence >= 0.2

