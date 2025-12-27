"""Evaluation service for quality assurance and regression testing."""

import re
from typing import Dict, List, Optional, Tuple

import structlog
from sqlalchemy.orm import Session

from app.db.models import BaselineQuery
from app.rag.intent_classification import QueryIntent

logger = structlog.get_logger(__name__)


class GroundednessChecker:
    """Checks if RAG-generated answers are grounded in retrieved context."""

    @staticmethod
    def check_groundedness(
        answer: str, retrieved_documents: List[Dict], threshold: float = 0.7
    ) -> Tuple[bool, float, List[str]]:
        """
        Check if answer is grounded in retrieved documents.

        Args:
            answer: Generated answer text
            retrieved_documents: List of retrieved document dicts with 'page_content' and 'metadata'
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            Tuple of (is_grounded, confidence_score, missing_info)
        """
        if not answer or not retrieved_documents:
            return False, 0.0, ["No answer or no retrieved documents"]

        # Extract text from retrieved documents
        context_text = " ".join(
            [doc.get("page_content", "") for doc in retrieved_documents]
        )

        if not context_text.strip():
            return False, 0.0, ["Empty context"]

        # Simple keyword-based groundedness check
        # Count how many significant words from answer appear in context
        answer_words = set(
            word.lower()
            for word in re.findall(r"\b\w+\b", answer)
            if len(word) > 3  # Ignore short words
        )
        context_words = set(
            word.lower()
            for word in re.findall(r"\b\w+\b", context_text)
            if len(word) > 3
        )

        if not answer_words:
            return True, 1.0, []  # Empty answer is trivially grounded

        # Calculate overlap
        overlap = answer_words.intersection(context_words)
        overlap_ratio = len(overlap) / len(answer_words) if answer_words else 0.0

        # Find missing information (words in answer but not in context)
        missing_info = list(answer_words - context_words)

        is_grounded = overlap_ratio >= threshold

        return is_grounded, overlap_ratio, missing_info[:10]  # Limit to 10 examples

    @staticmethod
    def check_no_hallucination_phrases(answer: str) -> Tuple[bool, List[str]]:
        """
        Check for common hallucination phrases that indicate no information.

        Args:
            answer: Generated answer text

        Returns:
            Tuple of (has_hallucination_phrase, detected_phrases)
        """
        hallucination_phrases = [
            "нямам информация",
            "нямам данни",
            "не мога да намеря",
            "не мога да отговоря",
            "не знам",
            "не съм сигурен",
            "не мога да кажа",
        ]

        answer_lower = answer.lower()
        detected = [
            phrase for phrase in hallucination_phrases if phrase in answer_lower
        ]

        return len(detected) > 0, detected


