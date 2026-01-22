"""Service for calculating reply certainty (confidence in answer correctness)."""

import re
from typing import Dict, List, Optional, Tuple

import structlog

from app.rag.intent_classification import QueryIntent
from app.services.evaluation import GroundednessChecker

logger = structlog.get_logger(__name__)


class SQLReplyCertaintyCalculator:
    """Calculate reply certainty for SQL-based answers."""

    @staticmethod
    def calculate(
        sql_result: Optional[Dict],
        sql_query: Optional[str] = None,
    ) -> float:
        """
        Calculate certainty for SQL query results.

        Args:
            sql_result: Result from SQL execution with keys:
                - success: bool
                - results: list of rows
                - row_count: int
                - error: str (if failed)
            sql_query: The SQL query that was executed

        Returns:
            Certainty score between 0.0 and 1.0
        """
        if not sql_result:
            return 0.0

        # Start with base certainty
        certainty = 0.0

        # Factor 1: Execution success (0.40 points)
        if sql_result.get("success", False):
            certainty += 0.40
        else:
            # Failed execution - very low certainty
            return 0.05

        # Factor 2: Query complexity (0.40 points)
        query_complexity_score = SQLReplyCertaintyCalculator._assess_query_complexity(
            sql_query
        )
        certainty += query_complexity_score

        # Factor 3: Result validation (0.15 points)
        result_validation_score = SQLReplyCertaintyCalculator._validate_results(
            sql_result, sql_query
        )
        certainty += result_validation_score

        # Factor 4: Clean execution (0.05 points)
        # If no warnings or sanitization issues
        if sql_result.get("warning") is None:
            certainty += 0.05

        # Cap at 0.95 (never 100% certain)
        return min(0.95, certainty)

    @staticmethod
    def _assess_query_complexity(sql_query: Optional[str]) -> float:
        """
        Assess query complexity and return confidence score.

        Simpler queries = higher confidence.

        Args:
            sql_query: SQL query string

        Returns:
            Score between 0.0 and 0.40
        """
        if not sql_query:
            return 0.20  # Default moderate

        query_lower = sql_query.lower()

        # Simple aggregations (COUNT, SUM, AVG, MIN, MAX) - highest confidence
        simple_aggregations = ["count(*)", "count(", "sum(", "avg(", "min(", "max("]
        if any(agg in query_lower for agg in simple_aggregations):
            # Check if it's truly simple (no joins, subqueries)
            has_join = "join" in query_lower
            has_subquery = "select" in query_lower.replace(
                query_lower.split("select", 1)[0] + "select", "", 1
            )

            if not has_join and not has_subquery:
                return 0.40  # Simple aggregation - high confidence

        # Single table SELECT
        if query_lower.count("from") == 1 and "join" not in query_lower:
            return 0.35

        # Queries with JOINs but no subqueries
        if "join" in query_lower and "(" not in query_lower:
            return 0.25

        # Complex queries (subqueries, multiple joins, CTEs)
        if any(
            keyword in query_lower
            for keyword in ["with ", "union", "intersect", "except"]
        ):
            return 0.15

        # Default for other queries
        return 0.20

    @staticmethod
    def _validate_results(sql_result: Dict, sql_query: Optional[str]) -> float:
        """
        Validate that results are reasonable.

        Args:
            sql_result: SQL execution result
            sql_query: SQL query string

        Returns:
            Score between 0.0 and 0.15
        """
        if not sql_result.get("success"):
            return 0.0

        row_count = sql_result.get("row_count", 0)
        results = sql_result.get("results", [])

        # Check for empty results
        if row_count == 0:
            # Empty result might be correct, but slightly less certain
            return 0.10

        # Check for reasonable result sizes
        if row_count > 10000:
            # Very large result sets might indicate an issue
            return 0.08

        # Check if we have actual data
        if results and len(results) > 0:
            # Check for null/None heavy results (might indicate data issues)
            first_row = results[0] if isinstance(results, list) else None
            if first_row:
                if isinstance(first_row, dict):
                    null_count = sum(1 for v in first_row.values() if v is None)
                    total_fields = len(first_row)
                    if total_fields > 0 and null_count / total_fields > 0.5:
                        return 0.08  # More than 50% nulls

        # Normal, reasonable results
        return 0.15


