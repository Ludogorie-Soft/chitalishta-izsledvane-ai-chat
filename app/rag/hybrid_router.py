"""Hybrid routing logic that combines rule-based and LLM-based intent classification."""

import logging
from typing import Optional

from app.rag.intent_classification import (
    IntentClassificationResult,
    QueryIntent,
    RuleBasedIntentClassifier,
)
from app.rag.llm_intent_classification import (
    LLMIntentClassifier,
    get_llm_intent_classifier,
)

logger = logging.getLogger(__name__)


class HybridIntentRouter:
    """
    Hybrid router that combines rule-based and LLM-based intent classification.

    This router runs both classifiers and makes a deterministic decision based on
    their combined signals. It provides a safe fallback to hybrid when uncertain.
    """

    def __init__(
        self,
        rule_classifier: Optional[RuleBasedIntentClassifier] = None,
        llm_classifier: Optional[LLMIntentClassifier] = None,
    ):
        """
        Initialize the hybrid router.

        Args:
            rule_classifier: Optional rule-based classifier. If None, creates a default one.
            llm_classifier: Optional LLM-based classifier. If None, creates a default one
                (with fallback to rule-based if LLM is unavailable).
        """
        self.rule_classifier = rule_classifier or RuleBasedIntentClassifier()
        self.llm_classifier = llm_classifier or get_llm_intent_classifier()

    def route(self, query: str) -> IntentClassificationResult:
        """
        Route a query by combining rule-based and LLM-based classification signals.

        The routing logic:
        1. Runs both classifiers
        2. If both agree on intent → use that intent, combine confidences
        3. If they disagree:
           - If one has high confidence (>0.8) and the other has low (<0.5) → trust the high confidence one
           - If both have moderate confidence → use hybrid
           - If one says hybrid → use hybrid
           - Otherwise, use weighted decision based on confidence scores
        4. Safe fallback: if uncertainty is high, default to hybrid

        Args:
            query: User query in Bulgarian.

        Returns:
            IntentClassificationResult with final intent decision and explanation.
        """
        # Run both classifiers
        rule_result = self.rule_classifier.classify(query)
        llm_result = self.llm_classifier.classify(query)

        # Combine signals and make decision
        final_result = self._combine_signals(rule_result, llm_result, query)

        return final_result

    def _combine_signals(
        self,
        rule_result: IntentClassificationResult,
        llm_result: IntentClassificationResult,
        query: str,
    ) -> IntentClassificationResult:
        """
        Combine signals from both classifiers and make final decision.

        Args:
            rule_result: Result from rule-based classifier.
            llm_result: Result from LLM-based classifier.
            query: Original query (for context in explanations).

        Returns:
            Final IntentClassificationResult with combined decision.
        """
        rule_intent = rule_result.intent
        rule_confidence = rule_result.confidence
        llm_intent = llm_result.intent
        llm_confidence = llm_result.confidence

        # Case 1: Both agree on intent
        if rule_intent == llm_intent:
            # Combine confidences (weighted average, slightly favor LLM for ambiguous cases)
            combined_confidence = (rule_confidence * 0.4 + llm_confidence * 0.6)
            # Cap at 0.95 to leave room for uncertainty
            combined_confidence = min(combined_confidence, 0.95)

            explanation = (
                f"И двата класификатора са съгласни за intent '{rule_intent.value}'. "
                f"Rule-based увереност: {rule_confidence:.2%}, "
                f"LLM увереност: {llm_confidence:.2%}. "
                f"Комбинирана увереност: {combined_confidence:.2%}."
            )

            return IntentClassificationResult(
                intent=rule_intent,
                confidence=combined_confidence,
                matched_rules=rule_result.matched_rules,
                explanation=explanation,
            )

        # Case 2: One says hybrid → use hybrid (hybrid is a safe default)
        if rule_intent == QueryIntent.HYBRID or llm_intent == QueryIntent.HYBRID:
            # Use the confidence from the one that said hybrid, or average if both said hybrid
            if rule_intent == QueryIntent.HYBRID and llm_intent == QueryIntent.HYBRID:
                hybrid_confidence = (rule_confidence + llm_confidence) / 2
                explanation = (
                    f"И двата класификатора са идентифицирали хибридна заявка. "
                    f"Rule-based увереност: {rule_confidence:.2%}, "
                    f"LLM увереност: {llm_confidence:.2%}. "
                    f"Комбинирана увереност: {hybrid_confidence:.2%}."
                )
            elif rule_intent == QueryIntent.HYBRID:
                hybrid_confidence = rule_confidence * 0.6 + llm_confidence * 0.4
                explanation = (
                    f"Rule-based класификаторът идентифицира хибридна заявка "
                    f"(увереност: {rule_confidence:.2%}). "
                    f"LLM класификаторът предложи '{llm_intent.value}' "
                    f"(увереност: {llm_confidence:.2%}). "
                    f"Използва се хибриден режим като безопасен избор. "
                    f"Комбинирана увереност: {hybrid_confidence:.2%}."
                )
            else:  # llm_intent == QueryIntent.HYBRID
                hybrid_confidence = rule_confidence * 0.4 + llm_confidence * 0.6
                explanation = (
                    f"LLM класификаторът идентифицира хибридна заявка "
                    f"(увереност: {llm_confidence:.2%}). "
                    f"Rule-based класификаторът предложи '{rule_intent.value}' "
                    f"(увереност: {rule_confidence:.2%}). "
                    f"Използва се хибриден режим като безопасен избор. "
                    f"Комбинирана увереност: {hybrid_confidence:.2%}."
                )

            return IntentClassificationResult(
                intent=QueryIntent.HYBRID,
                confidence=min(hybrid_confidence, 0.9),  # Cap hybrid confidence
                matched_rules=rule_result.matched_rules,
                explanation=explanation,
            )

        # Case 3: High confidence disagreement
        # If one has high confidence (>0.8) and the other has low (<0.5), trust the high one
        high_confidence_threshold = 0.8
        low_confidence_threshold = 0.5

        if rule_confidence > high_confidence_threshold and llm_confidence < low_confidence_threshold:
            explanation = (
                f"Rule-based класификаторът има висока увереност ({rule_confidence:.2%}) "
                f"за '{rule_intent.value}', докато LLM има ниска увереност ({llm_confidence:.2%}) "
                f"за '{llm_intent.value}'. Използва се решението на rule-based класификатора."
            )
            return IntentClassificationResult(
                intent=rule_intent,
                confidence=rule_confidence * 0.9,  # Slightly reduce due to disagreement
                matched_rules=rule_result.matched_rules,
                explanation=explanation,
            )

        if llm_confidence > high_confidence_threshold and rule_confidence < low_confidence_threshold:
            explanation = (
                f"LLM класификаторът има висока увереност ({llm_confidence:.2%}) "
                f"за '{llm_intent.value}', докато rule-based има ниска увереност ({rule_confidence:.2%}) "
                f"за '{rule_intent.value}'. Използва се решението на LLM класификатора."
            )
            return IntentClassificationResult(
                intent=llm_intent,
                confidence=llm_confidence * 0.9,  # Slightly reduce due to disagreement
                matched_rules=rule_result.matched_rules,
                explanation=explanation,
            )

        # Case 4: Moderate confidence disagreement → use hybrid as safe fallback
        if rule_confidence < 0.7 and llm_confidence < 0.7:
            hybrid_confidence = (rule_confidence + llm_confidence) / 2
            explanation = (
                f"И двата класификатора имат умерена увереност и не са съгласни. "
                f"Rule-based: '{rule_intent.value}' ({rule_confidence:.2%}), "
                f"LLM: '{llm_intent.value}' ({llm_confidence:.2%}). "
                f"Използва се хибриден режим като безопасен избор. "
                f"Комбинирана увереност: {hybrid_confidence:.2%}."
            )
            return IntentClassificationResult(
                intent=QueryIntent.HYBRID,
                confidence=min(hybrid_confidence, 0.75),
                matched_rules=rule_result.matched_rules,
                explanation=explanation,
            )

        # Case 5: Weighted decision based on confidence scores
        # Use the intent with higher confidence, but reduce confidence due to disagreement
        if rule_confidence > llm_confidence:
            final_intent = rule_intent
            final_confidence = (rule_confidence * 0.7 + llm_confidence * 0.3) * 0.85  # Penalty for disagreement
            explanation = (
                f"Rule-based класификаторът предложи '{rule_intent.value}' "
                f"с увереност {rule_confidence:.2%}, "
                f"LLM предложи '{llm_intent.value}' с увереност {llm_confidence:.2%}. "
                f"Използва се '{rule_intent.value}' поради по-висока увереност, "
                f"но с намалена увереност поради несъгласие. "
                f"Финална увереност: {final_confidence:.2%}."
            )
        else:
            final_intent = llm_intent
            final_confidence = (llm_confidence * 0.7 + rule_confidence * 0.3) * 0.85  # Penalty for disagreement
            explanation = (
                f"LLM класификаторът предложи '{llm_intent.value}' "
                f"с увереност {llm_confidence:.2%}, "
                f"rule-based предложи '{rule_intent.value}' с увереност {rule_confidence:.2%}. "
                f"Използва се '{llm_intent.value}' поради по-висока увереност, "
                f"но с намалена увереност поради несъгласие. "
                f"Финална увереност: {final_confidence:.2%}."
            )

        return IntentClassificationResult(
            intent=final_intent,
            confidence=min(final_confidence, 0.85),  # Cap confidence when there's disagreement
            matched_rules=rule_result.matched_rules,
            explanation=explanation,
        )


def get_hybrid_router(
    rule_classifier: Optional[RuleBasedIntentClassifier] = None,
    llm_classifier: Optional[LLMIntentClassifier] = None,
) -> HybridIntentRouter:
    """
    Factory function to get a default HybridIntentRouter.

    Args:
        rule_classifier: Optional rule-based classifier. If None, creates a default one.
        llm_classifier: Optional LLM-based classifier. If None, creates a default one.

    Returns:
        HybridIntentRouter instance
    """
    return HybridIntentRouter(
        rule_classifier=rule_classifier,
        llm_classifier=llm_classifier,
    )



