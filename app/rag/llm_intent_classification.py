"""LLM-based intent classification using LangChain structured output."""

import json
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.rag.intent_classification import IntentClassificationResult, QueryIntent

logger = logging.getLogger(__name__)

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.runnables import RunnableLambda, RunnableSerializable
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseChatModel = object  # type: ignore[assignment]
    RunnableLambda = object  # type: ignore[assignment]
    RunnableSerializable = object  # type: ignore[assignment]
    ChatPromptTemplate = object  # type: ignore[assignment]
    ChatOpenAI = None  # type: ignore[assignment]
    _LLM_IMPORT_ERROR = _e
else:
    _LLM_IMPORT_ERROR = None

class LLMIntentSchema(BaseModel):
    """
    Pydantic schema used for LangChain structured output.

    This is what the LLM is instructed to produce.
    """

    intent: QueryIntent = Field(
        description="Detected intent of the query: 'rag', 'sql' or 'hybrid'."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence in the classification between 0.0 and 1.0. "
            "Use higher values when the intent is very clear."
        ),
    )
    reason: str = Field(
        description="Short Bulgarian explanation why this intent was selected."
    )


class LLMIntentClassifier:
    """
    LLM-based intent classifier using LangChain structured output.

    This classifier is intended to handle more ambiguous / complex queries
    than the purely rule-based classifier.
    """

    def __init__(self, llm: BaseChatModel):
        if _LLM_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain LLM packages are required for LLMIntentClassifier.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai"
            ) from _LLM_IMPORT_ERROR

        self.llm = llm
        self.chain: RunnableSerializable = self._build_chain(llm)

    def _build_chain(self, llm: BaseChatModel) -> RunnableSerializable:
        """Build a LangChain runnable with a Bulgarian prompt and structured output."""
        system_prompt = (
            "Ти си класификатор на потребителски заявки за система за данни за читалища.\n"
            "Класифицирай всяка заявка в една от следните категории:\n"
            "1) 'sql' – когато потребителят иска числа, статистики, агрегати, брой, средно, максимум,\n"
            "   минимум, проценти, разпределения, таблици, списъци, \"топ\" класации и др.\n"
            "2) 'rag' – когато потребителят иска описателна текстова информация, обяснения,\n"
            "   история, контекст, \"какво е\", \"как се\", \"защо\", \"разкажи\" и др.\n"
            "3) 'hybrid' – когато заявката ясно комбинира и двете: иска и числа/статистика,\n"
            "   и описателен текст (напр. \"Колко читалища има и разкажи за тях\").\n"
            "\n"
            "Винаги връщай валиден JSON обект със следната структура:\n"
            "{{\n"
            '  "intent": "sql" | "rag" | "hybrid",\n'
            '  "confidence": число между 0.0 и 1.0,\n'
            '  "reason": "кратко обяснение на български (1–2 изречения)"\n'
            "}}\n"
            "\n"
            "Правила за confidence:\n"
            "  * 0.8–1.0, ако си силно уверен\n"
            "  * 0.5–0.8, ако си умерено уверен\n"
            "  * под 0.5, ако заявката е неясна или гранична\n"
            "\n"
            "Бъди стриктен и не измисляй други стойности за intent."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "user",
                    "Класифицирай следната заявка и върни само валиден JSON:\n\n"
                    "Заявка: \"{query}\"\n",
                ),
            ]
        )

        # Try to use structured output if supported (OpenAI)
        # Otherwise, we'll parse JSON from the response
        try:
            structured_llm = llm.with_structured_output(LLMIntentSchema)
            return prompt | structured_llm
        except (AttributeError, NotImplementedError, TypeError):
            # Fallback: parse JSON from text response
            # Use RunnableLambda to properly wrap the parsing function
            return prompt | llm | RunnableLambda(self._parse_json_response)

    def _parse_json_response(self, response) -> LLMIntentSchema:
        """
        Parse JSON from LLM text response.

        This is a fallback for models that don't support structured output natively.
        """
        # Extract text content if it's a message object
        if hasattr(response, "content"):
            text = response.content
        elif isinstance(response, str):
            text = response
        else:
            text = str(response)

        # Try to extract JSON from the response
        # Look for JSON object in the text
        json_match = re.search(r"\{[^{}]*\"intent\"[^{}]*\}", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Try to find any JSON-like structure
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract fields manually
            intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', text)
            confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', text)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', text)

            intent_str = intent_match.group(1) if intent_match else "rag"
            confidence_val = float(confidence_match.group(1)) if confidence_match else 0.5
            reason_str = reason_match.group(1) if reason_match else "Неуспешно парсиране на отговора."

            # Validate intent
            try:
                intent = QueryIntent(intent_str.lower())
            except ValueError:
                intent = QueryIntent.RAG

            return LLMIntentSchema(
                intent=intent,
                confidence=max(0.0, min(1.0, confidence_val)),
                reason=reason_str,
            )

        # Validate and create schema
        intent_str = data.get("intent", "rag").lower()
        try:
            intent = QueryIntent(intent_str)
        except ValueError:
            intent = QueryIntent.RAG

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        reason = data.get("reason", "Няма обяснение предоставено.")

        return LLMIntentSchema(intent=intent, confidence=confidence, reason=reason)

    def classify(self, query: str) -> IntentClassificationResult:
        """
        Classify query intent using the LLM.

        Args:
            query: User query in Bulgarian.

        Returns:
            IntentClassificationResult compatible with the rule-based classifier.
        """
        if not query.strip():
            # For empty queries, mirror rule-based behavior but with explicit reason.
            return IntentClassificationResult(
                intent=QueryIntent.RAG,
                confidence=0.0,
                matched_rules=[],
                explanation="Празна заявка - използва се RAG по подразбиране (LLM класификатор).",
            )

        result: LLMIntentSchema = self.chain.invoke({"query": query})

        # Ensure confidence is within [0.0, 1.0]
        confidence = max(0.0, min(float(result.confidence), 1.0))

        return IntentClassificationResult(
            intent=result.intent,
            confidence=confidence,
            matched_rules=[],
            explanation=result.reason,
        )