class RAGReplyCertaintyCalculator:
    """Calculate reply certainty for RAG-based answers."""

    def __init__(self):
        """Initialize RAG certainty calculator."""
        self.groundedness_checker = GroundednessChecker()

    def calculate(
        self,
        answer: str,
        retrieved_documents: Optional[List[Dict]] = None,
        rag_metadata: Optional[Dict] = None,
    ) -> Tuple[float, Dict]:
        """
        Calculate certainty for RAG-generated answers.

        Args:
            answer: Generated answer text
            retrieved_documents: List of retrieved documents
            rag_metadata: Additional RAG metadata

        Returns:
            Tuple of (certainty_score, details_dict)
        """
        if not answer or not retrieved_documents:
            return 0.20, {"reason": "No answer or no retrieved documents"}

        details = {}

        # Factor 1: Groundedness check (0.50 points)
        is_grounded, groundedness_score, missing_info = (
            self.groundedness_checker.check_groundedness(
                answer, retrieved_documents, threshold=0.7
            )
        )
        details["groundedness_score"] = groundedness_score
        details["is_grounded"] = is_grounded
        details["missing_info_count"] = len(missing_info)

        groundedness_certainty = groundedness_score * 0.50

        # Factor 2: Number of retrieved documents (0.20 points)
        doc_count = len(retrieved_documents)
        if doc_count >= 5:
            doc_certainty = 0.20
        elif doc_count >= 3:
            doc_certainty = 0.15
        elif doc_count >= 1:
            doc_certainty = 0.10
        else:
            doc_certainty = 0.0

        details["document_count"] = doc_count

        # Factor 3: No hallucination phrases (0.20 points)
        has_hallucination, detected_phrases = (
            self.groundedness_checker.check_no_hallucination_phrases(answer)
        )
        if has_hallucination:
            hallucination_certainty = 0.0
            details["hallucination_detected"] = True
            details["hallucination_phrases"] = detected_phrases
        else:
            hallucination_certainty = 0.20
            details["hallucination_detected"] = False

        # Factor 4: Document relevance (0.10 points)
        # Check if documents have relevance scores
        relevance_certainty = 0.05  # Default moderate
        if retrieved_documents:
            # Check for relevance scores in metadata
            relevance_scores = []
            for doc in retrieved_documents:
                metadata = doc.get("metadata", {})
                if "relevance_score" in metadata:
                    relevance_scores.append(metadata["relevance_score"])

            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                details["avg_relevance_score"] = avg_relevance
                if avg_relevance > 0.8:
                    relevance_certainty = 0.10
                elif avg_relevance > 0.6:
                    relevance_certainty = 0.07

        # Total certainty
        total_certainty = (
            groundedness_certainty
            + doc_certainty
            + hallucination_certainty
            + relevance_certainty
        )

        # Cap at 0.90 (RAG rarely has 100% certainty)
        total_certainty = min(0.90, total_certainty)

        return total_certainty, details


