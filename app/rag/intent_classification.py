"""Intent classification for query routing."""
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """Query intent types."""

    RAG = "rag"  # Semantic search, text-based questions
    SQL = "sql"  # Numeric, aggregation, statistical queries
    HYBRID = "hybrid"  # Combines both RAG and SQL


class IntentClassificationResult(BaseModel):
    """Result of intent classification."""

    intent: QueryIntent = Field(description="Detected query intent")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    matched_rules: List[str] = Field(
        default_factory=list, description="List of matched keyword rules"
    )
    explanation: str = Field(
        default="", description="Human-readable explanation of the classification"
    )


class RuleBasedIntentClassifier:
    """
    Rule-based intent classifier using Bulgarian keyword matching.

    This classifier uses keyword patterns to determine if a query should be
    handled by RAG (semantic search), SQL (numeric/aggregation), or Hybrid (both).
    """

    # Bulgarian keywords that indicate SQL/numeric queries
    SQL_KEYWORDS: List[str] = [
        # Counting and aggregation
        "колко",
        "брой",
        "броя",
        "броят",
        "общо",
        "общия",
        "общият",
        "сума",
        "сумата",
        "сбор",
        "сбора",
        # Statistical operations
        "средно",
        "средната",
        "средният",
        "средното",
        "среден",
        "максимум",
        "максимално",
        "максималната",
        "минимум",
        "минимално",
        "минималната",
        "процент",
        "процента",
        "проценти",
        "процентите",
        # Distribution and grouping
        "разпределение",
        "разпределението",
        "разпределения",
        "групиране",
        "групиране по",
        "по регион",
        "по град",
        "по статус",
        "по година",
        # List and table requests
        "списък",
        "списъка",
        "списъци",
        "таблица",
        "таблицата",
        "таблици",
        "графика",
        "графиката",
        "графики",
        # Ranking and comparison
        "топ",
        "най-много",
        "най-малко",
        "най-голям",
        "най-голяма",
        "най-голямо",
        "най-малък",
        "най-малка",
        "най-малко",
        "сравнение",
        "сравнение между",
        "сравни",
        # Statistical terms
        "статистика",
        "статистиката",
        "статистики",
        "анализ",
        "анализа",
        "данни",
        "данните",
    ]

    # Bulgarian keywords that indicate RAG/semantic queries
    RAG_KEYWORDS: List[str] = [
        # Question words
        "какво",
        "какво е",
        "какво представлява",
        "как",
        "как се",
        "какво е",
        "защо",
        "защо се",
        "къде",
        "къде се",
        "кога",
        "кога се",
        "кой",
        "коя",
        "кое",
        "кои",
        # Descriptive requests
        "опиши",
        "описвам",
        "описание",
        "описанието",
        "разкажи",
        "разказвам",
        "разказ",
        "разказа",
        # Information requests
        "информация",
        "информацията",
        "информация за",
        "детайли",
        "детайлите",
        "детайли за",
        "подробности",
        "подробностите",
        "подробности за",
        # Contextual questions
        "история",
        "историята",
        "история на",
        "история за",
        "контекст",
        "контекста",
        "контекст за",
        "обяснение",
        "обяснението",
        "обяснение на",
        "обясни",
        # General knowledge
        "какво знаеш",
        "какво знаеш за",
        "разкажи за",
        "разкажи ми за",
        "какво можеш да кажеш",
        "какво можеш да кажеш за",
    ]

    # Keywords that suggest hybrid queries (combining both)
    HYBRID_KEYWORDS: List[str] = [
        "и",
        "също",
        "освен това",
        "допълнително",
        "плюс",
        "както и",
        "включително",
        "заедно с",
    ]

    def __init__(self, sql_keywords: List[str] = None, rag_keywords: List[str] = None):
        """
        Initialize the rule-based classifier.

        Args:
            sql_keywords: Custom SQL keywords. If None, uses default.
            rag_keywords: Custom RAG keywords. If None, uses default.
        """
        self.sql_keywords = sql_keywords or self.SQL_KEYWORDS
        self.rag_keywords = rag_keywords or self.RAG_KEYWORDS

        # Normalize keywords to lowercase for matching
        self.sql_keywords_lower = [kw.lower() for kw in self.sql_keywords]
        self.rag_keywords_lower = [kw.lower() for kw in self.RAG_KEYWORDS]

    def classify(self, query: str) -> IntentClassificationResult:
        """
        Classify query intent based on keyword matching.

        Args:
            query: User query in Bulgarian

        Returns:
            IntentClassificationResult with intent, confidence, and explanation
        """
        query_lower = query.lower().strip()

        if not query_lower:
            # Empty query defaults to RAG with low confidence
            return IntentClassificationResult(
                intent=QueryIntent.RAG,
                confidence=0.0,
                matched_rules=[],
                explanation="Празна заявка - използва се RAG по подразбиране",
            )

        # Count keyword matches
        sql_matches = self._count_matches(query_lower, self.sql_keywords_lower)
        rag_matches = self._count_matches(query_lower, self.rag_keywords_lower)

        # Check for hybrid indicators
        has_hybrid_indicators = any(
            indicator in query_lower for indicator in [kw.lower() for kw in self.HYBRID_KEYWORDS]
        )

        # Compute scores
        sql_score = self._compute_score(sql_matches, len(query_lower.split()))
        rag_score = self._compute_score(rag_matches, len(query_lower.split()))

        # Determine intent
        if has_hybrid_indicators and sql_matches > 0 and rag_matches > 0:
            # Explicit hybrid indicators with both types of keywords
            intent = QueryIntent.HYBRID
            confidence = min(0.9, (sql_score + rag_score) / 2)
            matched_rules = self._get_matched_keywords(query_lower, sql_matches, rag_matches)
            explanation = (
                f"Открити са индикатори за хибридна заявка: "
                f"{sql_matches} SQL ключови думи и {rag_matches} RAG ключови думи"
            )
        elif sql_matches > 0 and sql_score > rag_score:
            # SQL intent
            intent = QueryIntent.SQL
            confidence = sql_score
            matched_rules = self._get_matched_keywords(query_lower, sql_matches, 0)
            explanation = (
                f"Открити са {sql_matches} SQL ключови думи "
                f"(увереност: {confidence:.2%})"
            )
        elif rag_matches > 0 and rag_score > sql_score:
            # RAG intent
            intent = QueryIntent.RAG
            confidence = rag_score
            matched_rules = self._get_matched_keywords(query_lower, 0, rag_matches)
            explanation = (
                f"Открити са {rag_matches} RAG ключови думи "
                f"(увереност: {confidence:.2%})"
            )
        elif sql_matches > 0 and rag_matches == 0:
            # Only SQL keywords
            intent = QueryIntent.SQL
            confidence = sql_score
            matched_rules = self._get_matched_keywords(query_lower, sql_matches, 0)
            explanation = (
                f"Открити са само SQL ключови думи "
                f"(увереност: {confidence:.2%})"
            )
        elif rag_matches > 0 and sql_matches == 0:
            # Only RAG keywords
            intent = QueryIntent.RAG
            confidence = rag_score
            matched_rules = self._get_matched_keywords(query_lower, 0, rag_matches)
            explanation = (
                f"Открити са само RAG ключови думи "
                f"(увереност: {confidence:.2%})"
            )
        elif sql_matches > 0 and rag_matches > 0:
            # Both types found, but no explicit hybrid indicators
            # Default to hybrid if scores are close, otherwise use higher score
            if abs(sql_score - rag_score) < 0.2:
                intent = QueryIntent.HYBRID
                confidence = (sql_score + rag_score) / 2
                explanation = (
                    f"Открити са и SQL ({sql_matches}) и RAG ({rag_matches}) "
                    f"ключови думи с близки резултати - използва се хибриден режим"
                )
            elif sql_score > rag_score:
                intent = QueryIntent.SQL
                confidence = sql_score
                explanation = (
                    f"Открити са и SQL и RAG ключови думи, "
                    f"но SQL има по-висок резултат ({sql_score:.2%})"
                )
            else:
                intent = QueryIntent.RAG
                confidence = rag_score
                explanation = (
                    f"Открити са и SQL и RAG ключови думи, "
                    f"но RAG има по-висок резултат ({rag_score:.2%})"
                )
            matched_rules = self._get_matched_keywords(query_lower, sql_matches, rag_matches)
        else:
            # No keywords matched - default to RAG with low confidence
            intent = QueryIntent.RAG
            confidence = 0.3
            matched_rules = []
            explanation = (
                "Не са открити специфични ключови думи - "
                "използва се RAG по подразбиране с ниска увереност"
            )

        # Cap confidence at 0.95 to leave room for LLM-based classification
        confidence = min(confidence, 0.95)

        return IntentClassificationResult(
            intent=intent,
            confidence=confidence,
            matched_rules=matched_rules,
            explanation=explanation,
        )

    def _count_matches(self, query: str, keywords: List[str]) -> int:
        """
        Count how many keywords match in the query.

        Args:
            query: Lowercase query text
            keywords: List of lowercase keywords to match

        Returns:
            Number of unique keywords that matched
        """
        matched = set()
        for keyword in keywords:
            if keyword in query:
                matched.add(keyword)
        return len(matched)

    def _get_matched_keywords(
        self, query: str, sql_matches: int, rag_matches: int
    ) -> List[str]:
        """
        Get list of matched keywords for explanation.

        Args:
            query: Lowercase query text
            sql_matches: Number of SQL matches
            rag_matches: Number of RAG matches

        Returns:
            List of matched keyword examples
        """
        matched = []
        if sql_matches > 0:
            for keyword in self.sql_keywords_lower:
                if keyword in query:
                    matched.append(f"SQL: {keyword}")
                    if len(matched) >= 3:  # Limit examples
                        break
        if rag_matches > 0:
            for keyword in self.rag_keywords_lower:
                if keyword in query:
                    matched.append(f"RAG: {keyword}")
                    if len(matched) >= 6:  # Limit total examples
                        break
        return matched

    def _compute_score(self, matches: int, query_length: int) -> float:
        """
        Compute confidence score based on matches and query length.

        Args:
            matches: Number of keyword matches
            query_length: Length of query in words

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if matches == 0:
            return 0.0

        # Base score from number of matches
        # More matches = higher confidence
        match_score = min(1.0, matches / 3.0)  # Cap at 3 matches

        # Adjust based on query length
        # Shorter queries with matches are more confident
        # Longer queries might have matches by chance
        if query_length <= 3:
            length_factor = 1.0
        elif query_length <= 6:
            length_factor = 0.9
        elif query_length <= 10:
            length_factor = 0.8
        else:
            length_factor = 0.7

        return match_score * length_factor


def get_intent_classifier() -> RuleBasedIntentClassifier:
    """
    Factory function to get the default intent classifier.

    Returns:
        RuleBasedIntentClassifier instance
    """
    return RuleBasedIntentClassifier()