def _check_tgi_health(base_url: str, timeout: int = 5) -> bool:
    """
    Check if TGI service is available and healthy.

    Args:
        base_url: Base URL of TGI service (e.g., "http://localhost:8080")
        timeout: Request timeout in seconds

    Returns:
        True if TGI is available, False otherwise
    """
    try:
        import requests

        # Remove /v1 suffix if present for health check
        health_url = base_url.replace("/v1", "").rstrip("/") + "/health"
        response = requests.get(health_url, timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.debug(f"TGI health check failed: {e}")
        return False


def get_default_llm() -> BaseChatModel:
    """
    Create a default LangChain chat model based on settings.

    Supports:
    - OpenAI via langchain-openai
    - TGI (Text Generation Inference) via OpenAI-compatible API (Docker)
    """
    if _LLM_IMPORT_ERROR is not None:
        raise ImportError(
            "LangChain LLM packages are required for get_default_llm.\n"
            "Install them with:\n"
            "  poetry add langchain langchain-openai"
        ) from _LLM_IMPORT_ERROR

    provider = settings.llm_provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI LLM. "
                "Set it in your .env file."
            )
        if ChatOpenAI is None:
            raise ImportError(
                "langchain-openai is required for OpenAI LLM. "
                "Install it with: poetry add langchain-openai"
            )

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            temperature=0.0,
        )

    elif provider == "tgi":
        # TGI (Text Generation Inference) via OpenAI-compatible API
        if ChatOpenAI is None:
            raise ImportError(
                "langchain-openai is required for TGI (uses OpenAI-compatible API). "
                "Install it with: poetry add langchain-openai"
            )

        if not settings.tgi_enabled:
            raise ValueError(
                "TGI is disabled in settings. Set TGI_ENABLED=true to use TGI."
            )

        # Check if TGI is available
        base_url = settings.tgi_base_url.replace("/v1", "").rstrip("/")
        if not _check_tgi_health(base_url, timeout=5):
            logger.warning(
                f"TGI service is not available at {base_url}. "
                "Make sure the TGI Docker container is running: docker-compose up -d tgi"
            )
            raise ConnectionError(
                f"TGI service is not available at {base_url}.\n"
                "Make sure the TGI Docker container is running:\n"
                "  docker-compose up -d tgi\n"
                "Wait for the model to load (first start may take several minutes)."
            )

        # Use ChatOpenAI with TGI's OpenAI-compatible endpoint
        # TGI doesn't require authentication, so we use a dummy API key
        return ChatOpenAI(
            base_url=settings.tgi_base_url,
            api_key="not-needed",  # TGI doesn't require auth
            model=settings.tgi_model_name,
            temperature=0.0,
            timeout=settings.tgi_timeout,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. "
            "Supported providers: 'openai', 'tgi'"
        )


def get_llm_intent_classifier(
    llm: Optional[BaseChatModel] = None, fallback_to_rule_based: bool = True
) -> LLMIntentClassifier:
    """
    Factory function to get a default LLMIntentClassifier.

    If no LLM is provided, a default one is created using configuration.
    If LLM initialization fails and fallback_to_rule_based is True,
    returns a rule-based classifier wrapped to match LLMIntentClassifier interface.

    Args:
        llm: Optional LLM instance. If None, creates one from settings.
        fallback_to_rule_based: If True, falls back to rule-based classifier on error.

    Returns:
        LLMIntentClassifier instance

    Raises:
        ImportError: If LangChain packages are missing
        ValueError: If provider configuration is invalid
        ConnectionError: If TGI is unavailable and fallback is disabled
    """
    try:
        llm = llm or get_default_llm()
        return LLMIntentClassifier(llm=llm)
    except (ConnectionError, ValueError) as e:
        if fallback_to_rule_based:
            logger.warning(
                f"Failed to initialize LLM: {e}. "
                "Falling back to rule-based intent classifier."
            )
            # Return a wrapper that uses rule-based classifier
            from app.rag.intent_classification import RuleBasedIntentClassifier

            rule_classifier = RuleBasedIntentClassifier()

            class FallbackLLMIntentClassifier:
                """
                Wrapper that uses rule-based classifier when LLM is unavailable.

                Implements the same interface as LLMIntentClassifier.
                """

                def classify(self, query: str) -> IntentClassificationResult:
                    """Classify query using rule-based classifier as fallback."""
                    result = rule_classifier.classify(query)
                    # Update explanation to indicate fallback
                    result.explanation = (
                        f"{result.explanation} "
                        "(Използван е rule-based класификатор поради недостъпност на LLM)"
                    )
                    return result

            # Return instance that matches LLMIntentClassifier interface
            return FallbackLLMIntentClassifier()  # type: ignore[return-value]
        else:
            raise