class BaselineComparator:
    """Compares actual query results against baseline expectations."""

    @staticmethod
    def compare_intent(
        actual_intent: str, expected_intent: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare actual intent with expected intent.

        Args:
            actual_intent: Actual detected intent (sql/rag/hybrid)
            expected_intent: Expected intent from baseline

        Returns:
            Tuple of (matches, error_message)
        """
        if actual_intent == expected_intent:
            return True, None

        return False, f"Intent mismatch: expected '{expected_intent}', got '{actual_intent}'"

    @staticmethod
    def compare_execution_flags(
        actual_sql_executed: bool,
        actual_rag_executed: bool,
        expected_sql_executed: bool,
        expected_rag_executed: bool,
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare actual execution flags with expected flags.

        Args:
            actual_sql_executed: Whether SQL was actually executed
            actual_rag_executed: Whether RAG was actually executed
            expected_sql_executed: Expected SQL execution flag
            expected_rag_executed: Expected RAG execution flag

        Returns:
            Tuple of (matches, error_message)
        """
        errors = []
        if actual_sql_executed != expected_sql_executed:
            errors.append(
                f"SQL execution mismatch: expected {expected_sql_executed}, got {actual_sql_executed}"
            )
        if actual_rag_executed != expected_rag_executed:
            errors.append(
                f"RAG execution mismatch: expected {expected_rag_executed}, got {actual_rag_executed}"
            )

        if errors:
            return False, "; ".join(errors)

        return True, None

    @staticmethod
    def compare_answer(
        actual_answer: str,
        expected_answer: Optional[str],
        comparison_mode: str = "contains",
    ) -> Tuple[bool, Optional[str], float]:
        """
        Compare actual answer with expected answer.

        Args:
            actual_answer: Actual generated answer
            expected_answer: Expected answer text or pattern
            comparison_mode: 'exact', 'contains', or 'pattern'

        Returns:
            Tuple of (matches, error_message, similarity_score)
        """
        if not expected_answer:
            # No expected answer specified - always pass
            return True, None, 1.0

        if not actual_answer:
            return False, "Actual answer is empty", 0.0

        actual_lower = actual_answer.lower().strip()
        expected_lower = expected_answer.lower().strip()

        if comparison_mode == "exact":
            if actual_lower == expected_lower:
                return True, None, 1.0
            return False, f"Exact match failed", 0.0

        elif comparison_mode == "contains":
            if expected_lower in actual_lower:
                return True, None, 1.0
            # Calculate partial similarity
            similarity = BaselineComparator._calculate_similarity(
                actual_lower, expected_lower
            )
            return False, f"Expected content not found in answer", similarity

        elif comparison_mode == "pattern":
            # Use regex pattern matching
            try:
                pattern = re.compile(expected_lower, re.IGNORECASE)
                if pattern.search(actual_lower):
                    return True, None, 1.0
                return False, f"Pattern not matched", 0.0
            except re.error:
                # Invalid regex - fall back to contains
                return BaselineComparator.compare_answer(
                    actual_answer, expected_answer, "contains"
                )

        return False, f"Unknown comparison mode: {comparison_mode}", 0.0

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Calculate simple word-based similarity between two texts."""
        words1 = set(re.findall(r"\b\w+\b", text1.lower()))
        words2 = set(re.findall(r"\b\w+\b", text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def compare_sql_query(
        actual_sql: Optional[str], expected_sql: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare actual SQL query with expected SQL query.

        Args:
            actual_sql: Actual generated SQL query
            expected_sql: Expected SQL query from baseline

        Returns:
            Tuple of (matches, error_message)
        """
        if not expected_sql:
            # No expected SQL specified - always pass
            return True, None

        if not actual_sql:
            return False, "Expected SQL query but none was executed"

        # Normalize SQL for comparison (remove whitespace differences)
        actual_normalized = re.sub(r"\s+", " ", actual_sql.strip().upper())
        expected_normalized = re.sub(r"\s+", " ", expected_sql.strip().upper())

        if actual_normalized == expected_normalized:
            return True, None

        # Check if expected SQL is contained in actual SQL (for partial matches)
        if expected_normalized in actual_normalized:
            return True, None

        return False, f"SQL query mismatch: expected pattern not found in actual query"


class EvaluationService:
    """Service for evaluating query results against baselines and checking quality."""

    def __init__(self, db: Session):
        """
        Initialize evaluation service.

        Args:
            db: Database session
        """
        self.db = db
        self.groundedness_checker = GroundednessChecker()
        self.baseline_comparator = BaselineComparator()

    def get_active_baselines(self) -> List[BaselineQuery]:
        """Get all active baseline queries."""
        return (
            self.db.query(BaselineQuery)
            .filter(BaselineQuery.is_active == True)
            .order_by(BaselineQuery.created_at.desc())
            .all()
        )

    def evaluate_against_baseline(
        self,
        baseline: BaselineQuery,
        actual_result: Dict,
        retrieved_documents: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Evaluate actual query result against a baseline.

        Args:
            baseline: BaselineQuery instance
            actual_result: Actual query result dict with keys:
                - answer
                - intent
                - sql_executed
                - rag_executed
                - sql_query (optional)
            retrieved_documents: Optional list of retrieved documents for groundedness check

        Returns:
            Evaluation result dict with:
                - passed: bool
                - errors: List[str]
                - warnings: List[str]
                - groundedness_check: Dict (if RAG was executed)
        """
        errors = []
        warnings = []
        passed = True

        # Check intent
        intent_match, intent_error = self.baseline_comparator.compare_intent(
            actual_result.get("intent", ""), baseline.expected_intent
        )
        if not intent_match:
            errors.append(intent_error)
            passed = False

        # Check execution flags
        exec_match, exec_error = self.baseline_comparator.compare_execution_flags(
            actual_result.get("sql_executed", False),
            actual_result.get("rag_executed", False),
            baseline.expected_sql_executed,
            baseline.expected_rag_executed,
        )
        if not exec_match:
            errors.append(exec_error)
            passed = False

        # Check SQL query (if expected)
        if baseline.expected_sql_query:
            sql_match, sql_error = self.baseline_comparator.compare_sql_query(
                actual_result.get("sql_query"), baseline.expected_sql_query
            )
            if not sql_match:
                errors.append(sql_error)
                passed = False

        # Check answer
        comparison_mode = (
            baseline.baseline_metadata.get("comparison_mode", "contains")
            if baseline.baseline_metadata
            else "contains"
        )
        answer_match, answer_error, similarity = (
            self.baseline_comparator.compare_answer(
                actual_result.get("answer", ""),
                baseline.expected_answer,
                comparison_mode,
            )
        )
        if not answer_match:
            if similarity < 0.5:
                errors.append(answer_error)
                passed = False
            else:
                warnings.append(f"{answer_error} (similarity: {similarity:.2%})")

        # Groundedness check (if RAG was executed)
        groundedness_result = None
        if actual_result.get("rag_executed") and retrieved_documents:
            is_grounded, confidence, missing_info = (
                self.groundedness_checker.check_groundedness(
                    actual_result.get("answer", ""), retrieved_documents
                )
            )
            has_hallucination_phrase, detected_phrases = (
                self.groundedness_checker.check_no_hallucination_phrases(
                    actual_result.get("answer", "")
                )
            )

            groundedness_result = {
                "is_grounded": is_grounded,
                "confidence": confidence,
                "missing_info": missing_info,
                "has_hallucination_phrase": has_hallucination_phrase,
                "detected_phrases": detected_phrases,
            }

            if not is_grounded:
                warnings.append(
                    f"Answer may not be fully grounded (confidence: {confidence:.2%})"
                )
            if has_hallucination_phrase:
                warnings.append(
                    f"Answer contains 'no information' phrases: {', '.join(detected_phrases)}"
                )

        return {
            "baseline_id": baseline.id,
            "baseline_query": baseline.query,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "groundedness_check": groundedness_result,
        }