class HybridReplyCertaintyCalculator:
    """Calculate reply certainty for hybrid queries (SQL + RAG)."""

    def __init__(self):
        """Initialize hybrid certainty calculator."""
        self.sql_calculator = SQLReplyCertaintyCalculator()
        self.rag_calculator = RAGReplyCertaintyCalculator()

    def calculate(
        self,
        final_answer: str,
        sql_result: Optional[Dict] = None,
        rag_result: Optional[Dict] = None,
        sql_query: Optional[str] = None,
    ) -> Tuple[float, Dict]:
        """
        Calculate certainty for hybrid queries.

        Args:
            final_answer: The synthesized final answer
            sql_result: SQL execution result
            rag_result: RAG result with answer and retrieved documents
            sql_query: The SQL query that was executed

        Returns:
            Tuple of (certainty_score, breakdown_dict)
        """
        # Calculate component certainties
        sql_certainty = 0.0
        rag_certainty = 0.0
        rag_details = {}

        if sql_result:
            sql_certainty = self.sql_calculator.calculate(sql_result, sql_query)

        if rag_result:
            retrieved_docs = rag_result.get("retrieved_documents", [])
            rag_answer = rag_result.get("answer", "")
            rag_certainty, rag_details = self.rag_calculator.calculate(
                rag_answer, retrieved_docs, rag_result.get("metadata")
            )

        # Estimate contribution of each component
        sql_contribution = self._estimate_sql_contribution(
            final_answer, sql_result
        )
        rag_contribution = 1.0 - sql_contribution

        # Detect conflicts between SQL and RAG
        conflict_detected = self._detect_conflict(
            final_answer, sql_result, rag_result
        )

        # Calculate base certainty (weighted by contribution)
        base_certainty = (
            sql_certainty * sql_contribution + rag_certainty * rag_contribution
        )

        # Apply conflict penalty, but trust SQL more
        if conflict_detected:
            # If SQL contribution is high, trust it more (smaller penalty)
            if sql_contribution > 0.5:
                penalty = 0.10  # 10% penalty when SQL is dominant
            else:
                penalty = 0.20  # 20% penalty when RAG is dominant
            final_certainty = base_certainty * (1 - penalty)
        else:
            # No conflict, slight bonus for agreement
            final_certainty = min(0.90, base_certainty + 0.03)

        # Build detailed breakdown
        breakdown = {
            "sql_certainty": round(sql_certainty, 3),
            "rag_certainty": round(rag_certainty, 3),
            "sql_contribution": round(sql_contribution, 3),
            "rag_contribution": round(rag_contribution, 3),
            "conflict_detected": conflict_detected,
            "rag_details": rag_details,
        }

        return final_certainty, breakdown

    @staticmethod
    def _estimate_sql_contribution(
        answer: str, sql_result: Optional[Dict]
    ) -> float:
        """
        Estimate how much SQL contributed to the final answer.

        Args:
            answer: Final answer text
            sql_result: SQL execution result

        Returns:
            Contribution ratio between 0.0 and 1.0
        """
        if not sql_result or not sql_result.get("success"):
            return 0.0

        if not answer:
            return 0.0

        # Extract numbers from SQL results
        results = sql_result.get("results", [])
        sql_numbers = set()

        if results:
            for row in results[:10]:  # Check first 10 rows
                if isinstance(row, dict):
                    for value in row.values():
                        if isinstance(value, (int, float)):
                            sql_numbers.add(str(int(value)))
                elif isinstance(row, (list, tuple)):
                    for value in row:
                        if isinstance(value, (int, float)):
                            sql_numbers.add(str(int(value)))

        # Check if SQL numbers appear in the answer
        answer_has_sql_numbers = any(num in answer for num in sql_numbers)

        if not answer_has_sql_numbers:
            return 0.20  # SQL result not prominently featured

        # Estimate based on answer length
        answer_words = len(answer.split())

        if answer_words < 20:
            return 0.70  # Short answer, SQL is dominant
        elif answer_words < 50:
            return 0.50  # Medium answer, balanced
        else:
            return 0.30  # Long answer, RAG is dominant

    @staticmethod
    def _detect_conflict(
        answer: str,
        sql_result: Optional[Dict],
        rag_result: Optional[Dict],
    ) -> bool:
        """
        Detect if there are conflicts between SQL and RAG results.

        Args:
            answer: Final synthesized answer
            sql_result: SQL execution result
            rag_result: RAG result

        Returns:
            True if conflict detected, False otherwise
        """
        if not sql_result or not rag_result:
            return False

        # Extract numbers from SQL results
        sql_numbers = set()
        results = sql_result.get("results", [])

        if results:
            for row in results[:5]:
                if isinstance(row, dict):
                    for value in row.values():
                        if isinstance(value, (int, float)):
                            sql_numbers.add(int(value))
                elif isinstance(row, (list, tuple)):
                    for value in row:
                        if isinstance(value, (int, float)):
                            sql_numbers.add(int(value))

        if not sql_numbers:
            return False

        # Extract numbers from RAG answer
        rag_answer = rag_result.get("answer", "")
        rag_numbers = [int(n) for n in re.findall(r"\b\d{2,}\b", rag_answer)]

        if not rag_numbers:
            return False  # No numbers in RAG, no conflict

        # Check for significant numerical conflicts
        # If RAG mentions a number that's very different from SQL
        for sql_num in sql_numbers:
            for rag_num in rag_numbers:
                # If numbers differ by more than 20% and both are substantial
                if abs(sql_num - rag_num) > max(sql_num, rag_num) * 0.2:
                    if sql_num > 100 or rag_num > 100:  # Only for significant numbers
                        logger.warning(
                            "conflict_detected",
                            sql_number=sql_num,
                            rag_number=rag_num,
                        )
                        return True

        return False


