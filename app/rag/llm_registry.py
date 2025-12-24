"""LLM registry for managing and selecting LLM models based on task type."""

import logging
from enum import Enum
from typing import Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_openai import ChatOpenAI
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseChatModel = object  # type: ignore[assignment]
    ChatOpenAI = None  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None

# Try to import Hugging Face support
try:
    from langchain_huggingface import ChatHuggingFace
    _HUGGINGFACE_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.chat_models import ChatHuggingFace
        _HUGGINGFACE_AVAILABLE = True
    except ImportError:
        ChatHuggingFace = None  # type: ignore[assignment]
        _HUGGINGFACE_AVAILABLE = False


class LLMTask(str, Enum):
    """Task types for LLM model selection."""

    CLASSIFICATION = "classification"  # Intent classification, routing
    GENERATION = "generation"  # RAG, SQL agent, answer generation
    SYNTHESIS = "synthesis"  # Combining multiple results


class LLMRegistry:
    """
    Registry for managing LLM models with task-based selection.

    This registry allows different models to be used for different tasks
    (e.g., faster/cheaper model for classification, more powerful model for generation).
    """

    def __init__(
        self,
        default_provider: Optional[str] = None,
        classification_provider: Optional[str] = None,
        generation_provider: Optional[str] = None,
        synthesis_provider: Optional[str] = None,
    ):
        """
        Initialize LLM registry.

        Args:
            default_provider: Default provider for all tasks. If None, uses settings.
            classification_provider: Provider for classification tasks. If None, uses settings or default.
            generation_provider: Provider for generation tasks. If None, uses settings or default.
            synthesis_provider: Provider for synthesis tasks. If None, uses settings or default.
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain LLM packages are required for LLMRegistry.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.default_provider = default_provider or settings.llm_provider.lower()

        # Get task-specific providers from settings if not provided
        if classification_provider is None:
            classification_provider = (
                settings.llm_provider_classification.lower()
                if settings.llm_provider_classification
                else None
            )
        self.classification_provider = classification_provider or self.default_provider

        if generation_provider is None:
            generation_provider = (
                settings.llm_provider_generation.lower()
                if settings.llm_provider_generation
                else None
            )
        self.generation_provider = generation_provider or self.default_provider

        if synthesis_provider is None:
            synthesis_provider = (
                settings.llm_provider_synthesis.lower()
                if settings.llm_provider_synthesis
                else None
            )
        self.synthesis_provider = synthesis_provider or self.default_provider

        # Cache for created LLM instances
        self._llm_cache: Dict[str, BaseChatModel] = {}

    def get_llm(
        self,
        task: LLMTask = LLMTask.GENERATION,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> BaseChatModel:
        """
        Get LLM instance for a specific task.

        Args:
            task: Task type (classification, generation, synthesis)
            provider: Override provider for this call. If None, uses task-specific provider.
            model_name: Override model name. If None, uses default for provider.
            temperature: Override temperature. If None, uses default for task.
            **kwargs: Additional parameters to pass to LLM constructor

        Returns:
            LangChain BaseChatModel instance
        """
        # Determine provider
        if provider is None:
            if task == LLMTask.CLASSIFICATION:
                provider = self.classification_provider
            elif task == LLMTask.SYNTHESIS:
                provider = self.synthesis_provider
            else:  # GENERATION
                provider = self.generation_provider

        # Create cache key
        cache_key = f"{provider}:{task.value}:{model_name or 'default'}:{temperature or 'default'}"

        # Return cached instance if available
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        # Create new LLM instance
        llm = self._create_llm(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            task=task,
            **kwargs,
        )

        # Cache it
        self._llm_cache[cache_key] = llm

        return llm

    def _create_llm(
        self,
        provider: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        task: LLMTask = LLMTask.GENERATION,
        **kwargs,
    ) -> BaseChatModel:
        """
        Create LLM instance for a provider.

        Args:
            provider: LLM provider name
            model_name: Model name override
            temperature: Temperature override
            task: Task type (for default temperature selection)
            **kwargs: Additional parameters

        Returns:
            LangChain BaseChatModel instance
        """
        provider = provider.lower()

        # Default temperature based on task
        if temperature is None:
            if task == LLMTask.CLASSIFICATION:
                temperature = 0.0  # Deterministic for classification
            elif task == LLMTask.SYNTHESIS:
                temperature = 0.3  # Slightly creative for synthesis
            else:  # GENERATION
                temperature = 0.0  # Default to deterministic

        if provider == "openai":
            return self._create_openai_llm(model_name, temperature, **kwargs)
        elif provider == "tgi":
            return self._create_tgi_llm(model_name, temperature, **kwargs)
        elif provider == "huggingface":
            return self._create_huggingface_llm(model_name, temperature, **kwargs)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                "Supported providers: 'openai', 'huggingface', 'tgi'"
            )

    def _create_openai_llm(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> BaseChatModel:
        """Create OpenAI LLM instance."""
        if ChatOpenAI is None:
            raise ImportError(
                "langchain-openai is required for OpenAI LLM. "
                "Install it with: poetry add langchain-openai"
            )

        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI LLM. "
                "Set it in your .env file."
            )

        model = model_name or settings.openai_chat_model

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=model,
            temperature=temperature,
            **kwargs,
        )

    def _create_tgi_llm(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> BaseChatModel:
        """Create TGI (Text Generation Inference) LLM instance."""
        if ChatOpenAI is None:
            raise ImportError(
                "langchain-openai is required for TGI (uses OpenAI-compatible API). "
                "Install it with: poetry add langchain-openai"
            )

        if not settings.tgi_enabled:
            raise ValueError(
                "TGI is disabled in settings. Set TGI_ENABLED=true to use TGI."
            )

        from app.rag.llm_intent_classification import _check_tgi_health

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

        model = model_name or settings.tgi_model_name

        return ChatOpenAI(
            base_url=settings.tgi_base_url,
            api_key="not-needed",  # TGI doesn't require auth
            model=model,
            temperature=temperature,
            timeout=settings.tgi_timeout,
            **kwargs,
        )

    def _create_huggingface_llm(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> BaseChatModel:
        """Create Hugging Face LLM instance."""
        if not _HUGGINGFACE_AVAILABLE or ChatHuggingFace is None:
            raise ImportError(
                "Hugging Face LLM support is required. "
                "Install it with:\n"
                "  poetry add langchain-community\n"
                "\n"
                "Note: langchain-community is already included in your dependencies. "
                "If you see this error, make sure langchain-community is properly installed."
            )

        model = model_name or settings.huggingface_llm_model

        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

            # Load model and tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model)
            hf_model = AutoModelForCausalLM.from_pretrained(model)

            # Create pipeline
            hf_pipeline = pipeline(
                "text-generation",
                model=hf_model,
                tokenizer=tokenizer,
                temperature=temperature,
                max_new_tokens=kwargs.get("max_new_tokens", 512),
            )

            # Create ChatHuggingFace with the pipeline
            return ChatHuggingFace(
                llm=hf_pipeline,
            )
        except ImportError as e:
            raise ImportError(
                f"Missing dependencies for Hugging Face model '{model}'. "
                f"Error: {e}\n"
                "Install required dependencies:\n"
                "  poetry add transformers\n"
                "  # For GPU support (optional, install separately):\n"
                "  # pip install torch"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Failed to initialize Hugging Face model '{model}'. "
                f"Error: {e}\n"
                "Make sure the model name is correct and you have the necessary "
                "dependencies installed.\n"
                "You may need to install additional dependencies:\n"
                "  poetry add transformers\n"
                "  # For GPU support (optional, install separately):\n"
                "  # pip install torch\n"
                "\n"
                "Note: First run will download the model (may take several minutes)."
            ) from e

    def clear_cache(self):
        """Clear the LLM instance cache."""
        self._llm_cache.clear()

    def get_cached_llm_count(self) -> int:
        """Get the number of cached LLM instances."""
        return len(self._llm_cache)


# Global registry instance
_global_registry: Optional[LLMRegistry] = None


def get_llm_registry() -> LLMRegistry:
    """
    Get the global LLM registry instance.

    Returns:
        LLMRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = LLMRegistry()
    return _global_registry


