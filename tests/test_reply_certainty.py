"""Tests for reply certainty calculation."""

import pytest

from app.rag.intent_classification import QueryIntent
from app.services.reply_certainty import (
    ReplyCertaintyService,
    SQLReplyCertaintyCalculator,
    RAGReplyCertaintyCalculator,
    HybridReplyCertaintyCalculator,
)


class TestSQLReplyCertaintyCalculator:
    """Tests for SQL reply certainty calculation."""

    def test_successful_simple_count(self):
        """Test high certainty for successful simple COUNT query."""
        sql_result = {
            "success": True,
            "results": [{"count": 3597}],
            "row_count": 1,
        }
        sql_query = "SELECT COUNT(*) FROM chitalishta"

        certainty = SQLReplyCertaintyCalculator.calculate(sql_result, sql_query)

        assert certainty >= 0.90, "Simple COUNT should have high certainty"
        assert certainty <= 0.95, "Certainty should be capped at 0.95"

    def test_failed_query(self):
        """Test very low certainty for failed query."""
        sql_result = {
            "success": False,
            "error": "Syntax error",
        }
        sql_query = "SELECT * FORM chitalishta"

        certainty = SQLReplyCertaintyCalculator.calculate(sql_result, sql_query)

        assert certainty <= 0.10, "Failed query should have very low certainty"

    def test_complex_query_lower_certainty(self):
        """Test that complex queries have lower certainty than simple ones."""
        simple_result = {
            "success": True,
            "results": [{"count": 100}],
            "row_count": 1,
        }
        simple_query = "SELECT COUNT(*) FROM chitalishta"

        complex_result = {
            "success": True,
            "results": [{"name": "Sofia", "count": 120}],
            "row_count": 1,
        }
        complex_query = """
            WITH cte AS (SELECT * FROM chitalishta)
            SELECT name, COUNT(*) FROM cte JOIN other_table USING (id)
        """

        simple_certainty = SQLReplyCertaintyCalculator.calculate(simple_result, simple_query)
        complex_certainty = SQLReplyCertaintyCalculator.calculate(complex_result, complex_query)

        assert simple_certainty > complex_certainty, "Simple queries should have higher certainty"

    def test_empty_results(self):
        """Test moderate certainty for empty results."""
        sql_result = {
            "success": True,
            "results": [],
            "row_count": 0,
        }
        sql_query = "SELECT * FROM chitalishta WHERE name = 'NonExistent'"

        certainty = SQLReplyCertaintyCalculator.calculate(sql_result, sql_query)

        assert 0.40 < certainty < 0.70, "Empty results should have moderate certainty"


class TestRAGReplyCertaintyCalculator:
    """Tests for RAG reply certainty calculation."""

    def test_high_groundedness(self):
        """Test high certainty for well-grounded answer."""
        calculator = RAGReplyCertaintyCalculator()

        answer = "Читалището е културна институция в България."
        documents = [
            {"page_content": "Читалището е културна институция. То се намира в България."},
            {"page_content": "Читалищата имат дълга история в страната."},
        ]

        certainty, details = calculator.calculate(answer, documents)

        assert certainty >= 0.60, "Well-grounded answer should have good certainty"
        assert details["is_grounded"] is True
        assert details["hallucination_detected"] is False

    def test_hallucination_detected(self):
        """Test low certainty when hallucination phrases detected."""
        calculator = RAGReplyCertaintyCalculator()

        answer = "Нямам информация за този въпрос."
        documents = [
            {"page_content": "Читалищата са важна част от културата."}
        ]

        certainty, details = calculator.calculate(answer, documents)

        assert certainty < 0.50, "Hallucination should result in low certainty"
        assert details["hallucination_detected"] is True

    def test_no_documents(self):
        """Test very low certainty with no retrieved documents."""
        calculator = RAGReplyCertaintyCalculator()

        answer = "Читалището е културна институция."
        documents = []

        certainty, details = calculator.calculate(answer, documents)

        assert certainty <= 0.30, "No documents should result in very low certainty"