class ReplyCertaintyService:
    """Main service for calculating reply certainty across all query types."""

    def __init__(self):
        """Initialize reply certainty service."""
        self.sql_calculator = SQLReplyCertaintyCalculator()
        self.rag_calculator = RAGReplyCertaintyCalculator()
        self.hybrid_calculator = HybridReplyCertaintyCalculator()

    def calculate(
        self,
        intent: QueryIntent,
        answer: str,
        sql_result: Optional[Dict] = None,
        rag_result: Optional[Dict] = None,
        sql_query: Optional[str] = None,
    ) -> Tuple[float, Optional[Dict]]:
        """
        Calculate reply certainty based on query intent.

        Args:
            intent: Query intent (SQL, RAG, or HYBRID)
            answer: Final answer text
            sql_result: SQL execution result (if applicable)
            rag_result: RAG result with documents (if applicable)
            sql_query: SQL query string (if applicable)

        Returns:
            Tuple of (certainty_score, breakdown_dict)
        """
        try:
            if intent == QueryIntent.SQL:
                certainty = self.sql_calculator.calculate(sql_result, sql_query)
                breakdown = {
                    "method": "sql",
                    "sql_certainty": round(certainty, 3),
                }
                return certainty, breakdown

            elif intent == QueryIntent.RAG:
                retrieved_docs = []
                if rag_result:
                    retrieved_docs = rag_result.get("retrieved_documents", [])

                certainty, details = self.rag_calculator.calculate(
                    answer, retrieved_docs, rag_result.get("metadata") if rag_result else None
                )
                breakdown = {
                    "method": "rag",
                    "rag_certainty": round(certainty, 3),
                    "rag_details": details,
                }
                return certainty, breakdown

            elif intent == QueryIntent.HYBRID:
                certainty, breakdown = self.hybrid_calculator.calculate(
                    answer, sql_result, rag_result, sql_query
                )
                breakdown["method"] = "hybrid"
                return certainty, breakdown

            else:
                # Unknown intent
                logger.warning("unknown_intent", intent=intent)
                return 0.5, {"method": "unknown", "reason": "Unknown intent"}

        except Exception as e:
            logger.error(
                "reply_certainty_calculation_error",
                error=str(e),
                intent=intent,
                exc_info=True,
            )
            # Return conservative certainty on error
            return 0.5, {"method": "error", "reason": str(e)}


def get_reply_certainty_service() -> ReplyCertaintyService:
    """
    Factory function to get reply certainty service.

    Returns:
        ReplyCertaintyService instance
    """
    return ReplyCertaintyService()