def get_llm_for_task(
    task: LLMTask = LLMTask.GENERATION,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs,
) -> BaseChatModel:
    """
    Convenience function to get LLM for a specific task.

    Args:
        task: Task type (classification, generation, synthesis)
        provider: Override provider
        model_name: Override model name
        temperature: Override temperature
        **kwargs: Additional parameters

    Returns:
        LangChain BaseChatModel instance
    """
    registry = get_llm_registry()
    return registry.get_llm(
        task=task,
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs,
    )


def get_classification_llm(**kwargs) -> BaseChatModel:
    """
    Get LLM optimized for classification tasks.

    Args:
        **kwargs: Additional parameters

    Returns:
        LangChain BaseChatModel instance
    """
    return get_llm_for_task(task=LLMTask.CLASSIFICATION, **kwargs)


def get_generation_llm(**kwargs) -> BaseChatModel:
    """
    Get LLM optimized for generation tasks.

    Args:
        **kwargs: Additional parameters

    Returns:
        LangChain BaseChatModel instance
    """
    return get_llm_for_task(task=LLMTask.GENERATION, **kwargs)


def get_synthesis_llm(**kwargs) -> BaseChatModel:
    """
    Get LLM optimized for synthesis tasks.

    Args:
        **kwargs: Additional parameters

    Returns:
        LangChain BaseChatModel instance
    """
    return get_llm_for_task(task=LLMTask.SYNTHESIS, **kwargs)