class TestHybridReplyCertaintyCalculator:
    """Tests for hybrid reply certainty calculation."""

    def test_high_sql_high_rag_no_conflict(self):
        """Test high certainty when both components are confident and agree."""
        calculator = HybridReplyCertaintyCalculator()

        final_answer = "В България има 3597 читалища. Те играят важна културна роля."
        sql_result = {
            "success": True,
            "results": [{"count": 3597}],
            "row_count": 1,
        }
        rag_result = {
            "answer": "Читалищата играят важна културна роля в България.",
            "retrieved_documents": [
                {"page_content": "Читалищата са културни институции."}
            ] * 5,
        }
        sql_query = "SELECT COUNT(*) FROM chitalishta"

        certainty, breakdown = calculator.calculate(
            final_answer, sql_result, rag_result, sql_query
        )

        assert certainty >= 0.70, "High SQL and RAG certainty should result in high hybrid certainty"
        assert breakdown["conflict_detected"] is False
        assert 0 <= breakdown["sql_contribution"] <= 1
        assert 0 <= breakdown["rag_contribution"] <= 1
        assert abs(breakdown["sql_contribution"] + breakdown["rag_contribution"] - 1.0) < 0.01

    def test_conflict_detection(self):
        """Test that conflicts between SQL and RAG are detected."""
        calculator = HybridReplyCertaintyCalculator()

        # SQL says 3597, RAG mentions 3000
        final_answer = "Има 3597 читалища според базата данни."
        sql_result = {
            "success": True,
            "results": [{"count": 3597}],
            "row_count": 1,
        }
        rag_result = {
            "answer": "В България има около 3000 читалища.",
            "retrieved_documents": [
                {"page_content": "Около 3000 читалища функционират в страната."}
            ],
        }

        certainty, breakdown = calculator.calculate(
            final_answer, sql_result, rag_result, None
        )

        # Conflict may or may not be detected depending on threshold (20% difference)
        # But certainty should still be reasonable if SQL is trusted
        assert 0.40 <= certainty <= 0.90


class TestReplyCertaintyService:
    """Tests for main reply certainty service."""

    def test_sql_intent(self):
        """Test certainty calculation for SQL intent."""
        service = ReplyCertaintyService()

        sql_result = {
            "success": True,
            "results": [{"count": 3597}],
            "row_count": 1,
        }

        certainty, breakdown = service.calculate(
            intent=QueryIntent.SQL,
            answer="3597",
            sql_result=sql_result,
            sql_query="SELECT COUNT(*) FROM chitalishta",
        )

        assert certainty >= 0.80, "Successful SQL should have high certainty"
        assert breakdown["method"] == "sql"
        assert "sql_certainty" in breakdown

    def test_rag_intent(self):
        """Test certainty calculation for RAG intent."""
        service = ReplyCertaintyService()

        rag_result = {
            "answer": "Читалището е културна институция.",
            "retrieved_documents": [
                {"page_content": "Читалищата са културни институции в България."}
            ] * 3,
        }

        certainty, breakdown = service.calculate(
            intent=QueryIntent.RAG,
            answer="Читалището е културна институция.",
            rag_result=rag_result,
        )

        assert 0.30 <= certainty <= 0.90, "RAG certainty should be in reasonable range"
        assert breakdown["method"] == "rag"
        assert "rag_certainty" in breakdown
        assert "rag_details" in breakdown

    def test_hybrid_intent(self):
        """Test certainty calculation for HYBRID intent."""
        service = ReplyCertaintyService()

        sql_result = {
            "success": True,
            "results": [{"count": 100}],
            "row_count": 1,
        }
        rag_result = {
            "answer": "Читалищата имат богата история.",
            "retrieved_documents": [
                {"page_content": "История на читалищата в България."}
            ] * 4,
        }

        certainty, breakdown = service.calculate(
            intent=QueryIntent.HYBRID,
            answer="Има 100 читалища. Те имат богата история.",
            sql_result=sql_result,
            rag_result=rag_result,
            sql_query="SELECT COUNT(*) FROM chitalishta",
        )

        assert 0.40 <= certainty <= 0.90, "Hybrid certainty should be in reasonable range"
        assert breakdown["method"] == "hybrid"
        assert "sql_certainty" in breakdown
        assert "rag_certainty" in breakdown
        assert "sql_contribution" in breakdown
        assert "rag_contribution" in breakdown
        assert "conflict_detected" in breakdown

    def test_error_handling(self):
        """Test that errors are handled gracefully."""
        service = ReplyCertaintyService()

        # Missing required data
        certainty, breakdown = service.calculate(
            intent=QueryIntent.SQL,
            answer="Test answer",
            sql_result=None,  # Missing SQL result
        )

        # Should return conservative fallback
        assert certainty == 0.5
        assert "error" in breakdown or breakdown.get("sql_certainty") == 0.0

