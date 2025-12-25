"""Hallucination control modes for LLM responses."""

from enum import Enum
from typing import Dict, Optional

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.prompts import ChatPromptTemplate
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseChatModel = object  # type: ignore[assignment]
    ChatPromptTemplate = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class HallucinationMode(str, Enum):
    """
    Hallucination control modes for LLM responses.

    - LOW_TOLERANCE: Strict mode with low temperature, citation requirements, and grounding enforcement
    - MEDIUM_TOLERANCE: Balanced mode with moderate temperature and some flexibility
    - HIGH_TOLERANCE: Creative mode with higher temperature and more flexibility
    """

    LOW_TOLERANCE = "low"
    MEDIUM_TOLERANCE = "medium"
    HIGH_TOLERANCE = "high"


class HallucinationConfig:
    """Configuration for hallucination control mode."""

    def __init__(
        self,
        mode: HallucinationMode = HallucinationMode.MEDIUM_TOLERANCE,
        temperature: Optional[float] = None,
        enforce_citations: Optional[bool] = None,
        require_grounding: Optional[bool] = None,
    ):
        """
        Initialize hallucination configuration.

        Args:
            mode: Hallucination mode
            temperature: Override temperature (if None, uses mode default)
            enforce_citations: Override citation enforcement (if None, uses mode default)
            require_grounding: Override grounding requirement (if None, uses mode default)
        """
        self.mode = mode

        # Set defaults based on mode
        mode_defaults = self._get_mode_defaults(mode)

        self.temperature = temperature if temperature is not None else mode_defaults["temperature"]
        self.enforce_citations = (
            enforce_citations
            if enforce_citations is not None
            else mode_defaults["enforce_citations"]
        )
        self.require_grounding = (
            require_grounding
            if require_grounding is not None
            else mode_defaults["require_grounding"]
        )

    @staticmethod
    def _get_mode_defaults(mode: HallucinationMode) -> Dict[str, any]:
        """Get default configuration for a mode."""
        defaults = {
            HallucinationMode.LOW_TOLERANCE: {
                "temperature": 0.0,  # Deterministic
                "enforce_citations": True,
                "require_grounding": True,
            },
            HallucinationMode.MEDIUM_TOLERANCE: {
                "temperature": 0.3,  # Slightly creative
                "enforce_citations": False,
                "require_grounding": True,
            },
            HallucinationMode.HIGH_TOLERANCE: {
                "temperature": 0.7,  # More creative
                "enforce_citations": False,
                "require_grounding": False,
            },
        }
        return defaults.get(mode, defaults[HallucinationMode.MEDIUM_TOLERANCE])

    def get_llm_with_config(self, base_llm: BaseChatModel) -> BaseChatModel:
        """
        Get LLM instance configured with hallucination control settings.

        Args:
            base_llm: Base LLM instance to configure

        Returns:
            Configured LLM instance (may be the same instance with updated parameters)
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for HallucinationConfig.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai"
            ) from _LANGCHAIN_IMPORT_ERROR

        # Create a copy with updated temperature
        # Note: Some LLM classes may not support direct temperature modification
        # In that case, we'll need to create a new instance
        try:
            # Try to update temperature if the LLM supports it
            if hasattr(base_llm, "temperature"):
                base_llm.temperature = self.temperature
                return base_llm
            elif hasattr(base_llm, "model_kwargs"):
                # For some LangChain LLMs, temperature is in model_kwargs
                if base_llm.model_kwargs is None:
                    base_llm.model_kwargs = {}
                base_llm.model_kwargs["temperature"] = self.temperature
                return base_llm
            else:
                # If we can't modify, return as-is (temperature will be set via prompt)
                return base_llm
        except Exception:
            # If modification fails, return as-is
            return base_llm


class PromptEnhancer:
    """Enhances prompts based on hallucination mode."""

    @staticmethod
    def enhance_rag_prompt(
        base_prompt: str, config: HallucinationConfig
    ) -> ChatPromptTemplate:
        """
        Enhance RAG prompt with hallucination control instructions.

        Args:
            base_prompt: Base prompt template
            config: Hallucination configuration

        Returns:
            Enhanced prompt template
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for PromptEnhancer.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai"
            ) from _LANGCHAIN_IMPORT_ERROR

        # Add mode-specific instructions
        mode_instructions = PromptEnhancer._get_mode_instructions(config)

        # Combine base prompt with mode instructions
        enhanced_prompt = f"{base_prompt}\n\n{mode_instructions}"

        # Parse the enhanced prompt
        # The base_prompt should already be a template string with {context} and {question}
        # We'll create a new template with the enhanced system message
        system_prompt = enhanced_prompt

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{{question}}"),  # Use double braces for template
            ]
        )

    @staticmethod
    def _get_mode_instructions(config: HallucinationConfig) -> str:
        """Get mode-specific instructions for prompts."""
        if config.mode == HallucinationMode.LOW_TOLERANCE:
            return (
                "СТРОГИ ПРАВИЛА ЗА ТОЧНОСТ:\n"
                "1. Отговаряй СТРОГО на базата на предоставения контекст. НИКОГА не измисляй факти.\n"
                "2. Ако информацията не е в контекста, кажи ясно: 'Нямам информация за това в предоставения контекст.'\n"
                "3. Когато цитираш факти, уточни откъде идват (база данни или анализ).\n"
                "4. Не прави предположения или изводи, които не са директно подкрепени от контекста.\n"
                "5. Ако не си сигурен, кажи честно че нямаш достатъчно информация.\n"
                "6. Бъди максимално точен и конкретен.\n"
            )
        elif config.mode == HallucinationMode.HIGH_TOLERANCE:
            return (
                "ГЪВКАВИ ПРАВИЛА:\n"
                "1. Използвай предоставения контекст като основа, но можеш да правиш разумни изводи.\n"
                "2. Ако контекстът не е достатъчен, можеш да допълниш с общи знания, но уточни когато правиш това.\n"
                "3. Можеш да обясняваш и интерпретираш информацията по-свободно.\n"
                "4. Бъди полезен и информативен, дори когато контекстът е ограничен.\n"
            )
        else:  # MEDIUM_TOLERANCE
            return (
                "БАЛАНСИРАНИ ПРАВИЛА:\n"
                "1. Отговаряй предимно на базата на предоставения контекст.\n"
                "2. Можеш да правиш разумни изводи, но ги базирай на контекста.\n"
                "3. Ако информацията не е в контекста, кажи честно, но можеш да предложиш общи обяснения.\n"
                "4. Бъди точен, но не прекалено стриктен.\n"
            )

    @staticmethod
    def enhance_sql_prompt(
        base_prompt: str, config: HallucinationConfig
    ) -> str:
        """
        Enhance SQL agent prompt with hallucination control instructions.

        Args:
            base_prompt: Base SQL agent prompt
            config: Hallucination configuration

        Returns:
            Enhanced prompt string
        """
        mode_instructions = PromptEnhancer._get_sql_mode_instructions(config)
        return f"{base_prompt}\n\n{mode_instructions}"

    @staticmethod
    def _get_sql_mode_instructions(config: HallucinationConfig) -> str:
        """Get mode-specific instructions for SQL agent."""
        if config.mode == HallucinationMode.LOW_TOLERANCE:
            return (
                "СТРОГИ ПРАВИЛА ЗА SQL:\n"
                "1. Генерирай САМО SQL заявки, които са 100% коректни спрямо схемата.\n"
                "2. Ако не си сигурен в структурата на таблиците, не генерирай заявка.\n"
                "3. Връщай резултатите точно както са в базата данни, без интерпретация.\n"
                "4. Ако заявката не може да бъде изпълнена, върни грешка вместо да опитваш отново.\n"
            )
        elif config.mode == HallucinationMode.HIGH_TOLERANCE:
            return (
                "ГЪВКАВИ ПРАВИЛА ЗА SQL:\n"
                "1. Генерирай SQL заявки, които са логични и полезни.\n"
                "2. Можеш да експериментираш с различни подходи, ако първият не работи.\n"
                "3. Можеш да интерпретираш резултатите и да ги обясняваш.\n"
            )
        else:  # MEDIUM_TOLERANCE
            return (
                "БАЛАНСИРАНИ ПРАВИЛА ЗА SQL:\n"
                "1. Генерирай коректни SQL заявки спрямо схемата.\n"
                "2. Ако има проблем, опитай да го коригираш разумно.\n"
                "3. Връщай резултатите точно, но можеш да ги обясняваш.\n"
            )

    @staticmethod
    def enhance_synthesis_prompt(
        base_prompt: str, config: HallucinationConfig
    ) -> str:
        """
        Enhance synthesis prompt with hallucination control instructions.

        Args:
            base_prompt: Base synthesis prompt
            config: Hallucination configuration

        Returns:
            Enhanced prompt string
        """
        mode_instructions = PromptEnhancer._get_synthesis_mode_instructions(config)
        return f"{base_prompt}\n\n{mode_instructions}"

    @staticmethod
    def _get_synthesis_mode_instructions(config: HallucinationConfig) -> str:
        """Get mode-specific instructions for synthesis."""
        if config.mode == HallucinationMode.LOW_TOLERANCE:
            return (
                "СТРОГИ ПРАВИЛА ЗА СИНТЕЗА:\n"
                "1. Използвай СТРОГО само информацията от SQL резултатите и RAG контекста.\n"
                "2. Не добавяй информация, която не е в предоставените данни.\n"
                "3. Уточнявай източника на всяка част от информацията (SQL или RAG).\n"
                "4. Ако има противоречия, приоритизирай SQL резултатите за фактически данни.\n"
            )
        elif config.mode == HallucinationMode.HIGH_TOLERANCE:
            return (
                "ГЪВКАВИ ПРАВИЛА ЗА СИНТЕЗА:\n"
                "1. Комбинирай SQL и RAG информацията свободно.\n"
                "2. Можеш да правиш изводи и обяснения, дори когато информацията е частична.\n"
                "3. Бъди полезен и информативен.\n"
            )
        else:  # MEDIUM_TOLERANCE
            return (
                "БАЛАНСИРАНИ ПРАВИЛА ЗА СИНТЕЗА:\n"
                "1. Комбинирай SQL и RAG информацията логично.\n"
                "2. Можеш да правиш разумни изводи, но базирай ги на данните.\n"
                "3. Бъди точен, но не прекалено стриктен.\n"
            )


def get_default_hallucination_config(
    mode: Optional[HallucinationMode] = None,
) -> HallucinationConfig:
    """
    Get default hallucination configuration.

    Args:
        mode: Optional mode override. If None, uses MEDIUM_TOLERANCE.

    Returns:
        HallucinationConfig instance
    """
    return HallucinationConfig(mode=mode or HallucinationMode.MEDIUM_TOLERANCE)



